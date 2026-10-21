from collections.abc import Iterable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from backend.config import Settings
from backend.database import Database
from backend.modules import DemoModule, ModuleDetail, ModuleManifest, ModuleRegistry, PlatformModule
from backend.persistence import ConfigStorageError, ModuleConfigService


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

    app = FastAPI(title=config.platform_name, version="0.1.0", lifespan=lifespan)
    registry = ModuleRegistry()
    for module in modules if modules is not None else [DemoModule()]:
        registry.register(module)
    app.state.registry = registry
    app.state.settings = config
    app.state.database = database
    config_service = ModuleConfigService(registry, database)
    app.state.config_service = config_service

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
    def list_modules() -> list[ModuleManifest]:
        return registry.manifests()

    @app.get("/api/modules/{module_id}", response_model=ModuleDetail)
    def module_detail(module_id: str) -> ModuleDetail:
        detail = registry.detail(module_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Module not found")
        try:
            return detail.model_copy(update={"public_config": config_service.load(module_id)})
        except ConfigStorageError:
            raise HTTPException(status_code=503, detail="Module configuration storage unavailable") from None

    # Core metadata routes take precedence over module routers, including root routes.
    for module in registry.modules():
        detail = registry.detail(module.manifest.id)
        if detail is not None and detail.status == "enabled":
            app.include_router(module.router, prefix=f"/api/modules/{detail.id}")

    return app
