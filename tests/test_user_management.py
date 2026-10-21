from concurrent.futures import ThreadPoolExecutor
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError

from backend.app import create_app
from backend.auth.service import HASHER, digest
from backend.models import AuthEvent, AuthSession, AuthUser
from backend.user_management import CreateUser, UpdateUser, UserDenied
from tests.test_auth import auth, login, ORIGIN
from tests.test_module_management import headers

PATH='/api/admin/users'
FIELDS={'id','username','role','active','created_at'}


def new_user(client, username='new-viewer', role=None):
    password=secrets.token_urlsafe(24)
    value={'username':username,'password':password}
    if role is not None: value['role']=role
    return client.post(PATH,json=value,headers=headers(client)),password


def edit(client,user,**changes):
    value={'role':user['role'],'active':user['active'],'expected_role':user['role'],'expected_active':user['active'],**changes}
    return client.patch(PATH+'/'+user['id'],json=value,headers=headers(client))


def exercise_user_contract(client):
    result,password=new_user(client)
    assert result.status_code==201
    row=result.json()
    assert set(row)==FIELDS and row['role']=='viewer' and row['active'] is True
    assert password not in result.text
    assert new_user(client)[0].status_code==409
    changed=edit(client,row,role='admin')
    assert changed.status_code==200 and changed.json()['role']=='admin'
    assert edit(client,row,active=False).status_code==409
    disabled=edit(client,changed.json(),active=False)
    assert disabled.status_code==200 and disabled.json()['active'] is False
    enabled=edit(client,disabled.json(),active=True)
    assert enabled.status_code==200
    page=client.get(PATH+'?limit=1')
    assert page.status_code==200 and page.headers['Cache-Control']=='no-store'
    assert len(page.json()['items'])==1 and page.json()['next_after_username']
    next_page=client.get(PATH+'?limit=1&after_username='+page.json()['next_after_username'])
    assert len(next_page.json()['items'])==1
    assert next_page.json()['items'][0]['username']>page.json()['items'][0]['username']
    for name in ['a_b','ab0','a.b','a-b']:
        assert new_user(client,name)[0].status_code==201
    names=[item['username'] for item in client.get(PATH+'?limit=50').json()['items']]
    assert names==sorted(names)
    return row['id'],password


def test_user_creation_update_pagination_and_persistence(auth,caplog):
    client,service,actor=auth
    assert login(client).status_code==200
    user_id,password=exercise_user_contract(client)
    assert password not in caplog.text
    with service.transaction() as session:
        row=session.get(AuthUser,user_id)
        assert HASHER.verify(row.password_hash,password) and row.password_hash.startswith('$argon2id$')
        assert row.role=='admin' and row.active and row.is_admin
        events=session.scalars(select(AuthEvent).where(AuthEvent.user_id==user_id)).all()
        assert len(events)==4 and all(password not in str(e.__dict__) for e in events)
    restarted=create_app(service.settings)
    try:
        assert any(u.id==user_id and u.role=='admin' for u in restarted.state.user_management.page(actor).items)
    finally: restarted.state.database.dispose()


@pytest.mark.parametrize('role,status',[('owner',200),('admin',403),('viewer',403)])
def test_user_permission_matrix_and_csrf(auth,role,status):
    client,service,actor=auth
    assert client.get(PATH).status_code==401
    assert client.post(PATH,json={},headers={'Origin':ORIGIN}).status_code==401
    assert login(client).status_code==200
    with service.transaction() as session: session.get(AuthUser,actor).role=role
    assert client.get(PATH).status_code==status
    value={'username':'candidate','password':secrets.token_urlsafe(24),'role':'owner'}
    assert client.post(PATH,json=value,headers={'Origin':ORIGIN}).status_code==403
    assert client.post(PATH,json=value,headers={'Origin':'https://untrusted.test'}).status_code==403
    assert client.post(PATH,json=value,headers=headers(client)).status_code==(201 if role=='owner' else 403)
    own={'id':actor,'role':role,'active':True}
    assert edit(client,own,role='owner').status_code==(200 if role=='owner' else 403)


