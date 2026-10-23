import ipaddress
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        hide_input_in_errors=True, env_prefix="RUNTU_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    platform_name: str = "Runtu Platform"
    database_url: SecretStr | None = None
    auth_origin: str | None = None
    auth_allow_loopback_http: bool = False
    auth_session_seconds: int = Field(default=3600, ge=60, le=86400)
    auth_idle_seconds: int = Field(default=900, ge=30, le=3600)
    expose_api_docs: bool = False
    telegram_bot_token: SecretStr | None = None
    telegram_bot_username: str = ""
    telegram_webhook_secret: SecretStr | None = None
    telegram_binding_enabled: bool = False

    @model_validator(mode="after")
    def validate_auth_origin(self):
        if self.auth_origin:
            parsed = urlsplit(self.auth_origin)
            if (parsed.scheme not in ("https", "http") or not parsed.hostname or
                    parsed.username or parsed.password or parsed.path not in ("", "/") or
                    parsed.query or parsed.fragment):
                raise ValueError("Set an explicit HTTP(S) authentication origin without path or credentials")
            try:
                port = parsed.port
            except ValueError:
                raise ValueError("Invalid authentication origin port") from None
            host = parsed.hostname.lower()
            if parsed.scheme == "http" and not (self.auth_allow_loopback_http and is_loopback(host)):
                raise ValueError("HTTP authentication requires explicit loopback-only development mode")
            authority = f"[{host}]" if ":" in host else host
            if port and port != (443 if parsed.scheme == "https" else 80):
                authority += f":{port}"
            self.auth_origin = f"{parsed.scheme}://{authority}"
        return self

    @field_validator("database_url", mode="before")
    @classmethod
    def empty_database_url(cls, value):
        return None if value == "" else value


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
