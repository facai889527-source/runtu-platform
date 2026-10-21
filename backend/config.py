from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RUNTU_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    platform_name: str = "Runtu Platform"