def test_self_last_owner_and_session_revocation(auth):
    client,service,actor=auth
    assert login(client).status_code==200
    own=client.get(PATH).json()['items'][0]
    assert edit(client,own,active=False).status_code==403
    assert edit(client,own,role='viewer').status_code==403
    created,password=new_user(client,role='owner')
    row=created.json()
    # Even with another owner, self-demotion remains forbidden.
    assert edit(client,own,role='admin').status_code==403
    other=create_app(service.settings)
    try:
        with TestClient(other,base_url=ORIGIN) as target:
            assert login(target,password,'new-viewer').status_code==200
            assert edit(client,row,active=False).status_code==200
            assert target.get(PATH).status_code==401
            assert edit(client,dict(row,active=False),active=True).status_code==200
            assert target.get(PATH).status_code==401
    finally: other.state.database.dispose()
    assert client.get(PATH).status_code==200


@pytest.mark.parametrize('change',[{'username':'../bad'},{'username':3},{'password':'short'},{'password':'x'*129},{'role':'root'},{'active':False},{'is_admin':True},{'id':'chosen'}])
def test_create_invalid_body_never_echoes_secret(auth,change):
    client,*_=auth
    assert login(client).status_code==200
    secret=secrets.token_urlsafe(24)
    response=client.post(PATH,json={'username':'candidate','password':secret,**change},headers=headers(client))
    assert response.status_code==422 and secret not in response.text and response.headers['Cache-Control']=='no-store'


@pytest.mark.parametrize('query',['limit=0','limit=51','limit=sql-marker','after_username=../private','after_username='+'a'*65])
def test_users_bounded_query(auth,query):
    client,*_=auth
    assert login(client).status_code==200
    response=client.get(PATH+'?'+query)
    assert response.status_code==422 and 'sql-marker' not in response.text and 'private' not in response.text


def test_user_write_rollback_and_input_boundaries(auth):
    client,service,actor=auth
    assert login(client).status_code==200
    def fail(*_): raise OperationalError('event failure',{},Exception('fixture'))
    event.listen(AuthEvent,'before_insert',fail)
    try:
        result,password=new_user(client)
        assert result.status_code==503 and password not in result.text
    finally: event.remove(AuthEvent,'before_insert',fail)
    assert len(client.get(PATH).json()['items'])==1
    assert client.post(PATH,content=b'{' + b'x'*4096,headers={**headers(client),'Content-Type':'application/json'}).status_code==413
    assert client.post(PATH,content=b'{',headers={**headers(client),'Content-Type':'application/json'}).status_code==422
    assert client.post(PATH,content='body',headers={**headers(client),'Content-Type':'text/plain'}).status_code==415
    own=client.get(PATH).json()['items'][0]
    for change in [{'active':'false'},{'role':'root'},{'expected_role':'root'},{'password':secrets.token_urlsafe(24)}]:
        assert edit(client,own,**change).status_code==422


def test_update_rolls_back_account_sessions_and_audit_on_failure(auth):
    client,service,_=auth
    assert login(client).status_code==200
    created,password=new_user(client)
    row=created.json()
    other=create_app(service.settings)
    try:
        with TestClient(other,base_url=ORIGIN) as target:
            assert login(target,password,'new-viewer').status_code==200
            def fail(*_): raise OperationalError('event failure',{},Exception('fixture'))
            event.listen(AuthEvent,'before_insert',fail)
            try:
                assert edit(client,row,active=False).status_code==503
            finally: event.remove(AuthEvent,'before_insert',fail)
            # Rollback includes session revocation and account status, not just the event.
            assert target.get('/api/auth/me').json()['authenticated'] is True
            current=next(item for item in client.get(PATH).json()['items'] if item['id']==row['id'])
            assert current['active'] is True
    finally: other.state.database.dispose()


def test_concurrent_owners_cannot_remove_each_other_or_last_owner(auth):
    client,service,actor=auth
    assert login(client).status_code==200
    row=new_user(client,role='owner')[0].json()
    manager=client.app.state.user_management
    value=UpdateUser(role='viewer',active=True,expected_role='owner',expected_active=True)
    def demote(pair):
        try:
            manager.update(*pair,value)
            return 'saved'
        except UserDenied: return 'denied'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(demote,[(actor,row['id']),(row['id'],actor)]))==['denied','saved']
    with service.transaction() as session:
        assert session.scalar(select(func.count()).select_from(AuthUser).where(AuthUser.role=='owner',AuthUser.active.is_(True)))==1
