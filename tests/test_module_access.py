from concurrent.futures import ThreadPoolExecutor
import secrets

import pytest
from alembic import command
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import event, func, inspect, select, update
from sqlalchemy.exc import OperationalError

from backend.app import create_app
from backend.auth.service import AuthUnavailable, digest
from backend.config import Settings
from backend.migrations import migrate_database, migration_config
from backend.models import AuthUser, ModuleConfigRecord, UserModuleGrant, UserModuleGrantEvent
from backend.module_access import GrantInput, require_module_access
from backend.user_management import CreateUser, UserDenied
from tests.test_auth import auth, login, ORIGIN
from tests.test_module_management import headers
from tests.test_module_lifecycle import make_module


def access_modules():
    modules=[make_module(module_id=name) for name in ['alpha','beta','required','auth','example']]
    for module in modules[:4]:
        module.manifest=module.manifest.model_copy(update={'access_mode':'assigned','required':module.manifest.id=='required'})
    return modules


@pytest.fixture
def assigned(tmp_path):
    settings=Settings(_env_file=None,database_url=f'sqlite:///{tmp_path/"grants.db"}',auth_origin=ORIGIN)
    app=create_app(settings,modules=access_modules())
    migrate_database(app.state.database)
    password=secrets.token_urlsafe(24)
    actor=app.state.auth_service.bootstrap('operator',password)
    app.add_api_route('/assigned-probe',lambda:{'ok':True},dependencies=[Depends(require_module_access('alpha'))])
    with TestClient(app,base_url=ORIGIN) as client:
        yield client,app,actor,password,settings


def put_grant(client,user_id,module_id='alpha',granted=True,expected=False):
    return client.put(f'/api/admin/users/{user_id}/modules/{module_id}',json={'granted':granted,'expected_granted':expected},headers=headers(client))


def exercise_grant_contract(client,app,actor):
    target=app.state.user_management.create(actor,CreateUser(username='grant-reader',password=secrets.token_urlsafe(24)))
    assert client.get('/api/me/modules').json()=={'items':[],'next_after_module':None}
    # Management roles do not silently gain assigned business API access.
    assert client.get('/api/modules/alpha/ping').status_code==403
    assert put_grant(client,actor).status_code==200
    assert put_grant(client,actor).status_code==200
    assert client.get('/api/modules/alpha/ping').status_code==200
    assert put_grant(client,target.id).status_code==200
    page=client.get(f'/api/admin/users/{target.id}/modules?limit=1').json()
    assert [row['module_id'] for row in page['items']]==['alpha'] and page['next_after_module']=='alpha'
    assert client.get(f'/api/admin/users/{target.id}/modules?limit=1&after_module=alpha').json()['items'][0]['module_id']=='beta'
    assert client.get('/api/me/modules').json()['items']==[{'module_id':'alpha','name':'Example','enabled':True,'granted':True}]
    # Global disable wins without deleting grants.
    with app.state.database.transaction() as session:
        session.add(ModuleConfigRecord(module_id='alpha',show_in_navigation=True,enabled=False,revision=0))
    assert client.get('/api/modules/alpha/ping').status_code==404
    assert client.get('/api/me/modules').json()['items']==[]
    with app.state.database.transaction() as session:
        session.execute(update(ModuleConfigRecord).where(ModuleConfigRecord.module_id=='alpha').values(enabled=True))
    assert put_grant(client,actor,granted=False,expected=True).status_code==200
    assert client.get('/api/modules/alpha/ping').status_code==403
    return target.id


def test_grant_contract_enforcement_and_public_compatibility(assigned):
    client,app,actor,password,_=assigned
    assert client.get('/api/modules/example/ping').status_code==200
    assert client.get('/api/modules').status_code==401
    assert client.get('/api/modules/alpha/ping').status_code==401
    assert client.get('/api/me/modules').status_code==401
    assert login(client,password).status_code==200
    exercise_grant_contract(client,app,actor)
    assert client.get('/assigned-probe').status_code==403
    assert put_grant(client,actor).status_code==200
    assert client.get('/assigned-probe').status_code==200
    assert client.post('/api/modules/alpha/action',headers=headers(client)).status_code==403


def test_default_public_demo_has_no_fake_grant_candidate(auth):
    client,_,actor=auth
    assert client.get('/api/modules/demo').status_code==401
    assert login(client).status_code==200
    assert client.get('/api/modules').json()[0]['access_mode']=='public'
    assert client.get('/api/me/modules').json()=={'items':[],'next_after_module':None}
    assert client.get(f'/api/admin/users/{actor}/modules').json()=={'items':[],'next_after_module':None}
    assert put_grant(client,actor,'demo').status_code==403


@pytest.mark.parametrize('role,expected',[('owner',200),('admin',403),('viewer',403)])
def test_grant_edit_permission_matrix_and_user_disabling(assigned,role,expected):
    client,app,actor,password,_=assigned
    assert login(client,password).status_code==200
    with app.state.database.transaction() as session: session.get(AuthUser,actor).role=role
    url=f'/api/admin/users/{actor}/modules'
    assert client.get(url).status_code==expected
    assert put_grant(client,actor).status_code==expected
    assert client.get('/api/me/modules').status_code==200
    with app.state.database.transaction() as session: session.get(AuthUser,actor).active=False
    assert client.get('/api/me/modules').status_code==401
    assert client.get('/api/modules/alpha/ping').status_code==401


