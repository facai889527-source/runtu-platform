from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from threading import Event
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from alembic import command
from fastapi.testclient import TestClient
from pydantic import SecretStr
from cryptography.fernet import Fernet
from uuid import uuid4
import pytest
from sqlalchemy import delete, event, inspect, select
from sqlalchemy.exc import OperationalError

from backend.auth.service import AuthDenied, digest
from backend.models import AccountNotification, TelegramChallenge, NotificationDelivery, NotificationPreferences, AuthEvent, AuthRateLimit, AuthSession, AuthUser, PersonalTelegramBot, TelegramPlatform
from backend.migrations import migration_config, migrate_database
from backend.notifications import NotificationInput, TelegramTransport
from backend.user_management import CreateUser, UserConflict
from tests.test_auth import auth, login, ORIGIN, PASSWORD
from tests.test_module_management import headers
from tests.test_registration import applicant, set_policy, signup

PATH='/api/me/notifications'
TOKEN='123456789:'+'fixture_'*5
WEBHOOK='fixture_webhook_'*4


def payload(revision=0, enabled=False, registration=False):
    return dict(enabled=enabled,private_target=enabled,events=dict(registration=registration,account_security=False,tool_outcomes=False,system_errors=False),expected_revision=revision)


def exercise_notification_preferences(client):
    current=client.get(PATH)
    assert current.status_code==200 and current.headers['cache-control']=='no-store'
    assert set(current.json())=={'enabled','revision','available','bound','destination','paused','pairing','events','supported','bot_mode','bot_username','personal_available','public_available','private_target','owner_account','identity','candidate_identity','custom_test_available'}
    assert current.json()['bound'] is False and current.json()['destination'] is None
    saved=client.put(PATH,json=payload(),headers=headers(client))
    assert saved.status_code==200 and saved.json()['revision']==0
    assert client.put(PATH,json=payload(1),headers=headers(client)).status_code==409
    assert client.get('/api/admin/notifications/telegram').status_code==404


def seed_public(notifications):
    service=notifications.auth
    if not notifications.personal.vault.available:service.settings.notification_encryption_keys=SecretStr(Fernet.generate_key().decode())
    with service.transaction() as session:
        source=session.get(TelegramPlatform,1)
        existing=session.scalar(select(AuthUser).where(AuthUser.username=='public-bot-fixture'))
        if not existing:
            existing=AuthUser(id=str(uuid4()),username='public-bot-fixture',password_hash='unusable-test-hash',role='owner',active=True,is_admin=True,created_at=service.clock())
            session.add(existing);session.flush()
        if not session.get(PersonalTelegramBot,existing.id):
            session.add(PersonalTelegramBot(user_id=existing.id,ciphertext=notifications.personal.vault.seal(existing.id,SecretStr(TOKEN)),bot_id='123456789',username='RuntuFixtureBot',fingerprint=digest(TOKEN),update_offset=0,lease_id=None,lease_until=None))
            session.add(AccountNotification(user_id=existing.id,bot_mode='personal',bot_key=digest(TOKEN),chat_id='111111111',bound_at=service.clock(),private_target=False,enabled=False,registration=False,paused=False,revision=1,changed_at=service.clock()))
        source.owner_id,source.fingerprint,source.public_key=existing.id,digest(TOKEN),digest('fixture-public-generation')


@pytest.fixture
def ready(auth):
    client,service,actor=auth
    assert login(client).status_code==200
    config=service.settings;config.telegram_bot_token=SecretStr(TOKEN);config.telegram_bot_username='RuntuFixtureBot'
    config.telegram_webhook_secret=SecretStr(WEBHOOK);config.telegram_binding_enabled=True
    notifications=client.app.state.notifications;notifications.transport=Mock();notifications.transport.send.return_value=True
    seed_public(notifications)
    return client,service,actor,notifications


def callback(client, token, chat=123456789, **changes):
    message=dict(text='/start '+token,chat={'id':chat,'type':'private'},**{'from':{'id':chat,'is_bot':False}})
    message.update(changes)
    return client.post('/api/telegram/webhook',json={'update_id':1,'message':message},headers={'X-Telegram-Bot-Api-Secret-Token':WEBHOOK})


