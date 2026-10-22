"""Metadata/storage unit harness; real authentication boundary is tested separately."""
from backend.app import create_app as platform_app
from backend.auth.routes import require_authenticated


def create_app(*args, **kwargs):
    app = platform_app(*args, **kwargs)
    # These tests isolate registry/storage behavior, not authentication.
    app.dependency_overrides[require_authenticated] = lambda: object()
    return app
