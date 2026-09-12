from pydantic import BaseModel, ConfigDict, Field


class FinancialExposureResponse(BaseModel):
    plant_id: int
    plant_name: str
    plant_type: str
    capacity_mw: float
    forecast_points: int
    energy_price_inr_per_mwh: float = Field(..., gt=0)
    estimated_deviation_mwh: float
    estimated_exposure_inr: float
    exposure_label: str = "ESTIMATED"
    currency: str = "INR"
    generated_at: str

    model_config = ConfigDict(from_attributes=True)
