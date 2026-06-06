from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Automated Outreach Pipeline"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    APP_API_KEY: SecretStr | None = None

    LOG_LEVEL: str = "INFO"
    LOG_DIR: Path = Path("logs")
    LOG_FILE: str = "app.log"

    DATABASE_URL: str = "postgresql+psycopg://outreach:outreach@localhost:5432/outreach"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_TASK_EAGER_PROPAGATES: bool = True

    HTTP_TIMEOUT_SECONDS: float = 20.0
    RETRY_MAX_RETRIES: int = 3
    RETRY_BACKOFF_BASE_SECONDS: float = 1.0
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_SECONDS: int = 60
    CACHE_TTL_SECONDS: int = 3600

    OCEAN_BASE_URL: str = "https://api.ocean.io/v3"
    OCEAN_API_KEY: SecretStr | None = None
    OCEAN_COMPANY_LIMIT: int = 20

    PROSPEO_BASE_URL: str = "https://api.prospeo.io"
    PROSPEO_API_KEY: SecretStr | None = None
    PROSPEO_PAGE_LIMIT: int = 1

    EAZYREACH_BASE_URL: str = "https://api.eazyreach.app"
    EAZYREACH_API_KEY: SecretStr | None = None
    EAZYREACH_EMAIL_LOOKUP_PATH: str = "/api/v1/linkedin/email"

    BREVO_BASE_URL: str = "https://api.brevo.com/v3"
    BREVO_API_KEY: SecretStr | None = None
    BREVO_SENDER_EMAIL: str = "outreach@example.com"
    BREVO_SENDER_NAME: str = "Vocallabs"
    BREVO_REPLY_TO_EMAIL: str | None = None

    OPENAI_API_KEY: SecretStr | None = None
    OPENAI_MODEL: str = "gpt-5.2"
    OUTREACH_PRODUCT_NAME: str = "Vocallabs"
    OUTREACH_VALUE_PROP: str = (
        "AI-powered voice and outreach automation that helps revenue teams "
        "qualify prospects faster and follow up consistently"
    )
    OUTREACH_CALL_TO_ACTION: str = "Would it be worth a short conversation next week?"

    DEFAULT_PAGE_LIMIT: int = 100
    MAX_PAGE_LIMIT: int = 500

    @property
    def retry_delays(self) -> list[float]:
        return [
            self.RETRY_BACKOFF_BASE_SECONDS * (2**attempt)
            for attempt in range(self.RETRY_MAX_RETRIES)
        ]


def get_secret_value(value: SecretStr | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return str(value)


def settings_as_safe_dict(settings: Settings) -> dict[str, Any]:
    data = settings.model_dump()
    for key in list(data):
        if "KEY" in key or "SECRET" in key or "TOKEN" in key:
            data[key] = "***" if data[key] else None
    return data


@lru_cache
def get_settings() -> Settings:
    return Settings()
