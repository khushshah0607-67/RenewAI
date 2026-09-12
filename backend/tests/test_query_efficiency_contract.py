from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models.forecast import Forecast
from app.db.models.historical_generation import HistoricalGeneration
from app.db.models.plant import Plant
from app.db.models.weather_data import WeatherData
from app.main import app
from app.services.generation_service import GenerationService
from app.services.plant_service import PlantService
from app.services.weather.weather_service import WeatherService

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


client = TestClient(app)


@pytest.fixture
def db_session() -> Session:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(delete(table))
        session.commit()
        yield session
    finally:
        session.close()


def _make_plant(session: Session, name: str = "Plant A", suffix: int = 1) -> Plant:
    plant = Plant(
        name=f"{name} {suffix}",
        plant_type="SOLAR",
        latitude=12.0 + suffix,
        longitude=77.0 + suffix,
        installed_capacity_mw=5.0,
        export_limit_mw=4.0,
        timezone="UTC",
    )
    session.add(plant)
    session.commit()
    session.refresh(plant)
    return plant


def test_generation_list_limit_offset_and_chronological_order(db_session: Session):
    plant = _make_plant(db_session, suffix=1)
    base = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    records = [
        HistoricalGeneration(plant_id=plant.id, timestamp=base + timedelta(minutes=45), generation_mw=1.0),
        HistoricalGeneration(plant_id=plant.id, timestamp=base, generation_mw=0.5),
        HistoricalGeneration(plant_id=plant.id, timestamp=base + timedelta(minutes=15), generation_mw=0.75),
        HistoricalGeneration(plant_id=plant.id, timestamp=base + timedelta(minutes=30), generation_mw=1.25),
    ]
    db_session.add_all(records)
    db_session.commit()

    subset = GenerationService(db_session).list_generation(plant.id, limit=2, offset=1)

    assert [row.timestamp for row in subset] == [
        base + timedelta(minutes=15),
        base + timedelta(minutes=30),
    ]


def test_generation_list_date_range_and_empty_result(db_session: Session):
    plant = _make_plant(db_session, suffix=2)
    base = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    db_session.add_all(
        [
            HistoricalGeneration(plant_id=plant.id, timestamp=base, generation_mw=1.0),
            HistoricalGeneration(plant_id=plant.id, timestamp=base + timedelta(minutes=15), generation_mw=1.5),
            HistoricalGeneration(plant_id=plant.id, timestamp=base + timedelta(minutes=30), generation_mw=2.0),
        ]
    )
    db_session.commit()

    windowed = GenerationService(db_session).list_generation(
        plant.id,
        start=base + timedelta(minutes=15),
        end=base + timedelta(minutes=15),
    )
    assert len(windowed) == 1
    assert windowed[0].timestamp == base + timedelta(minutes=15)

    empty = GenerationService(db_session).list_generation(
        plant.id,
        start=base + timedelta(days=2),
        end=base + timedelta(days=3),
    )
    assert empty == []


def test_generation_list_respects_maximum_limit(db_session: Session):
    plant = _make_plant(db_session, suffix=3)
    records = [
        HistoricalGeneration(plant_id=plant.id, timestamp=datetime(2024, 1, 1, hour, 0, tzinfo=timezone.utc), generation_mw=1.0)
        for hour in range(10)
    ]
    db_session.add_all(records)
    db_session.commit()

    fetched = GenerationService(db_session).list_generation(plant.id, limit=100000)
    assert len(fetched) <= 5000


