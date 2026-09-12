from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RiskMetric(BaseModel):
    score: float = Field(..., ge=0, le=100)
    level: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class PlantRiskResponse(BaseModel):
    plant_id: int
    plant_name: str
    plant_type: str
    capacity_mw: float
    forecast_points: int
    overall_score: float = Field(..., ge=0, le=100)
    risk_level: str
    generated_at: datetime
    under_generation_risk: RiskMetric
    forecast_uncertainty_risk: RiskMetric
    ramp_change_risk: RiskMetric

    model_config = ConfigDict(from_attributes=True)
