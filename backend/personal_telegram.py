"""Account-bound Bot ownership, encrypted storage and explicit exclusive update ingestion."""
from datetime import timedelta
import re
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.auth.service import aware, digest
from backend.models import PersonalTelegramBot
from backend.telegram_security import TelegramAPI, TelegramVault, TelegramUnavailable, TelegramBusy, SecretStorageUnavailable
from backend.user_management import UserConflict


class PersonalBotInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,hide_input_in_errors=True)
    token: SecretStr
    exclusive: bool
    expected_revision: int=Field(ge=0,le=2147483646)

    @field_validator('token')
    @classmethod
    def token_format(cls,value):
        if not re.fullmatch(r'[1-9][0-9]{4,19}:[A-Za-z0-9_-]{30,80}',value.get_secret_value()):raise ValueError('Invalid Bot token')
        return value

    @field_validator('exclusive')
    @classmethod
    def exclusive_required(cls,value):
        if value is not True:raise ValueError('Exclusive control required')
        return value


class PersonalBots:
    def __init__(self,notifications):
        self.n=notifications
        self.vault=TelegramVault(notifications.auth.settings)
        self.api=TelegramAPI()

    @property
    def available(self):return bool(self.n.enabled and self.vault.available)

    def ready(self,session):return bool(self.n.is_enabled(session) and self.vault.available)

    def context(self,session,row):
        if not self.ready(session):raise SecretStorageUnavailable()
        bot=session.get(PersonalTelegramBot,row.user_id)
        if not bot or row.bot_key!=bot.fingerprint:raise SecretStorageUnavailable()
        token=self.vault.open(row.user_id,bot.ciphertext)
        if digest(token.get_secret_value())!=bot.fingerprint:raise SecretStorageUnavailable()
        return token,bot.username

    def bind(self,actor,key,value,target=None):
        # Authorize before any credential-bearing network request, then recheck
        # under the business mutex before committing results of external calls.
        with self.n.own(actor,key,target=target) as (session,user):
            row=self.n.profile(session,user.id);self.n.expect(row,value.expected_revision)
            if not user.active:raise TelegramUnavailable()
            recipient=user.id
        if not self.available:raise SecretStorageUnavailable()
        self.n.auth._reserve([('telegram-personal:'+actor,5),('telegram-personal-global',30)])
        me=self.api.call(value.token,'getMe')
        if (not isinstance(me,dict) or me.get('is_bot') is not True or type(me.get('id')) is not int
                or not 0<me['id']<2**52 or str(me['id'])!=value.token.get_secret_value().split(':')[0]
                or not isinstance(me.get('username'),str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{1,28}[Bb][Oo][Tt]',me['username'])):raise TelegramUnavailable()
        self.no_webhook(value.token)
        ciphertext=self.vault.seal(recipient,value.token)
        fingerprint=digest(value.token.get_secret_value())
        try:
            with self.n.own(actor,key,True,target) as (session,user):
                row=self.n.profile(session,user.id,True);self.n.expect(row,value.expected_revision)
                if not user.active:raise TelegramUnavailable()
                other=session.scalar(select(PersonalTelegramBot.user_id).where(PersonalTelegramBot.bot_id==str(me['id']),PersonalTelegramBot.user_id!=user.id))
                if other:raise UserConflict()
                self.n.clear(session,row);session.flush()
                session.add(PersonalTelegramBot(user_id=user.id,ciphertext=ciphertext,bot_id=str(me['id']),username=me['username'],fingerprint=fingerprint,update_offset=0,lease_id=None,lease_until=None))
                row.bot_mode,row.bot_key='personal',fingerprint
                self.n.change(row);self.n.auth._event(session,'telegram_personal_selected','notification-manager:'+actor,user.id)
                session.flush();return self.n.public(session,user,row)
        except IntegrityError:raise UserConflict() from None

    def no_webhook(self,token):
        info=self.api.call(token,'getWebhookInfo')
        if not isinstance(info,dict) or info.get('url')!='':raise TelegramBusy()

    def rotate(self,actor,key,revision,target=None):
        with self.n.own(actor,key,True,target) as (session,user):
            row=self.n.profile(session,user.id);self.n.expect(row,revision)
            self.context(session,row)
            bot=session.get(PersonalTelegramBot,user.id)
            if row.bot_mode!='personal':raise UserConflict()
            bot.ciphertext=self.vault.rotate(user.id,bot.ciphertext)
            self.n.auth._event(session,'telegram_secret_rotated','notification-manager:'+actor,user.id)
            session.flush();return self.n.public(session,user,row)

    def sync(self,actor,key,revision,target=None):
        from backend.notifications import NotificationIncomplete
        self.n.auth._reserve([('telegram-sync:'+actor,10),('telegram-sync-global',60)])
        lease=str(uuid4())
        with self.n.own(actor,key,True,target) as (session,user):
            row=self.n.profile(session,user.id);self.n.expect(row,revision)
            if row.bot_mode not in ('personal','public') or not user.active:raise UserConflict()
            if row.bot_mode=='personal':token,_=self.context(session,row);source_owner=user.id
            else:token,_,_,source_owner=self.n.public_context(session)
            request_key,request_mode=row.bot_key,row.bot_mode
            bot=session.get(PersonalTelegramBot,source_owner)
            now=self.n.auth.clock()
            if bot.lease_until and aware(bot.lease_until)>now:raise TelegramBusy()
            bot.lease_id,bot.lease_until=lease,now+timedelta(seconds=30)
            offset,recipient,fingerprint=bot.update_offset,source_owner,bot.fingerprint
        try:
            self.no_webhook(token)
            updates=self.api.call(token,'getUpdates',{'offset':offset,'limit':20,'timeout':0,'allowed_updates':['message']})
            if not isinstance(updates,list) or len(updates)>20:raise TelegramUnavailable()
            with self.n.own(actor,key,True,target) as (session,user):
                row=self.n.profile(session,user.id);self.n.expect(row,revision)
                bot=session.get(PersonalTelegramBot,recipient)
                if (not user.active or not bot or bot.lease_id!=lease or not bot.lease_until or aware(bot.lease_until)<=self.n.auth.clock()
                        or bot.fingerprint!=fingerprint or row.bot_mode!=request_mode or row.bot_key!=request_key or not self.n.selected(row,session)):raise UserConflict()
                # Validate/deduplicate the entire bounded batch before consuming
                # proofs. Sort so out-of-order replies cannot skip older proofs.
                ordered={}
                for update in updates:
                    if not isinstance(update,dict) or type(update.get('update_id')) is not int or not 0<=update['update_id']<2147483647:raise TelegramUnavailable()
                    ident=update['update_id']
                    if ident in ordered and ordered[ident]!=update:raise TelegramUnavailable()
                    ordered[ident]=update
                next_offset=offset
                for _,update in sorted(ordered.items()):
                    if update['update_id']<next_offset:continue
                    self.n.process_pair_message(session,update,'personal',fingerprint,recipient)
                    try:
                        _,_,public_key,public_owner=self.n.public_context(session)
                        if public_owner==recipient:self.n.process_pair_message(session,update,'public',public_key)
                    except (NotificationIncomplete,SecretStorageUnavailable,TelegramUnavailable):pass
                    next_offset=update['update_id']+1
                bot.update_offset=next_offset;bot.lease_id,bot.lease_until=None,None
                session.flush();return self.n.public(session,user,row)
        finally:
            # A slow/failed old request must never clear a replacement lease.
            with self.n.auth.transaction() as session:
                self.n.lock(session)
                bot=session.get(PersonalTelegramBot,recipient)
                if bot and bot.lease_id==lease:bot.lease_id,bot.lease_until=None,None
