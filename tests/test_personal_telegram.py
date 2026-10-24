from datetime import timedelta
from urllib.parse import parse_qs,urlsplit
from unittest.mock import Mock

from alembic import command
from cryptography.fernet import Fernet
from pydantic import SecretStr
import pytest
from sqlalchemy import select

from backend.auth.service import digest
from backend.models import AccountNotification,AuthUser,PersonalTelegramBot,TelegramChallenge,AuthEvent,TelegramPlatform
from backend.migrations import migration_config
from backend.telegram_security import TelegramBusy,TelegramUnavailable
from backend.user_management import UserConflict
from tests.test_auth import auth
from tests.test_notifications import ready,PATH,payload,other,callback
from tests.test_module_management import headers

TOKEN='987654321:'+'personal_fixture_'*3


@pytest.fixture
def personal(ready):
    client,service,actor,notifications=ready
    if not notifications.personal.vault.available:service.settings.notification_encryption_keys=SecretStr(Fernet.generate_key().decode())
    api=Mock()
    api.call.side_effect=lambda token,method,data=None: {'getMe':{'id':987654321,'is_bot':True,'username':'PrivateFixtureBot'},'getWebhookInfo':{'url':''},'getUpdates':[]}[method]
    notifications.personal.api=api
    return client,service,actor,notifications,api


def action(client,path,name,revision,**extra):
    return client.post(path+'/'+name,json={'expected_revision':revision,**extra},headers=headers(client))


def choose(client,path=PATH):
    current=client.get(path).json()
    response=action(client,path,'choose-personal',current['revision'],token=TOKEN,exclusive=True)
    assert response.status_code==200,response.status_code
    return response.json()


def prove(client,api,path=PATH,chat=887766):
    row=choose(client,path)
    link=action(client,path,'connect',row['revision']).json()
    token=parse_qs(urlsplit(link['url']).query)['start'][0]
    message={'update_id':100,'message':{'text':'/start '+token,'chat':{'type':'private','id':chat},'from':{'id':chat,'is_bot':False}}}
    base=api.call.side_effect
    api.call.side_effect=lambda secret,method,data=None:[message] if method=='getUpdates' else base(secret,method,data)
    assert callback(client,token,chat).status_code==200
    assert client.get(path).json()['pairing']['state']=='waiting'  # Public callback cannot bind personal bot.
    synced=action(client,path,'sync-personal',link['revision'])
    assert synced.status_code==200 and synced.json()['pairing']['state']=='confirm'
    confirmed=action(client,path,'confirm',link['revision'])
    assert confirmed.status_code==200
    return confirmed.json(),message


def test_personal_lifecycle_encrypted_proof_verified_send_and_pristine_unlink(personal,caplog):
    client,service,actor,notifications,api=personal
    row,message=prove(client,api)
    assert row['bot_mode']=='personal' and row['bot_username']=='PrivateFixtureBot' and row['bound'] and not row['enabled'] and not row['private_target']
    with service.transaction() as session:
        bot=session.get(PersonalTelegramBot,actor)
        assert TOKEN not in bot.ciphertext and bot.update_offset==101 and bot.lease_id is None
        assert notifications.personal.vault.open(actor,bot.ciphertext)==SecretStr(TOKEN)
        assert not any(TOKEN in str(e.source_hash) for e in session.scalars(select(AuthEvent)))
    enabled=client.put(PATH,json=payload(row['revision'],True,True),headers=headers(client)).json()
    assert action(client,PATH,'test',enabled['revision']).json()=={'state':'sent'}
    notifications.transport.send.assert_called_once_with(TOKEN,'887766','Runtu：Telegram 个人消息设置测试。')
    synced=action(client,PATH,'sync-personal',enabled['revision'])
    assert synced.status_code==200 and synced.json()['pairing']['state']=='none'  # Replay ignored by offset and consumed challenge.
    assert TOKEN not in str(row) and TOKEN not in caplog.text
    cleared=action(client,PATH,'disconnect',enabled['revision']).json()
    assert cleared['bot_mode'] is None and not cleared['enabled'] and not cleared['private_target'] and not any(cleared['events'].values())
    with service.transaction() as session:
        assert session.get(PersonalTelegramBot,actor) is None and session.get(TelegramChallenge,actor) is None
    assert not notifications._deliver(actor,enabled['revision'],'fixture')


def test_personal_works_without_shared_bot_and_fails_closed_without_keys(personal):
    client,service,actor,notifications,api=personal
    service.settings.telegram_bot_token=None;service.settings.telegram_webhook_secret=None
    with service.transaction() as session:session.get(TelegramPlatform,1).owner_id=None
    row=choose(client)
    assert row['available'] and not row['public_available']
    assert action(client,PATH,'connect',row['revision']).status_code==200
    service.settings.notification_encryption_keys=None
    current=client.get(PATH).json()
    assert not current['available'] and not current['personal_available']
    assert action(client,PATH,'connect',current['revision']).status_code==422
    assert action(client,PATH,'rotate-secret',current['revision']).status_code==503
    assert action(client,PATH,'disconnect',current['revision']).json()['bot_mode'] is None
    calls=api.call.call_count
    assert action(client,PATH,'choose-personal',current['revision']+1,token=TOKEN,exclusive=True).status_code==503
    assert api.call.call_count==calls


