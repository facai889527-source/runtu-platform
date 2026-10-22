import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.metadata_app import create_app
from backend.config import Settings
from backend.modules import ModuleManifest, PublicModuleConfig


def make_module(status="enabled", module_id="example"):
    class ExampleModule:
        manifest = ModuleManifest(
            id=module_id, name="Example", version="1", description="Test",
            category="tools", status=status, capabilities=("example:read",),
        )
        router = APIRouter()
        public_config = PublicModuleConfig(refresh_interval_seconds=30)
        internal_config = {"password": "dummy-private-value"}

    @ExampleModule.router.get("/ping")
    def ping():
        return {"pong": True}

    @ExampleModule.router.post("/action")
    def action():
        return {"done": True}

    return ExampleModule()


@pytest.mark.parametrize("status", ["enabled", "disabled"])
def test_lifecycle_metadata_and_route_boundary(status):
    with TestClient(create_app(Settings(_env_file=None, expose_api_docs=True), modules=[make_module(status)])) as client:
        manifest = client.get("/api/modules").json()[0]
        assert manifest["status"] == status
        assert manifest["category"] == "tools"
        assert manifest["capabilities"] == ["example:read"]
        assert "public_config" not in manifest
        response = client.get("/api/modules/example")
        assert response.status_code == 200
        assert response.json()["public_config"] == {
            "show_in_navigation": True, "refresh_interval_seconds": 30,
        }
        expected = 200 if status == "enabled" else 404
        assert client.get("/api/modules/example/ping").status_code == expected
        assert client.post("/api/modules/example/action").status_code == (403 if status == 'enabled' else 404)
        paths = client.get("/openapi.json").json()["paths"]
        assert ("/api/modules/example/ping" in paths) == (status == "enabled")
        assert client.post("/api/modules/example").status_code == 405
        assert client.get("/api/modules/unknown").status_code == 404
        assert client.get("/api/modules/unknown/ping").status_code == 404
        assert client.get("/api/health").json()["status"] == "ok"


def test_duplicate_id_rejected_even_when_disabled():
    with pytest.raises(ValueError, match="already registered"):
        create_app(modules=[make_module(), make_module("disabled")])


def test_public_config_does_not_expose_internal_or_environment_values(monkeypatch):
    monkeypatch.setenv("RUNTU_PRIVATE_TOKEN", "dummy-environment-secret")
    module = make_module()
    module.settings = {"token": "dummy-settings-secret"}
    with TestClient(create_app(modules=[module])) as client:
        for path in ("/api/modules", "/api/modules/example"):
            response = client.get(path)
            assert response.status_code == 200
            for forbidden in ("password", "token", "dummy-private", "dummy-settings", "dummy-environment"):
                assert forbidden not in response.text


def test_unknown_or_sensitive_public_config_fields_fail_at_startup():
    module = make_module()
    module.public_config = {"refresh_interval_seconds": 30, "token": "dummy-secret"}
    with pytest.raises(ValidationError):
        create_app(modules=[module])
    with pytest.raises(ValidationError):
        PublicModuleConfig(refresh_interval_seconds="dummy-secret")


def test_original_demo_remains_compatible():
    with TestClient(create_app()) as client:
        detail = client.get("/api/modules/demo").json()
        assert detail["id"] == "demo"
        assert detail["status"] == "enabled"
        assert detail["category"] is None
        assert detail["capabilities"] == []
        assert detail["public_config"]["refresh_interval_seconds"] is None


def test_core_metadata_cannot_be_shadowed_by_module_root_route():
    module = make_module()

    @module.router.get("")
    def conflicting_route():
        return {"password": "dummy-private-value"}

    with TestClient(create_app(modules=[module])) as client:
        response = client.get("/api/modules/example")
        assert response.status_code == 200
        assert response.json()["id"] == "example"
        assert "password" not in response.text