def test_grant_rejection_boundaries_no_secret_echo(assigned):
    client,app,actor,password,_=assigned
    assert login(client,password).status_code==200
    for module_id in ['example','required','auth','missing']:
        assert put_grant(client,actor,module_id).status_code==403
    assert put_grant(client,'unknown').status_code==404
    path=f'/api/admin/users/{actor}/modules/alpha'
    assert client.put(path,json={'granted':True,'expected_granted':False},headers={'Origin':ORIGIN}).status_code==403
    assert client.put(path,json={},headers={'Origin':'https://untrusted.test'}).status_code==403
    for value in [{'granted':'true','expected_granted':False},{'granted':True,'expected_granted':False,'private':'not-for-echo'}]:
        response=client.put(path,json=value,headers=headers(client))
        assert response.status_code==422 and 'not-for-echo' not in response.text
    for query in ['limit=0','limit=51','after_module=../private']:
        assert client.get('/api/me/modules?'+query).status_code==422
    assert client.get('/api/me/modules').headers['Cache-Control']=='no-store'


def test_grant_concurrency_noop_audit_and_rollback(assigned):
    client,app,actor,password,_=assigned
    assert login(client,password).status_code==200
    service=app.state.module_access
    def grant(_): return service.save(actor,actor,'alpha',GrantInput(granted=True,expected_granted=False))
    with ThreadPoolExecutor(max_workers=2) as pool: assert all(row.granted for row in pool.map(grant,range(2)))
    with app.state.database.transaction() as session:
        rows=session.scalars(select(UserModuleGrantEvent)).all()
        assert len(rows)==1 and set(rows[0].__table__.columns.keys())=={'id','actor_id','user_id','module_id','action','created_at'}
    def fail(*_): raise OperationalError('grant audit fixture',{},Exception('disposable'))
    event.listen(UserModuleGrantEvent,'before_insert',fail)
    try: assert put_grant(client,actor,granted=False,expected=True).status_code==503
    finally: event.remove(UserModuleGrantEvent,'before_insert',fail)
    assert client.get('/api/modules/alpha/ping').status_code==200
    assert put_grant(client,actor,granted=False,expected=False).status_code==409
    assert put_grant(client,actor,granted=False,expected=True).status_code==200
    assert client.get('/api/modules/alpha/ping').status_code==403


def test_disabled_module_grants_and_disabled_target_cannot_bypass(assigned):
    client,app,actor,password,_=assigned
    assert login(client,password).status_code==200
    target=app.state.user_management.create(actor,CreateUser(username='disabled-user',password=secrets.token_urlsafe(24)))
    with app.state.database.transaction() as session:
        session.get(AuthUser,target.id).active=False
        session.add(ModuleConfigRecord(module_id='beta',show_in_navigation=True,enabled=False,revision=0))
    assert put_grant(client,target.id).status_code==403
    response=put_grant(client,actor,'beta')
    assert response.status_code==200 and response.json()=={'module_id':'beta','name':'Example','granted':True,'enabled':False}
    assert client.get('/api/modules/beta/ping').status_code==404
    assert client.get('/api/me/modules').json()['items']==[]


def test_waiting_grant_write_rechecks_revoked_session_inside_transaction(assigned):
    client,app,actor,password,_=assigned
    assert login(client,password).status_code==200
    # Disposable fixture only: simulate revocation after the HTTP dependency ran.
    session_key=digest(client.cookies.get('__Host-runtu_session'))
    assert client.post('/api/auth/logout',headers=headers(client)).status_code==200
    with pytest.raises(UserDenied):
        app.state.module_access.save(actor,actor,'alpha',GrantInput(granted=True,expected_granted=False),session_key)
    with app.state.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(UserModuleGrantEvent))==0


def test_grant_migration_preserves_users_and_only_drops_new_tables(tmp_path):
    app=create_app(Settings(_env_file=None,database_url=f'sqlite:///{tmp_path/"legacy.db"}',auth_origin=ORIGIN),modules=access_modules())
    db=app.state.database
    try:
        migrate_database(db,'0004_module_management')
        actor=app.state.auth_service.bootstrap('operator',secrets.token_urlsafe(24))
        with pytest.raises(AuthUnavailable): app.state.module_access.page(actor,actor,own=True)
        migrate_database(db)
        app.state.module_access.save(actor,actor,'alpha',GrantInput(granted=True,expected_granted=False))
        with db.engine.begin() as connection:
            config=migration_config();config.attributes['connection']=connection
            command.check(config)
            command.downgrade(config,'0004_module_management')
        assert 'user_module_grants' not in inspect(db.engine).get_table_names()
        with db.transaction() as session: assert session.scalar(select(func.count()).select_from(AuthUser))==1
        migrate_database(db)
        assert app.state.module_access.page(actor,actor,own=True).items==[]
    finally: db.dispose()
