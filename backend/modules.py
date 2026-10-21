from typing import Protocol

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field


class ModuleManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    version: str
    description: str


class PlatformModule(Protocol):
    manifest: ModuleManifest
    router: APIRouter


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, PlatformModule] = {}

    def register(self, module: PlatformModule) -> None:
        if module.manifest.id in self._modules:
            raise ValueError(f"Module already registered: {module.manifest.id}")
        self._modules[module.manifest.id] = module

    def modules(self) -> tuple[PlatformModule, ...]:
        return tuple(self._modules.values())

    def manifests(self) -> list[ModuleManifest]:
        return [module.manifest for module in self._modules.values()]


class DemoModule:
    manifest = ModuleManifest(
        id="demo", name="演示模块", version="0.1.0", description="仅展示模块注册，无业务功能。"
    )
    router = APIRouter()
