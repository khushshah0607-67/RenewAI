from __future__ import annotations

from datetime import datetime, timezone

from app.db.models.plant import Plant
from app.db.repositories.forecast_repository import ForecastRepository
from app.services.financial.estimated_exposure_service import EstimatedExposureService
from app.services.risk.rule_based_risk_service import RuleBasedRiskService
from app.services.weather.weather_service import WeatherService


class PrototypeExplainabilityService:
    def __init__(self, db):
        self.db = db
        self.forecast_repository = ForecastRepository(db)
        self.risk_service = RuleBasedRiskService(db)
        self.financial_service = EstimatedExposureService(db)
        self.weather_service = WeatherService(db)

    def explain_plant(self, plant: Plant) -> dict:
        forecast_rows = self.forecast_repository.get_for_plant(plant.id)
        if not forecast_rows:
            raise ValueError("No forecast data available for this plant.")

        risk = self.risk_service.assess_plant_risk(plant)
        financial = self.financial_service.estimate_exposure(plant)

        weather_rows = self.weather_service.list_weather(plant.id, limit=24)
        if weather_rows:
            temp_avg = sum(item.temperature_c for item in weather_rows if item.temperature_c is not None) / len([item for item in weather_rows if item.temperature_c is not None])
            cloud_avg = sum(item.cloud_cover_percent for item in weather_rows if item.cloud_cover_percent is not None) / len([item for item in weather_rows if item.cloud_cover_percent is not None])
            humidity_avg = sum(item.humidity_percent for item in weather_rows if item.humidity_percent is not None) / len([item for item in weather_rows if item.humidity_percent is not None])
        else:
            temp_avg = None
            cloud_avg = None
            humidity_avg = None

        p50_points = [row.p50_mw for row in forecast_rows]
        expected_generation = sum(p50_points) / len(p50_points)
        recent_history = p50_points[-3:]
        recent_trend = (recent_history[-1] - recent_history[0]) if len(recent_history) > 1 else 0.0

        factors = [
            {
                "factor_name": "recent_generation_trend",
                "importance": 0.9,
                "contribution": round(recent_trend, 3),
                "direction": "positive" if recent_trend >= 0 else "negative",
                "explanation": f"Recent median forecast trend is {recent_trend:.2f} MW across the latest three forecast points.",
                "is_prototype": True,
                "source": "prototype",
            },
            {
                "factor_name": "forecast_uncertainty",
                "importance": 0.8,
                "contribution": round(risk["forecast_uncertainty_risk"]["score"], 2),
                "direction": "negative" if risk["forecast_uncertainty_risk"]["score"] >= 50 else "positive",
                "explanation": f"The forecast spread is driving a {risk['forecast_uncertainty_risk']['score']:.1f}% uncertainty contribution to risk.",
                "is_prototype": True,
                "source": "prototype",
            },
            {
                "factor_name": "weather_conditions",
                "importance": 0.7,
                "contribution": round(float(cloud_avg or 0.0), 2),
                "direction": "negative" if cloud_avg is not None and cloud_avg > 60 else "positive",
                "explanation": "Average weather conditions indicate a cloud cover and humidity profile of "
                f"{cloud_avg:.1f}% cloud and {humidity_avg:.1f}% humidity." if cloud_avg is not None and humidity_avg is not None else "Weather context is unavailable for this plant right now.",
                "is_prototype": True,
                "source": "prototype",
            },
            {
                "factor_name": "expected_generation_level",
                "importance": 0.85,
                "contribution": round(expected_generation, 2),
                "direction": "positive" if expected_generation > 0 else "negative",
                "explanation": f"The median forecast expectation is {expected_generation:.2f} MW across the 24-hour window.",
                "is_prototype": True,
                "source": "prototype",
            },
            {
                "factor_name": "risk_contribution",
                "importance": 1.0,
                "contribution": round(risk["overall_score"], 2),
                "direction": "negative" if risk["overall_score"] >= 50 else "positive",
                "explanation": f"Overall risk is {risk['risk_level']} with a score of {risk['overall_score']:.2f}, which is shaping the current recommendation set.",
                "is_prototype": True,
                "source": "prototype",
            },
        ]

        return {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "risk_level": risk["risk_level"],
            "overall_risk_score": risk["overall_score"],
            "estimated_exposure_inr": financial["estimated_exposure_inr"],
            "exposure_label": financial["exposure_label"],
            "forecast_summary": (
                f"Expected median generation is {expected_generation:.2f} MW over the next forecast horizon; "
                f"recent trend is {recent_trend:.2f} MW and overall risk is {risk['risk_level']}."
            ),
            "explanation_version": "prototype-v1",
            "prototype_note": "This is a prototype explanation layer and not an actual SHAP or model-attribute explanation.",
            "factors": factors,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
