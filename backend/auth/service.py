from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import ipaddress
import hashlib
import hmac
import re
import secrets
import threading
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import SQLAlchemyError

from backend.models import AuthBootstrap, AuthEvent, AuthRateLimit, AuthSession, AuthUser

HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16)
USERNAME = re.compile(r'^[a-z0-9_.-]{3,64}$')


def utcnow():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def csrf_token(token):
    # Standard HMAC, keyed by the random session secret. Never expose the session ID.
    return hmac.new(token.encode('ascii'), b'runtu-csrf-v1', hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class Identity:
    id: str
    username: str
    role: str

    @property
    def is_admin(self):
        # Compatibility response field; the old DB boolean is not an authorization source.
        return self.role in ('owner', 'admin')


class AuthUnavailable(RuntimeError):
    pass


class AuthDenied(RuntimeError):
    pass


class RateLimited(RuntimeError):
    pass


class BootstrapRefused(RuntimeError):
    pass


class AuthService:
    def __init__(self, database, settings, clock=utcnow):
        self.database, self.settings, self.clock = database, settings, clock
        self._dummy_hash = HASHER.hash(secrets.token_urlsafe(32))
        self._verification_slots = threading.BoundedSemaphore(2)

    @contextmanager
    def transaction(self):
        if self.database is None:
            raise AuthUnavailable('Authentication storage unavailable')
        try:
            with self.database.transaction() as session:
                yield session
        except SQLAlchemyError:
            raise AuthUnavailable('Authentication storage unavailable') from None

    def _event(self, session, event, source, user_id=None, source_ip=None):
        event_id = str(uuid4())
        session.add(AuthEvent(id=event_id, event=event, user_id=user_id, source_ip=source_ip,
                              source_hash=digest(source), created_at=self.clock()))
        return event_id

    def _valid(self, row):
        if row is None:
            return False
        now = self.clock()
        idle = self.settings.auth_idle_seconds if row.user_id else 600
        return aware(row.expires_at) > now and aware(row.last_seen_at) + timedelta(seconds=idle) > now

    def _reserve(self, buckets):
        now = self.clock()
        exceeded = False
        with self.transaction() as session:
            # Atomic upsert + conditional increments, shared across workers using this DB.
            if session.bind.dialect.name == 'sqlite':
                from sqlalchemy.dialects.sqlite import insert
            else:
                from sqlalchemy.dialects.postgresql import insert
            for name, limit in buckets:
                key = digest(name)
                session.execute(insert(AuthRateLimit).values(bucket=key, attempts=0,
                    reset_at=now + timedelta(seconds=300)).on_conflict_do_nothing(index_elements=['bucket']))
                session.execute(update(AuthRateLimit).where(AuthRateLimit.bucket == key,
                    AuthRateLimit.reset_at <= now).values(attempts=0, reset_at=now + timedelta(seconds=300)))
                result = session.execute(update(AuthRateLimit).where(AuthRateLimit.bucket == key,
                    AuthRateLimit.attempts < limit).values(attempts=AuthRateLimit.attempts + 1))
                exceeded = exceeded or result.rowcount != 1
        if exceeded:
            raise RateLimited('Too many authentication attempts')

    def csrf_session(self, token, source):
        if token and re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            with self.transaction() as session:
                row = session.get(AuthSession, digest(token))
                if self._valid(row):
                    if row.user_id is None:
                        return token
                    user = session.get(AuthUser, row.user_id)
                    if user and user.active:
                        return token
        self._reserve([(f'csrf:{source}', 30)])
        token = secrets.token_urlsafe(32)
        now = self.clock()
        with self.transaction() as session:
            session.add(AuthSession(token_hash=digest(token), user_id=None, created_at=now,
                                    last_seen_at=now, expires_at=now + timedelta(seconds=600)))
        return token

    def validate_csrf(self, token, supplied):
        if not token or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            raise AuthDenied('Invalid security context')
        if not supplied or not re.fullmatch(r'[0-9a-f]{64}', supplied) or not hmac.compare_digest(csrf_token(token), supplied):
            raise AuthDenied('Invalid security context')
        with self.transaction() as session:
            if not self._valid(session.get(AuthSession, digest(token))):
                raise AuthDenied('Invalid security context')

    def current(self, token):
        # Even anonymous identity checks verify the auth schema; missing migrations fail closed.
        with self.transaction() as session:
            session.execute(select(AuthBootstrap.id).limit(1))
            if not token or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
                return None
            row = session.get(AuthSession, digest(token))
            if not self._valid(row):
                if row:
                    session.delete(row)
                return None
            if not row.user_id:
                return None
            user = session.get(AuthUser, row.user_id)
            if not user or not user.active:
                session.delete(row)
                return None
            row.last_seen_at = self.clock()
            return Identity(user.id, user.username, user.role)

    def login(self, token, username, password, source, source_ip=None):
        username = username.strip().lower()
        self._reserve([(f'login-ip:{source}', 20), (f'login-account:{source}:{username}', 5)])
        with self.transaction() as session:
            user = session.scalar(select(AuthUser).where(AuthUser.username == username))
            encoded = user.password_hash if user else self._dummy_hash
            user_id = user.id if user else None
        if not self._verification_slots.acquire(blocking=False):
            raise RateLimited('Authentication capacity exceeded')
        try:
            try:
                valid = HASHER.verify(encoded, password)
            except (VerificationError, InvalidHashError):
                valid = False
        finally:
            self._verification_slots.release()
        next_token = secrets.token_urlsafe(32)
        identity = None
        with self.transaction() as session:
            user = session.get(AuthUser, user_id, with_for_update=True) if user_id else None
            old = session.get(AuthSession, digest(token))
            if valid and user and user.active and user.password_hash == encoded and self._valid(old):
                removed = session.execute(delete(AuthSession).where(AuthSession.token_hash == digest(token)))
                if removed.rowcount == 1:
                    now = self.clock()
                    previous_id = user.last_login_event_id
                    event_id = self._event(session, 'login_success', source, user.id, source_ip)
                    advanced = session.execute(update(AuthUser).where(AuthUser.id == user.id,
                        AuthUser.last_login_event_id == previous_id).values(last_login_event_id=event_id))
                    if advanced.rowcount != 1:
                        raise AuthUnavailable('Concurrent login; retry')
                    session.add(AuthSession(token_hash=digest(next_token), user_id=user.id, created_at=now,
                        previous_login_event_id=previous_id,
                        last_seen_at=now, expires_at=now + timedelta(seconds=self.settings.auth_session_seconds)))
                    user.last_login_event_id = event_id
                    if HASHER.check_needs_rehash(encoded):
                        user.password_hash = HASHER.hash(password)
                    identity = Identity(user.id, user.username, user.role)
            if identity is None:
                self._event(session, 'login_failed', source, user_id)
        if identity is None:
            raise AuthDenied('Invalid credentials')
        return next_token, identity

    def previous_login(self, token, user_id):
        with self.transaction() as session:
            row = session.get(AuthSession, digest(token)) if token else None
            user = session.get(AuthUser, user_id)
            if not self._valid(row) or row.user_id != user_id or not user or not user.active:
                raise AuthDenied('Authentication required')
            event = session.get(AuthEvent, row.previous_login_event_id) if row.previous_login_event_id else None
            if not event or event.user_id != user_id or event.event != 'login_success':
                return None
            try:
                address = str(ipaddress.ip_address(event.source_ip)) if event.source_ip and '%' not in event.source_ip else None
            except ValueError:
                address = None
            return {'at': aware(event.created_at).astimezone(timezone.utc).isoformat(), 'ip': address}

    def logout(self, token, source):
        with self.transaction() as session:
            row = session.get(AuthSession, digest(token))
            if row:
                self._event(session, 'logout', source, row.user_id)
                session.delete(row)

    def bootstrap(self, username, password):
        username = username.strip().lower()
        if not USERNAME.fullmatch(username) or not 14 <= len(password) <= 128:
            raise BootstrapRefused('Use a 3-64 character username and a 14-128 character password')
        encoded = HASHER.hash(password)
        try:
            with self.transaction() as session:
                if session.get(AuthBootstrap, 1) or session.scalar(select(AuthUser.id).limit(1)):
                    raise BootstrapRefused('Administrator bootstrap already consumed')
                now, user_id = self.clock(), str(uuid4())
                session.add(AuthBootstrap(id=1, created_at=now))
                session.add(AuthUser(id=user_id, username=username, password_hash=encoded,
                    active=True, is_admin=True, role='owner', created_at=now))
                self._event(session, 'bootstrap', 'local-cli', user_id)
        except AuthUnavailable:
            # Includes concurrent singleton/username conflict; no partially created administrator.
            raise BootstrapRefused('Bootstrap unavailable or already consumed') from None
        return user_id

    def cleanup(self):
        now = self.clock()
        with self.transaction() as session:
            sessions = session.execute(delete(AuthSession).where(or_(AuthSession.expires_at <= now,
                (AuthSession.user_id.is_(None)) & (AuthSession.last_seen_at <= now - timedelta(seconds=600)),
                (AuthSession.user_id.is_not(None)) & (AuthSession.last_seen_at <= now - timedelta(seconds=self.settings.auth_idle_seconds)))))
            session.execute(delete(AuthRateLimit).where(AuthRateLimit.reset_at <= now))
            return sessions.rowcount
