from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.models.plant import Plant
from app.db.repositories.forecast_repository import ForecastRepository
from app.services.financial.estimated_exposure_service import EstimatedExposureService, FinancialExposureConfig
from app.services.risk.rule_based_risk_service import RuleBasedRiskService
from app.services.recommendation.decision_support_service import DecisionSupportService


@dataclass(frozen=True)
class SimulationControls:
    battery_reserve_target: float = 0.0
    backup_availability: bool = False
    flexible_load_availability: bool = False
    curtailment_allowance: bool = False
    energy_price_inr_per_mwh: float | None = None


class WhatIfSimulationService:
    def __init__(self, db):
        self.db = db
        self.forecast_repository = ForecastRepository(db)
        self.risk_service = RuleBasedRiskService(db)
        self.financial_service = EstimatedExposureService(db)
        self.recommendation_service = DecisionSupportService(db)

    def simulate(self, plant: Plant, scenario: SimulationControls) -> dict:
        baseline_risk = self.risk_service.assess_plant_risk(plant)
        baseline_exposure = self.financial_service.estimate_exposure(plant)

        modified_risk_score = float(baseline_risk["overall_score"])
        modified_exposure = float(baseline_exposure["estimated_exposure_inr"])

        if scenario.battery_reserve_target > 0:
            modified_risk_score *= 0.92
        if scenario.backup_availability:
            modified_risk_score *= 0.88
        if scenario.flexible_load_availability:
            modified_risk_score *= 0.90
        if scenario.curtailment_allowance:
            modified_risk_score *= 0.96
        if scenario.energy_price_inr_per_mwh is not None:
            config = FinancialExposureConfig(price_inr_per_mwh=scenario.energy_price_inr_per_mwh)
            modified_exposure = float(
                EstimatedExposureService(self.db, config=config).estimate_exposure(plant)["estimated_exposure_inr"]
            )

        risk_level = "LOW" if modified_risk_score < 25 else "MEDIUM" if modified_risk_score < 60 else "HIGH"

        recommendations = []
        if scenario.battery_reserve_target > 0:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "severity": "MEDIUM",
                    "action": "Maintain reserve target",
                    "explanation": "The operator scenario keeps a battery reserve target in place to mitigate forecast uncertainty.",
                    "rationale": "This is a simulation-only recommendation and should be validated by operations before use.",
                }
            )
        if scenario.backup_availability:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "severity": "MEDIUM",
                    "action": "Activate backup support if needed",
                    "explanation": "Backup availability reduces shortfall exposure in the simulated scenario.",
                    "rationale": "Use this as a fallback contingency only after operator review.",
                }
            )
        if scenario.flexible_load_availability:
            recommendations.append(
                {
                    "priority": "LOW",
                    "severity": "LOW",
                    "action": "Shift flexible load to align with forecast",
                    "explanation": "Flexible load availability can help absorb production swings in the simulated profile.",
                    "rationale": "This remains a decision-support recommendation rather than a dispatch instruction.",
                }
            )
        if not recommendations:
            recommendations.append(
                {
                    "priority": "LOW",
                    "severity": "LOW",
                    "action": "Continue standard monitoring",
                    "explanation": "The simulated scenario remains relatively stable under the prototype rules.",
                    "rationale": "This is a decision-support recommendation only and not a guaranteed operating outcome.",
                }
            )

        return {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "plant_type": plant.plant_type,
            "baseline_risk_score": float(baseline_risk["overall_score"]),
            "baseline_risk_level": baseline_risk["risk_level"],
            "simulated_risk_score": round(modified_risk_score, 2),
            "simulated_risk_level": risk_level,
            "baseline_estimated_exposure_inr": float(baseline_exposure["estimated_exposure_inr"]),
            "simulated_estimated_exposure_inr": round(modified_exposure, 2),
            "risk_change": round(modified_risk_score - float(baseline_risk["overall_score"]), 2),
            "exposure_change": round(modified_exposure - float(baseline_exposure["estimated_exposure_inr"]), 2),
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "simulation_note": "Simulation output is in-memory decision support only and does not alter persistent operational data.",
        }
