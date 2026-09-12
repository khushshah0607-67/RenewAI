from pydantic import BaseModel, ConfigDict, Field


class FactorContribution(BaseModel):
    factor_name: str
    importance: float | None = None
    contribution: float | None = None
    direction: str
    explanation: str
    is_prototype: bool = True
    source: str = "prototype"

    model_config = ConfigDict(from_attributes=True)


class ExplanationResponse(BaseModel):
    plant_id: int
    plant_name: str
    plant_type: str
    risk_level: str
    overall_risk_score: float = Field(..., ge=0, le=100)
    estimated_exposure_inr: float
    exposure_label: str = "ESTIMATED"
    forecast_summary: str
    explanation_version: str = "prototype-v1"
    prototype_note: str = "This is a prototype explanation layer and not an actual SHAP or model-attribute explanation."
    factors: list[FactorContribution]
    generated_at: str

    model_config = ConfigDict(from_attributes=True)
