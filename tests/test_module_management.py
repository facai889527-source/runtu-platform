from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError

from backend.app import create_app
from backend.config import Settings
from backend.database import Database
from backend.migrations import migrate_database, migration_config
from backend.models import AuthUser, ModuleChangeRecord
from backend.modules import PublicModuleConfig
from backend.persistence import ConfigConflictError
from tests.test_auth import login, ORIGIN, PASSWORD
from tests.test_module_lifecycle import make_module


@pytest.fixture
def managed(tmp_path):
    module = make_module()
    required = make_module(module_id='required')
    required.manifest = required.manifest.model_copy(update={'required': True})
    settings = Settings(_env_file=None, database_url=f'sqlite:///{tmp_path / "management.db"}', auth_origin=ORIGIN)
    app = create_app(settings, modules=[module, required])
    migrate_database(app.state.database)
    user_id = app.state.auth_service.bootstrap('operator', PASSWORD)
    with TestClient(app, base_url=ORIGIN) as client:
        yield client, app.state.database, user_id, settings


def headers(client):
    return {'Origin': ORIGIN, 'X-CSRF-Token': client.get('/api/auth/csrf').json()['csrf_token']}


def payload(enabled=False, revision=0, interval=45):
    return {'enabled': enabled, 'expected_revision': revision,
            'public_config': {'show_in_navigation': False, 'refresh_interval_seconds': interval}}


def test_toggle_config_idempotent_restart_and_route_gate(managed):
    client, db, _, settings = managed
    assert login(client).status_code == 200
    assert client.get('/api/modules/example/ping').status_code == 200
    first = client.put('/api/admin/modules/example', json=payload(), headers=headers(client))
    assert first.status_code == 200 and first.json()['revision'] == 1
    assert first.json()['status'] == 'disabled'
    assert client.get('/api/modules').json()[0]['status'] == 'disabled'
    assert client.get('/api/modules/example/ping').status_code == 404
    assert client.put('/api/admin/modules/example', json=payload(), headers=headers(client)).json()['revision'] == 1
    with db.transaction() as session:
        assert session.scalar(select(func.count()).select_from(ModuleChangeRecord)) == 1
    second = client.put('/api/admin/modules/example', json=payload(True, 1), headers=headers(client))
    assert second.status_code == 200 and second.json()['revision'] == 2
    assert client.get('/api/modules/example/ping').status_code == 200
    assert client.post('/api/modules/example/action', headers=headers(client)).status_code == 403
    with TestClient(create_app(settings, modules=[make_module()]), base_url=ORIGIN) as restarted:
        detail = restarted.get('/api/modules/example').json()
        assert detail['revision'] == 2 and detail['public_config']['refresh_interval_seconds'] == 45
        assert restarted.get('/api/modules/example/ping').status_code == 200


@pytest.mark.parametrize('role,expected', [('owner', 200), ('admin', 200), ('viewer', 403)])
def test_permission_matrix_and_csrf(managed, role, expected):
    client, db, user_id, _ = managed
    assert client.put('/api/admin/modules/example', json=payload(), headers={'Origin': ORIGIN}).status_code == 401
    with db.transaction() as session:
        session.get(AuthUser, user_id).role = role
    assert login(client).status_code == 200
    assert client.put('/api/admin/modules/example', json=payload(), headers={'Origin': ORIGIN}).status_code == 403
    assert client.put('/api/admin/modules/example', json=payload(), headers=headers(client)).status_code == expected
    with db.transaction() as session:
        session.get(AuthUser, user_id).active = False
    assert client.put('/api/admin/modules/example', json=payload(), headers=headers(client)).status_code in (401, 403)


