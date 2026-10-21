from datetime import timedelta

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import select, inspect, delete
from concurrent.futures import ThreadPoolExecutor
from alembic import command

from backend.app import create_app
from backend.auth.routes import require_admin
from backend.auth.service import AuthService, BootstrapRefused, digest
from backend.config import Settings
from backend.migrations import migrate_database, migration_config
from backend.database import Database
from backend.models import AuthEvent, AuthSession, AuthUser

ORIGIN = 'https://runtu.test'
PASSWORD = 'disposable-test-password-14'


@pytest.fixture
def auth(tmp_path):
    app = create_app(Settings(_env_file=None, database_url=f'sqlite:///{tmp_path / "auth.db"}', auth_origin=ORIGIN))
    migrate_database(app.state.database)
    service = app.state.auth_service
    user_id = service.bootstrap('operator', PASSWORD)

    @app.get('/test-admin')
    def probe(identity=Depends(require_admin)):
        return {'username': identity.username}

    with TestClient(app, base_url=ORIGIN) as client:
        yield client, service, user_id


def login(client, password=PASSWORD, username='operator'):
    csrf = client.get('/api/auth/csrf').json()['csrf_token']
    return client.post('/api/auth/login', json={'username': username, 'password': password},
                       headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf})


def test_real_login_rotation_cookie_logout_and_public_reads(auth):
    client, service, _ = auth
    assert client.get('/test-admin').status_code == 401
    initial = client.get('/api/auth/csrf')
    cookie = initial.headers['set-cookie']
    assert all(flag in cookie for flag in ('HttpOnly', 'Secure', 'SameSite=strict', 'Path=/'))
    old = client.cookies.get('__Host-runtu_session')
    assert old not in initial.text
    result = login(client)
    assert result.status_code == 200
    token = client.cookies.get('__Host-runtu_session')
    assert token != old and token not in result.text
    with service.transaction() as db:
        assert db.get(AuthSession, digest(old)) is None
        assert db.get(AuthSession, digest(token)).user_id
        assert db.scalar(select(AuthUser)).password_hash.startswith('$argon2id$')
    assert client.get('/api/auth/me').json()['authenticated'] is True
    assert client.get('/test-admin').status_code == 200
    csrf = client.get('/api/auth/csrf').json()['csrf_token']
    assert client.post('/api/auth/logout', headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf}).status_code == 200
    assert client.get('/api/auth/me').json() == {'authenticated': False, 'user': None}
    client.cookies.set('__Host-runtu_session', token)
    assert client.get('/test-admin').status_code == 401
    assert client.get('/api/health').status_code == 200
    assert client.get('/api/modules').status_code == 200
    assert client.get('/api/modules/demo').status_code == 200


def test_credentials_generic_and_no_secrets_in_audit_or_output(auth, caplog):
    client, service, _ = auth
    wrong = login(client, 'incorrect-secret')
    missing = login(client, 'incorrect-secret', 'unknown')
    assert wrong.status_code == missing.status_code == 401
    assert wrong.headers['Cache-Control'] == 'no-store'
    assert wrong.json() == missing.json() == {'detail': 'Invalid credentials'}
    with service.transaction() as db:
        events = db.scalars(select(AuthEvent)).all()
        assert [event.event for event in events].count('login_failed') == 2
        assert all(len(event.source_hash) == 64 for event in events)
    assert PASSWORD not in caplog.text and 'incorrect-secret' not in caplog.text
    assert PASSWORD not in wrong.text


def test_csrf_origin_host_and_input_rejections(auth):
    client, _, _ = auth
    assert client.post('/api/auth/login', json={}).status_code == 403
    csrf = client.get('/api/auth/csrf').json()['csrf_token']
    headers = {'Origin': ORIGIN, 'X-CSRF-Token': csrf}
    for changes in ({'Origin': 'https://attacker.test'}, {'Host': 'attacker.test'},
                    {'Sec-Fetch-Site': 'cross-site'}, {'X-CSRF-Token': '0' * 64}):
        assert client.post('/api/auth/login', headers=headers | changes, json={}).status_code == 403
    assert client.post('/api/auth/login', headers=headers, json={'password': PASSWORD}).status_code == 400
    assert client.post('/api/auth/login', headers=headers, content='x' * 5000,
                       ).status_code == 415
    assert client.post('/api/auth/login', headers=headers | {'Content-Type': 'application/json'},
                       content='x' * 5000).status_code == 413
    assert client.post('/api/auth/login', headers=headers | {'Content-Type': 'application/json'},
                       content='[' * 1500 + '0' + ']' * 1500).status_code == 400


@pytest.mark.parametrize('reason', ['absolute', 'idle', 'disabled', 'nonadmin'])
def test_session_expiry_disabled_and_admin_denial(auth, reason):
    client, service, user_id = auth
    assert login(client).status_code == 200
    token = client.cookies.get('__Host-runtu_session')
    with service.transaction() as db:
        if reason == 'disabled':
            db.get(AuthUser, user_id).active = False
        elif reason == 'nonadmin':
            db.get(AuthUser, user_id).is_admin = False
            db.get(AuthUser, user_id).role = 'viewer'
        else:
            row = db.get(AuthSession, digest(token))
            if reason == 'absolute':
                row.expires_at = service.clock() - timedelta(seconds=1)
            else:
                row.last_seen_at = service.clock() - timedelta(seconds=901)
    assert client.get('/test-admin').status_code == (403 if reason == 'nonadmin' else 401)
    if reason != 'nonadmin':
        with service.transaction() as db:
            assert db.get(AuthSession, digest(token)) is None


