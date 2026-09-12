from pydantic import BaseModel, ConfigDict, Field


class RecommendationItem(BaseModel):
    priority: str
    severity: str
    action: str
    explanation: str
    rationale: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    plant_id: int
    plant_name: str
    plant_type: str
    risk_level: str
    overall_risk_score: float = Field(..., ge=0, le=100)
    estimated_exposure_inr: float
    exposure_label: str = "ESTIMATED"
    recommendations: list[RecommendationItem]
    generated_at: str

    model_config = ConfigDict(from_attributes=True)