def test_weather_list_limit_offset_and_plant_isolation(db_session: Session):
    plant_one = _make_plant(db_session, suffix=4)
    plant_two = _make_plant(db_session, suffix=5)
    base = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)

    db_session.add_all(
        [
            WeatherData(plant_id=plant_one.id, timestamp=base, temperature_c=10.0, humidity_percent=50.0, wind_speed_mps=2.0, wind_direction_deg=90.0, cloud_cover_percent=20.0, precipitation_mm=0.0, radiation_w_m2=200.0),
            WeatherData(plant_id=plant_one.id, timestamp=base + timedelta(hours=1), temperature_c=11.0, humidity_percent=55.0, wind_speed_mps=2.5, wind_direction_deg=100.0, cloud_cover_percent=15.0, precipitation_mm=0.0, radiation_w_m2=220.0),
            WeatherData(plant_id=plant_one.id, timestamp=base + timedelta(hours=2), temperature_c=12.0, humidity_percent=45.0, wind_speed_mps=3.0, wind_direction_deg=120.0, cloud_cover_percent=25.0, precipitation_mm=0.0, radiation_w_m2=250.0),
            WeatherData(plant_id=plant_two.id, timestamp=base, temperature_c=20.0, humidity_percent=30.0, wind_speed_mps=3.0, wind_direction_deg=150.0, cloud_cover_percent=10.0, precipitation_mm=0.1, radiation_w_m2=300.0),
            WeatherData(plant_id=plant_two.id, timestamp=base + timedelta(hours=1), temperature_c=21.0, humidity_percent=35.0, wind_speed_mps=3.5, wind_direction_deg=170.0, cloud_cover_percent=12.0, precipitation_mm=0.2, radiation_w_m2=325.0),
        ]
    )
    db_session.commit()

    subset = WeatherService(db_session).list_weather(plant_one.id, limit=2, offset=1)

    assert len(subset) == 2
    assert [row.timestamp for row in subset] == [
        base + timedelta(hours=1),
        base + timedelta(hours=2),
    ]
    assert all(row.plant_id == plant_one.id for row in subset)


def test_weather_route_rejects_invalid_date_parameter(db_session: Session):
    plant = _make_plant(db_session)
    response = client.get(f"/api/plants/{plant.id}/weather?start=not-a-date")
    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "VALIDATION_ERROR"


def test_forecast_repository_filters_by_plant_and_respects_offset_limit(db_session: Session):
    first = _make_plant(db_session, suffix=6)
    second = _make_plant(db_session, suffix=7)
    base = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)

    db_session.add_all(
        [
            Forecast(plant_id=first.id, forecast_timestamp=base, p10_mw=1.0, p50_mw=2.0, p90_mw=3.0, model_version="v1"),
            Forecast(plant_id=first.id, forecast_timestamp=base + timedelta(hours=1), p10_mw=1.1, p50_mw=2.1, p90_mw=3.1, model_version="v1"),
            Forecast(plant_id=first.id, forecast_timestamp=base + timedelta(hours=2), p10_mw=1.2, p50_mw=2.2, p90_mw=3.2, model_version="v1"),
            Forecast(plant_id=second.id, forecast_timestamp=base, p10_mw=10.0, p50_mw=20.0, p90_mw=30.0, model_version="v1"),
            Forecast(plant_id=second.id, forecast_timestamp=base + timedelta(hours=1), p10_mw=11.0, p50_mw=21.0, p90_mw=31.0, model_version="v1"),
        ]
    )
    db_session.commit()

    fetched = db_session.query(Forecast).filter(Forecast.plant_id == first.id).order_by(Forecast.forecast_timestamp.asc()).offset(1).limit(2).all()
    assert len(fetched) == 2
    assert [row.forecast_timestamp.replace(tzinfo=timezone.utc) if row.forecast_timestamp.tzinfo is None else row.forecast_timestamp.astimezone(timezone.utc) for row in fetched] == [
        base + timedelta(hours=1),
        base + timedelta(hours=2),
    ]


def test_plant_list_supports_limit_and_offset(db_session: Session):
    _make_plant(db_session, suffix=8)
    _make_plant(db_session, suffix=9)
    _make_plant(db_session, suffix=10)

    plants = PlantService(db_session).list_plants(limit=2, offset=1)

    assert len(plants) == 2
    names = [plant.name for plant in plants]
    assert names == ["Plant A 9", "Plant A 10"]


def test_query_efficiency_large_dataset_returns_bounded_window(db_session: Session):
    plant = _make_plant(db_session, suffix=11)
    timestamps = [datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc) + timedelta(hours=i) for i in range(120)]
    rows = [
        WeatherData(
            plant_id=plant.id,
            timestamp=ts,
            temperature_c=10.0,
            humidity_percent=50.0,
            wind_speed_mps=2.0,
            wind_direction_deg=90.0,
            cloud_cover_percent=20.0,
            precipitation_mm=0.0,
            radiation_w_m2=200.0,
        )
        for ts in timestamps
    ]
    db_session.add_all(rows)
    db_session.commit()

    results = WeatherService(db_session).list_weather(plant.id, limit=25, offset=10)
    assert len(results) == 25
    first_ts = results[0].timestamp
    if first_ts.tzinfo is None:
        first_ts = first_ts.replace(tzinfo=timezone.utc)
    assert first_ts == datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