def test_rate_limit_reset_and_bootstrap_once(auth):
    client, service, _ = auth
    for _ in range(5):
        assert login(client, 'wrong').status_code == 401
    result = login(client, 'wrong')
    assert result.status_code == 429 and result.headers['Retry-After'] == '300'
    now = service.clock()
    service.clock = lambda: now + timedelta(seconds=301)
    assert login(client).status_code == 200
    with pytest.raises(BootstrapRefused):
        service.bootstrap('second-admin', PASSWORD)


def test_unconfigured_fails_closed_without_changing_anonymous_contract():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get('/api/auth/me').status_code == 503
        assert client.get('/api/health').json()['database'] == 'not_configured'
        assert client.get('/api/modules').status_code == 200
        assert client.get('/openapi.json').status_code == 404


def test_https_origin_cannot_be_used_over_http(auth):
    client, _, _ = auth
    assert client.get('http://runtu.test/api/auth/csrf').status_code == 403


def test_expired_prelogin_csrf_and_cleanup(auth):
    client, service, _ = auth
    csrf = client.get('/api/auth/csrf').json()['csrf_token']
    now = service.clock()
    service.clock = lambda: now + timedelta(seconds=601)
    assert client.post('/api/auth/login', json={'username': 'operator', 'password': PASSWORD},
        headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf}).status_code == 403
    assert service.cleanup() == 1


def test_bootstrap_concurrency_and_marker_survives_user_deletion(tmp_path):
    db = Database(f'sqlite:///{tmp_path / "concurrent.db"}')
    migrate_database(db)
    service = AuthService(db, Settings(_env_file=None))
    def attempt(index):
        try:
            service.bootstrap(f'admin-{index}', PASSWORD)
            return True
        except BootstrapRefused:
            return False
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sum(pool.map(attempt, [1, 2])) == 1
        with db.transaction() as session:
            session.execute(delete(AuthUser))
        with pytest.raises(BootstrapRefused):
            service.bootstrap('third-admin', PASSWORD)
    finally:
        db.dispose()


def test_interactive_cli_uses_real_storage_and_refuses_pipe(auth, monkeypatch, capsys):
    from backend import auth_cli
    client, service, _ = auth
    monkeypatch.setenv('RUNTU_DATABASE_URL', service.database.engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr(auth_cli.sys.stdin, 'isatty', lambda: False)
    assert auth_cli.main(['bootstrap-admin']) == 1
    monkeypatch.setattr(auth_cli.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr('builtins.input', lambda _: 'duplicate')
    monkeypatch.setattr(auth_cli.getpass, 'getpass', lambda _: PASSWORD)
    assert auth_cli.main(['bootstrap-admin']) == 1
    output = capsys.readouterr()
    assert PASSWORD not in output.out + output.err


def test_missing_auth_schema_fails_closed_and_upgrade_downgrade_preserves_config(tmp_path):
    db = Database(f'sqlite:///{tmp_path / "legacy.db"}')
    cfg = migration_config()
    with db.engine.begin() as connection:
        cfg.attributes['connection'] = connection
        command.upgrade(cfg, '0001_module_configs')
    app = create_app(Settings(_env_file=None, database_url=str(db.engine.url), auth_origin=ORIGIN))
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get('/api/auth/me').status_code == 503
        assert client.get('/api/modules').status_code == 503  # Missing state migration fails closed.
    migrate_database(db)
    assert 'auth_users' in inspect(db.engine).get_table_names()
    with db.engine.begin() as connection:
        cfg.attributes['connection'] = connection
        command.downgrade(cfg, '0001_module_configs')
    assert 'auth_users' not in inspect(db.engine).get_table_names()
    assert not db.is_ready()  # New application requires the state columns.
    db.dispose()


def test_loopback_http_requires_explicit_opt_in(tmp_path):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_origin='http://127.0.0.1:5173')
    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_origin='http://public.test', auth_allow_loopback_http=True)
    app = create_app(Settings(_env_file=None, database_url=f'sqlite:///{tmp_path / "dev.db"}',
        auth_origin='http://127.0.0.1:5173', auth_allow_loopback_http=True))
    migrate_database(app.state.database)
    with TestClient(app, base_url='http://127.0.0.1:5173', client=('127.0.0.1', 12345)) as client:
        cookie = client.get('/api/auth/csrf').headers['set-cookie']
        assert 'runtu_dev_session=' in cookie and 'HttpOnly' in cookie and 'Secure' not in cookie
    with TestClient(app, base_url='http://127.0.0.1:5173', client=('192.0.2.1', 12345)) as client:
        assert client.get('/api/auth/csrf').status_code == 403
