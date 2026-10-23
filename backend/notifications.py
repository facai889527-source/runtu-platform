"""Telegram-only, bounded best-effort delivery. Never serialize transport errors."""
from concurrent.futures import Future
from contextlib import contextmanager
import http.client
import json
from queue import Empty, Full, Queue
import re
from threading import Event, Thread

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, update

from backend.auth.policy import permissions_for
from backend.auth.service import AuthDenied, AuthUnavailable
from backend.models import AuthBootstrap, AuthEvent, AuthSession, AuthUser, NotificationPreferences, RegistrationApplication
from backend.user_management import UserConflict

CAPABILITIES = dict(registration=True, account_security=False, tool_outcomes=False, system_errors=False)
TOKEN = re.compile(r'[1-9][0-9]{4,19}:[A-Za-z0-9_-]{30,80}\Z')
CHAT = re.compile(r'-?[1-9][0-9]{0,18}\Z')


class NotificationIncomplete(Exception): pass


class EventPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    registration: bool
    account_security: bool
    tool_outcomes: bool
    system_errors: bool

    @model_validator(mode='after')
    def supported_only(self):
        if self.account_security or self.tool_outcomes or self.system_errors:
            raise ValueError('Unsupported event source')
        return self


class NotificationInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    enabled: bool
    chat_id: str = Field(max_length=21)
    events: EventPreferences
    expected_revision: int = Field(ge=0, le=2147483646)

    @field_validator('chat_id')
    @classmethod
    def validate_chat(cls, value):
        # Numeric IDs only: no usernames, URLs, whitespace or Telegram method paths.
        if value and (not CHAT.fullmatch(value) or abs(int(value)) >= 2**52):
            raise ValueError('Invalid chat ID')
        return value


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
        self.queue = Queue(maxsize=16)
        self.stopped = Event()
        self.worker = None

    @property
    def configured(self):
        secret = self.auth.settings.telegram_bot_token
        return bool(secret and TOKEN.fullmatch(secret.get_secret_value()))

    @contextmanager
    def admin(self, actor, key, *, write=False):
        with self.auth.transaction() as session:
            if write:
                locked = session.execute(update(AuthBootstrap).where(AuthBootstrap.id == 1).values(id=1))
                if locked.rowcount != 1: raise AuthUnavailable()
            row = session.get(AuthSession, key, with_for_update=True)
            user = session.get(AuthUser, actor)
            if (not self.auth._valid(row) or row.user_id != actor or not user or not user.active
                    or 'notifications.manage' not in permissions_for(user.role)):
                raise AuthDenied()
            yield session

    def preferences(self, session):
        row = session.get(NotificationPreferences, 1)
        if row is None: raise AuthUnavailable()
        return row

    def public(self, row):
        return dict(enabled=row.enabled, chat_id=row.chat_id, revision=row.revision,
            token_configured=self.configured, token_source='environment',
            events=dict(registration=row.registration, account_security=False, tool_outcomes=False, system_errors=False),
            supported=CAPABILITIES.copy())

    def read(self, actor, key):
        with self.admin(actor, key) as session: return self.public(self.preferences(session))

    def save(self, actor, key, value):
        with self.admin(actor, key, write=True) as session:
            row = self.preferences(session)
            if row.revision != value.expected_revision: raise UserConflict()
            if value.enabled and (not self.configured or not value.chat_id): raise NotificationIncomplete()
            if (row.enabled, row.chat_id, row.registration) != (value.enabled, value.chat_id, value.events.registration):
                if row.revision >= 2147483646: raise UserConflict()
                row.enabled, row.chat_id, row.registration = value.enabled, value.chat_id, value.events.registration
                row.revision += 1
                self.auth._event(session, 'notifications_updated', 'notification-settings', actor)
                session.flush()
            return self.public(row)

    def start(self):
        self.worker = Thread(target=self._run, daemon=True, name='telegram-delivery')
        self.worker.start()

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

    def registration_committed(self, event_id):
        # Called only after the authoritative registration transaction commits.
        # Queue pressure, absent schema or transport failures never affect signup.
        self._offer(('registration', event_id))

    def test(self, actor, key, revision):
        with self.admin(actor, key) as session:
            row = self.preferences(session)
            if row.revision != revision: raise UserConflict()
            if not row.enabled or not row.chat_id or not self.configured: raise NotificationIncomplete()
        # Global across sessions, administrators and workers: one attempt / 5 min.
        self.auth._reserve([('telegram-test-global', 1)])
        future = Future()
        if not self._offer(('test', actor, key, revision, future)): future.set_result(False)
        return future

    def _deliver(self, row, text):
        if not row.enabled or not row.chat_id or not self.configured: return False
        return self.transport.send(self.auth.settings.telegram_bot_token.get_secret_value(), row.chat_id, text) is True

    def _registration(self, event_id):
        with self.auth.transaction() as session:
            row = self.preferences(session)
            event = session.get(AuthEvent, event_id)
            application = session.get(RegistrationApplication, event.user_id) if event else None
            if (not row.enabled or not row.registration or not self.configured or not row.chat_id
                    or not event or event.event != 'registration_submitted' or not application or not application.pending):
                return False
            # No usernames, IPs, credentials or private account details leave Runtu.
        self.auth._reserve([('telegram-registration-global', 5)])
        return self._deliver(row, 'Runtu：收到新的账户注册申请，请前往用户管理审核。')

    def _test_delivery(self, actor, key, revision):
        with self.admin(actor, key) as session:
            row = self.preferences(session)
            if row.revision != revision: return False
        return self._deliver(row, 'Runtu：Telegram 消息设置测试。')

    def _run(self):
        while not self.stopped.is_set():
            try: item = self.queue.get(timeout=.1)
            except Empty: continue
            success = False
            try:
                success = self._test_delivery(*item[1:-1]) if item[0] == 'test' else self._registration(item[1])
            except Exception:
                # Deliberately no exception/log text: transport paths contain a secret.
                pass
            finally:
                if item[0] == 'test' and not item[-1].done(): item[-1].set_result(success)
                self.queue.task_done()
