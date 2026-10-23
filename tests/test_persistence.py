from io import StringIO
import os
from pathlib import Path
import subprocess
import sys

import pytest
from alembic import command
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from tests.metadata_app import create_app
from backend.config import Settings
from backend.database import Database
from backend.migrations import migrate_database, migration_config
from backend.models import ModuleConfigRecord
from backend.modules import DemoModule, ModuleManifest, ModuleRegistry, PublicModuleConfig
from backend.persistence import (
    ConfigConflictError, ConfigStorageError, DatabaseNotConfiguredError,
    ModuleConfigService, UnknownModuleError,
)


@pytest.fixture
def database(tmp_path):
    db = Database(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    migrate_database(db)
    try:
        yield db
    finally:
        db.dispose()


def registry():
    result = ModuleRegistry()
    result.register(DemoModule())
    return result


def test_migration_upgrade_repeat_downgrade_and_model_match(database):
    migrate_database(database)
    assert database.is_ready()
    columns = {column["name"] for column in inspect(database.engine).get_columns("module_configs")}
    assert columns == {"module_id", "show_in_navigation", "refresh_interval_seconds", "updated_at", "enabled", "revision"}
    with database.engine.begin() as connection:
        cfg = migration_config()
        cfg.attributes["connection"] = connection
        command.check(cfg)
        command.downgrade(cfg, "base")
    assert "module_configs" not in inspect(database.engine).get_table_names()
    assert not database.is_ready()
    migrate_database(database)
    assert database.is_ready()


def test_save_update_and_restart_roundtrip(database):
    service = ModuleConfigService(registry(), database)
    assert service.load("demo") == PublicModuleConfig()
    expected = PublicModuleConfig(show_in_navigation=False, refresh_interval_seconds=20)
    service.save("demo", expected)
    with database.transaction() as session:
        first = session.get(ModuleConfigRecord, "demo").updated_at
        assert first is not None
    service.save("demo", {"show_in_navigation": True, "refresh_interval_seconds": 40})
    with database.transaction() as session:
        rows = session.scalars(select(ModuleConfigRecord)).all()
        assert len(rows) == 1
        assert rows[0].updated_at >= first
    restarted = Database(database.engine.url.render_as_string(hide_password=False))
    try:
        assert ModuleConfigService(registry(), restarted).load("demo").refresh_interval_seconds == 40
    finally:
        restarted.dispose()


def test_duplicate_insert_rolls_back_and_next_save_works(database):
    service = ModuleConfigService(registry(), database)
    service.save("demo", PublicModuleConfig(refresh_interval_seconds=10), create_only=True)
    with pytest.raises(ConfigConflictError):
        service.save("demo", PublicModuleConfig(refresh_interval_seconds=99), create_only=True)
    assert service.load("demo").refresh_interval_seconds == 10
    service.save("demo", PublicModuleConfig(refresh_interval_seconds=30))
    assert service.load("demo").refresh_interval_seconds == 30


def test_transaction_rolls_back_all_changes_on_constraint_failure(database):
    service = ModuleConfigService(registry(), database)
    service.save("demo", PublicModuleConfig(refresh_interval_seconds=10))
    with pytest.raises(IntegrityError):
        with database.transaction() as session:
            session.get(ModuleConfigRecord, "demo").refresh_interval_seconds = 50
            session.add(ModuleConfigRecord(module_id="invalid", refresh_interval_seconds=0))
            session.flush()
    assert service.load("demo").refresh_interval_seconds == 10
    with database.transaction() as session:
        assert session.get(ModuleConfigRecord, "invalid") is None


def test_invalid_unknown_and_sensitive_config_never_written(database, monkeypatch):
    service = ModuleConfigService(registry(), database)
    monkeypatch.setenv("RUNTU_PRIVATE_TOKEN", "dummy-secret")
    with pytest.raises(UnknownModuleError):
        service.save("missing", PublicModuleConfig())
    with pytest.raises(UnknownModuleError):
        service.load("missing")
    for config in ({"token": "dummy-secret"}, {"refresh_interval_seconds": 0},
                   {"show_in_navigation": "dummy-secret"}, {"refresh_interval_seconds": 86401}):
        with pytest.raises(ValidationError):
            service.save("demo", config)
    with pytest.raises(ValidationError):
        service.save("demo", PublicModuleConfig.model_construct(refresh_interval_seconds="dummy-secret"))
    with database.transaction() as session:
        assert session.scalars(select(ModuleConfigRecord)).all() == []


def test_schema_defaults(database):
    with database.transaction() as session:
        session.add(ModuleConfigRecord(module_id="demo"))
    with database.transaction() as session:
        row = session.get(ModuleConfigRecord, "demo")
        assert row.show_in_navigation is True
        assert row.refresh_interval_seconds is None
        assert row.updated_at is not None


def test_disabled_module_retains_configuration_and_no_write_http(database):
    class DisabledModule:
        manifest = ModuleManifest(id="demo", name="Demo", version="1", description="Test", status="disabled")
        router = APIRouter()

    ModuleConfigService(registry(), database).save("demo", PublicModuleConfig(refresh_interval_seconds=25))
    settings = Settings(_env_file=None, database_url=str(database.engine.url))
    with TestClient(create_app(settings, modules=[DisabledModule()])) as client:
        assert client.get("/api/health").json()["database"] == "ready"
        response = client.get("/api/modules/demo")
        assert response.status_code == 200
        assert response.json()["status"] == "disabled"
        assert response.json()["public_config"]["refresh_interval_seconds"] == 25
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)("/api/modules/demo").status_code == 405
    assert ModuleConfigService(registry(), database).load("demo").refresh_interval_seconds == 25


