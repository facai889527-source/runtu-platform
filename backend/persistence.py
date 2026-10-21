from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.database import Database
from backend.models import ModuleConfigRecord
from backend.modules import ModuleRegistry, PublicModuleConfig


class UnknownModuleError(ValueError):
    pass


class ConfigConflictError(RuntimeError):
    pass


class ConfigStorageError(RuntimeError):
    pass


class DatabaseNotConfiguredError(ConfigStorageError):
    pass


class ModuleConfigService:
    def __init__(self, registry: ModuleRegistry, database: Database | None) -> None:
        self.registry = registry
        self.database = database

    def _module(self, module_id: str):
        detail = self.registry.detail(module_id)
        if detail is None:
            raise UnknownModuleError("Module is not registered")
        return detail

    def load(self, module_id: str) -> PublicModuleConfig:
        detail = self._module(module_id)
        if self.database is None:
            return detail.public_config
        try:
            with self.database.transaction() as session:
                row = session.get(ModuleConfigRecord, module_id)
                if row is None:
                    return detail.public_config
                return PublicModuleConfig(
                    show_in_navigation=row.show_in_navigation,
                    refresh_interval_seconds=row.refresh_interval_seconds,
                )
        except (SQLAlchemyError, ValidationError) as error:
            raise ConfigStorageError("Module configuration storage unavailable") from error

    def save(
        self, module_id: str, config: PublicModuleConfig | dict, *, create_only: bool = False
    ) -> PublicModuleConfig:
        self._module(module_id)
        # Explicitly validate and project the allowlist. Never persist arbitrary dictionaries.
        validated = PublicModuleConfig.model_validate(config)
        if self.database is None:
            raise DatabaseNotConfiguredError("Database is not configured")
        try:
            with self.database.transaction() as session:
                row = None if create_only else session.get(ModuleConfigRecord, module_id)
                if row is None:
                    row = ModuleConfigRecord(module_id=module_id)
                    session.add(row)
                row.show_in_navigation = validated.show_in_navigation
                row.refresh_interval_seconds = validated.refresh_interval_seconds
                row.updated_at = datetime.now(timezone.utc)
                session.flush()
        except IntegrityError as error:
            raise ConfigConflictError("Module configuration conflicts with stored data") from error
        except SQLAlchemyError as error:
            raise ConfigStorageError("Module configuration storage unavailable") from error
        return PublicModuleConfig(
            show_in_navigation=validated.show_in_navigation,
            refresh_interval_seconds=validated.refresh_interval_seconds,
        )
