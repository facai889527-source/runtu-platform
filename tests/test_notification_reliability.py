from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from urllib.parse import urlsplit,parse_qs
from uuid import uuid4
from unittest.mock import Mock
import json
import pytest
from alembic import command
from sqlalchemy import select,text
from backend.auth.service import digest
from backend.models import AuthUser,AuthSession,TelegramPlatform,TelegramChallenge,AccountNotification,PersonalTelegramBot
from backend.migrations import migration_config
from backend.user_management import UserConflict
from backend.telegram_security import TelegramUnavailable
from tests.test_auth import auth
from tests.test_notifications import ready,PATH,bind,payload,callback,begin
from tests.test_module_management import headers
from tests.test_personal_telegram import personal,choose,action


def participants(n,count):
    people=[]
    with n.auth.transaction() as session:
        source=session.get(TelegramPlatform,1)
        for i in range(count):
            uid=str(uuid4());key=digest('fixture-session-'+uid);now=n.auth.clock()
            session.add(AuthUser(id=uid,username='parallel-'+uid,password_hash='unusable-fixture',role='viewer',active=True,is_admin=False,created_at=now))
            session.flush()
            session.add(AuthSession(token_hash=key,user_id=uid,created_at=now,last_seen_at=now,expires_at=now+timedelta(hours=1)))
            row=n.profile(session,uid,True);row.bot_mode='public';row.bot_key=source.public_key
            people.append((uid,key))
    return people


def update(ident,token,chat,**details):
    return {'update_id':ident,'message':{'text':'/start '+token,'chat':{'id':chat,'type':'private'},'from':{'id':chat,'is_bot':False,**details}}}


def test_100_simultaneous_challenges_atomic_consumption_and_confirmed_identity(ready):
    client,service,actor,n=ready;people=participants(n,100);gate=Barrier(100)
    def start(person):
        gate.wait(timeout=20)
        result=n.begin(*person,0)
        return parse_qs(urlsplit(result['url']).query)['start'][0]
    with ThreadPoolExecutor(max_workers=100) as pool:tokens=list(pool.map(start,people))
    assert len(set(tokens))==100
    messages=[update(i,t,1000000+i,first_name='Fixture '+str(i)) for i,t in enumerate(tokens)]
    gate=Barrier(100)
    def consume(message):gate.wait(timeout=20);n.callback(message)
    with ThreadPoolExecutor(max_workers=100) as pool:list(pool.map(consume,reversed(messages)))
    # Duplicate proof from a different sender cannot replace the consumed identity.
    with ThreadPoolExecutor(max_workers=20) as pool:list(pool.map(n.callback,[update(i,t,2000000+i) for i,t in enumerate(tokens)]))
    for i,(uid,key) in enumerate(people):
        value=n.read(uid,key)
        assert value['candidate_identity']['user_id']==str(1000000+i)
        assert value['candidate_identity']['chat_id']==str(1000000+i)
        assert not value['bound'] and not value['enabled']
        with pytest.raises(UserConflict):n.confirm(uid,key,1,candidate_user_id=str(2000000+i))
    gate=Barrier(100)
    def confirm(item):
        i,person=item;gate.wait(timeout=20)
        return n.confirm(*person,1,candidate_user_id=str(1000000+i))
    with ThreadPoolExecutor(max_workers=100) as pool:rows=list(pool.map(confirm,enumerate(people)))
    assert all(r['bound'] and not r['enabled'] and not r['private_target'] for r in rows)
    with service.transaction() as session:
        assert session.scalar(select(TelegramChallenge).where(TelegramChallenge.user_id.in_([p[0] for p in people]))) is None
    assert n.transport.send.call_count==0


def test_out_of_order_shared_poll_does_not_skip_another_accounts_proof(ready):
    client,service,actor,n=ready;people=participants(n,3)
    starts=[n.begin(*p,0) for p in people]
    tokens=[parse_qs(urlsplit(v['url']).query)['start'][0] for v in starts]
    messages=[update(10+i,t,3000000+i,first_name='<b>Fixture</b>',last_name='Name',username=None) for i,t in enumerate(tokens)]
    n.personal.api=Mock();n.personal.api.call.side_effect=lambda token,method,data=None:{'url':''} if method=='getWebhookInfo' else [messages[2],messages[0],messages[1],messages[0]]
    synced=n.personal.sync(*people[0],1)
    assert synced['candidate_identity']['first_name']=='<b>Fixture</b>'
    for i,p in enumerate(people):assert n.read(*p)['candidate_identity']['user_id']==str(3000000+i)
    with service.transaction() as session:
        source=session.get(TelegramPlatform,1);bot=session.get(PersonalTelegramBot,source.owner_id)
        assert bot.update_offset==13 and bot.lease_id is None
    assert n.transport.send.call_count==0


def test_conflicting_duplicate_batch_rolls_back_all_proofs_and_offset(ready):
    _,service,_,n=ready;p=participants(n,1)[0];start=n.begin(*p,0);token=parse_qs(urlsplit(start['url']).query)['start'][0]
    n.personal.api=Mock();n.personal.api.call.side_effect=lambda secret,method,data=None:{'url':''} if method=='getWebhookInfo' else [update(1,token,4000001),update(1,token,4000002)]
    with pytest.raises(TelegramUnavailable):n.personal.sync(*p,1)
    assert n.read(*p)['pairing']['state']=='waiting'
    with service.transaction() as session:
        source=session.get(TelegramPlatform,1);bot=session.get(PersonalTelegramBot,source.owner_id)
        assert bot.update_offset==0 and bot.lease_id is None


