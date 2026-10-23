import asyncio
import hmac
import json
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.auth.routes import auth_error, require_authenticated, token_from
from backend.auth.service import AuthDenied, digest
from backend.notifications import NotificationIncomplete, NotificationInput, NotificationService, TestInput
from backend.registration_routes import body
from backend.personal_telegram import PersonalBotInput
from backend.telegram_security import SecretStorageUnavailable, TelegramUnavailable, TelegramBusy


def install_notifications(app):
    service = NotificationService(app.state.auth_service)
    app.state.notifications = service
    app.state.registration.notification = service.registration_committed
    router = APIRouter()

    def owner_scope(request, identity, target):
        if request.query_params: raise auth_error(422, 'Unexpected notification query')
        if target is not None and (not request.url.path.startswith('/api/admin/notifications/users/') or identity.role != 'owner'):
            raise auth_error(403, 'Notification access denied')

    def key(request): return digest(token_from(request, service.auth))
    def result(value): return JSONResponse(value, headers={'Cache-Control': 'no-store'})

    @router.get('/api/me/notifications')
    @router.get('/api/admin/notifications/users/{target}')
    def read(request: Request, identity=Depends(require_authenticated), target: str | None = None):
        owner_scope(request, identity, target)
        try: return result(service.read(identity.id, key(request), target))
        except AuthDenied: raise auth_error(403, 'Notification access denied') from None

    @router.put('/api/me/notifications')
    @router.put('/api/admin/notifications/users/{target}')
    async def save(request: Request, identity=Depends(require_authenticated), target: str | None = None):
        owner_scope(request, identity, target)
        value = await body(request, NotificationInput)
        try: return result(await run_in_threadpool(service.save, identity.id, key(request), value, target))
        except AuthDenied: raise auth_error(403, 'Notification access denied') from None
        except NotificationIncomplete: raise auth_error(422, 'Verified Telegram binding required') from None

    @router.post('/api/me/notifications/{action}')
    @router.post('/api/admin/notifications/users/{target}/{action}')
    async def action(action: str, request: Request, identity=Depends(require_authenticated), target: str | None = None):
        owner_scope(request, identity, target)
        if action not in ('choose-public', 'choose-personal', 'sync-personal', 'rotate-secret', 'connect', 'confirm', 'disconnect', 'test'): raise auth_error(404, 'Action unavailable')
        value = await body(request, PersonalBotInput if action=='choose-personal' else TestInput)
        try:
            if action=='choose-personal':return result(await run_in_threadpool(service.personal.bind,identity.id,key(request),value,target))
            if action in ('sync-personal','rotate-secret'):
                method=service.personal.sync if action=='sync-personal' else service.personal.rotate
                return result(await run_in_threadpool(method,identity.id,key(request),value.expected_revision,target))
            if action == 'test':
                future = await run_in_threadpool(service.test, identity.id, key(request), value.expected_revision, target)
                success = await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(future)), timeout=3)
                if not success: raise auth_error(502, 'Telegram delivery not confirmed; refresh settings')
                return result({'state': 'sent'})
            method = {'choose-public': service.choose_public, 'connect': service.begin, 'confirm': service.confirm, 'disconnect': service.unlink}[action]
            return result(await run_in_threadpool(method, identity.id, key(request), value.expected_revision, target))
        except AuthDenied: raise auth_error(403, 'Notification access denied') from None
        except NotificationIncomplete: raise auth_error(422, 'Verified Telegram binding or platform setup required') from None
        except SecretStorageUnavailable: raise auth_error(503, 'Secure Telegram storage unavailable; operator key setup required') from None
        except TelegramBusy: raise auth_error(409, 'Bot has an active webhook or polling conflict; no takeover performed') from None
        except TelegramUnavailable: raise auth_error(502, 'Telegram control verification or synchronization failed') from None
        except TimeoutError: raise auth_error(504, 'Delivery unconfirmed; do not retry immediately') from None

    @router.get('/api/admin/notifications/platform')
    def platform(request: Request,identity=Depends(require_authenticated)):
        if request.query_params:raise auth_error(422,'Unexpected query')
        with service.own(identity.id,key(request)) as (_,user):
            if user.role!='owner':raise auth_error(403,'Owner required')
        config=service.auth.settings
        return result(dict(feature_enabled=config.telegram_binding_enabled,public_ready=service.configured,
            token_present=bool(config.telegram_bot_token),username_present=bool(config.telegram_bot_username),
            webhook_secret_present=bool(config.telegram_webhook_secret),encryption_ready=service.personal.vault.available))

    app.include_router(router)

    @app.post('/api/telegram/webhook')
    async def webhook(request: Request):
        config = service.auth.settings
        expected = config.telegram_webhook_secret.get_secret_value() if config.telegram_webhook_secret else ''
        supplied = request.headers.get('x-telegram-bot-api-secret-token', '')
        if not service.configured: raise auth_error(503, 'Telegram binding unavailable')
        origin = urlsplit(config.auth_origin or '')
        if (request.url.scheme != 'https' or origin.scheme != 'https' or request.headers.get('host','').lower() != origin.netloc
                or not hmac.compare_digest(supplied.encode(), expected.encode())):
            raise auth_error(403, 'Callback denied')
        if request.headers.get('content-type','').split(';')[0].strip() != 'application/json': raise auth_error(415, 'JSON required')
        raw = bytearray()
        try:
            async for chunk in request.stream():
                if len(raw)+len(chunk)>8192: raise auth_error(413, 'Callback too large')
                raw.extend(chunk)
            try:
                data=json.loads(raw)
                if not isinstance(data,dict): raise ValueError()
            except (ValueError,TypeError,UnicodeError,RecursionError): raise auth_error(422, 'Invalid callback') from None
            await run_in_threadpool(service.auth._reserve, [('telegram-callback-global',300)])
            await run_in_threadpool(service.callback, data)
            # Never reveal whether a challenge, account or destination existed.
            return result({'ok': True})
        finally: raw.clear()
