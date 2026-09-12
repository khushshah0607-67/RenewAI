from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import AppException
from app.db.database import Base, get_db
from app.db.models.plant import Plant
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base.metadata.create_all(bind=engine)


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


client = TestClient(app)


def test_missing_plant_returns_standardized_error_envelope():
    response = client.get("/api/plants/999")

    assert response.status_code == 404
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "NOT_FOUND"
    assert payload["error"]["message"] == "Plant not found"


def test_validation_errors_return_standardized_error_envelope():
    response = client.post("/api/plants", json={})

    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "Request validation failed"
    assert isinstance(payload["error"].get("details"), list)


def test_service_unavailable_errors_return_standardized_error_envelope(monkeypatch):
    db = SessionLocal()
    db.add(
        Plant(
            name="Test Plant",
            plant_type="SOLAR",
            latitude=12.0,
            longitude=77.0,
            installed_capacity_mw=5.0,
            export_limit_mw=4.0,
            timezone="UTC",
        )
    )
    db.commit()
    db.close()

    def raise_unavailable(*args, **kwargs):
        raise AppException(status_code=503, code="WEATHER_SERVICE_UNAVAILABLE", message="Weather provider is unavailable")

    monkeypatch.setattr("app.services.weather.weather_service.WeatherService.fetch_and_store_weather", raise_unavailable)

    response = client.get("/api/plants/1/weather")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "WEATHER_SERVICE_UNAVAILABLE"
    assert payload["error"]["message"] == "Weather provider is unavailable"
