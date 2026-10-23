import ipaddress
import json
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.auth.service import AuthDenied, AuthService, AuthUnavailable, RateLimited, csrf_token
from backend.config import is_loopback
from backend.auth.policy import PERMISSIONS, ROLE_PERMISSIONS, permissions_for

router = APIRouter(prefix='/api/auth', tags=['identity'])


def auth_error(status, detail):
    return HTTPException(status, detail, headers={'Cache-Control': 'no-store'})


def auth_service(request: Request) -> AuthService:
    service = request.app.state.auth_service
    settings = service.settings
    if not settings.auth_origin or service.database is None:
        raise auth_error(503, 'Authentication unavailable')
    origin = urlsplit(settings.auth_origin)
    if origin.scheme == 'https' and request.url.scheme != 'https':
        raise auth_error(403, 'HTTPS required')
    # Never infer the trusted origin from arbitrary Host or forwarded headers.
    if request.headers.get('host', '').lower() != origin.netloc:
        raise auth_error(403, 'Invalid request origin')
    supplied = request.headers.get('origin')
    if supplied and supplied != settings.auth_origin:
        raise auth_error(403, 'Invalid request origin')
    if request.headers.get('sec-fetch-site') not in (None, 'same-origin', 'none'):
        raise auth_error(403, 'Invalid request origin')
    if origin.scheme == 'http' and (not request.client or not is_loopback(request.client.host)):
        raise auth_error(403, 'Loopback development access only')
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and supplied != settings.auth_origin:
        raise auth_error(403, 'Invalid request origin')
    return service


def cookie_name(service):
    return '__Host-runtu_session' if service.settings.auth_origin.startswith('https:') else 'runtu_dev_session'


def token_from(request, service):
    return request.cookies.get(cookie_name(service))


def response(service, content, token=None, delete_cookie=False, anonymous=False):
    result = JSONResponse(content, headers={'Cache-Control': 'no-store', 'Pragma': 'no-cache'})
    secure = service.settings.auth_origin.startswith('https:')
    if token:
        result.set_cookie(cookie_name(service), token, httponly=True, secure=secure, samesite='strict',
            path='/', max_age=600 if anonymous else service.settings.auth_session_seconds)
    elif delete_cookie:
        result.delete_cookie(cookie_name(service), path='/', secure=secure, httponly=True, samesite='strict')
    return result


def identity_json(identity):
    return {'authenticated': bool(identity), 'user': {'id': identity.id, 'username': identity.username,
        'is_admin': identity.is_admin} if identity else None}


@router.get('/csrf')
def csrf(request: Request, service=Depends(auth_service)):
    previous = token_from(request, service)
    token = service.csrf_session(previous, request.client.host if request.client else 'unknown')
    # Session ID appears only in HttpOnly Set-Cookie. This is a CSRF proof, not a credential.
    return response(service, {'csrf_token': csrf_token(token)}, token=token if token != previous else None, anonymous=True)


@router.get('/me')
def me(request: Request, service=Depends(auth_service)):
    identity = service.current(token_from(request, service))
    return response(service, identity_json(identity))


async def protected_post(request: Request, service=Depends(auth_service)):
    token = token_from(request, service)
    try:
        service.validate_csrf(token, request.headers.get('x-csrf-token'))
    except AuthDenied:
        raise auth_error(403, 'Invalid security context') from None
    return service, token


def observed_login_ip(request: Request):
    # Fail closed if an upstream server may have rewritten ASGI client from a
    # forwarded header. No forwarded address or arbitrary hostname is trusted.
    if any(name in request.headers for name in ('forwarded', 'x-forwarded-for', 'x-real-ip')):
        return None
    try:
        return str(ipaddress.ip_address(request.client.host)) if request.client and '%' not in request.client.host else None
    except ValueError:
        return None


@router.post('/login')
async def login(request: Request, context=Depends(protected_post)):
    service, old_token = context
    if request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
        raise auth_error(415, 'JSON required')
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > 4096:
            raise auth_error(413, 'Request too large')
        raw.extend(chunk)
    try:
        data = json.loads(raw)
        username, password = data['username'], data['password']
        if (not isinstance(username, str) or not isinstance(password, str) or
                not 1 <= len(username) <= 64 or not 1 <= len(password) <= 128 or
                set(data) != {'username', 'password'}):
            raise ValueError
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise auth_error(400, 'Invalid login request') from None
    try:
        token, identity = await run_in_threadpool(service.login, old_token, username, password,
            request.client.host if request.client else 'unknown', source_ip=observed_login_ip(request))
    except AuthDenied:
        raise auth_error(401, 'Invalid credentials') from None
    return response(service, identity_json(identity), token=token)


@router.post('/logout')
async def logout(request: Request, context=Depends(protected_post)):
    service, token = context
    service.logout(token, request.client.host if request.client else 'unknown')
    return response(service, identity_json(None), delete_cookie=True)


def require_authenticated(request: Request, service=Depends(auth_service)):
    identity = service.current(token_from(request, service))
    if identity is None:
        raise auth_error(401, 'Authentication required')
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        try:
            service.validate_csrf(token_from(request, service), request.headers.get('x-csrf-token'))
        except AuthDenied:
            raise auth_error(403, 'Invalid security context') from None
    return identity


@router.get('/activity')
def activity(request: Request, identity=Depends(require_authenticated), service=Depends(auth_service)):
    if request.query_params:
        raise auth_error(422, 'Invalid activity query')
    try:
        previous = service.previous_login(token_from(request, service), identity.id)
    except AuthDenied:
        raise auth_error(401, 'Authentication required') from None
    return response(service, {'previous_login': previous})


def require_admin(identity=Depends(require_authenticated)):
    if not identity.is_admin:
        raise auth_error(403, 'Administrator required')
    return identity


def require_permission(permission):
    def check(identity=Depends(require_authenticated)):
        if permission not in PERMISSIONS or permission not in permissions_for(identity.role):
            raise auth_error(403, 'Permission denied')
        return identity
    return check


def require_role(*roles):
    def check(identity=Depends(require_authenticated)):
        if not roles or any(role not in ROLE_PERMISSIONS for role in roles) or identity.role not in roles:
            raise auth_error(403, 'Role denied')
        return identity
    return check


def module_readonly_boundary(request: Request):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        raise auth_error(403, 'Module writes are not enabled')


admin_router = APIRouter(prefix='/api/admin', tags=['authorization'])


@admin_router.get('/me')
def admin_me(identity=Depends(require_permission('platform.read'))):
    return JSONResponse({'id': identity.id, 'username': identity.username, 'role': identity.role,
        'permissions': sorted(permissions_for(identity.role))}, headers={'Cache-Control': 'no-store'})


def install_auth(app, database, settings):
    app.state.auth_service = AuthService(database, settings)
    app.include_router(router)
    app.include_router(admin_router)

    @app.exception_handler(AuthUnavailable)
    async def unavailable(_request, _error):
        return JSONResponse({'detail': 'Authentication unavailable'}, status_code=503, headers={'Cache-Control':'no-store'})

    @app.exception_handler(RateLimited)
    async def limited(_request, _error):
        return JSONResponse({'detail': 'Too many attempts; retry later'}, status_code=429,
                            headers={'Retry-After':'300', 'Cache-Control':'no-store'})