def test_no_database_and_missing_schema_are_explicit(tmp_path):
    service = ModuleConfigService(registry(), None)
    assert service.load("demo") == PublicModuleConfig()
    with pytest.raises(DatabaseNotConfiguredError):
        service.save("demo", PublicModuleConfig())
    settings = Settings(_env_file=None, database_url=f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    with TestClient(create_app(settings)) as client:
        health = client.get("/api/health")
        assert health.status_code == 503
        assert health.json()["status"] == "degraded"
        assert health.json()["database"] == "unavailable"
        detail = client.get("/api/modules/demo")
        assert detail.status_code == 503
        assert detail.json() == {"detail": "Module configuration storage unavailable"}
        assert "empty.db" not in detail.text
        assert client.get("/api/modules/missing").status_code == 404
        assert client.get("/api/modules").status_code == 503  # State cannot be guessed when configured storage is unavailable.


def test_storage_error_rolls_back_and_reports_safe_message(tmp_path):
    db = Database(f"sqlite:///{(tmp_path / 'unmigrated.db').as_posix()}")
    try:
        service = ModuleConfigService(registry(), db)
        with pytest.raises(ConfigStorageError, match="storage unavailable"):
            service.save("demo", PublicModuleConfig())
        migrate_database(db)
        service.save("demo", PublicModuleConfig())
        assert service.load("demo") == PublicModuleConfig()
    finally:
        db.dispose()


def test_postgresql_offline_sql_only_not_live_database(monkeypatch):
    monkeypatch.setenv("RUNTU_DATABASE_URL", "postgresql+psycopg://localhost/runtu_test")
    output = StringIO()
    cfg = migration_config()
    cfg.output_buffer = output
    command.upgrade(cfg, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE module_configs" in sql
    assert "TIMESTAMP WITH TIME ZONE" in sql
    assert "PRIMARY KEY (module_id)" in sql


def test_documented_alembic_cli_uses_environment_url(tmp_path):
    environment = os.environ.copy()
    environment["RUNTU_DATABASE_URL"] = f"sqlite:///{(tmp_path / 'cli.db').as_posix()}"
    root = Path(__file__).resolve().parent.parent
    for arguments in (("upgrade", "head"), ("current",)):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=root, env=environment, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        if arguments == ("current",):
            assert "0011_personal_telegram_bot" in result.stdout
