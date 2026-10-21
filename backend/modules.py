from typing import Literal, Protocol

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field


class ModuleManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    version: str
    description: str
    category: str | None = None
    status: Literal["enabled", "disabled"] = "enabled"
    capabilities: tuple[str, ...] = ()


class PublicModuleConfig(BaseModel):
    """Explicit public allowlist; never serialize a module's internal settings."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    show_in_navigation: bool = True
    refresh_interval_seconds: int | None = Field(default=None, ge=1, le=86400)


class ModuleDetail(ModuleManifest):
    public_config: PublicModuleConfig = Field(default_factory=PublicModuleConfig)


class PlatformModule(Protocol):
    manifest: ModuleManifest
    router: APIRouter


class ConfiguredPlatformModule(PlatformModule, Protocol):
    public_config: PublicModuleConfig


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, PlatformModule] = {}
        self._details: dict[str, ModuleDetail] = {}

    def register(self, module: PlatformModule) -> None:
        if module.manifest.id in self._modules:
            raise ValueError(f"Module already registered: {module.manifest.id}")
        detail = ModuleDetail(
            **module.manifest.model_dump(),
            public_config=PublicModuleConfig.model_validate(
                getattr(module, "public_config", PublicModuleConfig())
            ),
        )
        self._modules[detail.id] = module
        self._details[detail.id] = detail

    def modules(self) -> tuple[PlatformModule, ...]:
        return tuple(self._modules.values())

    def manifests(self) -> list[ModuleManifest]:
        return [ModuleManifest(**detail.model_dump()) for detail in self._details.values()]

    def detail(self, module_id: str) -> ModuleDetail | None:
        return self._details.get(module_id)


class DemoModule:
    manifest = ModuleManifest(
        id="demo", name="演示模块", version="0.1.0", description="仅展示模块注册，无业务功能。"
    )
    router = APIRouter()
