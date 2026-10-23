"""Registration policy, anonymous submissions and owner reviews."""
from contextlib import contextmanager
from uuid import uuid4

from argon2.exceptions import HashingError
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import delete, select, update

from backend.auth.service import AuthDenied, AuthUnavailable, HASHER, RateLimited, USERNAME, aware, utcnow
from backend.models import AuthBootstrap, AuthEvent, AuthSession, AuthUser, RegistrationApplication, RegistrationPolicy
from backend.user_management import UserConflict, UserDenied, UserManagementService, UserMissing


class Signup(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    username: str = Field(min_length=3, max_length=64)
    password: SecretStr = Field(min_length=14, max_length=128)

    @field_validator('username')
    @classmethod
    def username_valid(cls, value):
        value = value.strip().lower()
        if not USERNAME.fullmatch(value): raise ValueError('Invalid username')
        return value


class PolicyInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    enabled: bool
    approval_required: bool
    expected_revision: int = Field(ge=0, le=2147483646)


def policy_json(row):
    return dict(enabled=row.enabled, approval_required=row.approval_required, revision=row.revision)


class RegistrationService:
    def __init__(self, auth):
        self.auth = auth
        self.users = UserManagementService(auth.database)

    def policy(self):
        with self.auth.transaction() as session:
            row = session.get(RegistrationPolicy, 1)
            if row is None: raise AuthUnavailable()
            return policy_json(row)

    def session_valid(self, session, key, actor=None):
        row = session.get(AuthSession, key, with_for_update=True)
        if not self.auth._valid(row) or row.user_id != actor: raise AuthDenied()

    @contextmanager
    def owner(self, actor, key):
        with self.users.transaction(actor, write=True) as session:
            self.session_valid(session, key, actor)
            yield session

    def save_policy(self, actor, key, value):
        with self.owner(actor, key) as session:
            row = session.get(RegistrationPolicy, 1)
            if row is None: raise AuthUnavailable()
            if row.revision != value.expected_revision: raise UserConflict()
            if (row.enabled, row.approval_required) != (value.enabled, value.approval_required):
                if row.revision >= 2147483646: raise UserConflict()
                row.enabled, row.approval_required = value.enabled, value.approval_required
                row.revision += 1
                self.users.event(session, actor, actor, 'registration_policy_updated')
                session.flush()
            return policy_json(row)

    def signup(self, key, value, source):
        # Reuse shared DB buckets and process hashing capacity; never trust forwarded IP.
        self.auth._reserve([(f'register-ip:{source}', 5), ('register-global', 30),
                            (f'register-name:{value.username}', 3)])
        if not self.policy()['enabled']: raise UserDenied()
        if not self.auth._verification_slots.acquire(blocking=False): raise RateLimited()
        try:
            encoded = HASHER.hash(value.password.get_secret_value())
        except HashingError:
            raise AuthUnavailable() from None
        finally:
            self.auth._verification_slots.release()
        with self.auth.transaction() as session:
            locked = session.execute(update(AuthBootstrap).where(AuthBootstrap.id == 1).values(id=1))
            if locked.rowcount != 1: raise AuthUnavailable()
            self.session_valid(session, key)
            policy = session.get(RegistrationPolicy, 1)
            if policy is None: raise AuthUnavailable()
            if not policy.enabled: raise UserDenied()
            existing = session.scalar(select(AuthUser.id).where(AuthUser.username == value.username))
            if not existing:
                user_id = str(uuid4())
                session.add(AuthUser(id=user_id, username=value.username, password_hash=encoded,
                    active=not policy.approval_required, role='viewer', is_admin=False, created_at=utcnow()))
                session.flush()
                if policy.approval_required:
                    session.add(RegistrationApplication(user_id=user_id, pending=True, created_at=utcnow()))
                self.auth._event(session, 'registration_submitted', source, user_id)
            # Same acknowledgement and consumed anonymous context for duplicates.
            session.execute(delete(AuthSession).where(AuthSession.token_hash == key))
            session.flush()
        return {'state': 'submitted'}

    def pending(self, actor, key, limit=20, after=None, state='pending'):
        if state not in ('pending', 'rejected'): raise ValueError('Invalid review state')
        with self.owner(actor, key) as session:
            name = AuthUser.username.collate('C' if session.bind.dialect.name == 'postgresql' else 'BINARY')
            rejected = select(AuthEvent.id).where(AuthEvent.user_id == AuthUser.id,
                AuthEvent.event == 'registration_rejected').exists()
            query = select(AuthUser.id, AuthUser.username).join(RegistrationApplication).where(
                RegistrationApplication.pending.is_(True), rejected if state == 'rejected' else ~rejected)
            if after is not None: query = query.where(name > after)
            rows = session.execute(query.order_by(name).limit(limit+1)).all()
            items = [dict(id=r.id, username=r.username, state=state) for r in rows[:limit]]
            return dict(items=items, next_after_username=items[-1]['username'] if len(rows)>limit else None)

    def rejected(self, session, target):
        return session.scalar(select(AuthEvent.id).where(AuthEvent.user_id == target,
            AuthEvent.event == 'registration_rejected').limit(1)) is not None

    def detail(self, actor, key, target):
        with self.owner(actor, key) as session:
            application = session.get(RegistrationApplication, target)
            row = session.get(AuthUser, target)
            if application is None or row is None: raise UserMissing()
            state = 'rejected' if self.rejected(session, target) else 'pending' if application.pending else 'approved'
            return dict(id=row.id, username=row.username, state=state, created_at=aware(application.created_at).isoformat())

    def approve(self, actor, key, target):
        with self.owner(actor, key) as session:
            application = session.get(RegistrationApplication, target)
            if application is None: raise UserMissing()
            if self.rejected(session, target): raise UserConflict()
            if not application.pending: return {'state': 'approved'}
            row = session.get(AuthUser, target)
            if row is None or row.active or row.role != 'viewer' or row.is_admin: raise UserDenied()
            row.active = True
            application.pending = False
            session.execute(delete(AuthSession).where(AuthSession.user_id == target))
            self.users.event(session, actor, target, 'registration_approved')
            session.flush()
            return {'state': 'approved'}

    def reject(self, actor, key, target):
        # The existing pending flag remains true for every unapproved application.
        # Its durable audit decision distinguishes rejection without a schema change;
        # existing edit/grant/downgrade guards therefore continue to fail closed.
        with self.owner(actor, key) as session:
            application = session.get(RegistrationApplication, target)
            if application is None: raise UserMissing()
            if self.rejected(session, target): return {'state': 'rejected'}
            if not application.pending: raise UserConflict()
            row = session.get(AuthUser, target)
            if row is None or row.active or row.role != 'viewer' or row.is_admin: raise UserDenied()
            session.execute(delete(AuthSession).where(AuthSession.user_id == target))
            self.users.event(session, actor, target, 'registration_rejected')
            session.flush()
            return {'state': 'rejected'}
