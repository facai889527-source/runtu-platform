from collections.abc import Iterable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse

from backend.config import Settings
from backend.auth.routes import install_auth, module_readonly_boundary, require_permission
from backend.database import Database
from backend.modules import DemoModule, ModuleDetail, ModuleManifest, ModuleRegistry, PlatformModule, ModuleUpdate
from backend.persistence import ConfigConflictError, ConfigStorageError, ModuleConfigService, UnknownModuleError
from backend.module_management import ModuleManagementService, ModulePermissionError, ModuleProtectedError
from backend.module_audit import AuditUnavailable, ModuleAuditPage, ModuleAuditService
from backend.user_routes import install_user_management


def create_app(
    settings: Settings | None = None, modules: Iterable[PlatformModule] | None = None
) -> FastAPI:
    config = settings if settings is not None else Settings()
    database = Database(config.database_url.get_secret_value()) if config.database_url else None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            if database is not None:
                database.dispose()

    app = FastAPI(title=config.platform_name, version="0.1.0", lifespan=lifespan,
        docs_url="/docs" if config.expose_api_docs else None,
        redoc_url=None, openapi_url="/openapi.json" if config.expose_api_docs else None)
    install_auth(app, database, config)
    install_user_management(app, database)
    registry = ModuleRegistry()
    for module in modules if modules is not None else [DemoModule()]:
        registry.register(module)
    app.state.registry = registry
    app.state.settings = config
    app.state.database = database
    config_service = ModuleConfigService(registry, database)
    app.state.config_service = config_service
    management = ModuleManagementService(registry, database)
    app.state.module_management = management
    audit = ModuleAuditService(registry, database)
    app.state.module_audit = audit

    @app.exception_handler(AuditUnavailable)
    async def audit_unavailable(_request, _error):
        return JSONResponse({'detail': 'Module audit storage unavailable'}, status_code=503,
                            headers={'Cache-Control': 'no-store'})

    @app.exception_handler(ConfigStorageError)
    async def storage_unavailable(_request, _error):
        return JSONResponse({'detail': 'Module configuration storage unavailable'}, status_code=503,
                            headers={'Cache-Control': 'no-store'})

    @app.exception_handler(RequestValidationError)
    async def invalid_module_write(request, error):
        if request.url.path.startswith(('/api/admin/modules/', '/api/admin/users')):
            return JSONResponse({'detail': 'Invalid module request'}, status_code=422,
                                headers={'Cache-Control': 'no-store'})
        return await request_validation_exception_handler(request, error)

    @app.get("/api/health", response_model=None)
    def health():
        database_status = "not_configured" if database is None else (
            "ready" if database.is_ready() else "unavailable"
        )
        result = {"status": "ok", "platform": config.platform_name, "database": database_status}
        if database_status == "unavailable":
            result["status"] = "degraded"
            return JSONResponse(status_code=503, content=result)
        return result

    @app.get("/api/modules", response_model=list[ModuleManifest])
    def list_modules(response: Response) -> list[ModuleManifest]:
        response.headers['Cache-Control'] = 'no-store'
        return management.manifests()

    @app.get("/api/modules/{module_id}", response_model=ModuleDetail)
    def module_detail(module_id: str, response: Response) -> ModuleDetail:
        response.headers['Cache-Control'] = 'no-store'
        try:
            return management.detail(module_id)
        except UnknownModuleError:
            raise HTTPException(status_code=404, detail="Module not found")

    @app.get('/api/admin/modules/{module_id}/changes', response_model=ModuleAuditPage)
    def module_changes(module_id: str, response: Response,
                       limit: int = Query(10, ge=1, le=50),
                       before_revision: int | None = Query(None, ge=1, le=2147483647),
                       _identity=Depends(require_permission('audit.read'))):
        response.headers['Cache-Control'] = 'no-store'
        try:
            return audit.page(module_id, limit, before_revision)
        except UnknownModuleError:
            raise HTTPException(404, 'Module not found', headers={'Cache-Control': 'no-store'}) from None

    @app.put('/api/admin/modules/{module_id}', response_model=ModuleDetail)
    def update_module(module_id: str, value: ModuleUpdate,
                      identity=Depends(require_permission('module.manage'))):
        try:
            return JSONResponse(management.save(module_id, value, identity.id).model_dump(mode='json'),
                                headers={'Cache-Control': 'no-store'})
        except UnknownModuleError:
            raise HTTPException(404, 'Module not found') from None
        except (ModuleProtectedError, ModulePermissionError):
            raise HTTPException(403, 'Module operation not permitted') from None
        except ConfigConflictError:
            raise HTTPException(409, 'Module changed; reload before saving') from None

    def enabled_boundary(module_id):
        def check():
            if management.detail(module_id).status != 'enabled':
                raise HTTPException(404, 'Module not available', headers={'Cache-Control': 'no-store'})
        return check

    # Core metadata routes take precedence over module routers, including root routes.
    for module in registry.modules():
        detail = registry.detail(module.manifest.id)
        if detail is not None:
            app.include_router(module.router, prefix=f"/api/modules/{detail.id}",
                               include_in_schema=detail.status == 'enabled',
                               dependencies=[Depends(enabled_boundary(detail.id)), Depends(module_readonly_boundary)])

    return app
