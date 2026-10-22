import secrets
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError

from backend.auth.service import AuthDenied, HASHER, digest
from backend.models import AuthEvent, AuthSession, AuthUser, RegistrationApplication, UserModuleGrant
from backend.migrations import migration_config
from backend.registration import PolicyInput, Signup
from tests.test_auth import auth, login, ORIGIN
from tests.test_module_management import headers

POLICY='/api/admin/registration-policy'
PENDING='/api/admin/registrations'


def set_policy(client, enabled=True, approval=True):
    old=client.get(POLICY).json()
    return client.put(POLICY,json=dict(enabled=enabled,approval_required=approval,expected_revision=old['revision']),headers=headers(client))


def applicant(app):
    return TestClient(app,base_url=ORIGIN)


def signup(client, name='candidate', **extra):
    password=secrets.token_urlsafe(24)
    result=client.post('/api/auth/register',json=dict(username=name,password=password,**extra),headers=headers(client))
    return result,password


def exercise_registration_contract(owner, app):
    assert owner.get('/api/auth/registration-policy').json()==dict(enabled=False,approval_required=True)
    with applicant(app) as guest:
        assert signup(guest)[0].status_code==403
        assert set_policy(owner).status_code==200
        result,password=signup(guest)
        assert result.status_code==202 and result.json()=={'state':'submitted'}
        assert password not in result.text and 'no-store' in result.headers['Cache-Control']
        assert guest.get('/api/auth/me').json()['authenticated'] is False
        assert login(guest,password,'candidate').status_code==401
        row=owner.get(PENDING).json()['items'][0]
        assert row['state']=='pending'
        value=dict(role='owner',active=True,expected_role='viewer',expected_active=False)
        assert owner.patch('/api/admin/users/'+row['id'],json=value,headers=headers(owner)).status_code==403
        approved=owner.post(PENDING+'/'+row['id']+'/approve',headers=headers(owner))
        assert approved.status_code==200 and approved.json()=={'state':'approved'}
        assert owner.post(PENDING+'/'+row['id']+'/approve',headers=headers(owner)).status_code==200
        assert login(guest,password,'candidate').status_code==200
        access=guest.get('/api/admin/me').json()
        assert access['role']=='viewer' and 'users.manage' not in access['permissions']
        assert guest.get('/api/me/modules').json()['items']==[]
        assert owner.get(PENDING).json()['items']==[]
    return row['id']


def test_default_registration_approval_and_no_privilege(auth,caplog):
    client,service,_=auth
    assert login(client).status_code==200
    user_id=exercise_registration_contract(client,client.app)
    with service.transaction() as session:
        assert session.scalar(select(func.count()).select_from(UserModuleGrant).where(UserModuleGrant.user_id==user_id))==0
        assert session.scalar(select(func.count()).select_from(AuthEvent).where(AuthEvent.event=='registration_approved'))==1
    assert 'password_hash' not in caplog.text


@pytest.mark.parametrize('role,status',[('owner',200),('admin',403),('viewer',403)])
def test_registration_owner_matrix_csrf_and_stale_policy(auth,role,status):
    client,service,actor=auth
    assert client.get(POLICY).status_code==401
    assert login(client).status_code==200
    with service.transaction() as session: session.get(AuthUser,actor).role=role
    assert client.get(POLICY).status_code==status
    value=dict(enabled=True,approval_required=True,expected_revision=0)
    assert client.put(POLICY,json=value,headers={'Origin':ORIGIN}).status_code==403
    assert client.put(POLICY,json=value,headers=headers(client)).status_code==status
    assert client.get(PENDING).status_code==status
    if role=='owner':
        assert client.put(POLICY,json=value,headers=headers(client)).status_code==409
        value['expected_revision']=1
        assert client.put(POLICY,json=value,headers=headers(client)).json()['revision']==1


def test_signup_input_origin_rate_limits_and_duplicates(auth):
    owner,service,_=auth
    assert login(owner).status_code==200 and set_policy(owner).status_code==200
    with applicant(owner.app) as guest:
        for extra in [{'role':'owner'},{'active':True},{'is_admin':True},{'grants':['demo']}]:
            result,password=signup(guest,**extra)
            assert result.status_code==422 and password not in result.text
        assert guest.post('/api/auth/register',json={},headers={'Origin':ORIGIN}).status_code==403
        assert guest.post('/api/auth/register',json={},headers={**headers(guest),'Origin':'https://evil.test'}).status_code==403
        assert signup(guest,'duplicate')[0].status_code==202
        assert signup(guest,'duplicate')[0].status_code==202
        assert signup(guest,'duplicate')[0].status_code==202
        assert signup(guest,'duplicate')[0].status_code==429
    with service.transaction() as session:
        assert session.scalar(select(func.count()).select_from(AuthUser).where(AuthUser.username=='duplicate'))==1


def test_policy_change_does_not_approve_existing_and_direct_viewer(auth):
    owner,service,_=auth
    assert login(owner).status_code==200 and set_policy(owner).status_code==200
    with applicant(owner.app) as guest:
        assert signup(guest,'pending')[0].status_code==202
        assert set_policy(owner,approval=False).status_code==200
        result,password=signup(guest,'direct')
        assert result.status_code==202 and login(guest,password,'direct').status_code==200
        assert guest.get('/api/admin/me').json()['role']=='viewer'
    assert len(owner.get(PENDING).json()['items'])==1
    with service.transaction() as session:
        pending=session.scalar(select(AuthUser).where(AuthUser.username=='pending'))
        assert not pending.active and pending.role=='viewer'


