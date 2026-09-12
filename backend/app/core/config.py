from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(..., alias="DATABASE_URL")
    app_env: str = Field(default="development", alias="APP_ENV")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT", ge=1, le=65535)
    cors_origins: list[str] | str = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        alias="CORS_ORIGINS",
    )
    weather_provider_base_url: str = Field(
        default="https://api.open-meteo.com/v1/forecast",
        alias="WEATHER_PROVIDER_BASE_URL",
    )
    weather_provider_timeout_seconds: int = Field(
        default=20,
        alias="WEATHER_PROVIDER_TIMEOUT_SECONDS",
        gt=0,
    )
    weather_forecast_days: int = Field(
        default=3,
        alias="WEATHER_FORECAST_DAYS",
        gt=0,
        le=16,
    )

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("DATABASE_URL is required and cannot be empty.")
        return cleaned

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                items = raw.strip("[]").split(",")
            else:
                items = raw.split(",")
            return [item.strip() for item in items if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        raise RuntimeError(
            "Invalid backend configuration. Ensure DATABASE_URL is set in the environment or a local .env file."
        ) from exc
