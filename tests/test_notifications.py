from concurrent.futures import ThreadPoolExecutor
import json
from threading import Event
from unittest.mock import Mock

from alembic import command
from pydantic import SecretStr
import pytest
from sqlalchemy import delete, event, inspect, select
from sqlalchemy.exc import OperationalError

from backend.auth.service import AuthDenied, digest
from backend.migrations import migration_config
from backend.models import AuthEvent, AuthRateLimit, AuthSession, AuthUser, NotificationPreferences
from backend.notifications import CAPABILITIES, NotificationInput, TelegramTransport
from tests.test_auth import auth, login, ORIGIN
from tests.test_module_management import headers
from tests.test_registration import applicant, set_policy, signup

PATH = '/api/admin/notifications/telegram'
# Deliberately synthetic, nonfunctional credential; never use external networking.
TOKEN = '123456789:' + 'fixture_' * 5


def payload(revision=0, **changes):
    return dict(enabled=False, chat_id='', events=dict(registration=False, account_security=False,
        tool_outcomes=False, system_errors=False), expected_revision=revision, **changes)


def exercise_notification_preferences(client):
    current = client.get(PATH)
    assert current.status_code == 200 and current.headers['cache-control'] == 'no-store'
    assert set(current.json()) == {'enabled','chat_id','events','supported','token_configured','token_source','revision'}
    assert current.json()['supported'] == CAPABILITIES and current.json()['token_source'] == 'environment'
    value = payload(); value['chat_id'] = '-1001234567890'; value['events']['registration'] = True
    saved = client.put(PATH, json=value, headers=headers(client))
    assert saved.status_code == 200 and saved.json()['revision'] == 1
    assert client.put(PATH, json=value, headers=headers(client)).status_code == 409
    assert client.put(PATH, json=payload(1), headers=headers(client)).json()['revision'] == 2


def test_preferences_secret_contract_and_optimistic_updates(auth):
    client, service, _ = auth
    assert login(client).status_code == 200
    exercise_notification_preferences(client)
    assert client.post(PATH+'/test',json={'expected_revision':2},headers=headers(client)).status_code == 422
    with service.transaction() as session:
        assert {col['name'] for col in inspect(session.bind).get_columns('notification_preferences')} == {
            'id','enabled','chat_id','registration','revision'}
        assert session.get(NotificationPreferences,1).chat_id == ''


@pytest.mark.parametrize('role,status', [('owner',200),('admin',200),('viewer',403)])
def test_notification_role_origin_csrf_and_revoked_session(auth, role, status):
    client, service, actor = auth
    assert client.get(PATH).status_code == 401
    assert login(client).status_code == 200
    with service.transaction() as session: session.get(AuthUser,actor).role = role
    assert client.get(PATH).status_code == status
    assert client.put(PATH,json=payload(),headers=headers(client)).status_code == status
    assert client.put(PATH,json=payload(),headers={'Origin':ORIGIN}).status_code == 403
    assert client.put(PATH,json=payload(),headers={**headers(client),'Origin':'https://foreign.test'}).status_code == 403
    key = digest(client.cookies.get('__Host-runtu_session'))
    with service.transaction() as session: session.execute(delete(AuthSession).where(AuthSession.token_hash==key))
    with pytest.raises(AuthDenied): client.app.state.notifications.read(actor,key)


def test_validation_no_secret_echo_and_unavailable_schema(auth, caplog):
    client, service, _ = auth
    assert login(client).status_code == 200
    for change in [dict(chat_id='https://evil.test'),dict(chat_id='@channel'),dict(chat_id='1\n'),dict(chat_id='0'),
                   dict(chat_id=str(2**52)),dict(bot_token=TOKEN),dict(url='https://evil.test'),dict(enabled='true')]:
        value=payload();value.update(change)
        response=client.put(PATH,json=value,headers=headers(client))
        assert response.status_code==422 and TOKEN not in response.text and response.headers['cache-control']=='no-store'
    value=payload();value['events']['system_errors']=True
    assert client.put(PATH,json=value,headers=headers(client)).status_code==422
    value=payload();value.update(enabled=True,chat_id='12345')
    assert client.put(PATH,json=value,headers=headers(client)).status_code==422
    with service.database.engine.begin() as connection:
        config=migration_config();config.attributes['connection']=connection
        command.downgrade(config,'0007_login_activity')
    assert client.get(PATH).status_code==503
    assert TOKEN not in caplog.text


def configure(client):
    service=client.app.state.notifications
    service.auth.settings.telegram_bot_token=SecretStr(TOKEN)
    service.transport=Mock()
    service.transport.send.return_value=True
    value=payload();value.update(enabled=True,chat_id='-10012345');value['events']['registration']=True
    assert client.put(PATH,json=value,headers=headers(client)).status_code==200
    return service