def test_registration_and_policy_audit_failure_rolls_back(auth):
    owner,service,_=auth
    assert login(owner).status_code==200 and set_policy(owner).status_code==200
    def fail(*_): raise OperationalError('fixture audit',{},Exception('temporary'))
    with applicant(owner.app) as guest:
        event.listen(AuthEvent,'before_insert',fail)
        try:
            assert signup(guest,'rollback')[0].status_code==503
            assert set_policy(owner,enabled=False).status_code==503
        finally: event.remove(AuthEvent,'before_insert',fail)
        assert owner.get(POLICY).json()['enabled'] is True
        with service.transaction() as session:
            assert session.scalar(select(AuthUser.id).where(AuthUser.username=='rollback')) is None
        assert signup(guest,'rollback')[0].status_code==202
        row=owner.get(PENDING).json()['items'][0]
        event.listen(AuthEvent,'before_insert',fail)
        try: assert owner.post(PENDING+'/'+row['id']+'/approve',headers=headers(owner)).status_code==503
        finally: event.remove(AuthEvent,'before_insert',fail)
        with service.transaction() as session:
            assert not session.get(AuthUser,row['id']).active
            assert session.get(RegistrationApplication,row['id']).pending


def test_concurrent_approval_and_revoked_owner_session(auth):
    owner,service,actor=auth
    assert login(owner).status_code==200 and set_policy(owner).status_code==200
    with applicant(owner.app) as guest: assert signup(guest)[0].status_code==202
    row=owner.get(PENDING).json()['items'][0]
    key=digest(owner.cookies.get('__Host-runtu_session'))
    def approve(_): return owner.app.state.registration.approve(actor,key,row['id'])
    with ThreadPoolExecutor(max_workers=2) as pool: assert all(x['state']=='approved' for x in pool.map(approve,range(2)))
    with service.transaction() as session:
        assert session.scalar(select(func.count()).select_from(AuthEvent).where(AuthEvent.event=='registration_approved'))==1
        session.delete(session.get(AuthSession,key))
    with pytest.raises(AuthDenied): owner.app.state.registration.save_policy(actor,key,PolicyInput(enabled=False,approval_required=True,expected_revision=1))


def test_pending_downgrade_refused_and_missing_policy_fails_closed(auth):
    owner,service,_=auth
    assert login(owner).status_code==200 and set_policy(owner).status_code==200
    with applicant(owner.app) as guest: assert signup(guest)[0].status_code==202
    with pytest.raises(RuntimeError,match='Resolve pending'):
        with service.database.engine.begin() as connection:
            config=migration_config();config.attributes['connection']=connection
            command.downgrade(config,'0005_user_module_access')
    row=owner.get(PENDING).json()['items'][0]
    assert owner.post(PENDING+'/'+row['id']+'/approve',headers=headers(owner)).status_code==200
    with service.database.engine.begin() as connection:
        config=migration_config();config.attributes['connection']=connection
        command.check(config)
        command.downgrade(config,'0005_user_module_access')
    assert owner.get('/api/auth/registration-policy').status_code==503


def test_signup_rechecks_policy_after_hash_and_consumes_anonymous_context(auth,monkeypatch):
    owner,service,_=auth
    assert login(owner).status_code==200 and set_policy(owner).status_code==200
    with applicant(owner.app) as guest:
        raw_key=guest.get('/api/auth/csrf').headers['set-cookie'].split(';')[0].split('=',1)[1]
        value=Signup(username='racing-policy',password=secrets.token_urlsafe(24))
        original=HASHER.hash
        def paused(password):
            encoded=original(password)
            assert set_policy(owner,enabled=False).status_code==200
            return encoded
        from types import SimpleNamespace
        import backend.registration as registration_module
        monkeypatch.setattr(registration_module,'HASHER',SimpleNamespace(hash=paused))
        from backend.user_management import UserDenied
        with pytest.raises(UserDenied): owner.app.state.registration.signup(digest(raw_key),value,'isolated')
        monkeypatch.setattr(registration_module,'HASHER',HASHER)
        assert set_policy(owner).status_code==200
        owner.app.state.registration.signup(digest(raw_key),value,'isolated')
        with pytest.raises(AuthDenied): owner.app.state.registration.signup(digest(raw_key),value,'isolated')
    with service.transaction() as session:
        assert session.scalar(select(func.count()).select_from(AuthUser).where(AuthUser.username=='racing-policy'))==1


def test_signup_concurrent_duplicate_creates_one_pending_account(auth):
    owner,service,_=auth
    assert login(owner).status_code==200 and set_policy(owner).status_code==200
    values=[]
    for i in range(2):
        token=service.csrf_session(None,'fixture-'+str(i))
        values.append((digest(token),Signup(username='concurrent',password=secrets.token_urlsafe(24)),'fixture-'+str(i)))
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(v=={'state':'submitted'} for v in pool.map(lambda args:owner.app.state.registration.signup(*args),values))
    with service.transaction() as session:
        assert session.scalar(select(func.count()).select_from(AuthUser).where(AuthUser.username=='concurrent'))==1
        assert session.scalar(select(func.count()).select_from(RegistrationApplication))==1


def test_registration_body_bounds_and_invalid_queries_are_sanitized(auth):
    owner,_,_=auth
    assert login(owner).status_code==200
    with applicant(owner.app) as guest:
        assert guest.post('/api/auth/register',content=b'x'*4097,headers={**headers(guest),'Content-Type':'application/json'}).status_code==413
        assert guest.post('/api/auth/register',content='private-marker',headers={**headers(guest),'Content-Type':'text/plain'}).status_code==415
        result=guest.post('/api/auth/register',json={'username':'candidate','password':'short-private'},headers=headers(guest))
        assert result.status_code==422 and 'short-private' not in result.text
    result=owner.get(PENDING+'?limit=private-marker')
    assert result.status_code==422 and 'private-marker' not in result.text
