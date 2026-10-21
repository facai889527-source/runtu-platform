from pathlib import Path

from alembic import command
from alembic.config import Config

from backend.database import Database


def migration_config() -> Config:
    root = Path(__file__).resolve().parent.parent
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    return config


def migrate_database(database: Database, revision: str = "head") -> None:
    """Explicit operator/test action. Never called by application startup."""
    config = migration_config()
    with database.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)