def test_real_feedback_rate_limit_safe_failure_and_masked_token(auth, caplog):
    client, auth_service, actor=auth
    assert login(client).status_code==200
    service=configure(client)
    response=client.get(PATH)
    assert response.json()['token_configured'] is True and TOKEN not in response.text
    result=client.post(PATH+'/test',json={'expected_revision':1},headers=headers(client))
    assert result.status_code==200 and result.json()=={'state':'sent'}
    assert client.post(PATH+'/test',json={'expected_revision':1},headers=headers(client)).status_code==429
    service.transport.send.assert_called_once_with(TOKEN,'-10012345','Runtu：Telegram 消息设置测试。')
    with auth_service.transaction() as session:
        session.execute(delete(AuthRateLimit))
        session.get(AuthUser,actor).role='admin'
    service.transport.send.side_effect=RuntimeError('transport secret '+TOKEN)
    result=client.post(PATH+'/test',json={'expected_revision':1},headers=headers(client))
    assert result.status_code==502 and TOKEN not in result.text and TOKEN not in caplog.text
    assert 'sent' not in result.text


def test_registration_emits_only_committed_pending_once_and_never_blocks(auth):
    client, auth_service, _=auth
    assert login(client).status_code==200
    service=configure(client)
    assert set_policy(client).status_code==200
    sent=Event()
    service.transport.send.side_effect=lambda *_: sent.set() or False
    with applicant(client.app) as guest:
        assert signup(guest,'notice-candidate')[0].status_code==202
    assert sent.wait(2)
    service.queue.join()
    service.transport.send.assert_called_once()
    assert 'notice-candidate' not in service.transport.send.call_args.args[-1]
    with applicant(client.app) as duplicate:
        assert signup(duplicate,'notice-candidate')[0].status_code==202
    service.queue.join();assert service.transport.send.call_count==1
    assert set_policy(client,approval=False).status_code==200
    with applicant(client.app) as direct:
        assert signup(direct,'direct-notice')[0].status_code==202
    service.queue.join();assert service.transport.send.call_count==1
    assert set_policy(client).status_code==200
    calls=[];client.app.state.registration.notification=calls.append
    def fail(*_): raise OperationalError('disposable audit',{},Exception('fixture'))
    event.listen(AuthEvent,'before_insert',fail)
    try:
        with applicant(client.app) as guest: assert signup(guest,'rollback-notice')[0].status_code==503
    finally: event.remove(AuthEvent,'before_insert',fail)
    assert calls==[]
    client.app.state.registration.notification=lambda *_: (_ for _ in ()).throw(RuntimeError('queue unavailable'))
    with applicant(client.app) as guest: assert signup(guest,'queue-failure')[0].status_code==202


def test_worker_rechecks_permission_revision_and_handles_bounded_queue(auth):
    client, auth_service, actor=auth
    assert login(client).status_code==200
    service=configure(client);key=digest(client.cookies.get('__Host-runtu_session'))
    with auth_service.transaction() as session: session.get(AuthUser,actor).role='viewer'
    with pytest.raises(AuthDenied): service._test_delivery(actor,key,1)
    with auth_service.transaction() as session: session.get(AuthUser,actor).role='owner'
    assert service._test_delivery(actor,key,0) is False
    service.close()
    assert service._offer(('registration','absent')) is False


def test_delivery_deadline_queue_pressure_and_no_business_wait(auth):
    client, _, _ = auth
    assert login(client).status_code == 200
    service = configure(client)
    entered, release = Event(), Event()
    def slow(*_):
        entered.set()
        release.wait(6)
        return False
    service.transport.send.side_effect = slow
    try:
        # The API returns an unconfirmed result on deadline; no success is invented.
        result = client.post(PATH+'/test', json={'expected_revision':1}, headers=headers(client))
        assert entered.is_set() and result.status_code == 504
        assert 'sent' not in result.text
        for _ in range(16): assert service._offer(('registration','fixture')) is True
        assert service._offer(('registration','fixture')) is False
        service.registration_committed('dropped-fixture')  # nonblocking when full
    finally:
        release.set()
        service.queue.join()


def test_audit_failure_rolls_back_settings_and_concurrent_saves(auth):
    client, auth_service, actor=auth
    assert login(client).status_code==200
    service=client.app.state.notifications;key=digest(client.cookies.get('__Host-runtu_session'))
    def fail(*_): raise OperationalError('fixture',{},Exception('fixture'))
    event.listen(AuthEvent,'before_insert',fail)
    value=payload();value['chat_id']='12345'
    try: assert client.put(PATH,json=value,headers=headers(client)).status_code==503
    finally: event.remove(AuthEvent,'before_insert',fail)
    assert client.get(PATH).json()['revision']==0
    def save(_):
        try: service.save(actor,key,NotificationInput.model_validate(value));return 'saved'
        except Exception as error:
            from backend.user_management import UserConflict
            if isinstance(error,UserConflict): return 'conflict'
            raise
    with ThreadPoolExecutor(max_workers=2) as pool: assert sorted(pool.map(save,range(2)))==['conflict','saved']
    with auth_service.database.engine.begin() as connection:
        config=migration_config();config.attributes['connection']=connection
        command.check(config)
        with pytest.raises(RuntimeError,match='clear notification'): command.downgrade(config,'0007_login_activity')
    assert client.get(PATH).json()['chat_id']=='12345'


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
