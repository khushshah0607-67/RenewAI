from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.generation_validation import GenerationDataContract
from app.core.time_utils import normalize_datetime_to_utc
from app.db.database import Base
from app.db.models.historical_generation import HistoricalGeneration
from app.db.models.plant import Plant
from app.db.models.weather_data import WeatherData
from app.schemas.plant import PlantCreate, PlantUpdate
from app.services.generation_service import GenerationService
from app.services.weather.weather_service import WeatherService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_timezone_aware_timestamp_to_utc():
    value = datetime(2024, 1, 1, 14, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert normalize_datetime_to_utc(value) == datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)


def test_naive_timestamp_plus_plant_timezone_to_utc():
    value = datetime(2024, 1, 1, 14, 30)
    assert normalize_datetime_to_utc(value, "Asia/Kolkata") == datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)


def test_invalid_timestamp_rejected():
    with pytest.raises(ValueError):
        normalize_datetime_to_utc("not-a-timestamp")


def test_duplicate_generation_timestamp_rejected(db_session: Session):
    plant = Plant(
        name="Test",
        plant_type="SOLAR",
        latitude=12.0,
        longitude=77.0,
        installed_capacity_mw=5.0,
        export_limit_mw=4.0,
        timezone="Asia/Kolkata",
    )
    db_session.add(plant)
    db_session.commit()

    first = HistoricalGeneration(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), generation_mw=1.5)
    second = HistoricalGeneration(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), generation_mw=2.0)
    db_session.add_all([first, second])
    with pytest.raises(Exception):
        db_session.commit()


def test_generation_above_installed_capacity_rejected():
    contract = GenerationDataContract(installed_capacity_mw=5.0)
    with pytest.raises(ValueError, match="installed capacity"):
        contract.validate_generation_row(datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), 5.1)


def test_negative_generation_rejected():
    contract = GenerationDataContract(installed_capacity_mw=5.0)
    with pytest.raises(ValueError, match="non-negative"):
        contract.validate_generation_row(datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), -0.1)


def test_chronological_sorting():
    rows = [
        (datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc), 2.0),
        (datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), 1.0),
    ]
    sorted_rows = GenerationDataContract(installed_capacity_mw=5.0).sort_records(rows)
    assert [ts for ts, _ in sorted_rows] == [
        datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
    ]


def test_15_minute_timestamp_detection():
    timestamps = [
        datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 9, 15, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 9, 30, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 9, 45, tzinfo=timezone.utc),
    ]
    assert GenerationDataContract.detect_resolution(timestamps) == "15min"


def test_hourly_data_detection():
    timestamps = [
        datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
    ]
    assert GenerationDataContract.detect_resolution(timestamps) == "60min"


def test_plant_export_limit_higher_than_installed_capacity_rejected():
    with pytest.raises(ValueError, match="export limit"):
        PlantCreate(
            name="Plant A",
            plant_type="SOLAR",
            latitude=10,
            longitude=20,
            installed_capacity_mw=5.0,
            export_limit_mw=6.0,
            timezone="UTC",
        )


def test_valid_export_limit_accepted():
    plant = PlantCreate(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        export_limit_mw=4.5,
        timezone="UTC",
    )
    assert plant.export_limit_mw == 4.5


def test_database_uniqueness_for_plant_and_timestamp(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    first = HistoricalGeneration(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), generation_mw=1.0)
    second = HistoricalGeneration(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), generation_mw=2.0)
    db_session.add_all([first, second])
    with pytest.raises(Exception):
        db_session.commit()


def test_valid_generation_upload_and_resolution(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="Asia/Kolkata",
    )
    db_session.add(plant)
    db_session.commit()

    csv_text = "timestamp,generation_mw\n2024-01-01T09:00:00+00:00,1.0\n2024-01-01T09:15:00+00:00,1.5\n2024-01-01T09:30:00+00:00,2.0\n"
    file = UploadFile(
        filename="generation.csv",
        file=io.BytesIO(csv_text.encode("utf-8")),
        headers={"content-type": "text/csv"},
    )

    result = GenerationService(db_session).upload_generation_csv(plant.id, file)

    assert result["rows_received"] == 3
    assert result["rows_inserted"] == 3
    assert result["rows_rejected"] == 0
    assert result["detected_resolution"] == "15min"
    assert result["ml_ready_15min"] is True
    assert result["gap_count"] == 0
    assert db_session.query(HistoricalGeneration).count() == 3


