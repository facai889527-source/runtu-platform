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


def install_notifications(app):
    service = NotificationService(app.state.auth_service)
    app.state.notifications = service
    app.state.registration.notification = service.registration_committed
    router = APIRouter(prefix='/api/me/notifications')

    def key(request): return digest(token_from(request, service.auth))
    def result(value): return JSONResponse(value, headers={'Cache-Control': 'no-store'})

    @router.get('')
    def read(request: Request, identity=Depends(require_authenticated)):
        if request.query_params: raise auth_error(422, 'Unexpected notification query')
        try: return result(service.read(identity.id, key(request)))
        except AuthDenied: raise auth_error(403, 'Notification access denied') from None

    @router.put('')
    async def save(request: Request, identity=Depends(require_authenticated)):
        value = await body(request, NotificationInput)
        try: return result(await run_in_threadpool(service.save, identity.id, key(request), value))
        except AuthDenied: raise auth_error(403, 'Notification access denied') from None
        except NotificationIncomplete: raise auth_error(422, 'Verified Telegram binding required') from None

    @router.post('/{action}')
    async def action(action: str, request: Request, identity=Depends(require_authenticated)):
        if action not in ('connect', 'confirm', 'disconnect', 'test'): raise auth_error(404, 'Action unavailable')
        value = await body(request, TestInput)
        try:
            if action == 'test':
                future = await run_in_threadpool(service.test, identity.id, key(request), value.expected_revision)
                success = await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(future)), timeout=3)
                if not success: raise auth_error(502, 'Telegram delivery not confirmed; refresh settings')
                return result({'state': 'sent'})
            method = {'connect': service.begin, 'confirm': service.confirm, 'disconnect': service.unlink}[action]
            return result(await run_in_threadpool(method, identity.id, key(request), value.expected_revision))
        except AuthDenied: raise auth_error(403, 'Notification access denied') from None
        except NotificationIncomplete: raise auth_error(422, 'Verified Telegram binding or platform setup required') from None
        except TimeoutError: raise auth_error(504, 'Delivery unconfirmed; do not retry immediately') from None

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
