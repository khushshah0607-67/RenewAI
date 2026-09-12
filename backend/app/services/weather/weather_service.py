from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.weather_data import WeatherData
from app.services.weather.open_meteo_client import OpenMeteoClient


class WeatherService:
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenMeteoClient()

    def fetch_and_store_weather(self, plant_id: int, latitude: float, longitude: float, timezone: str) -> list[WeatherData]:
        data = self.client.fetch_hourly_weather(latitude, longitude, timezone)
        if not data:
            return []

        existing_timestamps = {
            ts
            for ts, in self.db.execute(
                select(WeatherData.timestamp).where(WeatherData.plant_id == plant_id)
            ).all()
        }

        records_to_add: list[WeatherData] = []
        for row in data:
            timestamp = row["timestamp"]
            if timestamp in existing_timestamps:
                continue

            records_to_add.append(
                WeatherData(
                    plant_id=plant_id,
                    timestamp=timestamp,
                    temperature_c=row.get("temperature_c"),
                    humidity_percent=row.get("humidity_percent"),
                    wind_speed_mps=row.get("wind_speed_mps"),
                    wind_direction_deg=row.get("wind_direction_deg"),
                    cloud_cover_percent=row.get("cloud_cover_percent"),
                    precipitation_mm=row.get("precipitation_mm"),
                    radiation_w_m2=row.get("radiation_w_m2"),
                )
            )
            existing_timestamps.add(timestamp)

        if records_to_add:
            self.db.add_all(records_to_add)
            self.db.commit()
            for record in records_to_add:
                self.db.refresh(record)

        return self.list_weather(plant_id)

    def list_weather(
        self,
        plant_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[WeatherData]:
        stmt = select(WeatherData).where(WeatherData.plant_id == plant_id)
        if start is not None:
            stmt = stmt.where(WeatherData.timestamp >= start)
        if end is not None:
            stmt = stmt.where(WeatherData.timestamp <= end)
        stmt = stmt.order_by(WeatherData.timestamp.asc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).all())