def begin(client):
    current=client.get(PATH).json()
    if current['bot_mode'] is None:
        assert client.post(PATH+'/choose-public',json={'expected_revision':current['revision']},headers=headers(client)).status_code==200
    revision=client.get(PATH).json()['revision']
    result=client.post(PATH+'/connect',json={'expected_revision':revision},headers=headers(client))
    assert result.status_code==200
    assert result.headers['cache-control']=='no-store'
    return parse_qs(urlsplit(result.json()['url']).query)['start'][0],result.json()['revision']


def bind(client, chat=123456789, registration=False):
    token,revision=begin(client)
    assert callback(client,token,chat).json()=={'ok':True}
    assert client.get(PATH).json()['bound'] is False
    result=client.post(PATH+'/confirm',json={'expected_revision':revision,'candidate_user_id':client.get(PATH).json().get('candidate_identity',{}).get('user_id')},headers=headers(client))
    assert result.status_code==200
    row=result.json()
    assert row['bound'] and not row['enabled']
    saved=client.put(PATH,json=payload(row['revision'],True,registration),headers=headers(client))
    assert saved.status_code==200
    return saved.json()


def exercise_verified_binding_contract(client):
    """Shared SQLite/PostgreSQL contract; fixture secrets and transport only."""
    notifications=client.app.state.notifications
    config=notifications.auth.settings
    previous=(config.telegram_bot_token,config.telegram_bot_username,config.telegram_webhook_secret,config.telegram_binding_enabled,notifications.transport)
    try:
        config.telegram_bot_token=SecretStr(TOKEN);config.telegram_bot_username='RuntuFixtureBot'
        config.telegram_webhook_secret=SecretStr(WEBHOOK);config.telegram_binding_enabled=True
        notifications.transport=Mock();notifications.transport.send.return_value=True
        seed_public(notifications)
        row=bind(client,55556789,True)
        assert client.post(PATH+'/test',json={'expected_revision':row['revision']},headers=headers(client)).json()=={'state':'sent'}
        notifications.transport.send.assert_called_once_with(TOKEN,'55556789','Runtu：Telegram 个人消息设置测试。')
        assert client.post(PATH+'/disconnect',json={'expected_revision':row['revision']},headers=headers(client)).status_code==200
        assert client.get(PATH).json()['destination'] is None
        # The shared contract also owns the encrypted source fixture. Unlink it
        # before a later PostgreSQL downgrade check; retain all downgrade guards.
        with notifications.auth.transaction() as session:
            source=session.get(TelegramPlatform,1)
            notifications.clear(session,session.get(AccountNotification,source.owner_id))
    finally:
        config.telegram_bot_token,config.telegram_bot_username,config.telegram_webhook_secret,config.telegram_binding_enabled,notifications.transport=previous


def test_shared_verified_binding_contract(auth):
    client,_,_=auth
    assert login(client).status_code==200
    exercise_verified_binding_contract(client)


def test_nested_clients_preserve_single_worker_and_outer_delivery(auth):
    client,_,_=auth
    assert login(client).status_code==200
    notifications=client.app.state.notifications
    worker=notifications.worker
    with applicant(client.app) as guest:
        assert guest.get('/api/auth/registration-policy').status_code==200
        assert notifications.worker is worker and notifications.lifetimes==2
    assert notifications.lifetimes==1 and not notifications.stopped.is_set() and worker.is_alive()
    exercise_verified_binding_contract(client)


def other(client, service, actor, name, role='viewer'):
    user=client.app.state.user_management.create(actor,CreateUser(username=name,password=PASSWORD,role=role))
    guest=TestClient(client.app,base_url=ORIGIN)
    assert login(guest,PASSWORD,name).status_code==200
    return guest,user.id


