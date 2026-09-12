from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.models.plant import Plant
from app.db.repositories.forecast_repository import ForecastRepository


@dataclass(frozen=True)
class FinancialExposureConfig:
    price_inr_per_mwh: float = 4500.0
    deviation_sensitivity: float = 0.5


DEFAULT_FINANCIAL_EXPOSURE_CONFIG = FinancialExposureConfig()


class EstimatedExposureService:
    def __init__(self, db, config: FinancialExposureConfig | None = None):
        self.db = db
        self.config = config or DEFAULT_FINANCIAL_EXPOSURE_CONFIG
        self.forecast_repository = ForecastRepository(db)

    def estimate_exposure(self, plant: Plant) -> dict:
        forecast_rows = self.forecast_repository.get_for_plant(plant.id)
        if not forecast_rows:
            raise HTTPException(status_code=404, detail="No forecast data available for this plant.")

        p10 = [row.p10_mw for row in forecast_rows]
        p50 = [row.p50_mw for row in forecast_rows]
        p90 = [row.p90_mw for row in forecast_rows]

        capacity = float(plant.capacity_mw)
        if capacity <= 0:
            raise HTTPException(status_code=400, detail="Plant capacity must be greater than zero.")

        average_p50 = sum(p50) / len(p50)
        average_p10 = sum(p10) / len(p10)
        average_p90 = sum(p90) / len(p90)

        average_shortfall_mw = max((capacity - average_p50) / 1.0, 0.0)
        average_uncertainty_mw = max((average_p90 - average_p10) / 2.0, 0.0)
        estimated_deviation_mwh = max((average_shortfall_mw + average_uncertainty_mw * self.config.deviation_sensitivity) * 24.0, 0.0)
        estimated_exposure_inr = estimated_deviation_mwh * self.config.price_inr_per_mwh

        return {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "capacity_mw": plant.capacity_mw,
            "forecast_points": len(forecast_rows),
            "energy_price_inr_per_mwh": self.config.price_inr_per_mwh,
            "estimated_deviation_mwh": round(estimated_deviation_mwh, 2),
            "estimated_exposure_inr": round(estimated_exposure_inr, 2),
            "exposure_label": "ESTIMATED",
            "currency": "INR",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
