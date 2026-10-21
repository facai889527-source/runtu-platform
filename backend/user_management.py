"""Owner-scoped identity administration; no registration or password reset."""
from contextlib import contextmanager
from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator
from argon2.exceptions import HashingError
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.auth.policy import permissions_for
from backend.auth.service import HASHER, USERNAME, AuthUnavailable, aware, utcnow
from backend.models import AuthBootstrap, AuthEvent, AuthSession, AuthUser
from backend.auth.service import digest

Role = Literal['owner', 'admin', 'viewer']


class UserDenied(Exception): pass
class UserConflict(Exception): pass
class UserMissing(Exception): pass


class UserPublic(BaseModel):
    id: str
    username: str
    role: Role
    active: bool
    created_at: datetime


class CreateUser(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    username: str = Field(min_length=3, max_length=64)
    password: SecretStr = Field(min_length=14, max_length=128)
    role: Role = 'viewer'

    @field_validator('username')
    @classmethod
    def valid_username(cls, value):
        value = value.strip().lower()
        if not USERNAME.fullmatch(value): raise ValueError('Invalid username')
        return value


class UpdateUser(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    role: Role
    active: bool
    expected_role: Role
    expected_active: bool


class UserPage(BaseModel):
    items: list[UserPublic]
    next_after_username: str | None


PUBLIC_COLUMNS = (AuthUser.id, AuthUser.username, AuthUser.role, AuthUser.active, AuthUser.created_at)


def public(row):
    return UserPublic(id=row.id, username=row.username, role=row.role, active=row.active, created_at=aware(row.created_at))


class UserManagementService:
    def __init__(self, database): self.database = database

    @contextmanager
    def transaction(self, actor_id, *, write=False):
        if self.database is None: raise AuthUnavailable()
        try:
            with self.database.transaction() as session:
                if write:
                    # Shared DB mutex before any actor/target read. SQLite acquires its
                    # write lock; PostgreSQL locks the singleton row. No schema change.
                    locked = session.execute(update(AuthBootstrap).where(AuthBootstrap.id == 1).values(id=1))
                    if locked.rowcount != 1: raise AuthUnavailable()
                actor = session.execute(select(AuthUser.active, AuthUser.role).where(AuthUser.id == actor_id)).first()
                if not actor or not actor.active or 'users.manage' not in permissions_for(actor.role): raise UserDenied()
                yield session
        except IntegrityError:
            raise UserConflict() from None
        except (SQLAlchemyError, ValidationError, HashingError):
            raise AuthUnavailable('User storage unavailable') from None

    def page(self, actor_id, limit=20, after_username=None):
        if type(limit) is not int or not 1 <= limit <= 50: raise ValueError('Invalid limit')
        if after_username is not None and not USERNAME.fullmatch(after_username): raise ValueError('Invalid cursor')
        with self.transaction(actor_id) as session:
            # Canonical usernames are ASCII. Keep cursor order identical across
            # SQLite, PostgreSQL locales and the browser's code-point comparison.
            name = AuthUser.username.collate('C' if session.bind.dialect.name == 'postgresql' else 'BINARY')
            query = select(*PUBLIC_COLUMNS)
            if after_username is not None: query = query.where(name > after_username)
            rows = session.execute(query.order_by(name).limit(limit+1)).all()
            items = [public(row) for row in rows[:limit]]
            return UserPage(items=items, next_after_username=items[-1].username if len(rows)>limit else None)

    def event(self, session, actor_id, target_id, action):
        session.add(AuthEvent(id=str(uuid4()), event=action, user_id=target_id,
            source_hash=digest('user-management:'+actor_id), created_at=utcnow()))

    def create(self, actor_id, value):
        # Caller validated a bounded body. The hash never enters the public model.
        value = CreateUser.model_validate(value)
        with self.transaction(actor_id, write=True) as session:
            if session.scalar(select(AuthUser.id).where(AuthUser.username == value.username)): raise UserConflict()
            row = AuthUser(id=str(uuid4()), username=value.username, role=value.role,
                active=True, is_admin=value.role in ('owner','admin'),
                password_hash=HASHER.hash(value.password.get_secret_value()), created_at=utcnow())
            session.add(row)
            self.event(session, actor_id, row.id, 'user_created')
            session.flush()
            return public(row)

    def update(self, actor_id, target_id, value):
        value = UpdateUser.model_validate(value)
        with self.transaction(actor_id, write=True) as session:
            row = session.execute(select(*PUBLIC_COLUMNS).where(AuthUser.id == target_id)).first()
            if row is None: raise UserMissing()
            if actor_id == target_id and (value.role != row.role or not value.active): raise UserDenied()
            if row.role != value.expected_role or row.active != value.expected_active: raise UserConflict()
            if row.role == value.role and row.active == value.active: return public(row)
            if row.role == 'owner' and row.active and (value.role != 'owner' or not value.active):
                owners = session.scalar(select(func.count()).select_from(AuthUser).where(AuthUser.active.is_(True), AuthUser.role == 'owner'))
                if owners <= 1: raise UserDenied()
            session.execute(update(AuthUser).where(AuthUser.id == target_id).values(role=value.role,
                active=value.active, is_admin=value.role in ('owner','admin')))
            # Role changes and disabling revoke all old sessions; re-enable cannot resurrect them.
            session.execute(delete(AuthSession).where(AuthSession.user_id == target_id))
            self.event(session, actor_id, target_id, 'user_updated')
            session.flush()
            return public(session.execute(select(*PUBLIC_COLUMNS).where(AuthUser.id == target_id)).one())