def test_personal_rotation_preserves_identity_and_new_key_decrypts(personal):
    client,service,actor,notifications,api=personal
    row,_=prove(client,api)
    old=service.settings.notification_encryption_keys.get_secret_value();new=Fernet.generate_key().decode()
    service.settings.notification_encryption_keys=SecretStr(new+','+old)
    rotated=action(client,PATH,'rotate-secret',row['revision'])
    assert rotated.status_code==200 and rotated.json()['bound'] and rotated.json()['revision']==row['revision']
    service.settings.notification_encryption_keys=SecretStr(new)
    assert client.get(PATH).json()['available']
    with service.transaction() as session:
        assert notifications.personal.vault.open(actor,session.get(PersonalTelegramBot,actor).ciphertext)==SecretStr(TOKEN)


@pytest.mark.parametrize('failure',['not-bot','id-mismatch','username','webhook','api','exclusive','malformed'])
def test_rejects_invalid_control_and_conflicts_without_secret_echo(personal,failure,caplog):
    client,service,actor,notifications,api=personal
    if failure in ('not-bot','id-mismatch','username'):
        me={'id':987654321,'is_bot':True,'username':'PrivateFixtureBot'}
        me[{'not-bot':'is_bot','id-mismatch':'id','username':'username'}[failure]]={'not-bot':False,'id-mismatch':111,'username':'invalid'}[failure]
        api.call.return_value=me;api.call.side_effect=None
    if failure=='webhook':api.call.side_effect=lambda token,method,data=None: {'id':987654321,'is_bot':True,'username':'PrivateFixtureBot'} if method=='getMe' else {'url':'https://existing.test/secret'}
    if failure=='api':api.call.side_effect=TelegramUnavailable()
    result=action(client,PATH,'choose-personal',0,token=TOKEN if failure!='malformed' else TOKEN+'/evil',exclusive=failure!='exclusive')
    assert result.status_code==({'webhook':409,'exclusive':422,'malformed':422}.get(failure,502))
    assert TOKEN not in result.text and 'existing.test' not in result.text and TOKEN not in caplog.text
    assert client.get(PATH).json()['bot_mode'] is None


def test_owner_personal_management_and_nonowner_idor(personal):
    client,service,actor,notifications,api=personal
    guest,target=other(client,service,actor,'personal-target','admin')
    path='/api/admin/notifications/users/'+target
    try:
        row,_=prove(client,api,path)
        with service.transaction() as session:
            assert session.get(PersonalTelegramBot,actor) is None
            cipher=session.get(PersonalTelegramBot,target).ciphertext
            assert notifications.personal.vault.open(target,cipher)==SecretStr(TOKEN)
        for name in ('choose-personal','sync-personal','rotate-secret'):
            assert action(guest,path,name,row['revision'],**({'token':TOKEN,'exclusive':True} if name=='choose-personal' else {})).status_code==403
        assert guest.get('/api/admin/notifications/platform').status_code==403
        assert client.get('/api/admin/notifications/platform').json()['encryption_ready']
        assert action(client,path,'disconnect',row['revision']).status_code==200
    finally:guest.close()


def test_personal_bot_unique_and_switching_clears_secret_and_challenge(personal):
    client,service,actor,notifications,api=personal
    row=choose(client)
    guest,target=other(client,service,actor,'personal-duplicate')
    try:
        assert action(guest,PATH,'choose-personal',0,token=TOKEN,exclusive=True).status_code==409
        assert guest.get(PATH).json()['bot_mode'] is None
    finally:guest.close()
    link=action(client,PATH,'connect',row['revision']).json()
    switched=action(client,PATH,'choose-public',link['revision']).json()
    assert switched['bot_mode']=='public' and not switched['bound'] and not switched['enabled']
    with service.transaction() as session:assert session.get(PersonalTelegramBot,actor) is None and session.get(TelegramChallenge,actor) is None


@pytest.mark.parametrize('change',['expired','group','sender','owner-role','disabled','rebind'])
def test_personal_private_proof_scope_races_and_expiry(personal,change):
    client,service,actor,notifications,api=personal
    row=choose(client);link=action(client,PATH,'connect',row['revision']).json()
    token=parse_qs(urlsplit(link['url']).query)['start'][0]
    message={'update_id':1,'message':{'text':'/start '+token,'chat':{'type':'private','id':887766},'from':{'id':887766,'is_bot':False}}}
    if change=='group':message['message']['chat']['type']='group'
    if change=='sender':message['message']['from']['id']=111
    if change=='expired':
        with service.transaction() as session:session.get(TelegramChallenge,actor).expires_at=service.clock()-timedelta(seconds=1)
    base=api.call.side_effect
    def updates(secret,method,data=None):
        if method!='getUpdates':return base(secret,method,data)
        if change=='owner-role':
            with service.transaction() as session:session.get(AuthUser,actor).role='viewer'
        if change=='disabled':
            with service.transaction() as session:session.get(AuthUser,actor).active=False
        if change=='rebind':
            with service.transaction() as session:session.get(AccountNotification,actor).revision+=1
        return [message]
    api.call.side_effect=updates
    result=action(client,PATH,'sync-personal',link['revision'])
    if change=='owner-role':assert result.status_code==200  # Self pairing does not require an owner role.
    elif change in ('disabled','rebind'):assert result.status_code in (403,409)
    else:assert result.status_code==200 and result.json()['pairing']['state']!='confirm'
    with service.transaction() as session:
        assert session.get(PersonalTelegramBot,actor).lease_id is None
        assert session.get(AccountNotification,actor).chat_id is None


