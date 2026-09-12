from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.models.plant import Plant
from app.db.repositories.forecast_repository import ForecastRepository
from app.services.financial.estimated_exposure_service import EstimatedExposureService
from app.services.risk.rule_based_risk_service import RuleBasedRiskService


@dataclass(frozen=True)
class RecommendationThresholds:
    high_risk_score: float = 60.0
    medium_risk_score: float = 25.0
    high_uncertainty_score: float = 50.0
    high_under_generation_score: float = 50.0
    high_exposure_threshold: float = 500000.0


DEFAULT_RECOMMENDATION_THRESHOLDS = RecommendationThresholds()


class DecisionSupportService:
    def __init__(self, db, thresholds: RecommendationThresholds | None = None):
        self.db = db
        self.thresholds = thresholds or DEFAULT_RECOMMENDATION_THRESHOLDS
        self.forecast_repository = ForecastRepository(db)
        self.risk_service = RuleBasedRiskService(db)
        self.financial_service = EstimatedExposureService(db)

    def build_recommendations(self, plant: Plant) -> dict:
        forecast_rows = self.forecast_repository.get_for_plant(plant.id)
        if not forecast_rows:
            raise ValueError("No forecast data available for this plant.")

        risk = self.risk_service.assess_plant_risk(plant)
        financial = self.financial_service.estimate_exposure(plant)

        recommendations = []
        risk_score = float(risk["overall_score"])
        under_generation_score = float(risk["under_generation_risk"]["score"])
        uncertainty_score = float(risk["forecast_uncertainty_risk"]["score"])
        exposure = float(financial["estimated_exposure_inr"])

        if under_generation_score >= self.thresholds.high_under_generation_score or risk_score >= self.thresholds.high_risk_score:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "severity": "HIGH",
                    "action": "Maintain or increase battery reserve",
                    "explanation": "Under-generation or overall risk is elevated; keep a larger reserve margin to absorb forecast shortfalls.",
                    "rationale": "Decision-support only: this helps buffer reliability risk while the operator confirms dispatch decisions.",
                }
            )
            recommendations.append(
                {
                    "priority": "HIGH",
                    "severity": "MEDIUM",
                    "action": "Use backup or flexible load",
                    "explanation": "The forecast suggests a meaningful shortfall risk, so plan for backup generation or load flexibility during risk windows.",
                    "rationale": "Operator review is still required before dispatching backup resources.",
                }
            )
        elif uncertainty_score >= self.thresholds.high_uncertainty_score:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "severity": "MEDIUM",
                    "action": "Maintain or increase battery reserve",
                    "explanation": "The forecast spread is large, so a modest reserve cushion is prudent while uncertainty remains elevated.",
                    "rationale": "Use this as a guardrail until forecast confidence improves.",
                }
            )

        if uncertainty_score < self.thresholds.high_uncertainty_score and under_generation_score < self.thresholds.high_under_generation_score:
            recommendations.append(
                {
                    "priority": "LOW",
                    "severity": "LOW",
                    "action": "Charge battery when generation is favorable",
                    "explanation": "Forecast conditions look favorable and available storage should be charged to reduce future shortfall exposure.",
                    "rationale": "Charge storage opportunistically when generation is above the near-term baseline.",
                }
            )

        if risk_score >= self.thresholds.high_risk_score or exposure >= self.thresholds.high_exposure_threshold:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "severity": "MEDIUM",
                    "action": "Review operating plan and exposure sensitivity",
                    "explanation": "Estimated exposure is elevated enough to merit a manual operator review of dispatch and reserve posture.",
                    "rationale": "This is a prototype estimate and not a guaranteed financial loss or dispatch instruction.",
                }
            )

        if risk_score < self.thresholds.medium_risk_score and uncertainty_score < self.thresholds.high_uncertainty_score:
            recommendations.append(
                {
                    "priority": "LOW",
                    "severity": "LOW",
                    "action": "Consider curtailment when over-generation risk is present",
                    "explanation": "If later signals indicate strong over-generation, curtailment may help avoid excess production or wasted storage headroom.",
                    "rationale": "This recommendation only applies when over-generation signals appear and should be reviewed by the operator.",
                }
            )

        if not recommendations:
            recommendations.append(
                {
                    "priority": "LOW",
                    "severity": "LOW",
                    "action": "Continue normal monitoring",
                    "explanation": "Current risk and exposure levels are manageable under the prototype rules; continue routine monitoring.",
                    "rationale": "This remains a decision-support recommendation, not a guarantee of safe operating conditions.",
                }
            )

        return {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "risk_level": risk["risk_level"],
            "overall_risk_score": risk["overall_score"],
            "estimated_exposure_inr": financial["estimated_exposure_inr"],
            "exposure_label": financial["exposure_label"],
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