def test_negative_generation_rejected(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    csv_text = "timestamp,generation_mw\n2024-01-01T09:00:00+00:00,-0.1\n"
    file = UploadFile(
        filename="generation.csv",
        file=io.BytesIO(csv_text.encode("utf-8")),
        headers={"content-type": "text/csv"},
    )

    result = GenerationService(db_session).upload_generation_csv(plant.id, file)

    assert result["rows_inserted"] == 0
    assert result["rows_rejected"] == 1
    assert result["valid_row_count"] == 0
    assert db_session.query(HistoricalGeneration).count() == 0


def test_generation_above_capacity_rejected(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    csv_text = "timestamp,generation_mw\n2024-01-01T09:00:00+00:00,5.1\n"
    file = UploadFile(
        filename="generation.csv",
        file=io.BytesIO(csv_text.encode("utf-8")),
        headers={"content-type": "text/csv"},
    )

    result = GenerationService(db_session).upload_generation_csv(plant.id, file)

    assert result["rows_rejected"] == 1
    assert "exceeds installed capacity" in result["errors"][0]
    assert db_session.query(HistoricalGeneration).count() == 0


def test_duplicate_timestamps_in_same_upload_are_rejected(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    csv_text = "timestamp,generation_mw\n2024-01-01T09:00:00+00:00,1.0\n2024-01-01T09:00:00+00:00,2.0\n"
    file = UploadFile(
        filename="generation.csv",
        file=io.BytesIO(csv_text.encode("utf-8")),
        headers={"content-type": "text/csv"},
    )

    result = GenerationService(db_session).upload_generation_csv(plant.id, file)

    assert result["duplicate_count"] == 1
    assert result["rows_inserted"] == 1
    assert db_session.query(HistoricalGeneration).count() == 1


def test_duplicate_upload_does_not_create_duplicate_database_rows(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    csv_text = "timestamp,generation_mw\n2024-01-01T09:00:00+00:00,1.0\n2024-01-01T09:15:00+00:00,1.5\n"
    file = UploadFile(
        filename="generation.csv",
        file=io.BytesIO(csv_text.encode("utf-8")),
        headers={"content-type": "text/csv"},
    )

    service = GenerationService(db_session)
    first = service.upload_generation_csv(plant.id, file)
    second = service.upload_generation_csv(plant.id, file)

    assert first["rows_inserted"] == 2
    assert second["duplicate_count"] == 2
    assert db_session.query(HistoricalGeneration).count() == 2


def test_timezone_normalization_to_utc(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="Asia/Kolkata",
    )
    db_session.add(plant)
    db_session.commit()

    csv_text = "timestamp,generation_mw\n2024-01-01T14:30:00,1.5\n"
    file = UploadFile(
        filename="generation.csv",
        file=io.BytesIO(csv_text.encode("utf-8")),
        headers={"content-type": "text/csv"},
    )

    summary = GenerationService(db_session).upload_generation_csv(plant.id, file)
    record = db_session.query(HistoricalGeneration).one()
    actual_timestamp = record.timestamp
    if actual_timestamp.tzinfo is None:
        actual_timestamp = actual_timestamp.replace(tzinfo=timezone.utc)

    assert summary["min_timestamp"] == datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    assert actual_timestamp == datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)


def test_hourly_detection_does_not_expand_to_15min(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    csv_text = "timestamp,generation_mw\n2024-01-01T09:00:00+00:00,1.0\n2024-01-01T10:00:00+00:00,2.0\n2024-01-01T11:00:00+00:00,3.0\n"
    file = UploadFile(
        filename="generation.csv",
        file=io.BytesIO(csv_text.encode("utf-8")),
        headers={"content-type": "text/csv"},
    )

    summary = GenerationService(db_session).upload_generation_csv(plant.id, file)

    assert summary["detected_resolution"] == "60min"
    assert summary["ml_ready_15min"] is False
    assert summary["gap_count"] == 0
    assert db_session.query(HistoricalGeneration).count() == 3


def test_irregular_gapped_data_reports_gap_count(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    csv_text = "timestamp,generation_mw\n2024-01-01T09:00:00+00:00,1.0\n2024-01-01T09:15:00+00:00,2.0\n2024-01-01T10:00:00+00:00,3.0\n"
    file = UploadFile(
        filename="generation.csv",
        file=io.BytesIO(csv_text.encode("utf-8")),
        headers={"content-type": "text/csv"},
    )

    summary = GenerationService(db_session).upload_generation_csv(plant.id, file)

    assert summary["detected_resolution"] == "irregular"
    assert summary["gap_count"] >= 1
    assert summary["ml_ready_15min"] is False


def test_list_generation_supports_date_range_and_pagination(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    records = [
        HistoricalGeneration(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), generation_mw=1.0),
        HistoricalGeneration(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 9, 15, tzinfo=timezone.utc), generation_mw=1.5),
        HistoricalGeneration(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), generation_mw=2.0),
    ]
    db_session.add_all(records)
    db_session.commit()

    service = GenerationService(db_session)
    subset = service.list_generation(plant.id, start=datetime(2024, 1, 1, 9, 15, tzinfo=timezone.utc), end=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), limit=1)

    assert len(subset) == 1
    actual_timestamp = subset[0].timestamp
    if actual_timestamp.tzinfo is None:
        actual_timestamp = actual_timestamp.replace(tzinfo=timezone.utc)
    assert actual_timestamp == datetime(2024, 1, 1, 9, 15, tzinfo=timezone.utc)


def test_upload_transaction_rollback_on_invalid_rows(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    csv_text = "timestamp,generation_mw\n2024-01-01T09:00:00+00:00,6.0\n2024-01-01T09:15:00+00:00,-1.0\n"
    file = UploadFile(
        filename="generation.csv",
        file=io.BytesIO(csv_text.encode("utf-8")),
        headers={"content-type": "text/csv"},
    )

    summary = GenerationService(db_session).upload_generation_csv(plant.id, file)

    assert summary["rows_inserted"] == 0
    assert summary["rows_rejected"] == 2
    assert db_session.query(HistoricalGeneration).count() == 0


def test_weather_timestamp_aware_input_becomes_utc():
    value = datetime(2024, 1, 1, 14, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    assert normalize_datetime_to_utc(value) == datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)


def test_weather_naive_input_uses_plant_timezone_before_utc_conversion():
    value = datetime(2024, 1, 1, 14, 30)
    assert normalize_datetime_to_utc(value, "Asia/Kolkata") == datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)


def test_weather_duplicate_timestamp_rejected(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    first = WeatherData(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), temperature_c=10.0, humidity_percent=50.0, wind_speed_mps=2.0, wind_direction_deg=90.0, cloud_cover_percent=20.0, precipitation_mm=0.0, radiation_w_m2=300.0)
    second = WeatherData(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), temperature_c=11.0, humidity_percent=55.0, wind_speed_mps=2.5, wind_direction_deg=100.0, cloud_cover_percent=25.0, precipitation_mm=0.0, radiation_w_m2=320.0)
    db_session.add_all([first, second])
    with pytest.raises(Exception):
        db_session.commit()


def test_weather_repeated_ingestion_skips_duplicates(db_session: Session, monkeypatch):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    payload = [
        {
            "timestamp": datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
            "temperature_c": 12.0,
            "humidity_percent": 50.0,
            "wind_speed_mps": 2.0,
            "wind_direction_deg": 90.0,
            "cloud_cover_percent": 10.0,
            "precipitation_mm": 0.0,
            "radiation_w_m2": 200.0,
        },
        {
            "timestamp": datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            "temperature_c": 13.0,
            "humidity_percent": 40.0,
            "wind_speed_mps": 3.0,
            "wind_direction_deg": 120.0,
            "cloud_cover_percent": 20.0,
            "precipitation_mm": 0.0,
            "radiation_w_m2": 250.0,
        },
    ]

    monkeypatch.setattr("app.services.weather.open_meteo_client.OpenMeteoClient.fetch_hourly_weather", lambda *args, **kwargs: payload)

    service = WeatherService(db_session)
    first = service.fetch_and_store_weather(plant.id, plant.latitude, plant.longitude, plant.timezone)
    second = service.fetch_and_store_weather(plant.id, plant.latitude, plant.longitude, plant.timezone)

    assert len(first) == 2
    assert len(second) == 2
    assert db_session.query(WeatherData).count() == 2


def test_weather_service_orders_and_paginates_chronologically(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    records = [
        WeatherData(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), temperature_c=10.0, humidity_percent=50.0, wind_speed_mps=2.0, wind_direction_deg=90.0, cloud_cover_percent=20.0, precipitation_mm=0.0, radiation_w_m2=200.0),
        WeatherData(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), temperature_c=9.0, humidity_percent=60.0, wind_speed_mps=1.5, wind_direction_deg=80.0, cloud_cover_percent=30.0, precipitation_mm=0.0, radiation_w_m2=180.0),
        WeatherData(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc), temperature_c=12.0, humidity_percent=45.0, wind_speed_mps=3.0, wind_direction_deg=100.0, cloud_cover_percent=25.0, precipitation_mm=0.0, radiation_w_m2=220.0),
    ]
    db_session.add_all(records)
    db_session.commit()

    service = WeatherService(db_session)
    ordered = service.list_weather(plant.id, limit=2)
    assert [record.timestamp for record in ordered] == [
        datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
    ]


