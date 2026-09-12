from pydantic import BaseModel, ConfigDict, Field


class SimulationScenario(BaseModel):
    battery_reserve_target: float = Field(default=0.0, ge=0)
    backup_availability: bool = False
    flexible_load_availability: bool = False
    curtailment_allowance: bool = False
    energy_price_inr_per_mwh: float | None = Field(default=None, gt=0)

    model_config = ConfigDict(extra="forbid")


class SimulationRecommendation(BaseModel):
    priority: str
    severity: str
    action: str
    explanation: str
    rationale: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SimulationResponse(BaseModel):
    plant_id: int
    plant_name: str
    plant_type: str
    baseline_risk_score: float
    baseline_risk_level: str
    simulated_risk_score: float
    simulated_risk_level: str
    baseline_estimated_exposure_inr: float
    simulated_estimated_exposure_inr: float
    risk_change: float
    exposure_change: float
    recommendations: list[SimulationRecommendation]
    generated_at: str
    simulation_note: str = "Simulation output is in-memory decision support only and does not alter persistent operational data."

    model_config = ConfigDict(from_attributes=True)
