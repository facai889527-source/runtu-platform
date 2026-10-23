"""Self-scoped verified Telegram binding and bounded best-effort delivery."""
from concurrent.futures import Future
from contextlib import contextmanager
from datetime import timedelta
import http.client
import json
from queue import Empty, Full, Queue
import re
import secrets
from threading import Event, Thread

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from backend.auth.service import AuthDenied, AuthUnavailable, aware, digest
from backend.models import AuthBootstrap, AuthEvent, AuthSession, AuthUser, AccountNotification, TelegramChallenge, NotificationDelivery, RegistrationApplication
from backend.user_management import UserConflict

TOKEN = re.compile(r'[1-9][0-9]{4,19}:[A-Za-z0-9_-]{30,80}\Z')
PAIR = re.compile(r'[A-Za-z0-9_-]{43}\Z')
PRIVILEGED = ('owner', 'admin')

class NotificationIncomplete(Exception): pass

class EventPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    registration: bool
    account_security: bool
    tool_outcomes: bool
    system_errors: bool

    @model_validator(mode='after')
    def supported_only(self):
        if self.account_security or self.tool_outcomes or self.system_errors: raise ValueError('Unsupported source')
        return self

class NotificationInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    enabled: bool
    events: EventPreferences
    expected_revision: int = Field(ge=0, le=2147483646)

class TestInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_revision: int = Field(ge=0, le=2147483646)

