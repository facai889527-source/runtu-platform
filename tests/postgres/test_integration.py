"""Destructive PG tests: exclusively enabled by the owned-container runner."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import secrets
from uuid import uuid4

from alembic import command
from fastapi import Depends
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app import create_app
from backend.auth.policy import PERMISSIONS, permissions_for
from backend.auth.routes import require_permission
from backend.auth.service import AuthDenied, AuthService, BootstrapRefused, HASHER, RateLimited, digest, utcnow
from backend.config import Settings
from backend.database import Database
from backend.migrations import migrate_database, migration_config
from backend.models import AuthBootstrap, AuthEvent, AuthRateLimit, AuthSession, AuthUser, ModuleConfigRecord
from scripts.pg_guard import GuardRefused, guarded_test_url


def test_registration_policy_approval_and_migration_guard(pg_auth):
    from tests.test_registration import exercise_registration_contract
    from tests.test_module_management import headers
    from backend.registration import PolicyInput
    from backend.models import RegistrationPolicy
    from sqlalchemy import event
    from sqlalchemy.exc import OperationalError
    db,_,settings,actor,password=pg_auth
    app=create_app(settings)
    with TestClient(app,base_url='https://runtu.test') as client:
        proof=client.get('/api/auth/csrf').json()['csrf_token']
        assert client.post('/api/auth/login',json={'username':'operator','password':password},headers={'Origin':'https://runtu.test','X-CSRF-Token':proof}).status_code==200
        exercise_registration_contract(client,app)
        key=digest(client.cookies.get('__Host-runtu_session'))
        def save(_):
            try:
                app.state.registration.save_policy(actor,key,PolicyInput(enabled=False,approval_required=True,expected_revision=1))
                return 'saved'
            except Exception as error:
                from backend.user_management import UserConflict
                if isinstance(error,UserConflict): return 'conflict'
                raise
        with ThreadPoolExecutor(max_workers=2) as pool: assert sorted(pool.map(save,range(2)))==['conflict','saved']
        def fail(*_): raise OperationalError('fixture registration audit',{},Exception('disposable'))
        event.listen(AuthEvent,'before_insert',fail)
        try:
            assert client.put('/api/admin/registration-policy',json=dict(enabled=True,approval_required=True,expected_revision=2),headers=headers(client)).status_code==503
        finally: event.remove(AuthEvent,'before_insert',fail)
        with db.transaction() as session: assert session.get(RegistrationPolicy,1).enabled is False
        with db.engine.begin() as connection:
            config=migration_config();config.attributes['connection']=connection
            command.check(config)
            command.downgrade(config,'0005_user_module_access')
        migrate_database(db)
        assert client.get('/api/auth/registration-policy').json()==dict(enabled=False,approval_required=True)


def test_assigned_module_grants_public_contract_and_atomicity(pg_auth):
    from tests.test_module_access import access_modules, exercise_grant_contract, put_grant
    from tests.test_module_management import headers
    from backend.module_access import GrantInput
    from backend.models import UserModuleGrantEvent
    from sqlalchemy import event
    from sqlalchemy.exc import OperationalError
    db,_,settings,actor,password=pg_auth
    app=create_app(settings,modules=access_modules())
    with TestClient(app,base_url='https://runtu.test') as client:
        from tests.test_login_boundaries import exercise_metadata_boundary
        exercise_metadata_boundary(client,app,actor,password)
        assert client.get('/api/modules/example/ping').status_code==200
        assert client.get('/api/modules/alpha/ping').status_code==401
        proof=client.get('/api/auth/csrf').json()['csrf_token']
        assert client.post('/api/auth/login',json={'username':'operator','password':password},headers={'Origin':'https://runtu.test','X-CSRF-Token':proof}).status_code==200
        exercise_grant_contract(client,app,actor)
        def grant(_): return app.state.module_access.save(actor,actor,'beta',GrantInput(granted=True,expected_granted=False))
        with ThreadPoolExecutor(max_workers=2) as pool: assert all(row.granted for row in pool.map(grant,range(2)))
        def fail(*_): raise OperationalError('fixture grant audit',{},Exception('disposable'))
        event.listen(UserModuleGrantEvent,'before_insert',fail)
        try: assert put_grant(client,actor,'beta',False,True).status_code==503
        finally: event.remove(UserModuleGrantEvent,'before_insert',fail)
        assert client.get('/api/modules/beta/ping').status_code==200
        with db.transaction() as session:
            assert session.scalar(select(func.count()).select_from(UserModuleGrantEvent).where(UserModuleGrantEvent.module_id=='beta'))==1
        with db.engine.begin() as connection:
            config=migration_config();config.attributes['connection']=connection
            command.check(config)
            command.downgrade(config,'0004_module_management')
        assert 'user_module_grants' not in inspect(db.engine).get_table_names()
        migrate_database(db)
        assert app.state.module_access.page(actor,actor,own=True).items==[]


def test_user_management_owner_contract_and_concurrent_quorum(pg_auth):
    from backend.user_management import CreateUser, UpdateUser, UserDenied
    from tests.test_user_management import exercise_user_contract
    db, _, settings, actor, password = pg_auth
    app=create_app(settings)
    with TestClient(app,base_url='https://runtu.test') as client:
        path='/api/admin/users'
        assert client.get(path).status_code==401
        proof=client.get('/api/auth/csrf').json()['csrf_token']
        assert client.post('/api/auth/login',json={'username':'operator','password':password},headers={'Origin':'https://runtu.test','X-CSRF-Token':proof}).status_code==200
        exercise_user_contract(client)
        manager=app.state.user_management
        other=manager.create(actor,CreateUser(username='other-owner',password=secrets.token_urlsafe(24),role='owner'))
        def demote(pair):
            try:
                manager.update(*pair,UpdateUser(role='viewer',active=True,expected_role='owner',expected_active=True))
                return 'saved'
            except UserDenied: return 'denied'
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(demote,[(actor,other.id),(other.id,actor)]))==['denied','saved']
        with db.transaction() as session:
            assert session.scalar(select(func.count()).select_from(AuthUser).where(AuthUser.active.is_(True),AuthUser.role=='owner'))==1


def test_module_audit_keyset_http_contract(pg_auth):
    from tests.test_module_audit import exercise_audit_pages
    from tests.test_module_lifecycle import make_module
    db, _, settings, actor, password = pg_auth
    app = create_app(settings, modules=[make_module()])
    with TestClient(app, base_url='https://runtu.test') as client:
        path='/api/admin/modules/example/changes'
        assert client.get(path).status_code==401
        proof=client.get('/api/auth/csrf').json()['csrf_token']
        assert client.post('/api/auth/login',json={'username':'operator','password':password},
            headers={'Origin':'https://runtu.test','X-CSRF-Token':proof}).status_code==200
        exercise_audit_pages(client)
        # A failed audit insert rolls back the configuration on PostgreSQL too.
        from sqlalchemy import event
        from sqlalchemy.exc import OperationalError
        from backend.models import ModuleChangeRecord
        from tests.test_module_management import headers, payload
        def fail_insert(*_args):
            raise OperationalError('fixture audit failure', {}, Exception('disposable'))
        event.listen(ModuleChangeRecord, 'before_insert', fail_insert)
        try:
            assert client.put('/api/admin/modules/example', json=payload(revision=13, interval=120),
                headers=headers(client)).status_code == 503
        finally:
            event.remove(ModuleChangeRecord, 'before_insert', fail_insert)
        assert client.get(path).json()['items'][0]['revision'] == 13
        assert app.state.module_management.detail('example').revision == 13
        for role,status in [('viewer',403),('admin',200),('owner',200)]:
            with db.transaction() as session:
                session.get(AuthUser,actor).role=role
            assert client.get(path).status_code==status


def test_module_management_persistence_rbac_and_concurrent_revision(pg_auth):
    from backend.persistence import ConfigConflictError
    from backend.models import ModuleChangeRecord
    from tests.test_module_lifecycle import make_module
    db, _, settings, user_id, password = pg_auth
    app = create_app(settings, modules=[make_module()])
    with TestClient(app, base_url='https://runtu.test') as client:
        proof = client.get('/api/auth/csrf').json()['csrf_token']
        assert client.post('/api/auth/login', json={'username': 'operator', 'password': password},
            headers={'Origin': 'https://runtu.test', 'X-CSRF-Token': proof}).status_code == 200
        value = {'enabled': False, 'expected_revision': 0,
                 'public_config': {'show_in_navigation': False, 'refresh_interval_seconds': 25}}
        assert client.put('/api/admin/modules/example', json=value, headers={'Origin': 'https://runtu.test'}).status_code == 403
        proof = client.get('/api/auth/csrf').json()['csrf_token']
        assert client.put('/api/admin/modules/example', json=value,
            headers={'Origin': 'https://runtu.test', 'X-CSRF-Token': proof}).status_code == 200
        assert client.get('/api/modules/example/ping').status_code == 404
        def save(interval):
            other = dict(value, expected_revision=1, public_config={'show_in_navigation': True, 'refresh_interval_seconds': interval})
            try:
                app.state.module_management.save('example', other, user_id)
                return 'saved'
            except ConfigConflictError:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(save, [35, 45])) == ['conflict', 'saved']
        with db.transaction() as session:
            assert session.scalar(select(func.count()).select_from(ModuleChangeRecord)) == 2
        restarted = create_app(settings, modules=[make_module()])
        try:
            assert restarted.state.module_management.detail('example').revision == 2
        finally:
            restarted.state.database.dispose()


@pytest.fixture
def pg_database():
    import os
    if not os.environ.get('RUNTU_PG_TEST_RUN_ID'):
        pytest.skip('Optional online PG suite: use python -m scripts.test_postgres')
    try:
        url = guarded_test_url()
    except GuardRefused:
        pytest.fail('Disposable container guard refused; no connection attempted', pytrace=False)
    control = Database(url)
    schema = 'runtu_case_' + secrets.token_hex(16)
    created = False
    db = None
    try:
        with control.engine.connect() as connection:
            actual = connection.execute(text('SELECT current_database(), current_user')).one()
            if tuple(actual) != (url.database, url.username):
                pytest.fail('Database identity mismatch; no migration attempted', pytrace=False)
        if inspect(control.engine).get_table_names(schema='public'):
            pytest.fail('Test database must start empty; no destructive action attempted', pytrace=False)
        with control.engine.begin() as connection:
            connection.execute(text('CREATE SCHEMA ' + schema))
        created = True
        db = Database(url.update_query_dict({'options': '-csearch_path=' + schema}))
        assert not inspect(db.engine).get_table_names()
        yield db
    finally:
        if db:
            db.dispose()
        try:
            if created:
                guarded_test_url()  # Recheck ownership before deleting this exact created schema.
                with control.engine.begin() as connection:
                    connection.execute(text('DROP SCHEMA ' + schema + ' CASCADE'))
        finally:
            control.dispose()


@pytest.fixture
def pg_auth(pg_database):
    migrate_database(pg_database)
    settings = Settings(_env_file=None, database_url=pg_database.engine.url.render_as_string(hide_password=False), auth_origin='https://runtu.test')
    service = AuthService(pg_database, settings)
    password = secrets.token_urlsafe(32)
    user_id = service.bootstrap('operator', password)
    return pg_database, service, settings, user_id, password


def test_migrations_constraints_legacy_owner_and_lossy_downgrades(pg_database):
    db = pg_database
    migrate_database(db, '0001_module_configs')
    with db.engine.begin() as connection:
        # Use the historical schema, not today's ORM columns, before upgrading.
        connection.execute(text("INSERT INTO module_configs(module_id,refresh_interval_seconds) VALUES ('retained',30)"))
    migrate_database(db, '0002_auth_foundation')
    with db.engine.begin() as connection:
        for user_id, admin in [('legacy-admin', True), ('legacy-reader', False)]:
            connection.execute(text('INSERT INTO auth_users (id,username,password_hash,active,is_admin,created_at) VALUES (:id,:id,:hash,TRUE,:admin,CURRENT_TIMESTAMP)'),
                {'id': user_id, 'admin': admin, 'hash': HASHER.hash(secrets.token_urlsafe(24))})
        connection.execute(text("INSERT INTO auth_sessions VALUES (:hash,'legacy-admin',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"), {'hash': 'a' * 64})
    migrate_database(db)
    inspector = inspect(db.engine)
    assert {c['name'] for c in inspector.get_unique_constraints('auth_users')}
    assert any(c['column_names'] == ['username'] for c in inspector.get_unique_constraints('auth_users'))
    assert 'ck_auth_users_role' in {c['name'] for c in inspector.get_check_constraints('auth_users')}
    assert {'ix_auth_sessions_user_id', 'ix_auth_sessions_expires_at'} <= {i['name'] for i in inspector.get_indexes('auth_sessions')}
    assert inspector.get_foreign_keys('auth_sessions')[0]['referred_table'] == 'auth_users'
    assert all(c['type'].timezone for c in inspector.get_columns('auth_sessions') if c['name'].endswith('_at'))
    with db.transaction() as session:
        assert session.get(AuthUser, 'legacy-admin').role == 'owner'
        assert session.get(AuthUser, 'legacy-reader').role == 'viewer'
        assert session.scalar(select(AuthSession)) is None
        assert session.get(ModuleConfigRecord, 'retained').show_in_navigation is True
    for statement in (
        "UPDATE auth_users SET role='unknown' WHERE id='legacy-reader'",
        "UPDATE auth_users SET username='legacy-admin' WHERE id='legacy-reader'",
        "UPDATE module_configs SET refresh_interval_seconds=0 WHERE module_id='retained'",
    ):
        with pytest.raises(IntegrityError), db.engine.begin() as connection:
            connection.execute(text(statement))
    with pytest.raises(IntegrityError), db.transaction() as session:
        session.add(AuthSession(token_hash='b' * 64, user_id='missing', created_at=utcnow(), last_seen_at=utcnow(), expires_at=utcnow()))
    config = migration_config()
    with db.engine.begin() as connection:
        config.attributes['connection'] = connection
        command.check(config)
    with db.transaction() as session:
        session.get(AuthUser, 'legacy-admin').role = 'admin'
    with db.engine.begin() as connection:
        config.attributes['connection'] = connection
        command.downgrade(config, '0002_auth_foundation')
        assert connection.scalar(text("SELECT is_admin FROM auth_users WHERE id='legacy-admin'")) is False
    migrate_database(db)
    with db.transaction() as session:
        assert session.get(AuthUser, 'legacy-admin').role == 'viewer'
    with db.engine.begin() as connection:
        config.attributes['connection'] = connection
        command.downgrade(config, '0001_module_configs')
    assert not any(name.startswith('auth_') for name in inspect(db.engine).get_table_names())
    assert not db.is_ready()  # Current application needs 0004 state columns.


def test_concurrent_bootstrap_exactly_one_owner_and_safe_audit(pg_database):
    migrate_database(pg_database)
    service = AuthService(pg_database, Settings(_env_file=None))
    password = secrets.token_urlsafe(32)
    def bootstrap(index):
        try:
            service.bootstrap(f'owner-{index}', password)
            return True
        except BootstrapRefused:
            return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(bootstrap, range(4))) == 1
    with pg_database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(AuthUser)) == 1
        assert session.get(AuthBootstrap, 1)
        events = session.scalars(select(AuthEvent)).all()
        assert len(events) == 1 and events[0].event == 'bootstrap'
        assert password not in str(events[0].__dict__)


def test_auth_api_rbac_rotation_csrf_and_disable(pg_auth):
    db, service, settings, user_id, password = pg_auth
    app = create_app(settings)
    for permission in PERMISSIONS | {'unknown'}:
        app.add_api_route('/pg-probe/' + permission, lambda: {'ok': True}, dependencies=[Depends(require_permission(permission))])
    with TestClient(app, base_url='https://runtu.test') as client:
        assert client.get('/api/admin/me').status_code == 401
        for role in ('viewer', 'admin', 'owner'):
            with db.transaction() as session:
                session.get(AuthUser, user_id).role = role
            csrf = client.get('/api/auth/csrf').json()['csrf_token']
            old = client.cookies.get('__Host-runtu_session')
            result = client.post('/api/auth/login', json={'username': 'operator', 'password': password}, headers={'Origin': 'https://runtu.test', 'X-CSRF-Token': csrf})
            assert result.status_code == 200
            assert 'HttpOnly' in result.headers['set-cookie'] and 'Secure' in result.headers['set-cookie']
            assert client.cookies.get('__Host-runtu_session') != old
            with db.transaction() as session:
                assert session.get(AuthSession, digest(old)) is None
            info = client.get('/api/admin/me').json()
            assert set(info) == {'id', 'username', 'role', 'permissions'}
            assert set(info['permissions']) == permissions_for(role)
            for permission in PERMISSIONS | {'unknown'}:
                assert client.get('/pg-probe/' + permission).status_code == (200 if permission in permissions_for(role) else 403)
        assert client.post('/api/auth/logout', headers={'Origin': 'https://runtu.test'}).status_code == 403
        csrf = client.get('/api/auth/csrf').json()['csrf_token']
        old = client.cookies.get('__Host-runtu_session')
        assert client.post('/api/auth/logout', headers={'Origin': 'https://runtu.test', 'X-CSRF-Token': csrf}).status_code == 200
        assert client.get('/api/admin/me').status_code == 401
        with db.transaction() as session:
            assert session.get(AuthSession, digest(old)) is None
        csrf = client.get('/api/auth/csrf').json()['csrf_token']
        assert client.post('/api/auth/login', json={'username': 'operator', 'password': password}, headers={'Origin': 'https://runtu.test', 'X-CSRF-Token': csrf}).status_code == 200
        with db.transaction() as session:
            session.get(AuthUser, user_id).active = False
        assert client.get('/api/admin/me').status_code == 401
        assert client.get('/api/health').status_code == 200
        for endpoint in ('/api/modules', '/api/modules/demo'):
            assert client.get(endpoint).status_code == 401
        with db.transaction() as session:
            events = session.scalars(select(AuthEvent)).all()
            assert len([e for e in events if e.event == 'login_success']) == 4
            assert all(password not in str(e.__dict__) for e in events)
            assert all(len(e.source_hash) == 64 and '127.0.0.1' not in str(e.__dict__) for e in events)


def test_atomic_failed_login_window_across_workers(pg_auth):
    db, _, settings, _, _ = pg_auth
    workers = [AuthService(db, settings) for _ in range(8)]
    tokens = [worker.csrf_session(None, '127.0.0.1') for worker in workers]
    def attempt(index):
        try:
            workers[index].login(tokens[index], 'operator', 'incorrect-disposable-password', '127.0.0.1')
            return 'unexpected-success'
        except AuthDenied:
            return 'denied'
        except RateLimited:
            return 'limited'
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(attempt, range(8)))
    assert outcomes.count('denied') == 5 and outcomes.count('limited') == 3
    with db.transaction() as session:
        assert session.get(AuthRateLimit, digest('login-account:127.0.0.1:operator')).attempts == 5
        assert session.get(AuthRateLimit, digest('login-ip:127.0.0.1')).attempts == 8
        assert session.scalar(select(func.count()).select_from(AuthEvent).where(AuthEvent.event == 'login_failed')) == 5


def test_same_preauth_session_cannot_login_twice_and_timezone_expiry(pg_auth):
    db, service, settings, _, password = pg_auth
    other = AuthService(db, settings)
    token = service.csrf_session(None, '127.0.0.1')
    def attempt(worker):
        try:
            return worker.login(token, 'operator', password, '127.0.0.1')[0]
        except AuthDenied:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        issued = [value for value in pool.map(attempt, (service, other)) if value]
    assert len(issued) == 1
    with db.engine.begin() as connection:
        connection.execute(text("SET LOCAL TIME ZONE 'Asia/Shanghai'"))
        with Session(bind=connection) as session:
            row = session.get(AuthSession, digest(issued[0]))
            assert row.expires_at.utcoffset() == timedelta(hours=8)
            assert service._valid(row)
            row.expires_at = utcnow() - timedelta(seconds=1)
            session.flush()
    assert service.current(issued[0]) is None


def test_foundation_migration_registration_to_assigned_access(pg_database):
    from tests.test_foundation_integration import exercise_foundation
    settings = Settings(_env_file=None,database_url=pg_database.engine.url.render_as_string(hide_password=False),auth_origin='https://runtu.test')
    exercise_foundation(pg_database,settings)
