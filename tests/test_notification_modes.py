from urllib.parse import parse_qs, urlsplit

from alembic import command
import pytest
from pydantic import SecretStr
from sqlalchemy import text

from backend.auth.service import digest
from backend.migrations import migration_config
from backend.models import AccountNotification, AuthSession, AuthUser, TelegramChallenge, TelegramPlatform
from tests.test_auth import auth
from tests.test_module_management import headers
from tests.test_notifications import ready, PATH, TOKEN, bind, begin, callback, other, payload


def post(client, path, action, revision):
    extra={'candidate_user_id':(client.get(path).json().get('candidate_identity') or {}).get('user_id')} if action=='confirm' else {}
    return client.post(path+'/'+action, json={'expected_revision':revision,**extra}, headers=headers(client))


def test_explicit_choice_target_and_complete_disconnect(ready):
    client,service,actor,notifications=ready
    initial=client.get(PATH).json()
    assert initial['bot_mode'] is None and not initial['available'] and initial['public_available']
    assert not initial['bound'] and not initial['private_target'] and not initial['enabled']
    assert post(client,PATH,'connect',0).status_code==422
    row=bind(client)
    assert row['bot_mode']=='public' and row['private_target']
    value=payload(row['revision'],True);value['private_target']=False
    assert client.put(PATH,json=value,headers=headers(client)).status_code==422
    value['enabled']=False
    removed=client.put(PATH,json=value,headers=headers(client)).json()
    assert not removed['private_target']
    assert not notifications._deliver(actor,row['revision'],'fixture')
    cleared=post(client,PATH,'disconnect',removed['revision']).json()
    for field in ('enabled','bound','private_target','paused'): assert cleared[field] is False
    assert cleared['bot_mode'] is None and cleared['destination'] is None
    assert not any(cleared['events'].values()) and cleared['pairing']['state']=='none'
    with service.transaction() as session:
        record=session.get(AccountNotification,actor)
        assert record.bot_key is None and session.get(TelegramChallenge,actor) is None
    assert post(client,PATH,'connect',cleared['revision']).status_code==422


def test_owner_management_private_proof_and_recipient_isolation(ready):
    client,service,actor,notifications=ready
    guest,recipient=other(client,service,actor,'managed-viewer')
    path='/api/admin/notifications/users/'+recipient
    try:
        initial=client.get(path).json()
        chosen=post(client,path,'choose-public',initial['revision']).json()
        assert guest.get(PATH).json()['bot_mode']=='public'
        started=post(client,path,'connect',chosen['revision']).json()
        token=parse_qs(urlsplit(started['url']).query)['start'][0]
        assert callback(client,token,777777).status_code==200
        assert post(guest,PATH,'confirm',started['revision']).status_code==409
        verified=post(client,path,'confirm',started['revision']).json()
        assert verified['bound'] and not verified['private_target'] and not verified['enabled']
        row=client.put(path,json=payload(verified['revision'],True),headers=headers(client)).json()
        assert client.post(path+'/test',json={'expected_revision':row['revision']},headers=headers(client)).json()=={'state':'sent'}
        notifications.transport.send.assert_called_once_with(TOKEN,'777777','Runtu：Telegram 个人消息设置测试。')
        assert client.get(PATH).json()['bot_mode'] is None
        assert client.put(path,json=payload(row['revision'],True,True),headers=headers(client)).status_code==403
        with service.transaction() as session:session.get(AuthUser,recipient).active=False
        assert post(client,path,'disconnect',row['revision']).json()['bot_mode'] is None
        assert client.get(path).status_code==200
    finally:guest.close()


@pytest.mark.parametrize('role',['admin','viewer'])
def test_non_owner_cannot_manage_any_other_account_or_owner_endpoint(ready,role):
    client,service,actor,_=ready
    guest,recipient=other(client,service,actor,'isolated-'+role,role)
    try:
        for target in (actor,recipient,'absent'):
            path='/api/admin/notifications/users/'+target
            assert guest.get(path).status_code==403
            assert guest.put(path,json=payload(),headers=headers(guest)).status_code==403
            for action in ('choose-public','connect','confirm','disconnect','test'):
                assert post(guest,path,action,0).status_code==403
        assert guest.get(PATH+'?target='+actor).status_code==422
        assert guest.put(PATH,json={**payload(),'target':actor},headers=headers(guest)).status_code==422
        assert post(guest,PATH,'choose-public',0).status_code==200
    finally:guest.close()


