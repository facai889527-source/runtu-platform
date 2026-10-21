"""Fixed public fields only; no module loading, file operations or arbitrary settings."""
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from backend.auth.policy import permissions_for
from backend.models import AuthUser, ModuleChangeRecord, ModuleConfigRecord
from backend.modules import ModuleUpdate, PublicModuleConfig
from backend.persistence import ConfigConflictError, ConfigStorageError, DatabaseNotConfiguredError, UnknownModuleError


class ModuleProtectedError(ValueError):
    pass


class ModulePermissionError(ValueError):
    pass


class ModuleManagementService:
    def __init__(self, registry, database):
        self.registry, self.database = registry, database

    def _detail(self, module_id, row=None):
        detail = self.registry.detail(module_id)
        if detail is None:
            raise UnknownModuleError('Module not registered')
        if row is None:
            return detail
        # A newly required module stays enabled even if an old optional override was disabled.
        enabled = detail.required or (row.enabled if row.enabled is not None else detail.status == 'enabled')
        return detail.model_copy(update={'status': 'enabled' if enabled else 'disabled',
            'revision': row.revision, 'public_config': PublicModuleConfig(
                show_in_navigation=row.show_in_navigation,
                refresh_interval_seconds=row.refresh_interval_seconds)})

    def detail(self, module_id):
        self._detail(module_id)  # Unknown IDs stay 404 even when storage is unavailable.
        if self.database is None:
            return self._detail(module_id)
        try:
            with self.database.transaction() as session:
                return self._detail(module_id, session.get(ModuleConfigRecord, module_id))
        except (SQLAlchemyError, ValidationError):
            raise ConfigStorageError('Module storage unavailable') from None

    def manifests(self):
        if self.database is None:
            return self.registry.manifests()
        try:
            with self.database.transaction() as session:
                rows = {row.module_id: row for row in session.scalars(select(ModuleConfigRecord))}
                return [self._detail(item.id, rows.get(item.id)) for item in self.registry.manifests()]
        except (SQLAlchemyError, ValidationError):
            raise ConfigStorageError('Module storage unavailable') from None

    def save(self, module_id, payload, actor_id):
        detail = self._detail(module_id)
        value = ModuleUpdate.model_validate(payload)
        if detail.required and not value.enabled:
            raise ModuleProtectedError('Required module cannot be disabled')
        if self.database is None:
            raise DatabaseNotConfiguredError('Database is not configured')
        try:
            with self.database.transaction() as session:
                # Recheck mutable grants within the write transaction, not the legacy admin flag.
                actor = session.execute(select(AuthUser.active, AuthUser.role)
                    .where(AuthUser.id == actor_id).with_for_update()).first()
                if not actor or not actor.active or 'module.manage' not in permissions_for(actor.role):
                    raise ModulePermissionError('Module management permission required')
                if session.bind.dialect.name == 'sqlite':
                    from sqlalchemy.dialects.sqlite import insert
                else:
                    from sqlalchemy.dialects.postgresql import insert
                session.execute(insert(ModuleConfigRecord).values(module_id=module_id,
                    show_in_navigation=detail.public_config.show_in_navigation,
                    refresh_interval_seconds=detail.public_config.refresh_interval_seconds,
                    enabled=None, revision=0).on_conflict_do_nothing(index_elements=['module_id']))
                row = session.get(ModuleConfigRecord, module_id, with_for_update=True)
                current = self._detail(module_id, row)
                same = ((current.status == 'enabled') == value.enabled and current.public_config == value.public_config)
                if same and value.expected_revision <= current.revision:
                    return current  # Exact retry is a no-op, including audit and revision.
                if current.revision != value.expected_revision:
                    raise ConfigConflictError('Module changed; reload before saving')
                now = datetime.now(timezone.utc)
                changed = session.execute(update(ModuleConfigRecord)
                    .where(ModuleConfigRecord.module_id == module_id,
                           ModuleConfigRecord.revision == value.expected_revision)
                    .values(enabled=value.enabled, **value.public_config.model_dump(),
                            revision=value.expected_revision + 1, updated_at=now))
                if changed.rowcount != 1:
                    raise ConfigConflictError('Module changed; reload before saving')
                session.add(ModuleChangeRecord(id=str(uuid4()), module_id=module_id, actor_id=actor_id,
                    revision=value.expected_revision + 1, action='updated', created_at=now))
                session.flush()
                session.refresh(row)
                result = self._detail(module_id, row)
            return result
        except (SQLAlchemyError, ValidationError):
            raise ConfigStorageError('Module storage unavailable') from None
