"""Credential boundary and fixed Telegram API. Never expose transport diagnostics."""
import http.client
import json
import re

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from pydantic import SecretStr


class SecretStorageUnavailable(Exception): pass
class TelegramUnavailable(Exception): pass
class TelegramBusy(TelegramUnavailable): pass


class TelegramVault:
    def __init__(self, settings): self.settings = settings

    def cipher(self):
        raw = self.settings.notification_encryption_keys
        if not raw: raise SecretStorageUnavailable()
        try:
            keys = raw.get_secret_value().split(',')
            if not 1 <= len(keys) <= 4 or any(k != k.strip() for k in keys): raise ValueError()
            return MultiFernet([Fernet(k.encode('ascii')) for k in keys])
        except (ValueError, TypeError, UnicodeError): raise SecretStorageUnavailable() from None

    @property
    def available(self):
        try: self.cipher(); return True
        except SecretStorageUnavailable: return False

    def seal(self, owner, secret):
        # Bind ciphertext to its account: copying a DB blob cannot swap identities.
        value = json.dumps({'owner':owner, 'token':secret.get_secret_value()}, separators=(',',':')).encode()
        return self.cipher().encrypt(value).decode('ascii')

    def open(self, owner, ciphertext):
        try:
            value = json.loads(self.cipher().decrypt(ciphertext.encode('ascii')))
            if not isinstance(value, dict) or set(value) != {'owner','token'} or value['owner'] != owner or not isinstance(value['token'],str): raise ValueError()
            return SecretStr(value['token'])
        except (InvalidToken, ValueError, TypeError, UnicodeError, KeyError): raise SecretStorageUnavailable() from None

    def rotate(self, owner, ciphertext):
        self.open(owner, ciphertext)  # Verify the owner envelope before rotating.
        try: return self.cipher().rotate(ciphertext.encode('ascii')).decode('ascii')
        except (InvalidToken, ValueError, TypeError, UnicodeError): raise SecretStorageUnavailable() from None


class TelegramAPI:
    METHODS = frozenset({'getMe','getWebhookInfo','getUpdates','getChat','getChatMember','sendMessage'})

    def call(self, token, method, payload=None):
        if method not in self.METHODS: raise TelegramUnavailable()
        connection = None
        try:
            credential = token.get_secret_value()
            if not re.fullmatch(r'[1-9][0-9]{0,19}:[A-Za-z0-9_-]{30,100}', credential): raise TelegramUnavailable()
            if payload is not None and not isinstance(payload, dict): raise TelegramUnavailable()
            body = json.dumps(payload if payload is not None else {}, allow_nan=False).encode()
            if len(body) > 65536: raise TelegramUnavailable()
            connection = http.client.HTTPSConnection('api.telegram.org', timeout=2)
            connection.set_debuglevel(0)
            connection.request('POST', '/bot'+credential+'/'+method,
                body=body, headers={'Content-Type':'application/json','Accept':'application/json'})
            response=connection.getresponse(); raw=response.read(65537)
            if response.status==409: raise TelegramBusy()
            if response.status!=200 or len(raw)>65536: raise TelegramUnavailable()
            value=json.loads(raw)
            if not isinstance(value,dict) or value.get('ok') is not True or 'result' not in value: raise TelegramUnavailable()
            return value['result']
        except TelegramUnavailable: raise
        except Exception: raise TelegramUnavailable() from None
        finally:
            if connection is not None:
                try: connection.close()
                except Exception: pass  # Cleanup diagnostics may include the credential-bearing URL.