def test_default_private_preferences_legacy_quarantine_and_unverified_denial(auth):
    client,service,actor=auth
    assert client.get(PATH).status_code==401
    assert login(client).status_code==200
    with service.transaction() as session:
        old=session.get(NotificationPreferences,1);old.chat_id='-1001234567890';old.enabled=True;old.registration=True
    exercise_notification_preferences(client)
    assert client.get(PATH).json()['available'] is False
    assert client.post(PATH+'/connect',json={'expected_revision':0},headers=headers(client)).status_code==422
    assert client.put(PATH,json=payload(enabled=True),headers=headers(client)).status_code==422
    assert client.post(PATH+'/test',json={'expected_revision':0},headers=headers(client)).status_code==422
    with service.transaction() as session:
        assert session.get(AccountNotification,actor).chat_id is None
        assert session.get(NotificationPreferences,1).chat_id=='-1001234567890'


def test_upgrade_quarantines_and_disables_legacy_without_copying_accounts(auth):
    client,service,actor=auth
    with service.database.engine.begin() as connection:
        config=migration_config();config.attributes['connection']=connection
        command.downgrade(config,'0008_notifications')
    with service.transaction() as session:
        old=session.get(NotificationPreferences,1);old.enabled=True;old.registration=True;old.chat_id='-1001234567890'
    migrate_database(service.database)
    with service.transaction() as session:
        old=session.get(NotificationPreferences,1)
        assert old.chat_id=='-1001234567890' and not old.enabled and not old.registration
        assert session.get(AccountNotification,actor) is None
    assert login(client).status_code==200
    assert client.get(PATH).json()['destination'] is None


@pytest.mark.parametrize('role', ['owner','admin','viewer'])
def test_every_active_account_self_service_and_csrf(auth,role):
    client,service,actor=auth
    with service.transaction() as session: session.get(AuthUser,actor).role=role
    assert login(client).status_code==200
    assert client.get(PATH).status_code==200
    assert client.get(PATH).json()['supported']['registration'] is (role!='viewer')
    assert client.put(PATH,json=payload(),headers=headers(client)).status_code==200
    assert client.put(PATH,json=payload(),headers={'Origin':ORIGIN}).status_code==403
    assert client.put(PATH,json=payload(),headers={**headers(client),'Origin':'https://foreign.test'}).status_code==403
    if role=='viewer': assert client.put(PATH,json=payload(registration=True),headers=headers(client)).status_code==403


def test_complete_pair_confirm_single_use_masked_and_no_secret_echo(ready,caplog):
    client,service,actor,notifications=ready
    token,revision=begin(client)
    with service.transaction() as session:
        challenge=session.get(TelegramChallenge,actor)
        assert challenge.token_hash==digest(token) and token not in str(challenge.__dict__)
    assert client.post(PATH+'/confirm',json={'expected_revision':revision},headers=headers(client)).status_code==409
    assert callback(client,token).json()=={'ok':True}
    assert callback(client,token,987654321).json()=={'ok':True}
    row=client.get(PATH).json();assert row['pairing']['candidate']=='••••6789' and not row['bound']
    result=client.post(PATH+'/confirm',json={'expected_revision':revision,'candidate_user_id':client.get(PATH).json().get('candidate_identity',{}).get('user_id')},headers=headers(client))
    assert result.status_code==200 and result.json()['bound']
    assert client.post(PATH+'/confirm',json={'expected_revision':revision},headers=headers(client)).status_code==409
    assert callback(client,token).json()=={'ok':True}
    assert notifications.transport.send.call_count==0
    for secret in (TOKEN,WEBHOOK,token):
        assert secret not in client.get(PATH).text and secret not in caplog.text


def test_account_a_cannot_target_read_change_or_send_to_b(ready):
    client,service,actor,notifications=ready
    bind(client,123456789,True)
    b,bid=other(client,service,actor,'other-notices')
    try:
        own=bind(b,987654321)
        assert own['destination']=='••••4321' and not own['supported']['registration']
        assert b.get(PATH+'?user_id='+actor).status_code==422
        assert b.get(PATH+'/'+actor).status_code in (404,405)
        for extra in ({'user_id':actor},{'chat_id':'123456789'},{'bot_token':TOKEN}):
            assert b.put(PATH,json={**payload(own['revision']),**extra},headers=headers(b)).status_code==422
            assert b.post(PATH+'/test',json={'expected_revision':own['revision'],**extra},headers=headers(b)).status_code==422
        assert b.post(PATH+'/test',json={'expected_revision':own['revision']},headers=headers(b)).json()=={'state':'sent'}
        assert notifications.transport.send.call_args.args[1]=='987654321'
        assert client.get(PATH).json()['destination']=='••••6789'
        assert b.post(PATH+'/disconnect',json={'expected_revision':own['revision']},headers=headers(b)).status_code==200
        assert client.get(PATH).json()['bound'] is True
    finally: b.close()