def test_owner_origin_csrf_stale_revision_and_revoked_pairing(ready):
    client,service,actor,_=ready
    guest,recipient=other(client,service,actor,'managed-admin','admin')
    path='/api/admin/notifications/users/'+recipient
    try:
        assert client.post(path+'/choose-public',json={'expected_revision':0}).status_code==403
        assert client.post(path+'/choose-public',json={'expected_revision':0},headers={**headers(client),'Origin':'https://foreign.test'}).status_code==403
        chosen=post(client,path,'choose-public',0).json()
        assert post(client,path,'choose-public',0).status_code==409
        started=post(client,path,'connect',chosen['revision']).json()
        token=parse_qs(urlsplit(started['url']).query)['start'][0]
        with service.transaction() as session:session.get(AuthUser,actor).role='admin'
        callback(client,token)
        with service.transaction() as session:assert session.get(TelegramChallenge,recipient).chat_id is None
        assert post(client,path,'confirm',started['revision']).status_code==403
    finally:guest.close()


def test_bot_configuration_rotation_blocks_old_challenges_and_delivery(ready):
    client,service,actor,notifications=ready
    row=bind(client)
    with service.transaction() as session:session.get(TelegramPlatform,1).public_key='rotated-generation'
    assert not client.get(PATH).json()['available']
    assert not notifications._deliver(actor,row['revision'],'fixture')
    assert post(client,PATH,'test',row['revision']).status_code==422
    new=post(client,PATH,'choose-public',row['revision']).json()
    assert new['available'] and not new['bound'] and not new['private_target'] and not new['enabled']
    token,revision=begin(client)
    with service.transaction() as session:session.get(TelegramPlatform,1).public_key='second-generation'
    callback(client,token)
    with service.transaction() as session:assert session.get(TelegramChallenge,actor).chat_id is None
    assert post(client,PATH,'confirm',revision).status_code==422


def test_owner_queued_test_rechecks_current_authority_and_target_active(ready):
    client,service,actor,notifications=ready
    guest,recipient=other(client,service,actor,'queued-recipient')
    try:
        row=bind(guest,888888)
        key=digest(client.cookies.get('__Host-runtu_session'))
        with service.transaction() as session:session.get(AuthUser,actor).role='admin'
        assert not notifications._deliver(recipient,row['revision'],'fixture',key=key,principal=actor)
        with service.transaction() as session:
            session.get(AuthUser,actor).role='owner';session.get(AuthUser,recipient).active=False
        assert not notifications._deliver(recipient,row['revision'],'fixture',key=key,principal=actor)
        notifications.transport.send.assert_not_called()
    finally:guest.close()


def test_migration_resets_existing_bindings_without_selecting_bot(ready):
    client,service,actor,_=ready
    with service.transaction() as session:
        source=session.get(TelegramPlatform,1);owner=source.owner_id
        notifications=client.app.state.notifications;notifications.clear(session,session.get(AccountNotification,owner))
    with service.database.engine.begin() as connection:
        config=migration_config();config.attributes['connection']=connection
        command.downgrade(config,'0009_account_notifications')
        connection.execute(text('INSERT INTO account_notifications (user_id,chat_id,bound_at,enabled,registration,paused,revision,changed_at) VALUES (:user,:chat,CURRENT_TIMESTAMP,true,true,false,4,CURRENT_TIMESTAMP)'),{'user':actor,'chat':'777777'})
        command.upgrade(config,'head');command.check(config)
    row=client.get(PATH).json()
    assert row['revision']==5 and row['bot_mode'] is None and not row['bound'] and not row['enabled'] and not row['private_target']
    assert not any(row['events'].values())