class TelegramTransport:
    def send(self, token, chat_id, text):
        # http.client has no URL/access logger, redirects or environment proxies.
        # Telegram requires the secret in its HTTPS method path. Never enable
        # wire debugging, interpolate exceptions, or return upstream bodies.
        connection = http.client.HTTPSConnection('api.telegram.org', timeout=2)
        connection.set_debuglevel(0)
        try:
            connection.request('POST', '/bot'+token+'/sendMessage',
                body=json.dumps(dict(chat_id=chat_id, text=text, disable_notification=True)).encode(),
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
            response = connection.getresponse()
            raw = response.read(8193)
            if response.status != 200 or len(raw) > 8192: return False
            data = json.loads(raw)
            message_id = data.get('result', {}).get('message_id')
            return data.get('ok') is True and type(message_id) is int and message_id > 0
        except Exception:
            return False
        finally:
            connection.close()


class NotificationService:
    def __init__(self, auth, transport=None):
        self.auth, self.transport = auth, transport or TelegramTransport()
        self.queue, self.stopped, self.worker = Queue(maxsize=16), Event(), None

    @property
    def configured(self):
        config = self.auth.settings
        return bool(config.telegram_binding_enabled and config.telegram_bot_token
            and TOKEN.fullmatch(config.telegram_bot_token.get_secret_value())
            and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{1,28}[Bb][Oo][Tt]', config.telegram_bot_username)
            and config.telegram_webhook_secret
            and re.fullmatch(r'[A-Za-z0-9_-]{32,256}', config.telegram_webhook_secret.get_secret_value()))

    def lock(self, session):
        if session.execute(update(AuthBootstrap).where(AuthBootstrap.id == 1).values(id=1)).rowcount != 1:
            raise AuthUnavailable()

    def identity(self, session, actor, key):
        context = session.get(AuthSession, key, with_for_update=True)
        user = session.get(AuthUser, actor)
        if not self.auth._valid(context) or context.user_id != actor or not user or not user.active: raise AuthDenied()
        return user

    @contextmanager
    def own(self, actor, key, write=False):
        with self.auth.transaction() as session:
            if write: self.lock(session)
            user = self.identity(session, actor, key)
            yield session, user

    def profile(self, session, actor, create=False):
        row = session.get(AccountNotification, actor)
        if row is None:
            row = AccountNotification(user_id=actor, chat_id=None, bound_at=None, enabled=False,
                registration=False, paused=False, revision=0, changed_at=self.auth.clock())
            if create: session.add(row); session.flush()
        return row

    def change(self, row):
        if row.revision >= 2147483646: raise UserConflict()
        row.revision += 1
        row.changed_at = self.auth.clock()

    def expect(self, row, revision):
        if row.revision != revision: raise UserConflict()

    def public(self, session, user, row):
        challenge = session.get(TelegramChallenge, user.id)
        valid = challenge and aware(challenge.expires_at) > self.auth.clock()
        pairing = dict(state='none', expires_at=None, candidate=None)
        if valid:
            pairing = dict(state='confirm' if challenge.chat_id else 'waiting',
                expires_at=aware(challenge.expires_at).isoformat(),
                candidate='••••'+challenge.chat_id[-4:] if challenge.chat_id else None)
        privileged = user.role in PRIVILEGED
        return dict(enabled=row.enabled, revision=row.revision, available=self.configured,
            bound=bool(row.chat_id and row.bound_at), destination='••••'+row.chat_id[-4:] if row.chat_id else None,
            paused=row.paused, pairing=pairing,
            events=dict(registration=row.registration if privileged else False,
                account_security=False, tool_outcomes=False, system_errors=False),
            supported=dict(registration=privileged, account_security=False, tool_outcomes=False, system_errors=False))

    def read(self, actor, key):
        with self.own(actor, key) as (session, user): return self.public(session, user, self.profile(session, actor))

    def save(self, actor, key, value):
        with self.own(actor, key, True) as (session, user):
            row = self.profile(session, actor, True); self.expect(row, value.expected_revision)
            if value.events.registration and user.role not in PRIVILEGED: raise AuthDenied()
            if value.enabled and (not self.configured or not row.chat_id or not row.bound_at): raise NotificationIncomplete()
            if (row.enabled, row.registration) != (value.enabled, value.events.registration) or row.paused:
                row.enabled, row.registration, row.paused = value.enabled, value.events.registration, False
                self.change(row); self.auth._event(session, 'notifications_updated', 'self-notifications', actor)
                session.flush()
            return self.public(session, user, row)

    def begin(self, actor, key, revision):
        if not self.configured: raise NotificationIncomplete()
        self.auth._reserve([('telegram-pair:'+actor, 5), ('telegram-pair-global', 30)])
        token = secrets.token_urlsafe(32)
        with self.own(actor, key, True) as (session, user):
            row = self.profile(session, actor, True); self.expect(row, revision)
            row.enabled, row.chat_id, row.bound_at, row.paused = False, None, None, False
            self.change(row)
            session.execute(delete(TelegramChallenge).where(TelegramChallenge.user_id == actor))
            expires = self.auth.clock()+timedelta(minutes=5)
            session.add(TelegramChallenge(user_id=actor, token_hash=digest(token), session_hash=key,
                chat_id=None, expires_at=expires))
            self.auth._event(session, 'telegram_pair_started', 'self-notifications', actor)
            session.flush()
            return dict(url='https://t.me/'+self.auth.settings.telegram_bot_username+'?start='+token,
                expires_at=expires.isoformat(), revision=row.revision)

    def callback(self, data):
        # Called only after the route verifies the webhook credential and origin.
        message = data.get('message')
        if not isinstance(message, dict): return
        chat, sender, text = message.get('chat'), message.get('from'), message.get('text')
        if not isinstance(chat, dict) or not isinstance(sender, dict) or chat.get('type') != 'private' or sender.get('is_bot') is not False: return
        chat_id = chat.get('id')
        if type(chat_id) is not int or not 0 < chat_id < 2**52 or sender.get('id') != chat_id or type(sender.get('id')) is not int: return
        if not isinstance(text, str) or not text.startswith('/start ') or not PAIR.fullmatch(text[7:]): return
        with self.auth.transaction() as session:
            self.lock(session)
            challenge = session.scalar(select(TelegramChallenge).where(TelegramChallenge.token_hash == digest(text[7:])))
            if not challenge or aware(challenge.expires_at) <= self.auth.clock(): return
            try: self.identity(session, challenge.user_id, challenge.session_hash)
            except AuthDenied: return
            # Consume the bearer once, but do NOT bind or send until browser confirmation.
            challenge.token_hash, challenge.chat_id = None, str(chat_id)
            session.flush()

    def confirm(self, actor, key, revision):
        if not self.configured: raise NotificationIncomplete()
        try:
            with self.own(actor, key, True) as (session, user):
                row = self.profile(session, actor, True); self.expect(row, revision)
                challenge = session.get(TelegramChallenge, actor)
                if (not challenge or challenge.session_hash != key or not challenge.chat_id
                        or challenge.token_hash is not None or aware(challenge.expires_at) <= self.auth.clock()): raise UserConflict()
                if session.scalar(select(AccountNotification.user_id).where(AccountNotification.chat_id == challenge.chat_id,
                        AccountNotification.user_id != actor)) is not None: raise UserConflict()
                row.chat_id, row.bound_at, row.enabled, row.paused = challenge.chat_id, self.auth.clock(), False, False
                self.change(row); session.delete(challenge)
                self.auth._event(session, 'telegram_bound', 'self-notifications', actor)
                session.flush()
                return self.public(session, user, row)
        except IntegrityError: raise UserConflict() from None

    def unlink(self, actor, key, revision):
        with self.own(actor, key, True) as (session, user):
            row = self.profile(session, actor, True); self.expect(row, revision)
            row.chat_id, row.bound_at, row.enabled, row.registration, row.paused = None, None, False, False, False
            self.change(row)
            session.execute(delete(TelegramChallenge).where(TelegramChallenge.user_id == actor))
            self.auth._event(session, 'telegram_unlinked', 'self-notifications', actor)
            session.flush()
            return self.public(session, user, row)

    def start(self):
        self.worker = Thread(target=self._run, daemon=True, name='telegram-delivery'); self.worker.start()

    def close(self):
        self.stopped.set()
        if self.worker: self.worker.join(timeout=3)
        while True:
            try:
                item = self.queue.get_nowait()
                if item[0] == 'test' and not item[-1].done(): item[-1].set_result(False)
                self.queue.task_done()
            except Empty: break

    def _offer(self, item):
        if self.stopped.is_set() or not self.worker or not self.worker.is_alive(): return False
        try: self.queue.put_nowait(item); return True
        except Full: return False

    def registration_committed(self, event_id): self._offer(('registration', event_id))

    def test(self, actor, key, revision):
        with self.own(actor, key) as (session, _):
            row = self.profile(session, actor); self.expect(row, revision)
            if not self.configured or not row.enabled or not row.chat_id or not row.bound_at: raise NotificationIncomplete()
        self.auth._reserve([('telegram-test:'+actor, 1), ('telegram-test-global', 20)])
        future = Future()
        if not self._offer(('test', actor, key, revision, self.auth.clock(), future)): future.set_result(False)
        return future

    def _deliver(self, actor, revision, text, event_id=None, key=None, queued_at=None):
        if not self.configured: return False
        now = self.auth.clock()
        if queued_at is not None and aware(queued_at)+timedelta(minutes=5) <= now: return False
        # Reserve before the short claim transaction; rate-limit failures are dropped.
        self.auth._reserve([('telegram-send:'+actor, 5), ('telegram-send-global', 100)])
        with self.auth.transaction() as session:
            self.lock(session)
            user = self.identity(session, actor, key) if key else session.get(AuthUser, actor)
            row = session.get(AccountNotification, actor)
            if (not user or not user.active or not row or row.revision != revision or not row.enabled
                    or row.paused or not row.chat_id or not row.bound_at): return False
            if event_id:
                event = session.get(AuthEvent, event_id)
                if (not event or event.event != 'registration_submitted' or user.role not in PRIVILEGED or not row.registration
                        or aware(event.created_at)+timedelta(minutes=5) <= now
                        or aware(row.changed_at) > aware(event.created_at)
                        or session.get(NotificationDelivery, (event_id, actor))): return False
                application = session.get(RegistrationApplication, event.user_id)
                if not application or not application.pending or session.scalar(select(AuthEvent.id).where(
                        AuthEvent.user_id == event.user_id, AuthEvent.event == 'registration_rejected').limit(1)): return False
                session.add(NotificationDelivery(event_id=event_id, user_id=actor, binding_revision=revision, claimed_at=now))
                session.flush()
            chat_id = row.chat_id
        # No network while holding the business mutex or transaction. A request
        # already in flight cannot be recalled by unlink; queued stale revisions drop.
        try: success = self.transport.send(self.auth.settings.telegram_bot_token.get_secret_value(), chat_id, text) is True
        except Exception: success = False
        if not success:
            with self.auth.transaction() as session:
                self.lock(session); row = session.get(AccountNotification, actor)
                if row and row.revision == revision:
                    row.enabled, row.paused = False, True; self.change(row)
        return success

    def _registration(self, event_id):
        # Bounded pages of eligible recipients; expiry and global send quota bound
        # work. Each recipient is rechecked and durably deduplicated before sending.
        after = ''
        while not self.stopped.is_set():
            with self.auth.transaction() as session:
                event = session.get(AuthEvent, event_id)
                if not event or aware(event.created_at)+timedelta(minutes=5) <= self.auth.clock(): return
                rows = session.execute(select(AccountNotification.user_id, AccountNotification.revision)
                    .join(AuthUser).where(AccountNotification.user_id > after, AuthUser.active.is_(True),
                    AuthUser.role.in_(PRIVILEGED), AccountNotification.enabled.is_(True),
                    AccountNotification.registration.is_(True), AccountNotification.chat_id.is_not(None))
                    .order_by(AccountNotification.user_id).limit(20)).all()
            if not rows: return
            for actor, revision in rows:
                try: self._deliver(actor, revision, 'Runtu：收到新的账户注册申请，请前往用户管理审核。', event_id=event_id)
                except Exception: pass
            after = rows[-1].user_id

    def _run(self):
        while not self.stopped.is_set():
            try: item = self.queue.get(timeout=.1)
            except Empty: continue
            success = False
            try:
                if item[0] == 'test':
                    _, actor, key, revision, queued_at, _ = item
                    success = self._deliver(actor, revision, 'Runtu：Telegram 个人消息设置测试。', key=key, queued_at=queued_at)
                else: self._registration(item[1])
            except Exception: pass  # Never log credentials, callback payloads or transport errors.
            finally:
                if item[0] == 'test' and not item[-1].done(): item[-1].set_result(success)
                self.queue.task_done()