def test_weather_service_rejects_impossible_negative_values():
    service = WeatherService(None)
    with pytest.raises(ValueError, match="negative"):
        service.validate_weather_row({
            "timestamp": datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
            "temperature_c": 5.0,
            "humidity_percent": -1.0,
            "wind_speed_mps": 2.0,
            "wind_direction_deg": 90.0,
            "cloud_cover_percent": 10.0,
            "precipitation_mm": 0.0,
            "radiation_w_m2": 200.0,
        })


def test_weather_service_rejects_invalid_timestamp_input():
    service = WeatherService(None)
    with pytest.raises(ValueError, match="Invalid timestamp"):
        service.validate_weather_row({
            "timestamp": "not-a-date",
            "temperature_c": 5.0,
            "humidity_percent": 50.0,
            "wind_speed_mps": 2.0,
            "wind_direction_deg": 90.0,
            "cloud_cover_percent": 10.0,
            "precipitation_mm": 0.0,
            "radiation_w_m2": 200.0,
        })


def test_weather_service_reports_quality_summary_and_gap_info(db_session: Session):
    plant = Plant(
        name="Plant A",
        plant_type="SOLAR",
        latitude=10,
        longitude=20,
        installed_capacity_mw=5.0,
        timezone="UTC",
    )
    db_session.add(plant)
    db_session.commit()

    records = [
        WeatherData(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), temperature_c=10.0, humidity_percent=50.0, wind_speed_mps=2.0, wind_direction_deg=90.0, cloud_cover_percent=20.0, precipitation_mm=0.0, radiation_w_m2=200.0),
        WeatherData(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), temperature_c=12.0, humidity_percent=45.0, wind_speed_mps=3.0, wind_direction_deg=120.0, cloud_cover_percent=25.0, precipitation_mm=0.0, radiation_w_m2=250.0),
        WeatherData(plant_id=plant.id, timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), temperature_c=11.0, humidity_percent=55.0, wind_speed_mps=2.0, wind_direction_deg=95.0, cloud_cover_percent=15.0, precipitation_mm=0.0, radiation_w_m2=230.0),
    ]
    db_session.add_all(records)
    db_session.commit()

    summary = WeatherService(db_session).get_weather_quality_summary(plant.id, start=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc), end=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
    assert summary["exists"] is True
    assert summary["count"] == 3
    assert summary["earliest_timestamp"] == datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    assert summary["latest_timestamp"] == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert summary["has_continuous_data"] is False
    assert summary["gap_count"] >= 1


def test_weather_service_raises_clear_backend_error_for_external_failure(monkeypatch):
    service = WeatherService(db=None)
    monkeypatch.setattr("app.services.weather.open_meteo_client.OpenMeteoClient.fetch_hourly_weather", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("downstream outage")))

    with pytest.raises(RuntimeError, match="downstream outage"):
        service.fetch_and_store_weather(1, 10.0, 20.0, "UTC")
