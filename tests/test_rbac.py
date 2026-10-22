from datetime import timedelta

import pytest
from alembic import command
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from backend.app import create_app
from backend.auth.policy import PERMISSIONS, permissions_for
from backend.auth.routes import require_permission, require_role
from backend.auth.service import HASHER, digest
from backend.config import Settings
from backend.database import Database
from backend.migrations import migrate_database, migration_config
from backend.models import AuthSession, AuthUser
from tests.test_auth import auth, login, PASSWORD, ORIGIN
from tests.test_module_lifecycle import make_module


@pytest.fixture
def protected(auth):
    client, service, user_id = auth
    def probe():
        return {'ok': True}
    for permission in sorted(PERMISSIONS | {'unknown.permission'}):
        client.app.add_api_route('/probe/' + permission, probe,
            dependencies=[Depends(require_permission(permission))])
    client.app.add_api_route('/probe/owner', probe, dependencies=[Depends(require_role('owner'))])
    client.app.add_api_route('/probe/unknown-role', probe, dependencies=[Depends(require_role('unknown'))])
    client.app.add_api_route('/probe/write', probe, methods=['POST'],
        dependencies=[Depends(require_permission('module.manage'))])
    return client, service, user_id


@pytest.mark.parametrize('role,grants', [
    ('owner', {'platform.read', 'module.read', 'module.manage', 'users.manage', 'audit.read'}),
    ('admin', {'platform.read', 'module.read', 'module.manage', 'audit.read'}),
    ('viewer', {'platform.read', 'module.read'}),
])
def test_real_session_matrix_and_direct_api_denial(protected, role, grants):
    client, service, user_id = protected
    with service.transaction() as db:
        user = db.get(AuthUser, user_id)
        user.role = role
        user.is_admin = True  # Legacy marker cannot give viewer or admin owner authority.
    assert login(client).status_code == 200
    for permission in PERMISSIONS:
        assert client.get('/probe/' + permission).status_code == (200 if permission in grants else 403)
    assert client.get('/probe/unknown.permission').status_code == 403
    assert client.get('/probe/unknown-role').status_code == 403
    assert client.get('/probe/owner').status_code == (200 if role == 'owner' else 403)
    response = client.get('/api/admin/me')
    assert response.status_code == 200 and response.headers['Cache-Control'] == 'no-store'
    assert set(response.json()) == {'id', 'username', 'role', 'permissions'}
    assert response.json()['role'] == role
    assert set(response.json()['permissions']) == grants
    for forbidden in ('password', 'token', 'cookie', 'source_hash'):
        assert forbidden not in response.text
    # A direct request bypasses every frontend visibility rule and still enforces server grants.
    csrf = client.get('/api/auth/csrf').json()['csrf_token']
    assert client.post('/probe/write', headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf}).status_code == (403 if role == 'viewer' else 200)
    assert client.post('/probe/write', headers={'Origin': ORIGIN}).status_code == 403


def test_anonymous_expired_revoked_disabled_and_role_changes(protected):
    client, service, user_id = protected
    for path in ('/api/admin/me', '/probe/audit.read', '/probe/unknown.permission'):
        assert client.get(path).status_code == 401
    assert client.post('/probe/write', headers={'Origin': ORIGIN}).status_code == 401
    assert login(client).status_code == 200
    with service.transaction() as db:
        db.get(AuthUser, user_id).role = 'viewer'
    assert client.get('/probe/users.manage').status_code == 403  # Same session, no cached grants.
    with service.transaction() as db:
        db.get(AuthUser, user_id).active = False
    assert client.get('/api/admin/me').status_code == 401
    with service.transaction() as db:
        db.get(AuthUser, user_id).active = True
    assert client.get('/api/admin/me').status_code == 401  # Observed disabled session was revoked.
    assert login(client).status_code == 200
    with service.transaction() as db:
        row = db.get(AuthSession, digest(client.cookies.get('__Host-runtu_session')))
        row.expires_at = service.clock() - timedelta(seconds=1)
    assert client.get('/api/admin/me').status_code == 401
    assert client.get('/api/health').status_code == 200
    for path in ('/api/modules', '/api/modules/demo'):
        assert client.get(path).status_code == 401


def test_unknown_role_has_no_grants_and_database_rejects_it(auth):
    assert permissions_for('unknown') == frozenset()
    _, service, user_id = auth
    with pytest.raises(IntegrityError):
        with service.database.transaction() as db:
            db.get(AuthUser, user_id).role = 'unknown'


def test_legacy_upgrade_and_downgrade_revokes_sessions_and_preserves_users(tmp_path):
    database = Database(f'sqlite:///{tmp_path / "legacy-rbac.db"}')
    config = migration_config()
    try:
        with database.engine.begin() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, '0002_auth_foundation')
            for user_id, admin in [('legacy-owner', True), ('legacy-viewer', False)]:
                connection.execute(text('INSERT INTO auth_users (id,username,password_hash,active,is_admin,created_at) VALUES (:id,:id,:password,TRUE,:admin,CURRENT_TIMESTAMP)'),
                    {'id': user_id, 'password': HASHER.hash(PASSWORD), 'admin': admin})
            connection.execute(text("INSERT INTO auth_sessions VALUES (:hash,'legacy-owner',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"), {'hash': 'a' * 64})
        migrate_database(database)
        with database.transaction() as db:
            assert db.get(AuthUser, 'legacy-owner').role == 'owner'
            assert db.get(AuthUser, 'legacy-viewer').role == 'viewer'
            assert db.scalar(select(AuthSession)) is None
            db.get(AuthUser, 'legacy-owner').role = 'viewer'
            db.get(AuthUser, 'legacy-viewer').role = 'admin'
        with database.engine.begin() as connection:
            config.attributes['connection'] = connection
            command.downgrade(config, '0002_auth_foundation')
            legacy = dict(connection.execute(text('SELECT id,is_admin FROM auth_users')).all())
            assert legacy['legacy-owner'] == 0 and legacy['legacy-viewer'] == 0
        migrate_database(database)
        assert database.is_ready()
        with database.transaction() as db:
            assert db.get(AuthUser, 'legacy-owner').role == 'viewer'
            assert db.get(AuthUser, 'legacy-viewer').role == 'viewer'
    finally:
        database.dispose()


def test_module_namespace_and_central_write_boundary(auth):
    _, service, _ = auth
    module = make_module()
    @module.router.get('/api/admin/me')
    def fake_admin():
        return {'fake': True}
    with TestClient(create_app(service.settings, modules=[module]), base_url=ORIGIN) as client:
        # Module-local route exists only inside its module namespace.
        assert client.get('/api/modules/example/api/admin/me').json() == {'fake': True}
        assert client.get('/api/admin/me').status_code == 401  # Never the plugin's fake admin.
        assert client.post('/api/modules/example/action').status_code == 403
        assert login(client).status_code == 200
        assert client.get('/api/admin/me').json()['role'] == 'owner'
        csrf = client.get('/api/auth/csrf').json()['csrf_token']
        assert client.post('/api/modules/example/action', headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf}).status_code == 403
        assert client.get('/api/modules/example/ping').status_code == 200
