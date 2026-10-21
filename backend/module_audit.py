"""Bounded, per-module audit reads. Never load users, sessions or config values."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.models import ModuleChangeRecord
from backend.persistence import UnknownModuleError


class AuditUnavailable(Exception):
    pass


class ModuleAuditItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    module_id: str = Field(max_length=64)
    actor_id: str = Field(max_length=36)
    action: Literal['updated']
    created_at: datetime
    revision: int = Field(ge=1, le=2147483647)


class ModuleAuditPage(BaseModel):
    items: list[ModuleAuditItem]
    next_before_revision: int | None


class ModuleAuditService:
    def __init__(self, registry, database):
        self.registry, self.database = registry, database

    def page(self, module_id, limit=10, before_revision=None):
        if self.registry.detail(module_id) is None:
            raise UnknownModuleError('Module not registered')
        if self.database is None:
            raise AuditUnavailable()
        # Keep the bound even for non-HTTP callers. No arbitrary sort or offset.
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError('Invalid audit limit')
        if before_revision is not None and (type(before_revision) is not int or not 1 <= before_revision <= 2147483647):
            raise ValueError('Invalid audit cursor')
        try:
            with self.database.transaction() as session:
                query = select(ModuleChangeRecord.module_id, ModuleChangeRecord.actor_id,
                    ModuleChangeRecord.action, ModuleChangeRecord.created_at, ModuleChangeRecord.revision
                ).where(ModuleChangeRecord.module_id == module_id)
                if before_revision is not None:
                    query = query.where(ModuleChangeRecord.revision < before_revision)
                rows = session.execute(query.order_by(ModuleChangeRecord.revision.desc()).limit(limit + 1)).all()
                items = [ModuleAuditItem(module_id=row.module_id, actor_id=row.actor_id,
                    action=row.action, revision=row.revision,
                    created_at=row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None
                    else row.created_at.astimezone(timezone.utc)) for row in rows[:limit]]
                return ModuleAuditPage(items=items,
                    next_before_revision=items[-1].revision if len(rows) > limit else None)
        except (SQLAlchemyError, ValidationError):
            raise AuditUnavailable() from None
