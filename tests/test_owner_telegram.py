from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from unittest.mock import Mock
import os

from cryptography.fernet import Fernet
from pydantic import SecretStr
import pytest
from sqlalchemy import select

from backend.auth.service import digest
from backend.models import TelegramPlatform,PersonalTelegramBot,AccountNotification,AuthUser
from backend.private_key_store import PrivateKeyStore,PrivateKeyError
from tests.test_auth import auth,login
from tests.test_notifications import PATH,payload,other
from tests.test_personal_telegram import action,TOKEN
from tests.test_module_management import headers


def mock_api(n):
    n.personal.api=Mock()
    n.personal.api.call.side_effect=lambda token,method,data=None:{'getMe':{'id':987654321,'is_bot':True,'username':'OwnerFixtureBot'},'getWebhookInfo':{'url':''},'getUpdates':[]}[method]
    n.transport=Mock();n.transport.send.return_value=True
    return n.personal.api


def setup(client):
    result=client.post('/api/admin/notifications/setup',json={'expected_revision':0},headers=headers(client))
    assert result.status_code==200
    return result.json()


def start(client):
    row=client.get(PATH).json()
    result=action(client,PATH,'connect',row['revision']).json()
    return result,parse_qs(urlsplit(result['url']).query)['start'][0]


def set_messages(api,messages):
    base=api.call.side_effect
    api.call.side_effect=lambda token,method,data=None:messages if method=='getUpdates' else base(token,method,data)


def update(id,token,chat):return {'update_id':id,'message':{'text':'/start '+token,'chat':{'id':chat,'type':'private'},'from':{'id':chat,'is_bot':False}}}


def bind_owner(client,api):
    row=client.get(PATH).json()
    bound=action(client,PATH,'choose-personal',row['revision'],token=TOKEN,exclusive=True)
    assert bound.status_code==200
    link,token=start(client);set_messages(api,[update(1,token,7654321)])
    assert action(client,PATH,'sync-bot',link['revision']).json()['pairing']['state']=='confirm'
    confirmed=action(client,PATH,'confirm',link['revision'])
    assert confirmed.status_code==200
    return confirmed.json()


def test_owner_bootstrap_private_key_store_and_idempotency(auth):
    client,service,actor=auth;assert login(client).status_code==200
    n=client.app.state.notifications
    initial=client.get(PATH).json();assert initial['owner_account'] and not initial['personal_available'] and not initial['public_available']
    row=setup(client)
    assert row['personal_available'] and not row['public_available'] and row['bot_mode'] is None
    key_path=Path(service.settings.notification_key_file)
    before=key_path.read_bytes();Fernet(before)
    again=setup(client)
    assert key_path.read_bytes()==before and again==row
    assert before.decode() not in str(row)
    n.personal.vault.store.cache=None
    assert n.personal.vault.available
    with service.transaction() as session:assert session.get(TelegramPlatform,1).enabled


def test_owner_bot_becomes_public_only_after_proof_and_shared_poll_is_scoped(auth):
    client,service,actor=auth;assert login(client).status_code==200
    setup(client);n=client.app.state.notifications;api=mock_api(n)
    guest,user_id=other(client,service,actor,'public-recipient','admin')
    try:
        row=client.get(PATH).json()
        bound=action(client,PATH,'choose-personal',row['revision'],token=TOKEN,exclusive=True).json()
        assert not guest.get(PATH).json()['public_available']
        owner_row=bind_owner(client,api)
        own=client.get(PATH).json()
        assert own['owner_account'] and own['public_available'] and not own['enabled'] and not own['private_target']
        assert guest.get(PATH).json()['bot_mode'] is None
        chosen=action(guest,PATH,'choose-public',0).json()
        assert chosen['public_available'] and not chosen['bound'] and not chosen['enabled']
        link,token=start(guest)
        set_messages(api,[update(2,token,1239876)])
        synced=action(guest,PATH,'sync-bot',link['revision'])
        assert synced.status_code==200 and synced.json()['pairing']['state']=='confirm'
        confirmed=action(guest,PATH,'confirm',link['revision']).json()
        assert confirmed['bound'] and not confirmed['enabled']
        enabled=guest.put(PATH,json=payload(confirmed['revision'],True,True),headers=headers(guest)).json()
        assert action(guest,PATH,'test',enabled['revision']).json()=={'state':'sent'}
        n.transport.send.assert_called_once_with(TOKEN,'1239876','Runtu：Telegram 个人消息设置测试。')
        with service.transaction() as session:
            assert session.get(PersonalTelegramBot,user_id) is None
            source=session.get(TelegramPlatform,1);assert source.owner_id==actor
            assert TOKEN not in session.get(PersonalTelegramBot,actor).ciphertext
        assert action(client,PATH,'disconnect',owner_row['revision']).status_code==200
        cleared=guest.get(PATH).json()
        assert cleared['bot_mode'] is None and not cleared['bound'] and not cleared['enabled'] and not cleared['private_target']
        assert not cleared['public_available']
    finally:guest.close()


def test_setup_owner_only_csrf_no_key_when_denied(auth):
    client,service,actor=auth;assert login(client).status_code==200
    key_path=Path(service.settings.notification_key_file)
    assert client.post('/api/admin/notifications/setup',json={'expected_revision':0}).status_code==403
    for role in ('admin','viewer'):
        guest,_=other(client,service,actor,'no-setup-'+role,role)
        try:assert guest.post('/api/admin/notifications/setup',json={'expected_revision':0},headers=headers(guest)).status_code==403
        finally:guest.close()
    assert not key_path.exists()


def test_public_revoked_owner_and_sync_conflicts_fail_closed(auth):
    client,service,actor=auth;assert login(client).status_code==200
    setup(client);n=client.app.state.notifications;api=mock_api(n)
    row=bind_owner(client,api)
    guest,_=other(client,service,actor,'revoked-public')
    try:
        chosen=action(guest,PATH,'choose-public',0).json()
        with service.transaction() as session:session.get(AuthUser,actor).role='admin'
        assert not guest.get(PATH).json()['public_available']
        assert action(guest,PATH,'connect',chosen['revision']).status_code==422
    finally:guest.close()


def test_private_key_permissions_reject_broad_access(tmp_path):
    store=PrivateKeyStore(tmp_path/'protected'/'master.key')
    secret=store.provision();assert isinstance(secret,SecretStr)
    assert store.read()==secret
    if os.name!='nt':
        os.chmod(store.path,0o644)
        with pytest.raises(PrivateKeyError):PrivateKeyStore(store.path).read()
    # A symlink cannot redirect the server key lookup.
    if os.name!='nt':
        link=tmp_path/'key-link';link.symlink_to(store.path)
        with pytest.raises(PrivateKeyError):PrivateKeyStore(link).read()


def test_multi_downgrade_preflights_before_platform_table_drop(auth):
    from alembic import command
    from sqlalchemy import inspect
    from tests.test_persistence import migration_config
    client,service,actor=auth
    with service.transaction() as session:
        session.add(PersonalTelegramBot(user_id=actor,ciphertext='test-only',bot_id='123456',username='FixtureBot',fingerprint='a'*64,update_offset=0))
    with service.database.engine.connect() as connection:
        config=migration_config();config.attributes['connection']=connection
        with pytest.raises(RuntimeError,match='Unlink personal'):
            command.downgrade(config,'0008_notifications')
        assert 'telegram_platform' in inspect(connection).get_table_names()
