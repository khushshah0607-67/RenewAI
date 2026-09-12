from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time_utils import normalize_datetime_to_utc
from app.db.models.weather_data import WeatherData
from app.services.weather.open_meteo_client import OpenMeteoClient

DEFAULT_QUERY_LIMIT = 1000
MAX_QUERY_LIMIT = 5000


class WeatherService:
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenMeteoClient()

    @staticmethod
    def normalize_timestamp(value: datetime | str | None, plant_timezone: str | None = None) -> datetime:
        return normalize_datetime_to_utc(value, plant_timezone)

    @staticmethod
    def validate_weather_row(row: dict, plant_timezone: str | None = None) -> dict:
        if not isinstance(row, dict):
            raise ValueError("Weather row must be a dictionary.")

        timestamp = row.get("timestamp")
        if timestamp is None:
            raise ValueError("Weather row is missing a timestamp.")
        normalized_timestamp = WeatherService.normalize_timestamp(timestamp, plant_timezone)

        validated = dict(row)
        validated["timestamp"] = normalized_timestamp

        for field_name in [
            "humidity_percent",
            "wind_speed_mps",
            "wind_direction_deg",
            "cloud_cover_percent",
            "precipitation_mm",
            "radiation_w_m2",
        ]:
            value = validated.get(field_name)
            if value is None:
                continue
            numeric_value = float(value)
            if numeric_value < 0:
                raise ValueError(f"{field_name} cannot be negative")
            if field_name == "humidity_percent" and numeric_value > 100:
                raise ValueError(f"{field_name} exceeds provider range")
            if field_name == "wind_direction_deg" and numeric_value > 360:
                raise ValueError(f"{field_name} exceeds provider range")
            if field_name == "cloud_cover_percent" and numeric_value > 100:
                raise ValueError(f"{field_name} exceeds provider range")
            validated[field_name] = numeric_value

        temperature_value = validated.get("temperature_c")
        if temperature_value is not None:
            validated["temperature_c"] = float(temperature_value)

        return validated

    @staticmethod
    def _normalize_db_timestamp(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _existing_timestamps(self, plant_id: int, start: datetime | None = None, end: datetime | None = None) -> set[datetime]:
        if self.db is None:
            return set()
        stmt = select(WeatherData.timestamp).where(WeatherData.plant_id == plant_id)
        if start is not None:
            stmt = stmt.where(WeatherData.timestamp >= start)
        if end is not None:
            stmt = stmt.where(WeatherData.timestamp <= end)
        return {
            self._normalize_db_timestamp(ts)
            for ts, in self.db.execute(stmt).all()
            if ts is not None
        }

    def get_weather_quality_summary(
        self,
        plant_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict:
        stmt = select(WeatherData).where(WeatherData.plant_id == plant_id)
        if start is not None:
            stmt = stmt.where(WeatherData.timestamp >= start)
        if end is not None:
            stmt = stmt.where(WeatherData.timestamp <= end)
        stmt = stmt.order_by(WeatherData.timestamp.asc())

        rows = list(self.db.scalars(stmt).all())
        if not rows:
            return {
                "exists": False,
                "count": 0,
                "earliest_timestamp": None,
                "latest_timestamp": None,
                "gap_count": 0,
                "has_continuous_data": False,
            }

        timestamps = [row.timestamp.astimezone(timezone.utc) if row.timestamp.tzinfo is not None else row.timestamp.replace(tzinfo=timezone.utc) for row in rows]
        gap_count = 0
        for previous, current in zip(timestamps, timestamps[1:]):
            if current - previous > timedelta(hours=1):
                gap_count += 1

        return {
            "exists": True,
            "count": len(rows),
            "earliest_timestamp": timestamps[0],
            "latest_timestamp": timestamps[-1],
            "gap_count": gap_count,
            "has_continuous_data": gap_count == 0 and len(timestamps) > 1,
        }

    def fetch_and_store_weather(
        self,
        plant_id: int,
        latitude: float,
        longitude: float,
        timezone: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[WeatherData]:
        if self.db is not None and start is not None and end is not None:
            start_utc = normalize_datetime_to_utc(start, timezone)
            end_utc = normalize_datetime_to_utc(end, timezone)
            existing_for_period = self._existing_timestamps(plant_id, start=start_utc, end=end_utc)
            if existing_for_period and len(existing_for_period) > 0:
                return self.list_weather(plant_id, start=start_utc, end=end_utc)

        try:
            data = self.client.fetch_hourly_weather(latitude, longitude, timezone, start=start, end=end)
        except Exception as exc:
            raise RuntimeError(f"Weather fetch failed for plant {plant_id}: {exc}") from exc

        if not data:
            return self.list_weather(plant_id, start=start, end=end)

        existing_timestamps = self._existing_timestamps(plant_id)
        records_to_add: list[WeatherData] = []
        seen_in_batch: set[datetime] = set()
        for row in data:
            validated_row = self.validate_weather_row(row, timezone)
            timestamp = validated_row["timestamp"]
            if timestamp in existing_timestamps or timestamp in seen_in_batch:
                continue

            records_to_add.append(
                WeatherData(
                    plant_id=plant_id,
                    timestamp=timestamp,
                    temperature_c=validated_row.get("temperature_c"),
                    humidity_percent=validated_row.get("humidity_percent"),
                    wind_speed_mps=validated_row.get("wind_speed_mps"),
                    wind_direction_deg=validated_row.get("wind_direction_deg"),
                    cloud_cover_percent=validated_row.get("cloud_cover_percent"),
                    precipitation_mm=validated_row.get("precipitation_mm"),
                    radiation_w_m2=validated_row.get("radiation_w_m2"),
                )
            )
            existing_timestamps.add(timestamp)
            seen_in_batch.add(timestamp)

        if records_to_add:
            try:
                self.db.add_all(records_to_add)
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
                remaining_records = [
                    record for record in records_to_add if record.timestamp not in self._existing_timestamps(plant_id)
                ]
                if remaining_records:
                    self.db.add_all(remaining_records)
                    self.db.commit()

        return self.list_weather(plant_id, start=start, end=end, plant_timezone=timezone)

    def list_weather(
        self,
        plant_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
        plant_timezone: str | None = None,
    ) -> list[WeatherData]:
        stmt = select(WeatherData).where(WeatherData.plant_id == plant_id)
        if start is not None:
            stmt = stmt.where(WeatherData.timestamp >= normalize_datetime_to_utc(start, plant_timezone))
        if end is not None:
            stmt = stmt.where(WeatherData.timestamp <= normalize_datetime_to_utc(end, plant_timezone))
        stmt = stmt.order_by(WeatherData.timestamp.asc())
        stmt = stmt.offset(max(offset, 0))
        query_limit = DEFAULT_QUERY_LIMIT if limit is None else min(limit, MAX_QUERY_LIMIT)
        stmt = stmt.limit(query_limit)

        rows = list(self.db.scalars(stmt).all())
        for row in rows:
            if row.timestamp.tzinfo is None:
                row.timestamp = row.timestamp.replace(tzinfo=timezone.utc)
            else:
                row.timestamp = row.timestamp.astimezone(timezone.utc)
        return rows
