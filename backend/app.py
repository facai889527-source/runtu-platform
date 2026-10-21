from collections.abc import Iterable

from fastapi import FastAPI

from backend.config import Settings
from backend.modules import DemoModule, ModuleManifest, ModuleRegistry, PlatformModule


def create_app(
    settings: Settings | None = None, modules: Iterable[PlatformModule] | None = None
) -> FastAPI:
    config = settings if settings is not None else Settings()
    app = FastAPI(title=config.platform_name, version="0.1.0")
    registry = ModuleRegistry()
    for module in modules if modules is not None else [DemoModule()]:
        registry.register(module)
        app.include_router(module.router, prefix=f"/api/modules/{module.manifest.id}")
    app.state.registry = registry
    app.state.settings = config

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "platform": config.platform_name}

    @app.get("/api/modules", response_model=list[ModuleManifest])
    def list_modules() -> list[ModuleManifest]:
        return registry.manifests()

    return app