@pytest.mark.parametrize('change', ['expired','revoked','disabled','group','channel','sender','bot','wrong-secret'])
def test_binding_proof_rejects_expired_replay_and_non_private_sources(ready,change):
    client,service,actor,_=ready
    token,revision=begin(client)
    options={}
    with service.transaction() as session:
        if change=='expired': session.get(TelegramChallenge,actor).expires_at=service.clock()-timedelta(seconds=1)
        if change=='revoked': session.execute(delete(AuthSession).where(AuthSession.token_hash==digest(client.cookies.get('__Host-runtu_session'))))
        if change=='disabled': session.get(AuthUser,actor).active=False
    if change in ('group','channel'): options={'chat':{'id':123456789,'type':change}}
    if change=='sender': options={'from':{'id':111,'is_bot':False}}
    if change=='bot': options={'from':{'id':123456789,'is_bot':True}}
    if change=='wrong-secret':
        response=client.post('/api/telegram/webhook',json={},headers={'X-Telegram-Bot-Api-Secret-Token':'wrong'})
        assert response.status_code==403
    else: assert callback(client,token,**options).status_code==200
    with service.transaction() as session:
        row=session.get(AccountNotification,actor);challenge=session.get(TelegramChallenge,actor)
        assert row.chat_id is None and challenge.chat_id is None


def test_unlink_rebind_invalidates_old_challenge_and_destination_conflict(ready):
    client,service,actor,_=ready
    row=bind(client)
    token,revision=begin(client)
    assert client.get(PATH).json()['bound'] is False
    result=client.post(PATH+'/disconnect',json={'expected_revision':revision},headers=headers(client))
    assert result.status_code==200
    assert callback(client,token).status_code==200
    assert client.get(PATH).json()['pairing']['state']=='none'
    bind(client)
    b,_=other(client,service,actor,'same-chat')
    try:
        token,revision=begin(b);assert callback(b,token).status_code==200
        conflict=b.post(PATH+'/confirm',json={'expected_revision':revision},headers=headers(b))
        assert conflict.status_code==409 and '123456789' not in conflict.text and actor not in conflict.text
        assert not b.get(PATH).json()['bound']
    finally:b.close()


def test_pairing_race_only_one_confirmation_and_settings_audit_rollback(ready):
    client,service,actor,notifications=ready
    token,revision=begin(client);callback(client,token)
    key=digest(client.cookies.get('__Host-runtu_session'))
    def confirm(_):
        try:notifications.confirm(actor,key,revision,candidate_user_id='123456789');return 'bound'
        except UserConflict:return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(confirm,range(2)))==['bound','conflict']
    revision=client.get(PATH).json()['revision']
    def fail(*_):raise OperationalError('fixture',{},Exception('fixture'))
    event.listen(AuthEvent,'before_insert',fail)
    try:assert client.put(PATH,json=payload(revision,True,True),headers=headers(client)).status_code==503
    finally:event.remove(AuthEvent,'before_insert',fail)
    assert client.get(PATH).json()['enabled'] is False


