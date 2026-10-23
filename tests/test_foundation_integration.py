"""One disposable-database journey from 0004 to approved viewer module access."""
from datetime import timedelta
import secrets

from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, func

from backend.app import create_app
from backend.auth.service import AuthService, digest
from backend.config import Settings
from backend.database import Database
from backend.migrations import migrate_database, migration_config
from backend.models import AuthUser, AuthSession, RegistrationApplication, RegistrationPolicy
from tests.test_auth import ORIGIN, login
from tests.legacy_auth import seed_legacy_owner
from tests.test_module_access import access_modules, put_grant
from tests.test_module_management import headers, payload
from tests.test_registration import set_policy, PENDING


def exercise_foundation(database, settings):
    # Caller owns a verified empty temporary database, never Settings()/.env.
    assert not inspect(database.engine).get_table_names()
    migrate_database(database, '0004_module_management')
    owner_password = secrets.token_urlsafe(24)
    owner_id = seed_legacy_owner(database, owner_password)
    assert 'user_module_grants' not in inspect(database.engine).get_table_names()
    migrate_database(database, '0005_user_module_access')
    assert 'user_module_grants' in inspect(database.engine).get_table_names()
    assert 'registration_policies' not in inspect(database.engine).get_table_names()
    migrate_database(database, '0006_registration_policy')
    migrate_database(database)  # Current application runs only after the login audit upgrade.
    with database.transaction() as session:
        original = session.get(AuthUser, owner_id)
        assert original.active and original.role == 'owner'
        policy = session.get(RegistrationPolicy, 1)
        assert not policy.enabled and policy.approval_required
    app = create_app(settings, modules=access_modules())
    password = secrets.token_urlsafe(24)
    value = dict(username='foundation-viewer', password=password)
    with TestClient(app, base_url=ORIGIN) as owner, TestClient(app, base_url=ORIGIN) as viewer:
        assert login(owner, owner_password).status_code == 200
        assert viewer.get('/api/modules').status_code == 401
        assert viewer.get('/api/modules/example/ping').status_code == 200
        assert viewer.post('/api/auth/register', json=value, headers=headers(viewer)).status_code == 403
        assert set_policy(owner).status_code == 200
        assert viewer.post('/api/auth/register', json=value, headers={'Origin':ORIGIN}).status_code == 403
        first = viewer.post('/api/auth/register', json=value, headers=headers(viewer))
        duplicate = viewer.post('/api/auth/register', json=value, headers=headers(viewer))
        assert first.status_code == duplicate.status_code == 202
        assert first.json() == duplicate.json() == {'state':'submitted'}
        assert password not in first.text + duplicate.text
        assert viewer.get('/api/auth/me').json()['authenticated'] is False
        assert login(viewer, password, value['username']).status_code == 401
        queue = owner.get(PENDING).json()['items']
        assert len(queue) == 1 and queue[0]['state'] == 'pending'
        target = queue[0]['id']
        assert owner.post(f'{PENDING}/{target}/approve', headers={'Origin':ORIGIN}).status_code == 403
        assert owner.post(f'{PENDING}/{target}/approve', headers=headers(owner)).status_code == 200
        assert owner.get(PENDING).json()['items'] == []
        assert login(viewer, password, value['username']).status_code == 200
        access = viewer.get('/api/admin/me').json()
        assert access['role'] == 'viewer' and 'users.manage' not in access['permissions']
        for path in ['/api/admin/users', PENDING, '/api/admin/registration-policy']:
            assert viewer.get(path).status_code == 403
        assert viewer.get('/api/me/modules').json()['items'] == []
        assert viewer.get('/api/modules/alpha/ping').status_code == 403
        grant_url = f'/api/admin/users/{target}/modules/alpha'
        assert owner.put(grant_url,json=dict(granted=True,expected_granted=False),headers={'Origin':ORIGIN}).status_code == 403
        assert put_grant(owner,target).status_code == 200
        assert viewer.get('/api/modules/alpha/ping').status_code == 200
        assert viewer.get('/api/modules/beta/ping').status_code == 403
        assert [row['module_id'] for row in viewer.get('/api/me/modules').json()['items']] == ['alpha']
        # A grant cannot override the global module switch.
        assert owner.put('/api/admin/modules/alpha',json=payload(False,0),headers=headers(owner)).status_code == 200
        assert viewer.get('/api/modules/alpha/ping').status_code == 404
        assert viewer.get('/api/me/modules').json()['items'] == []
        assert owner.put('/api/admin/modules/alpha',json=payload(True,1),headers=headers(owner)).status_code == 200
        assert viewer.get('/api/modules/alpha/ping').status_code == 200
        assert put_grant(owner,target,granted=False,expected=True).status_code == 200
        assert viewer.get('/api/modules/alpha/ping').status_code == 403
        assert put_grant(owner,target).status_code == 200
        assert viewer.post('/api/auth/logout',headers=headers(viewer)).status_code == 200
        assert viewer.get('/api/modules/alpha/ping').status_code == 401
        assert login(viewer,password,value['username']).status_code == 200
        with database.transaction() as session:
            row = session.get(AuthSession,digest(viewer.cookies.get('__Host-runtu_session')))
            row.expires_at = app.state.auth_service.clock() - timedelta(seconds=1)
        assert viewer.get('/api/modules').status_code == 401
        assert viewer.get('/api/modules/alpha/ping').status_code == 401
        assert login(viewer,password,value['username']).status_code == 200
        change = dict(role='viewer',active=False,expected_role='viewer',expected_active=True)
        assert owner.patch('/api/admin/users/'+target,json=change,headers=headers(owner)).status_code == 200
        assert viewer.get('/api/modules/alpha/ping').status_code == 401
        assert viewer.get('/api/me/modules').status_code == 401
        with database.transaction() as session:
            assert session.scalar(select(func.count()).select_from(AuthUser)) == 2
            assert session.scalar(select(func.count()).select_from(RegistrationApplication)) == 1
            assert session.get(RegistrationApplication,target).pending is False
    with database.engine.begin() as connection:
        config = migration_config(); config.attributes['connection'] = connection
        command.check(config)


def test_foundation_migrations_registration_approval_and_module_access(tmp_path):
    settings = Settings(_env_file=None,database_url=f'sqlite:///{tmp_path/"foundation.db"}',auth_origin=ORIGIN)
    database = Database(settings.database_url.get_secret_value())
    try:
        exercise_foundation(database,settings)
    finally:
        database.dispose()
