import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.modules import DemoModule, ModuleManifest, ModuleRegistry


def test_health_and_demo_manifest():
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok", "platform": "Runtu Platform", "database": "not_configured"
        }
        response = client.get("/api/modules")
        assert response.status_code == 200
        assert response.json()[0]["id"] == "demo"


def test_module_extension_routes_and_isolation():
    class ExampleModule:
        manifest = ModuleManifest(id="example", name="Example", version="1", description="Test")
        router = APIRouter()

    @ExampleModule.router.get("/ping")
    def ping():
        return {"pong": True}

    with TestClient(create_app(modules=[ExampleModule()])) as client:
        assert client.get("/api/modules").json()[0]["id"] == "example"
        assert client.get("/api/modules/example/ping").json() == {"pong": True}
    with TestClient(create_app(modules=[])) as client:
        assert client.get("/api/modules").json() == []
        assert client.get("/api/modules/example/ping").status_code == 404


def test_duplicate_registration_rejected():
    registry = ModuleRegistry()
    registry.register(DemoModule())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(DemoModule())
    assert len(registry.manifests()) == 1


def test_settings_from_environment(monkeypatch):
    monkeypatch.setenv("RUNTU_PLATFORM_NAME", "Local Test")
    with TestClient(create_app(Settings(_env_file=None))) as client:
        assert client.get("/api/health").json()["platform"] == "Local Test"
