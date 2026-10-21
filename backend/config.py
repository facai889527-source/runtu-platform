from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RUNTU_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    platform_name: str = "Runtu Platform"
    database_url: SecretStr | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def empty_database_url(cls, value):
        return None if value == "" else value