def test_custom_plaintext_message_auth_limit_and_no_arbitrary_destination(ready):
    client,_,_,n=ready;row=bind(client)
    text_value='<b>plain text</b> & \n第二行 😀'
    bad={'expected_revision':row['revision'],'message':text_value}
    assert client.post(PATH+'/test',json=bad).status_code==403
    for extra in ({'chat_id':'other'},{'user_id':'other'},{'parse_mode':'HTML'}):
        assert client.post(PATH+'/test',json={**bad,**extra},headers=headers(client)).status_code==422
    for message in ('','  ','x'*4097,'😀'*2049,'bad\x00text'):
        assert client.post(PATH+'/test',json={**bad,'message':message},headers=headers(client)).status_code==422
    assert client.post(PATH+'/test',json=bad,headers=headers(client)).json()=={'state':'sent'}
    assert n.transport.send.call_args.args[1:]==('123456789',text_value)
    assert client.post(PATH+'/test',json=bad,headers=headers(client)).status_code==429
    assert n.transport.send.call_count==1


def test_identity_metadata_and_explicit_candidate_confirmation(personal):
    client,service,actor,n,api=personal
    choose(client);current=client.get(PATH).json();link=action(client,PATH,'connect',current['revision']).json();token=parse_qs(urlsplit(link['url']).query)['start'][0]
    base=api.call.side_effect
    api.call.side_effect=lambda secret,method,data=None:[update(1,token,5678901,first_name='Lin',last_name='Example',username='before_name')] if method=='getUpdates' else base(secret,method,data)
    row=action(client,PATH,'sync-bot',link['revision']).json();assert row['candidate_identity']['display_name']=='Lin Example'
    assert client.post(PATH+'/confirm',json={'expected_revision':link['revision']},headers=headers(client)).status_code==409
    assert client.post(PATH+'/confirm',json={'expected_revision':link['revision'],'candidate_user_id':'5678902'},headers=headers(client)).status_code==409
    confirmed=action(client,PATH,'confirm',link['revision']).json()
    assert confirmed['identity']['username']=='before_name' and confirmed['identity']['user_id']=='5678901'
    # Re-verification refreshes names, not mutable-username-only proof.
    next_link=action(client,PATH,'connect',confirmed['revision']).json();next_token=parse_qs(urlsplit(next_link['url']).query)['start'][0]
    api.call.side_effect=lambda secret,method,data=None:[update(2,next_token,5678901,first_name='Changed',username=None)] if method=='getUpdates' else base(secret,method,data)
    action(client,PATH,'sync-bot',next_link['revision']);row=action(client,PATH,'confirm',next_link['revision']).json()
    assert row['identity']['username'] is None and row['identity']['display_name']=='Changed' and not row['enabled']


def test_identity_migration_preserves_existing_routes_preferences_and_ciphertext(ready):
    client,service,actor,n=ready;row=bind(client)
    with service.transaction() as session:
        source=session.get(TelegramPlatform,1);owner=source.owner_id;cipher=session.get(PersonalTelegramBot,owner).ciphertext;public_key=source.public_key
    with service.database.engine.begin() as connection:
        config=migration_config();config.attributes['connection']=connection;command.downgrade(config,'0012_owner_public_bot')
        before=connection.execute(text('SELECT chat_id,enabled,registration,revision,bot_key,private_target FROM account_notifications WHERE user_id=:id'),{'id':actor}).one()
        command.upgrade(config,'0013_telegram_identity');command.check(config)
        after=connection.execute(text('SELECT chat_id,enabled,registration,revision,bot_key,private_target FROM account_notifications WHERE user_id=:id'),{'id':actor}).one()
        assert before==after
    with service.transaction() as session:
        assert session.get(PersonalTelegramBot,owner).ciphertext==cipher
        assert session.get(TelegramPlatform,1).public_key==public_key
    value=client.get(PATH).json();assert value['identity']['user_id']=='123456789' and value['enabled'] and value['private_target']


def test_webhook_empty_secret_is_never_accepted(ready):
    from pydantic import SecretStr
    client,service,actor,n=ready;token,revision=begin(client)
    service.settings.telegram_webhook_secret=SecretStr('')
    assert callback(client,token).status_code==403
    assert client.get(PATH).json()['pairing']['state']=='waiting'


def test_disabled_recipient_has_no_ready_capability_or_custom_delivery(ready):
    client,service,actor,n=ready;row=bind(client)
    with service.transaction() as session:session.get(AuthUser,actor).active=False
    # Own authentication is immediately revoked, regardless of persisted prefs.
    assert client.get(PATH).status_code in (401,403)
    assert client.post(PATH+'/test',json={'expected_revision':row['revision'],'message':'fixture'},headers=headers(client)).status_code in (401,403)
    assert n.transport.send.call_count==0
