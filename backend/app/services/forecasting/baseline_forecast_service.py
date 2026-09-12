from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.db.models.forecast import Forecast
from app.db.models.historical_generation import HistoricalGeneration
from app.db.repositories.forecast_repository import ForecastRepository
from app.db.repositories.historical_generation_repository import HistoricalGenerationRepository

MODEL_VERSION = "persistence-v1"


class BaselineForecastService:
    def __init__(self, db):
        self.db = db
        self.repository = ForecastRepository(db)
        self.historical_repository = HistoricalGenerationRepository(db)

    def _build_baseline_from_history(self, history: list[HistoricalGeneration]) -> float:
        if not history:
            raise HTTPException(status_code=404, detail="No historical generation data available for this plant.")

        recent = history[-24:]
        baseline = sum(record.generation_mw for record in recent) / len(recent)
        return max(baseline, 0.0)

    def generate_for_plant(self, plant_id: int) -> list[Forecast]:
        history = self.historical_repository.get_for_plant(plant_id)
        if not history:
            raise HTTPException(status_code=404, detail="No historical generation data available for this plant.")

        baseline = self._build_baseline_from_history(history)
        last_timestamp = max(record.timestamp for record in history)
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)

        generated_records: list[Forecast] = []
        for offset in range(24):
            forecast_ts = last_timestamp + timedelta(hours=offset + 1)
            uncertainty = baseline * 0.18
            p50 = baseline
            p10 = max(baseline - uncertainty, 0.0)
            p90 = baseline + uncertainty

            generated_records.append(
                Forecast(
                    plant_id=plant_id,
                    forecast_timestamp=forecast_ts,
                    p10_mw=p10,
                    p50_mw=p50,
                    p90_mw=p90,
                    model_version=MODEL_VERSION,
                )
            )

        self.repository.replace_for_plant(plant_id, generated_records)
        return generated_records

    def list_for_plant(
        self,
        plant_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Forecast]:
        records = self.repository.get_for_plant(plant_id, start=start, end=end, limit=limit, offset=offset)
        if records or (start is not None or end is not None or limit is not None or offset > 0):
            return records
        return self.generate_for_plant(plant_id)
