from collections.abc import Iterable

from fastapi import FastAPI, HTTPException

from backend.config import Settings
from backend.modules import DemoModule, ModuleDetail, ModuleManifest, ModuleRegistry, PlatformModule


def create_app(
    settings: Settings | None = None, modules: Iterable[PlatformModule] | None = None
) -> FastAPI:
    config = settings if settings is not None else Settings()
    app = FastAPI(title=config.platform_name, version="0.1.0")
    registry = ModuleRegistry()
    for module in modules if modules is not None else [DemoModule()]:
        registry.register(module)
    app.state.registry = registry
    app.state.settings = config

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "platform": config.platform_name}

    @app.get("/api/modules", response_model=list[ModuleManifest])
    def list_modules() -> list[ModuleManifest]:
        return registry.manifests()

    @app.get("/api/modules/{module_id}", response_model=ModuleDetail)
    def module_detail(module_id: str) -> ModuleDetail:
        detail = registry.detail(module_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Module not found")
        return detail

    # Core metadata routes take precedence over module routers, including root routes.
    for module in registry.modules():
        detail = registry.detail(module.manifest.id)
        if detail is not None and detail.status == "enabled":
            app.include_router(module.router, prefix=f"/api/modules/{detail.id}")

    return app
