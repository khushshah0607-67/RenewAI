from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.inference.fallback import (
    build_persistence_fallback,
    detect_large_timestamp_gaps,
    load_model_metadata,
)
from ml.inference.predict_generation import predict_generation
from app.db.models.forecast import Forecast
from app.db.models.plant import Plant
from app.db.repositories.forecast_repository import ForecastRepository
from app.db.repositories.historical_generation_repository import HistoricalGenerationRepository
from app.services.weather.weather_service import WeatherService


class BaselineForecastService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ForecastRepository(db)
        self.historical_repository = HistoricalGenerationRepository(db)

    @staticmethod
    def _unwrap_ml_predictions(ml_result: Any) -> list[dict[str, Any]]:
        if isinstance(ml_result, list):
            return ml_result
        if not isinstance(ml_result, dict):
            raise ValueError("ML inference returned an unexpected payload.")
        if ml_result.get("status") == "error":
            error = ml_result.get("error") or {}
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise ValueError(message or "ML inference failed.")
        forecast_rows = ml_result.get("forecast")
        if not isinstance(forecast_rows, list) or not forecast_rows:
            raise ValueError("ML inference returned no forecast rows.")
        return forecast_rows

    def _save_and_return_forecasts(
        self,
        plant: Plant,
        rows: list[dict[str, Any]],
        default_version: str,
    ) -> list[Forecast]:
        canonical_capacity_mw = float(plant.installed_capacity_mw)
        generated_records: list[Forecast] = []

        for row in rows:
            ts_val = row.get("timestamp")
            if isinstance(ts_val, str):
                dt = datetime.fromisoformat(ts_val)
            elif isinstance(ts_val, datetime):
                dt = ts_val
            else:
                continue

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)

            # Support both ml.inference.predict output ("p10", "p50", "p90")
            # and fallback output ("p10_kw", "p50_kw", "p90_kw", "forecast_kw")
            if "p50" in row:
                p10_kw = float(row.get("p10", 0.0))
                p50_kw = float(row.get("p50", 0.0))
                p90_kw = float(row.get("p90", 0.0))
            else:
                p10_kw = float(row.get("p10_kw", row.get("forecast_kw", 0.0)))
                p50_kw = float(row.get("p50_kw", row.get("forecast_kw", 0.0)))
                p90_kw = float(row.get("p90_kw", row.get("forecast_kw", 0.0)))

            # Correctly map kW -> MW
            p10_mw = max(0.0, min(p10_kw / 1000.0, canonical_capacity_mw))
            p50_mw = max(0.0, min(p50_kw / 1000.0, canonical_capacity_mw))
            p90_mw = max(0.0, min(p90_kw / 1000.0, canonical_capacity_mw))

            if p10_mw > p50_mw:
                p10_mw = p50_mw
            if p90_mw < p50_mw:
                p90_mw = p50_mw

            model_version = str(row.get("model_version") or default_version)

            generated_records.append(
                Forecast(
                    plant_id=plant.id,
                    forecast_timestamp=dt,
                    p10_mw=p10_mw,
                    p50_mw=p50_mw,
                    p90_mw=p90_mw,
                    model_version=model_version,
                )
            )

        self.repository.replace_for_plant(plant.id, generated_records)
        return generated_records

    def generate_for_plant(self, plant_id: int) -> list[Forecast]:
        plant = self.db.get(Plant, plant_id)
        if plant is None:
            raise HTTPException(status_code=404, detail="Plant not found")

        history = self.historical_repository.get_for_plant(plant_id)
        if not history:
            raise HTTPException(
                status_code=404,
                detail="No historical generation data available for this plant.",
            )

        canonical_capacity_mw = float(plant.installed_capacity_mw)
        if canonical_capacity_mw <= 0:
            raise HTTPException(
                status_code=400,
                detail="Plant capacity must be greater than zero.",
            )

        capacity_kw = canonical_capacity_mw * 1000.0

        plant_data = {
            "plant_id": str(plant.id),
            "capacity_kw": capacity_kw,
            "plant_capacity_kw": capacity_kw,
            "timezone": plant.timezone or "UTC",
            "renewable_type": (plant.plant_type or "solar").lower(),
        }

        history_sorted = sorted(history, key=lambda h: h.timestamp)
        hist_records = []
        for h in history_sorted:
            ts = (
                h.timestamp.astimezone(timezone.utc)
                if h.timestamp.tzinfo
                else h.timestamp.replace(tzinfo=timezone.utc)
            )
            hist_records.append({
                "timestamp": ts.isoformat(),
                "ac_power_kw": float(h.generation_mw) * 1000.0,
            })
        historical_df = pd.DataFrame(hist_records)

        metadata = load_model_metadata()

        # Check existing ML fallback contract for minimum history length (97 points)
        if len(historical_df) < 97:
            fallback_res = build_persistence_fallback(
                plant_data=plant_data,
                historical_data=historical_df,
                weather_data=None,
                fallback_reason="INSUFFICIENT_HISTORY",
                metadata=metadata,
            )
            return self._save_and_return_forecasts(
                plant,
                fallback_res["forecast"],
                metadata.get("model_version", "renewai-generalized-xgb-v1"),
            )

        latest_history_ts = history_sorted[-1].timestamp
        if latest_history_ts.tzinfo is None:
            latest_history_ts = latest_history_ts.replace(tzinfo=timezone.utc)
        else:
            latest_history_ts = latest_history_ts.astimezone(timezone.utc)

        weather_service = WeatherService(self.db)
        try:
            weather_service.fetch_and_store_weather(
                plant_id=plant.id,
                latitude=plant.latitude,
                longitude=plant.longitude,
                timezone=plant.timezone,
            )
        except Exception:
            pass

        weather_rows = weather_service.list_weather(
            plant_id=plant.id,
            start=latest_history_ts,
            limit=96,
            plant_timezone=plant.timezone,
        )

        if not weather_rows or len(weather_rows) < 25:
            weather_rows = weather_service.list_weather(
                plant_id=plant.id,
                limit=96,
                plant_timezone=plant.timezone,
            )

        if not weather_rows or len(weather_rows) < 25:
            fallback_res = build_persistence_fallback(
                plant_data=plant_data,
                historical_data=historical_df,
                weather_data=None,
                fallback_reason="WEATHER_UNAVAILABLE",
                metadata=metadata,
            )
            return self._save_and_return_forecasts(
                plant,
                fallback_res["forecast"],
                metadata.get("model_version", "renewai-generalized-xgb-v1"),
            )

        weather_records = []
        for w in weather_rows:
            w_ts = (
                w.timestamp.astimezone(timezone.utc)
                if w.timestamp.tzinfo
                else w.timestamp.replace(tzinfo=timezone.utc)
            )
            rad = float(w.radiation_w_m2) if w.radiation_w_m2 is not None else 0.0
            weather_records.append({
                "timestamp": w_ts.isoformat(),
                "ambient_temperature": float(w.temperature_c) if w.temperature_c is not None else 25.0,
                "relative_humidity": float(w.humidity_percent) if w.humidity_percent is not None else 50.0,
                "cloud_cover": float(w.cloud_cover_percent) if w.cloud_cover_percent is not None else 0.0,
                "shortwave_radiation_w_m2": rad,
                "irradiation": rad / 1000.0,
                "wind_speed": float(w.wind_speed_mps) if w.wind_speed_mps is not None else 0.0,
                "wind_direction": float(w.wind_direction_deg) if w.wind_direction_deg is not None else 0.0,
            })
        weather_df = pd.DataFrame(weather_records)

        has_large_gap, _ = detect_large_timestamp_gaps(weather_df, gap_minutes=720)
        if has_large_gap:
            fallback_res = build_persistence_fallback(
                plant_data=plant_data,
                historical_data=historical_df,
                weather_data=weather_df,
                fallback_reason="LARGE_TIMESTAMP_GAPS",
                metadata=metadata,
            )
            return self._save_and_return_forecasts(
                plant,
                fallback_res["forecast"],
                metadata.get("model_version", "renewai-generalized-xgb-v1"),
            )

        try:
            ml_result = predict_generation(plant_data, historical_df, weather_df)
            raw_predictions = self._unwrap_ml_predictions(ml_result)
            return self._save_and_return_forecasts(
                plant,
                raw_predictions,
                metadata.get("model_version", "renewai-generalized-xgb-v1"),
            )
        except Exception:
            fallback_res = build_persistence_fallback(
                plant_data=plant_data,
                historical_data=historical_df,
                weather_data=weather_df,
                fallback_reason="MODEL_ERROR",
                metadata=metadata,
            )
            return self._save_and_return_forecasts(
                plant,
                fallback_res["forecast"],
                metadata.get("model_version", "renewai-generalized-xgb-v1"),
            )

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


ForecastService = BaselineForecastService
