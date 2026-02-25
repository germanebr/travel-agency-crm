from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from epic_trips_crm.config.paths import env_file_path

_UNSET = object()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(env_file_path()),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"
    log_level: str = "INFO"

    database_url: str | None = None

    portal_url: str | None = Field(default=None, alias="PORTAL_URL")
    portal_username: str | None = Field(default=None, alias="PORTAL_USERNAME")
    portal_password: str | None = Field(default=None, alias="PORTAL_PASSWORD")
    portal_headless: bool = Field(default=True, alias="PORTAL_HEADLESS")


def require_database_url(value: object = _UNSET) -> str:
    """
    If `value` is provided (even None), use it. Otherwise fall back to settings.database_url.
    This makes the function unit-testable without depending on a local .env file.
    """
    url = settings.database_url if value is _UNSET else value

    if not isinstance(url, str) or not url.strip():
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to .env (recommended) or set it as an environment variable."
        )

    return url


settings = Settings()
