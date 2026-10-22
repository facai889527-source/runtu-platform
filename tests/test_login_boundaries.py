"""Real HTTP/session boundaries; all state belongs to disposable databases."""
from datetime import timedelta
from backend.models import AuthUser, AuthSession
from backend.auth.service import digest
from tests.test_auth import auth, login, ORIGIN
from tests.test_module_management import headers


def exercise_metadata_boundary(client, app, actor, password):
    metadata = ['/api/modules', '/api/modules/demo', '/api/modules/missing']
    # Supplied applications can have a different module; list and unknown still gate.
    for path in metadata:
        result = client.get(path)
        assert result.status_code == 401
        assert result.headers['cache-control'] == 'no-store'
        assert 'capabilities' not in result.text
    assert client.get('/api/health').status_code == 200
    assert client.get('/api/auth/me').json()['authenticated'] is False
    assert client.get('/api/auth/registration-policy').status_code == 200
    assert client.get('/api/admin/users').status_code == 401
    assert login(client, password).status_code == 200
    for role in ['owner', 'admin', 'viewer']:
        with app.state.database.transaction() as session:
            session.get(AuthUser, actor).role = role
        assert client.get('/api/modules').status_code == 200
        assert client.get('/api/modules/missing').status_code == 404
        expected = 200 if role == 'owner' else 403
        for path in ['/api/admin/users', '/api/admin/registration-policy', '/api/admin/registrations', f'/api/admin/users/{actor}/modules']:
            assert client.get(path).status_code == expected
        audit_status = 403 if role == 'viewer' else (200 if app.state.registry.detail('demo') else 404)
        assert client.get('/api/admin/modules/demo/changes').status_code == audit_status
        assert client.put('/api/admin/registration-policy', json=dict(enabled=True,approval_required=True,expected_revision=0), headers={'Origin': ORIGIN}).status_code == 403
    with app.state.database.transaction() as session:
        session.get(AuthUser, actor).role = 'owner'
        row = session.get(AuthSession, digest(client.cookies.get('__Host-runtu_session')))
        row.expires_at = app.state.auth_service.clock() - timedelta(seconds=1)
    assert client.get('/api/modules').status_code == 401
    assert login(client, password).status_code == 200
    with app.state.database.transaction() as session:
        session.get(AuthUser, actor).active = False
    assert client.get('/api/modules').status_code == 401
    with app.state.database.transaction() as session:
        session.get(AuthUser, actor).active = True
    assert client.get('/api/modules').status_code == 401
    assert login(client, password).status_code == 200
    assert client.get('/api/modules', headers={'Origin':'https://invalid.test'}).status_code == 403
    assert client.post('/api/auth/logout', headers=headers(client)).status_code == 200
    assert client.get('/api/modules').status_code == 401


def test_metadata_requires_valid_session_and_owner_management(auth):
    client, service, actor = auth
    from tests.test_auth import PASSWORD
    exercise_metadata_boundary(client, client.app, actor, PASSWORD)