def test_required_unknown_validation_and_conflict(managed):
    client, db, _, _ = managed
    assert login(client).status_code == 200
    assert client.put('/api/admin/modules/required', json=payload(), headers=headers(client)).status_code == 403
    assert client.put('/api/admin/modules/missing', json=payload(), headers=headers(client)).status_code == 404
    for change in [dict(payload(), enabled='false'), dict(payload(), expected_revision=-1),
                   dict(payload(), command='ignored'), payload(interval=0), payload(interval=86401),
                   dict(payload(), public_config={'show_in_navigation': 'false'}),
                   dict(payload(), public_config={'secret': 'not-accepted'})]:
        assert client.put('/api/admin/modules/example', json=change, headers=headers(client)).status_code == 422
    assert client.put('/api/admin/modules/example', json=payload(), headers=headers(client)).status_code == 200
    assert client.put('/api/admin/modules/example', json=payload(True), headers=headers(client)).status_code == 409
    with db.transaction() as session:
        rows = session.scalars(select(ModuleChangeRecord)).all()
        assert len(rows) == 1 and rows[0].module_id == 'example'
        assert set(rows[0].__table__.columns.keys()) == {'id', 'module_id', 'actor_id', 'revision', 'action', 'created_at'}


def test_audit_failure_rolls_back_state_and_configuration(managed):
    client, db, _, _ = managed
    assert login(client).status_code == 200
    def fail(_mapper, _connection, _target):
        raise OperationalError('audit insert', {}, Exception('disposable failure'))
    event.listen(ModuleChangeRecord, 'before_insert', fail)
    try:
        assert client.put('/api/admin/modules/example', json=payload(), headers=headers(client)).status_code == 503
    finally:
        event.remove(ModuleChangeRecord, 'before_insert', fail)
    detail = client.get('/api/modules/example').json()
    assert detail['status'] == 'enabled' and detail['revision'] == 0
    assert detail['public_config']['refresh_interval_seconds'] == 30


def test_concurrent_different_versions_one_commit(managed):
    client, db, actor, _ = managed
    service = client.app.state.module_management
    def save(interval):
        try:
            service.save('example', payload(interval=interval), actor)
            return 'saved'
        except ConfigConflictError:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, [40, 50])) == ['conflict', 'saved']
    assert service.detail('example').revision == 1
    with db.transaction() as session:
        assert session.scalar(select(func.count()).select_from(ModuleChangeRecord)) == 1


def test_migration_preserves_legacy_config_without_state_override(tmp_path):
    db = Database(f'sqlite:///{tmp_path / "legacy.db"}')
    config = migration_config()
    with db.engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, '0003_rbac_roles')
        from sqlalchemy import text
        connection.execute(text("INSERT INTO module_configs(module_id,show_in_navigation,refresh_interval_seconds) VALUES ('example',FALSE,20)"))
    migrate_database(db)
    app = create_app(Settings(_env_file=None, database_url=str(db.engine.url)), modules=[make_module('disabled')])
    assert app.state.module_management.detail('example').status == 'disabled'
    assert app.state.module_management.detail('example').public_config == PublicModuleConfig(show_in_navigation=False, refresh_interval_seconds=20)
    app.state.database.dispose()
    with db.engine.begin() as connection:
        config.attributes['connection'] = connection
        command.downgrade(config, '0003_rbac_roles')
    migrate_database(db)
    db.dispose()


def test_initially_disabled_module_can_be_enabled_without_restarting(managed):
    _, _, _, settings = managed
    with TestClient(create_app(settings, modules=[make_module('disabled')]), base_url=ORIGIN) as client:
        assert login(client).status_code == 200
        assert client.get('/api/modules/example/ping').status_code == 404
        assert client.put('/api/admin/modules/example', json=payload(True), headers=headers(client)).status_code == 200
        assert client.get('/api/modules/example/ping').status_code == 200


def test_revoked_session_and_validation_do_not_leak_inputs(managed):
    client, _, _, _ = managed
    assert login(client).status_code == 200
    proof_headers = headers(client)
    session_cookie = client.cookies.get('__Host-runtu_session')  # Disposable test fixture only.
    denied = client.put('/api/admin/modules/example', json=dict(payload(), private='not-for-response'), headers=proof_headers)
    assert denied.status_code == 422 and 'not-for-response' not in denied.text
    assert client.post('/api/auth/logout', headers=proof_headers).status_code == 200
    client.cookies.set('__Host-runtu_session', session_cookie)
    assert client.put('/api/admin/modules/example', json=payload(), headers=proof_headers).status_code == 401
    assert client.get('/api/modules').headers['Cache-Control'] == 'no-store'
