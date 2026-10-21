from datetime import datetime, timezone

import pytest
from sqlalchemy import event, update
from sqlalchemy.exc import OperationalError

from backend.models import AuthUser, ModuleChangeRecord
from tests.test_auth import login, ORIGIN
from tests.test_module_management import managed, headers, payload

PATH = '/api/admin/modules/example/changes'
FIELDS = {'module_id', 'actor_id', 'action', 'created_at', 'revision'}


def exercise_audit_pages(client):
    """Same HTTP contract runs on temporary SQLite and owned CI PostgreSQL."""
    assert client.get(PATH).json() == {'items': [], 'next_before_revision': None}
    for revision in range(12):
        result = client.put('/api/admin/modules/example', json=payload(revision=revision, interval=revision+40), headers=headers(client))
        assert result.status_code == 200
    first = client.get(PATH+'?limit=3')
    assert first.status_code == 200 and first.headers['Cache-Control'] == 'no-store'
    assert [row['revision'] for row in first.json()['items']] == [12,11,10]
    cursor = first.json()['next_before_revision']
    assert cursor == 10
    # A concurrent newer insert cannot shift the older page boundary.
    assert client.put('/api/admin/modules/example', json=payload(revision=12, interval=99), headers=headers(client)).status_code == 200
    seen = [12,11,10]
    while cursor is not None:
        page = client.get(PATH+f'?limit=3&before_revision={cursor}').json()
        for row in page['items']:
            assert set(row) == FIELDS and row['module_id'] == 'example' and row['action'] == 'updated'
            assert datetime.fromisoformat(row['created_at'].replace('Z','+00:00')).utcoffset().total_seconds() == 0
        seen.extend(row['revision'] for row in page['items'])
        cursor = page['next_before_revision']
    assert seen == list(range(12,0,-1))
    assert len(client.get(PATH).json()['items']) == 10
    assert len(client.get(PATH+'?limit=50').json()['items']) == 13
    assert client.get(PATH+'?before_revision=1').json() == {'items': [], 'next_before_revision': None}


def test_audit_transactions_keyset_filter_and_stable_sort(managed):
    client, db, actor, _ = managed
    assert login(client).status_code == 200
    exercise_audit_pages(client)
    # Same timestamps still order by unique module revision; other module excluded.
    assert client.put('/api/admin/modules/required', json=payload(True), headers=headers(client)).status_code == 200
    with db.transaction() as session:
        session.execute(update(ModuleChangeRecord).values(created_at=datetime(2026,1,1,tzinfo=timezone.utc)))
    page = client.get(PATH+'?limit=50').json()
    assert [row['revision'] for row in page['items']] == list(range(13,0,-1))
    assert all(row['actor_id'] == actor and set(row) == FIELDS for row in page['items'])
    assert len(client.get('/api/admin/modules/required/changes').json()['items']) == 1


@pytest.mark.parametrize('role,expected', [('owner',200),('admin',200),('viewer',403)])
def test_audit_permission_current_role_and_revocation(managed,role,expected):
    client,db,actor,_=managed
    assert client.get(PATH).status_code == 401
    assert login(client).status_code == 200
    with db.transaction() as session:
        session.get(AuthUser,actor).role=role
    response=client.get(PATH)
    assert response.status_code == expected
    assert response.headers['Cache-Control']=='no-store'
    assert client.get(PATH,headers={'Origin':'https://untrusted.test'}).status_code==403
    with db.transaction() as session:
        session.get(AuthUser,actor).active=False
    assert client.get(PATH).status_code==401


@pytest.mark.parametrize('query', ['limit=0','limit=51','limit=-1','limit=1.5','limit=sql-marker','before_revision=0','before_revision=-1','before_revision=2147483648','before_revision=sql-marker'])
def test_audit_bounded_parameters_no_input_echo(managed,query):
    client,*_=managed
    assert login(client).status_code==200
    response=client.get(PATH+'?'+query)
    assert response.status_code==422 and response.headers['Cache-Control']=='no-store'
    assert 'sql-marker' not in response.text


def test_audit_empty_unknown_rollback_and_noop(managed):
    client,db,_,_=managed
    assert login(client).status_code==200
    assert client.get('/api/admin/modules/missing/changes').status_code==404
    def fail(*_args): raise OperationalError('audit failure',{},Exception('fixture'))
    event.listen(ModuleChangeRecord,'before_insert',fail)
    try:
        assert client.put('/api/admin/modules/example',json=payload(),headers=headers(client)).status_code==503
    finally:
        event.remove(ModuleChangeRecord,'before_insert',fail)
    assert client.get(PATH).json()['items']==[]
    assert client.put('/api/admin/modules/example',json=payload(),headers=headers(client)).status_code==200
    assert client.put('/api/admin/modules/example',json=payload(),headers=headers(client)).status_code==200
    assert len(client.get(PATH).json()['items'])==1
    with db.engine.begin() as connection:
        connection.exec_driver_sql('DROP TABLE module_changes')
    response=client.get(PATH)
    assert response.status_code==503 and response.headers['Cache-Control']=='no-store'
    assert response.json()=={'detail':'Module audit storage unavailable'}
