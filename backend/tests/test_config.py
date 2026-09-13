from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import app


def test_settings_load_environment_values(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app_user:secretpass@db.example.com:5432/renewai")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_HOST", "0.0.0.0")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com, https://admin.example.com")
    monkeypatch.setenv("WEATHER_PROVIDER_BASE_URL", "https://api.open-meteo.example.com/v1")
    monkeypatch.setenv("WEATHER_PROVIDER_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("WEATHER_FORECAST_DAYS", "5")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_url == "postgresql+psycopg://app_user:secretpass@db.example.com:5432/renewai"
    assert settings.app_env == "production"
    assert settings.is_development is False
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 9000
    assert settings.cors_origins == ["https://app.example.com", "https://admin.example.com"]
    assert settings.weather_provider_base_url == "https://api.open-meteo.example.com/v1"
    assert settings.weather_provider_timeout_seconds == 30
    assert settings.weather_forecast_days == 5


def test_missing_database_url_is_rejected():
    with pytest.raises(ValidationError):
        Settings.model_validate({"database_url": "", "app_env": "development"})


def test_invalid_api_port_is_rejected():
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "database_url": "postgresql+psycopg://user:pass@localhost:5432/renewai",
                "api_port": 0,
                "app_env": "development",
            }
        )


def test_cors_origins_are_configured():
    cors_middleware = next(
        middleware for middleware in app.user_middleware if middleware.cls.__name__ == "CORSMiddleware"
    )
    assert "http://localhost:3000" in cors_middleware.kwargs["allow_origins"]
    assert "http://localhost:5173" in cors_middleware.kwargs["allow_origins"]


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.database import Base, get_db

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def isolate_test_db():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.clear()


def test_secret_values_do_not_appear_in_api_error_responses(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app_user:supersecret@localhost:5432/renewai")
    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/api/plants/999")

    assert response.status_code == 404
    payload = response.json()
    assert payload["status"] == "error"
    assert "supersecret" not in response.text.lower()
    assert payload["error"]["message"] == "Plant not found"
