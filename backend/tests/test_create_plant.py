import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models.forecast import Forecast  # noqa: F401
from app.db.models.historical_generation import HistoricalGeneration  # noqa: F401
from app.db.models.plant import Plant  # noqa: F401
from app.db.models.weather_data import WeatherData  # noqa: F401
from app.db.repositories.plant_repository import PlantRepository
from app.main import app
from app.schemas.plant import PlantCreate


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


def test_create_plant_uses_installed_capacity_as_canonical():
    TestingSessionLocal = _session_factory()
    db = TestingSessionLocal()

    repository = PlantRepository(db)
    plant = repository.create(
        PlantCreate(
            name="Rewa Ultra Mega Solar",
            plant_type="SOLAR",
            capacity_mw=500,
            latitude=26.9,
            longitude=71.5,
            timezone="Asia/Kolkata",
        )
    )

    assert plant.id is not None
    assert plant.installed_capacity_mw == 500
    assert plant.capacity_mw == 500
    assert plant.export_limit_mw is None
    db.close()


def test_create_plant_api_accepts_frontend_payload_and_keeps_canonical_field():
    TestingSessionLocal = _session_factory()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        response = client.post(
            "/api/plants",
            json={
                "name": "Rewa Ultra Mega Solar",
                "plant_type": "SOLAR",
                "capacity_mw": 500,
                "latitude": 26.9,
                "longitude": 71.5,
                "timezone": "Asia/Kolkata",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["installed_capacity_mw"] == 500
        assert body["capacity_mw"] == 500
        assert body["name"] == "Rewa Ultra Mega Solar"

        invalid_response = client.post(
            "/api/plants",
            json={
                "name": "Bad Plant",
                "plant_type": "SOLAR",
                "capacity_mw": 500,
                "export_limit_mw": 600,
                "latitude": 26.9,
                "longitude": 71.5,
                "timezone": "Asia/Kolkata",
            },
        )
        assert invalid_response.status_code == 422, invalid_response.text
    finally:
        app.dependency_overrides.clear()