def test_registration_routes_only_opted_privileged_verified_and_dedupes(ready):
    client,service,actor,notifications=ready
    bind(client,11111111,True)
    admin,admin_id=other(client,service,actor,'notice-admin','admin')
    viewer,viewer_id=other(client,service,actor,'notice-viewer')
    opted_out,out_id=other(client,service,actor,'notice-optout','owner')
    try:
        bind(admin,22222222,True);bind(viewer,33333333);bind(opted_out,44444444)
        assert set_policy(client).status_code==200
        with applicant(client.app) as guest:assert signup(guest,'notice-applicant')[0].status_code==202
        notifications.queue.join()
        assert sorted(call.args[1] for call in notifications.transport.send.call_args_list)==['11111111','22222222']
        assert all('notice-applicant' not in call.args[2] for call in notifications.transport.send.call_args_list)
        with service.transaction() as session:
            eid=session.scalar(select(AuthEvent.id).where(AuthEvent.event=='registration_submitted'))
            assert len(session.scalars(select(NotificationDelivery)).all())==2
        notifications.registration_committed(eid);notifications.queue.join()
        assert notifications.transport.send.call_count==2
        with applicant(client.app) as duplicate:assert signup(duplicate,'notice-applicant')[0].status_code==202
        notifications.queue.join();assert notifications.transport.send.call_count==2
        with service.transaction() as session:session.get(AuthUser,admin_id).role='viewer'
        assert admin.get(PATH).json()['events']['registration'] is False
    finally:admin.close();viewer.close();opted_out.close()


def test_test_send_rate_limit_failure_pause_stale_and_revoked_delivery(ready,caplog):
    client,service,actor,notifications=ready
    row=bind(client);revision=row['revision'];key=digest(client.cookies.get('__Host-runtu_session'))
    assert client.post(PATH+'/test',json={'expected_revision':revision},headers=headers(client)).json()=={'state':'sent'}
    assert client.post(PATH+'/test',json={'expected_revision':revision},headers=headers(client)).status_code==429
    assert notifications._deliver(actor,revision-1,'fixture',key=key) is False
    with service.transaction() as session:session.execute(delete(AuthRateLimit))
    notifications.transport.send.side_effect=RuntimeError(TOKEN)
    result=client.post(PATH+'/test',json={'expected_revision':revision},headers=headers(client))
    assert result.status_code==502 and TOKEN not in result.text and TOKEN not in caplog.text
    assert client.get(PATH).json()['paused'] and not client.get(PATH).json()['enabled']
    with service.transaction() as session:session.execute(delete(AuthSession).where(AuthSession.token_hash==key))
    with pytest.raises(AuthDenied):notifications._deliver(actor,revision,'fixture',key=key)


def test_recipient_claim_concurrency_and_current_role_active_binding_guards(ready):
    client,service,actor,notifications=ready
    row=bind(client,123456789,True)
    committed=[];client.app.state.registration.notification=committed.append
    assert set_policy(client).status_code==200
    with applicant(client.app) as guest:assert signup(guest,'concurrent-notice')[0].status_code==202
    event_id=committed[0]
    def deliver(_):return notifications._deliver(actor,row['revision'],'fixture',event_id=event_id)
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(deliver,range(2)))==[False,True]
    assert notifications.transport.send.call_count==1
    # A second authoritative event cannot bypass a subsequent demotion/disable.
    with applicant(client.app) as guest:assert signup(guest,'demotion-notice')[0].status_code==202
    second=committed[-1]
    with service.transaction() as session:session.get(AuthUser,actor).role='viewer'
    assert notifications._deliver(actor,row['revision'],'fixture',event_id=second) is False
    with service.transaction() as session:
        session.get(AuthUser,actor).role='owner';session.get(AuthUser,actor).active=False
    assert notifications._deliver(actor,row['revision'],'fixture',event_id=second) is False
    with service.transaction() as session:session.get(AuthUser,actor).active=True
    key=digest(client.cookies.get('__Host-runtu_session'))
    notifications.unlink(actor,key,row['revision'])
    assert notifications._deliver(actor,row['revision'],'fixture',event_id=second) is False
    assert notifications.transport.send.call_count==1


