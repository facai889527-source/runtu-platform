import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.auth.routes import auth_error, require_permission, token_from
from backend.auth.service import AuthDenied, digest
from backend.notifications import NotificationIncomplete, NotificationInput, NotificationService, TestInput
from backend.registration_routes import body


def install_notifications(app):
    service = NotificationService(app.state.auth_service)
    app.state.notifications = service
    app.state.registration.notification = service.registration_committed
    router = APIRouter(prefix='/api/admin/notifications/telegram')

    def key(request): return digest(token_from(request, service.auth))
    def result(value): return JSONResponse(value, headers={'Cache-Control': 'no-store'})

    @router.get('')
    def read(request: Request, identity=Depends(require_permission('notifications.manage'))):
        try: return result(service.read(identity.id, key(request)))
        except AuthDenied: raise auth_error(403, 'Notification access denied') from None

    @router.put('')
    async def save(request: Request, identity=Depends(require_permission('notifications.manage'))):
        value = await body(request, NotificationInput)
        try: return result(await run_in_threadpool(service.save, identity.id, key(request), value))
        except AuthDenied: raise auth_error(403, 'Notification access denied') from None
        except NotificationIncomplete: raise auth_error(422, 'Notification configuration incomplete') from None

    @router.post('/test')
    async def test(request: Request, identity=Depends(require_permission('notifications.manage'))):
        value = await body(request, TestInput)
        try:
            future = await run_in_threadpool(service.test, identity.id, key(request), value.expected_revision)
            # Deadline bounds the API even if a remote peer trickles data. The single
            # bounded worker prevents timed-out requests creating unbounded threads.
            success = await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(future)), timeout=3)
        except AuthDenied: raise auth_error(403, 'Notification access denied') from None
        except NotificationIncomplete: raise auth_error(422, 'Notification configuration incomplete') from None
        except TimeoutError: raise auth_error(504, 'Delivery result unconfirmed; do not retry immediately') from None
        if not success: raise auth_error(502, 'Telegram delivery not confirmed')
        return result({'state': 'sent'})

    app.include_router(router)
