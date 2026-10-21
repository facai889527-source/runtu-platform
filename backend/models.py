from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func, true
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ModuleConfigRecord(Base):
    __tablename__ = "module_configs"
    __table_args__ = (
        CheckConstraint(
            "refresh_interval_seconds IS NULL OR "
            "(refresh_interval_seconds >= 1 AND refresh_interval_seconds <= 86400)",
            name="ck_module_configs_refresh_interval",
        ),
        CheckConstraint('revision >= 0', name='ck_module_configs_revision'),
    )

    module_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    show_in_navigation: Mapped[bool] = mapped_column(Boolean, server_default=true())
    refresh_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ModuleChangeRecord(Base):
    __tablename__ = 'module_changes'
    __table_args__ = (UniqueConstraint('module_id', 'revision', name='uq_module_changes_revision'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    module_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthUser(Base):
    __tablename__ = "auth_users"
    __table_args__ = (CheckConstraint("role IN ('owner', 'admin', 'viewer')", name="ck_auth_users_role"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(16), default='viewer')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("auth_users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthEvent(Base):
    __tablename__ = "auth_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    bucket: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer)
    reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AuthBootstrap(Base):
    __tablename__ = "auth_bootstrap"
    __table_args__ = (CheckConstraint("id = 1", name="ck_auth_bootstrap_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserModuleGrant(Base):
    __tablename__ = 'user_module_grants'
    user_id: Mapped[str] = mapped_column(ForeignKey('auth_users.id'), primary_key=True)
    module_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserModuleGrantEvent(Base):
    __tablename__ = 'user_module_grant_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    module_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