def test_sync_conflict_lease_ownership_and_downgrade_guards(personal):
    client,service,actor,notifications,api=personal
    row=choose(client)
    with service.transaction() as session:
        bot=session.get(PersonalTelegramBot,actor);bot.lease_id='other';bot.lease_until=service.clock()+timedelta(seconds=30)
    assert action(client,PATH,'sync-personal',row['revision']).status_code==409
    with service.transaction() as session:session.get(PersonalTelegramBot,actor).lease_until=service.clock()-timedelta(seconds=1)
    base=api.call.side_effect
    def replace(secret,method,data=None):
        if method=='getUpdates':
            with service.transaction() as session:
                bot=session.get(PersonalTelegramBot,actor);bot.lease_id='replacement';bot.lease_until=service.clock()+timedelta(seconds=30)
            return []
        return base(secret,method,data)
    api.call.side_effect=replace
    assert action(client,PATH,'sync-personal',row['revision']).status_code==409
    with service.transaction() as session:assert session.get(PersonalTelegramBot,actor).lease_id=='replacement'
    with service.database.engine.begin() as connection:
        config=migration_config();config.attributes['connection']=connection;command.check(config)
        with pytest.raises(RuntimeError,match='Unlink'):command.downgrade(config,'0010_explicit_public_bot')
    assert action(client,PATH,'disconnect',row['revision']).status_code==200


def test_personal_submission_csrf_and_masking(personal):
    client,service,actor,notifications,api=personal
    assert client.post(PATH+'/choose-personal',json={'token':TOKEN,'exclusive':True,'expected_revision':0}).status_code==403
    assert client.post(PATH+'/choose-personal',json={'token':TOKEN,'exclusive':True,'expected_revision':0},headers={**headers(client),'Origin':'https://foreign.test'}).status_code==403
    assert api.call.call_count==0
    row=choose(client)
    assert TOKEN not in str(row) and set(row).isdisjoint({'token','ciphertext','fingerprint','update_offset'})


def test_owner_role_revocation_during_sync_and_stale_binding_commit(personal):
    client,service,actor,notifications,api=personal
    guest,target=other(client,service,actor,'revoked-personal')
    path='/api/admin/notifications/users/'+target
    try:
        row=choose(client,path)
        base=api.call.side_effect
        def demote(secret,method,data=None):
            if method=='getUpdates':
                with service.transaction() as session:session.get(AuthUser,actor).role='admin'
                return []
            return base(secret,method,data)
        api.call.side_effect=demote
        assert action(client,path,'sync-personal',row['revision']).status_code==403
        with service.transaction() as session:
            assert session.get(PersonalTelegramBot,target).lease_id is None
            session.get(AuthUser,actor).role='owner'
        api.call.side_effect=base
        def stale(secret,method,data=None):
            if method=='getWebhookInfo':
                with service.transaction() as session:
                    record=notifications.profile(session,actor,True);record.revision+=1
            return base(secret,method,data)
        api.call.side_effect=stale
        assert action(client,PATH,'choose-personal',0,token=TOKEN,exclusive=True).status_code==409
        with service.transaction() as session:assert session.get(PersonalTelegramBot,actor) is None
    finally:guest.close()


def test_sync_webhook_conflict_does_not_advance_offset_or_consume_pairing(personal):
    client,service,actor,notifications,api=personal
    row=choose(client)
    started=action(client,PATH,'connect',row['revision']).json()
    api.call.side_effect=TelegramBusy()
    result=action(client,PATH,'sync-personal',started['revision'])
    assert result.status_code==409
    with service.transaction() as session:
        bot=session.get(PersonalTelegramBot,actor)
        assert bot.update_offset==0 and bot.lease_id is None
        assert session.get(TelegramChallenge,actor).token_hash is not None


def test_expired_sync_lease_cannot_commit_updates(personal):
    client,service,actor,notifications,api=personal
    row=choose(client)
    base=api.call.side_effect
    def expire(secret,method,data=None):
        if method=='getUpdates':
            with service.transaction() as session:session.get(PersonalTelegramBot,actor).lease_until=service.clock()-timedelta(seconds=1)
            return [{'update_id':500}]
        return base(secret,method,data)
    api.call.side_effect=expire
    assert action(client,PATH,'sync-personal',row['revision']).status_code==409
    with service.transaction() as session:
        bot=session.get(PersonalTelegramBot,actor)
        assert bot.update_offset==0 and bot.lease_id is None
