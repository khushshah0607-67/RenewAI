from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.models.forecast import Forecast
from app.db.models.plant import Plant
from app.db.repositories.forecast_repository import ForecastRepository


@dataclass(frozen=True)
class RiskThresholds:
    under_generation_warning_pct: float = 0.15
    under_generation_critical_pct: float = 0.30
    uncertainty_warning_range: float = 0.20
    uncertainty_critical_range: float = 0.35
    ramp_warning_pct: float = 0.25
    ramp_critical_pct: float = 0.50
    low_cutoff: float = 25.0
    medium_cutoff: float = 60.0
    max_score: float = 100.0


RISK_THRESHOLDS = RiskThresholds()


class RuleBasedRiskService:
    def __init__(self, db):
        self.db = db
        self.forecast_repository = ForecastRepository(db)

    def _risk_level_from_score(self, score: float) -> str:
        if score >= RISK_THRESHOLDS.medium_cutoff:
            return "HIGH"
        if score >= RISK_THRESHOLDS.low_cutoff:
            return "MEDIUM"
        return "LOW"

    def _metric_from_score(self, score: float, label: str, description: str) -> dict:
        level = self._risk_level_from_score(score)
        return {
            "score": max(0.0, min(score, RISK_THRESHOLDS.max_score)),
            "level": level,
            "description": description,
        }

    def assess_plant_risk(self, plant: Plant) -> dict:
        forecast_rows = self.forecast_repository.get_for_plant(plant.id)
        if not forecast_rows:
            from app.services.forecasting.baseline_forecast_service import BaselineForecastService
            try:
                forecast_rows = BaselineForecastService(self.db).list_for_plant(plant.id)
            except Exception:
                forecast_rows = []

        if not forecast_rows:
            raise HTTPException(status_code=404, detail="No forecast data available for this plant.")

        p50_points = [row.p50_mw for row in forecast_rows]
        p10_points = [row.p10_mw for row in forecast_rows]
        p90_points = [row.p90_mw for row in forecast_rows]

        capacity = float(plant.installed_capacity_mw)
        if capacity <= 0:
            raise HTTPException(status_code=400, detail="Plant capacity must be greater than zero.")

        projected_mean = sum(p50_points) / len(p50_points)
        expected_gap_pct = max((capacity - projected_mean) / capacity, 0.0)
        under_generation_score = min(expected_gap_pct * 100 / RISK_THRESHOLDS.under_generation_warning_pct, 100.0)

        avg_uncertainty = sum((p90 - p10) for p10, p90 in zip(p10_points, p90_points)) / len(p10_points)
        uncertainty_pct = avg_uncertainty / max(capacity, 1e-9)
        uncertainty_score = min((uncertainty_pct / RISK_THRESHOLDS.uncertainty_warning_range) * 100.0, 100.0)

        ramp_values = []
        for previous, current in zip(p50_points, p50_points[1:]):
            delta = abs(current - previous)
            ramp_values.append(delta / max(capacity, 1e-9))

        ramp_change_pct = max(ramp_values, default=0.0)
        ramp_score = min((ramp_change_pct / RISK_THRESHOLDS.ramp_warning_pct) * 100.0, 100.0)

        under_generation_metric = self._metric_from_score(
            under_generation_score,
            "under_generation_risk",
            f"Projected median output is {expected_gap_pct * 100:.1f}% below plant capacity.",
        )
        uncertainty_metric = self._metric_from_score(
            uncertainty_score,
            "forecast_uncertainty_risk",
            f"Average forecast spread is {uncertainty_pct * 100:.1f}% of plant capacity.",
        )
        ramp_metric = self._metric_from_score(
            ramp_score,
            "ramp_change_risk",
            f"Largest observed step change is {ramp_change_pct * 100:.1f}% of plant capacity between consecutive forecast points.",
        )

        overall_score = (
            under_generation_metric["score"] * 0.45
            + uncertainty_metric["score"] * 0.35
            + ramp_metric["score"] * 0.20
        )
        risk_level = self._risk_level_from_score(overall_score)

        return {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "capacity_mw": plant.installed_capacity_mw,
            "forecast_points": len(forecast_rows),
            "overall_score": round(overall_score, 2),
            "risk_level": risk_level,
            "generated_at": datetime.now(timezone.utc),
            "under_generation_risk": under_generation_metric,
            "forecast_uncertainty_risk": uncertainty_metric,
            "ramp_change_risk": ramp_metric,
        }
