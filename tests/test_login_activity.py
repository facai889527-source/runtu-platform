from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from alembic import command

from backend.auth.service import digest
from backend.database import Database
from backend.migrations import migrate_database, migration_config
from backend.models import AuthEvent, AuthSession, AuthUser
from tests.test_auth import auth, login, ORIGIN


@pytest.mark.parametrize('role', ['owner', 'admin', 'viewer'])
def test_previous_login_is_session_snapshot_not_current_even_with_equal_timestamps(auth, role):
    original, service, user_id = auth
    with service.transaction() as db:
        db.get(AuthUser, user_id).role = role
    instant = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)
    service.clock = lambda: instant
    with TestClient(original.app, base_url=ORIGIN, client=('198.51.100.17', 5000)) as first:
        assert first.get('/api/auth/activity').status_code == 401
        assert login(first).status_code == 200
        assert first.get('/api/auth/activity').json() == {'previous_login': None}
        with TestClient(original.app, base_url=ORIGIN, client=('2001:db8::7', 5001)) as second:
            assert login(second, 'wrong-password').status_code == 401
            assert login(second).status_code == 200
            result = second.get('/api/auth/activity')
            assert result.headers['cache-control'] == 'no-store'
            assert result.json() == {'previous_login': {'at': instant.isoformat(), 'ip': '198.51.100.17'}}
            assert first.get('/api/auth/activity').json() == {'previous_login': None}
            assert second.get('/api/auth/activity?user_id=another').status_code == 422
            with service.transaction() as db:
                successes = db.scalars(select(AuthEvent).where(AuthEvent.event == 'login_success')).all()
                assert len(successes) == 2
                assert {event.source_ip for event in successes} == {'198.51.100.17', '2001:db8::7'}
                foreign = AuthEvent(id=str(uuid4()), event='login_success', user_id='another',
                    source_hash='0'*64, source_ip='192.0.2.99', created_at=instant)
                db.add(foreign)
                row = db.get(AuthSession, digest(second.cookies.get('__Host-runtu_session')))
                row.previous_login_event_id = foreign.id
            assert second.get('/api/auth/activity').json() == {'previous_login': None}


@pytest.mark.parametrize('headers', [
    {'X-Forwarded-For': '203.0.113.9'}, {'Forwarded': 'for=203.0.113.9'},
    {'X-Real-IP': '203.0.113.9'}, {'X-Forwarded-For': 'bad, 203.0.113.9'},
])
def test_forwarded_addresses_never_become_recorded_client_ip(auth, headers):
    original, service, _ = auth
    with TestClient(original.app, base_url=ORIGIN, client=('198.51.100.22', 5000)) as client:
        client.headers.update(headers)
        assert login(client).status_code == 200
        client.headers.clear()
        assert login(client).status_code == 200
        previous = client.get('/api/auth/activity').json()['previous_login']
        assert previous['ip'] is None and previous['at']
        with service.transaction() as db:
            failed = db.scalars(select(AuthEvent).where(AuthEvent.event == 'login_failed')).all()
            assert all(event.source_ip is None for event in failed)


def test_unknown_peer_ip_and_login_transaction_failure_do_not_invent_history(auth, monkeypatch):
    client, service, user_id = auth
    assert login(client).status_code == 200  # TestClient peer is a hostname, not an IP.
    assert login(client).status_code == 200
    assert client.get('/api/auth/activity').json()['previous_login']['ip'] is None
    with service.transaction() as db:
        before = db.get(AuthUser, user_id).last_login_event_id
    original = service._event
    def fail(session, event, *args, **kwargs):
        if event == 'login_success':
            raise RuntimeError('disposable audit failure')
        return original(session, event, *args, **kwargs)
    monkeypatch.setattr(service, '_event', fail)
    with pytest.raises(RuntimeError, match='disposable audit failure'):
        login(client)
    with service.transaction() as db:
        assert db.get(AuthUser, user_id).last_login_event_id == before
    assert client.get('/api/auth/activity').status_code == 200


def test_nullable_activity_migration_preserves_legacy_data_without_backfill(tmp_path):
    db = Database(f'sqlite:///{tmp_path / "legacy.db"}')
    try:
        migrate_database(db, '0006_registration_policy')
        tables = set(inspect(db.engine).get_table_names())
        with db.engine.begin() as connection:
            connection.execute(text("INSERT INTO auth_users (id,username,password_hash,active,is_admin,role,created_at) VALUES ('legacy','legacy','fixture-hash',1,0,'viewer',CURRENT_TIMESTAMP)"))
            connection.execute(text("INSERT INTO auth_events (id,event,user_id,source_hash,created_at) VALUES ('event','login_success','legacy','fixture-source-hash','2019-01-01 00:00:00')"))
            connection.execute(text("INSERT INTO auth_events (id,event,user_id,source_hash,created_at) VALUES ('current','login_success','legacy','fixture-source-hash','2020-01-01 00:00:00')"))
            connection.execute(text("INSERT INTO auth_sessions (token_hash,user_id,created_at,expires_at,last_seen_at) VALUES ('fixture','legacy','2020-01-01 00:00:00.000000','2030-01-01','2020-01-01')"))
            connection.execute(text("INSERT INTO auth_users (id,username,password_hash,active,is_admin,role,created_at) VALUES ('other','other','fixture-hash',1,0,'viewer',CURRENT_TIMESTAMP)"))
            connection.execute(text("INSERT INTO auth_events (id,event,user_id,source_hash,created_at) VALUES ('other-event','login_success','other','fixture-source-hash','2025-01-01')"))
        migrate_database(db, '0007_login_activity')
        assert set(inspect(db.engine).get_table_names()) == tables
        with db.transaction() as session:
            assert session.get(AuthUser, 'legacy').last_login_event_id == 'current'
            assert session.get(AuthSession, 'fixture').previous_login_event_id == 'event'
            assert session.get(AuthEvent, 'event').source_ip is None
        config = migration_config()
        with db.engine.begin() as connection:
            config.attributes['connection'] = connection
            command.downgrade(config, '0006_registration_policy')
            assert connection.scalar(text("SELECT username FROM auth_users WHERE id='legacy'")) == 'legacy'
            assert connection.scalar(text('SELECT count(*) FROM auth_events')) == 3
    finally:
        db.dispose()
