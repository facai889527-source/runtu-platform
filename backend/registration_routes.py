import json
from typing import Literal
from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.auth.routes import auth_service, protected_post, require_permission, token_from, auth_error, response
from backend.auth.service import AuthDenied, digest
from backend.registration import PolicyInput, Signup, RegistrationService


async def body(request, model, max_bytes=4096):
    if request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
        raise auth_error(415, 'JSON required')
    raw = bytearray()
    try:
        async for chunk in request.stream():
            if len(raw)+len(chunk)>max_bytes: raise auth_error(413, 'Request too large')
            raw.extend(chunk)
        try: return model.model_validate(json.loads(raw))
        except (ValueError, TypeError, UnicodeError, RecursionError):
            raise auth_error(422, 'Invalid registration request') from None
    finally: raw.clear()


def install_registration(app):
    service = RegistrationService(app.state.auth_service)
    app.state.registration = service
    router = APIRouter()

    def key(request): return digest(token_from(request, service.auth))
    def result(value): return JSONResponse(value, headers={'Cache-Control': 'no-store'})

    @router.get('/api/auth/registration-policy')
    def public_policy(_auth=Depends(auth_service)):
        value = service.policy()
        return result({k:value[k] for k in ('enabled','approval_required')})

    @router.post('/api/auth/register', status_code=202)
    async def register(request: Request, context=Depends(protected_post)):
        auth, token = context
        value = await body(request, Signup)
        try:
            data = await run_in_threadpool(service.signup, digest(token), value, request.client.host if request.client else 'unknown')
        except AuthDenied: raise auth_error(403, 'Anonymous registration context required') from None
        out = response(auth, data, delete_cookie=True)
        out.status_code = 202
        return out

    @router.get('/api/admin/registration-policy')
    def owner_policy(_identity=Depends(require_permission('users.manage'))):
        return result(service.policy())

    @router.put('/api/admin/registration-policy')
    async def save(request: Request, identity=Depends(require_permission('users.manage'))):
        value = await body(request, PolicyInput)
        try: data = await run_in_threadpool(service.save_policy, identity.id, key(request), value)
        except AuthDenied: raise auth_error(403, 'Invalid security context') from None
        return result(data)

    @router.get('/api/admin/registrations')
    def pending(request: Request, limit: int=Query(20,ge=1,le=50),
                after_username: str|None=Query(None,min_length=3,max_length=64,pattern=r'^[a-z0-9_.-]{3,64}$'),
                state: Literal['pending','rejected']=Query('pending'),
                identity=Depends(require_permission('users.manage'))):
        try: return result(service.pending(identity.id, key(request), limit, after_username, state))
        except AuthDenied: raise auth_error(403, 'Invalid security context') from None

    @router.get('/api/admin/registrations/{user_id}')
    def detail(request: Request, user_id: str=Path(min_length=1,max_length=36), identity=Depends(require_permission('users.manage'))):
        try: return result(service.detail(identity.id,key(request),user_id))
        except AuthDenied: raise auth_error(403, 'Invalid security context') from None

    @router.post('/api/admin/registrations/{user_id}/approve')
    def approve(request: Request, user_id: str=Path(min_length=1,max_length=36), identity=Depends(require_permission('users.manage'))):
        try: return result(service.approve(identity.id,key(request),user_id))
        except AuthDenied: raise auth_error(403, 'Invalid security context') from None

    @router.post('/api/admin/registrations/{user_id}/reject')
    def reject(request: Request, user_id: str=Path(min_length=1,max_length=36), identity=Depends(require_permission('users.manage'))):
        try: return result(service.reject(identity.id,key(request),user_id))
        except AuthDenied: raise auth_error(403, 'Invalid security context') from None

    app.include_router(router)