def test_pair_confirm_expiry_callback_boundary_and_no_hook_on_rollback(ready):
    client,service,actor,notifications=ready
    token,revision=begin(client);callback(client,token)
    with service.transaction() as session:session.get(TelegramChallenge,actor).expires_at=service.clock()-timedelta(seconds=1)
    assert client.post(PATH+'/confirm',json={'expected_revision':revision},headers=headers(client)).status_code==409
    assert client.post('/api/telegram/webhook',json={},headers={'Host':'foreign.test','X-Telegram-Bot-Api-Secret-Token':WEBHOOK}).status_code==403
    assert client.post('/api/telegram/webhook',content='bad callback',headers={'Content-Type':'application/json','X-Telegram-Bot-Api-Secret-Token':WEBHOOK}).status_code==422
    assert set_policy(client).status_code==200
    calls=[];client.app.state.registration.notification=calls.append
    def fail(*_):raise OperationalError('fixture',{},Exception('fixture'))
    event.listen(AuthEvent,'before_insert',fail)
    try:
        with applicant(client.app) as guest:assert signup(guest,'rollback-notice')[0].status_code==503
    finally:event.remove(AuthEvent,'before_insert',fail)
    assert calls==[]
    client.app.state.registration.notification=lambda *_:(_ for _ in ()).throw(RuntimeError('queue unavailable'))
    with applicant(client.app) as guest:assert signup(guest,'lost-notice')[0].status_code==202


def test_delivery_deadline_and_bounded_queue_do_not_block_business(ready):
    client,_,_,notifications=ready
    row=bind(client);entered,release=Event(),Event()
    def slow(*_):entered.set();release.wait(6);return True
    notifications.transport.send.side_effect=slow
    try:
        result=client.post(PATH+'/test',json={'expected_revision':row['revision']},headers=headers(client))
        assert result.status_code==504 and entered.is_set()
        for _ in range(16):assert notifications._offer(('registration','absent'))
        assert not notifications._offer(('registration','absent'))
        notifications.registration_committed('dropped')
    finally:release.set();notifications.queue.join()


def test_pair_callback_size_schema_and_downgrade_guards(ready):
    client,service,actor,_=ready
    assert client.post('/api/telegram/webhook',content='x'*8193,headers={'Content-Type':'application/json','X-Telegram-Bot-Api-Secret-Token':WEBHOOK}).status_code==413
    row=bind(client)
    with service.database.engine.begin() as connection:
        config=migration_config();config.attributes['connection']=connection
        command.check(config)
        with pytest.raises(RuntimeError,match='Unlink'):command.downgrade(config,'0008_notifications')
    assert client.post(PATH+'/disconnect',json={'expected_revision':row['revision']},headers=headers(client)).status_code==200
    with service.transaction() as session:source_owner=session.get(TelegramPlatform,1).owner_id
    source_path='/api/admin/notifications/users/'+source_owner
    source_row=client.get(source_path).json()
    assert client.post(source_path+'/disconnect',json={'expected_revision':source_row['revision']},headers=headers(client)).status_code==200
    with service.database.engine.begin() as connection:
        config=migration_config();config.attributes['connection']=connection;command.downgrade(config,'0008_notifications')
    assert client.get(PATH).status_code==503


@pytest.mark.parametrize('outcome', ['ok','refused','malformed','oversize','redirect','exception'])
def test_transport_fixed_https_bounded_no_redirect_or_error_leak(monkeypatch,caplog,outcome):
    connection=Mock();response=Mock();connection.getresponse.return_value=response
    response.status=302 if outcome=='redirect' else 200
    response.read.return_value = (b'x'*8193 if outcome=='oversize' else b'invalid' if outcome=='malformed'
        else json.dumps({'ok':outcome=='ok','result':{'message_id':1},'description':TOKEN}).encode())
    if outcome=='exception': connection.request.side_effect=RuntimeError(TOKEN)
    factory=Mock(return_value=connection);monkeypatch.setattr('backend.notifications.http.client.HTTPSConnection',factory)
    assert TelegramTransport().send(TOKEN,'-10012345','fixture') is (outcome=='ok')
    factory.assert_called_once_with('api.telegram.org',timeout=2)
    connection.set_debuglevel.assert_called_once_with(0)
    assert connection.request.call_args.args[:2]==('POST','/bot'+TOKEN+'/sendMessage')
    assert 'parse_mode' not in json.loads(connection.request.call_args.kwargs['body'])
    if outcome!='exception': response.read.assert_called_once_with(8193)
    connection.close.assert_called_once();assert TOKEN not in caplog.text
