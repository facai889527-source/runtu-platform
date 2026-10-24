import json
from unittest.mock import Mock

from cryptography.fernet import Fernet
from pydantic import SecretStr
import pytest

from backend.config import Settings
from backend.telegram_security import TelegramAPI, TelegramBusy, TelegramUnavailable, TelegramVault, SecretStorageUnavailable


def test_secret_encryption_binds_owner_rotates_and_fails_closed(tmp_path):
    first,second=Fernet.generate_key().decode(),Fernet.generate_key().decode()
    settings=Settings(_env_file=None,notification_encryption_keys=first,notification_key_file=str(tmp_path/"absent.key"))
    vault=TelegramVault(settings);secret=SecretStr('fixture-personal-secret')
    sealed=vault.seal('account-a',secret)
    assert secret.get_secret_value() not in sealed and vault.open('account-a',sealed)==secret
    with pytest.raises(SecretStorageUnavailable):vault.open('account-b',sealed)
    with pytest.raises(SecretStorageUnavailable):vault.open('account-a',sealed[:-2]+'xx')
    settings.notification_encryption_keys=SecretStr(second+','+first)
    rotated=vault.rotate('account-a',sealed)
    settings.notification_encryption_keys=SecretStr(second)
    assert vault.open('account-a',rotated)==secret
    with pytest.raises(SecretStorageUnavailable):vault.open('account-a',sealed)
    for invalid in (None,'bad-key',','.join([first]*5)):
        settings.notification_encryption_keys=SecretStr(invalid) if invalid else None
        assert not vault.available
        with pytest.raises(SecretStorageUnavailable):vault.seal('account-a',secret)


@pytest.mark.parametrize('outcome',['ok','redirect','busy','malformed','large','exception'])
def test_api_fixed_method_host_no_redirect_no_secret_error(monkeypatch,caplog,outcome):
    secret=SecretStr('123456789:'+'fixture_'*5)
    connection=Mock();response=Mock();connection.getresponse.return_value=response
    response.status={'redirect':302,'busy':409}.get(outcome,200)
    response.read.return_value=b'x'*65537 if outcome=='large' else b'bad' if outcome=='malformed' else json.dumps({'ok':True,'result':{'id':123,'is_bot':True}}).encode()
    if outcome=='exception':connection.request.side_effect=RuntimeError(secret.get_secret_value())
    factory=Mock(return_value=connection);monkeypatch.setattr('backend.telegram_security.http.client.HTTPSConnection',factory)
    if outcome=='ok':assert TelegramAPI().call(secret,'getMe')['is_bot']
    else:
        with pytest.raises(TelegramUnavailable) as failure:TelegramAPI().call(secret,'getMe')
        assert secret.get_secret_value() not in str(failure.value)
        if outcome == 'busy': assert isinstance(failure.value, TelegramBusy)
    factory.assert_called_once_with('api.telegram.org',timeout=2)
    connection.set_debuglevel.assert_called_once_with(0)
    connection.close.assert_called_once()
    with pytest.raises(TelegramUnavailable):TelegramAPI().call(secret,'https://foreign.test')
    assert secret.get_secret_value() not in caplog.text


@pytest.mark.parametrize('plaintext', [[], None, 'text', {'owner': 'a'}, {'owner': 'a', 'token': 1}])
def test_vault_rejects_invalid_authenticated_envelopes(plaintext):
    key = Fernet.generate_key()
    vault = TelegramVault(Settings(_env_file=None, notification_encryption_keys=key.decode()))
    ciphertext = Fernet(key).encrypt(json.dumps(plaintext).encode()).decode()
    with pytest.raises(SecretStorageUnavailable):
        vault.open('a', ciphertext)


@pytest.mark.parametrize('credential', ['123:short', '123:'+'a'*30+'/getMe', '123:'+'a'*30+'\r\nHost: evil', 'https://foreign.test'])
def test_api_rejects_credential_path_injection_before_connect(monkeypatch, credential):
    factory = Mock()
    monkeypatch.setattr('backend.telegram_security.http.client.HTTPSConnection', factory)
    with pytest.raises(TelegramUnavailable):
        TelegramAPI().call(SecretStr(credential), 'getMe')
    factory.assert_not_called()


@pytest.mark.parametrize('payload', [[], {'text': 'x'*65536}, {'offset': float('nan')}])
def test_api_bounds_request_before_connect(monkeypatch, payload):
    factory = Mock()
    monkeypatch.setattr('backend.telegram_security.http.client.HTTPSConnection', factory)
    with pytest.raises(TelegramUnavailable):
        TelegramAPI().call(SecretStr('123:'+'a'*30), 'getUpdates', payload)
    factory.assert_not_called()


def test_api_sanitizes_connect_and_cleanup_errors(monkeypatch):
    token = SecretStr('123:'+'a'*30)
    factory = Mock(side_effect=RuntimeError(token.get_secret_value()))
    monkeypatch.setattr('backend.telegram_security.http.client.HTTPSConnection', factory)
    with pytest.raises(TelegramUnavailable) as failure:
        TelegramAPI().call(token, 'getMe')
    assert str(failure.value) == ''
    connection = Mock()
    connection.getresponse.side_effect = RuntimeError(token.get_secret_value())
    connection.close.side_effect = RuntimeError(token.get_secret_value())
    factory.side_effect = None
    factory.return_value = connection
    with pytest.raises(TelegramUnavailable) as failure:
        TelegramAPI().call(token, 'getMe')
    assert str(failure.value) == ''
