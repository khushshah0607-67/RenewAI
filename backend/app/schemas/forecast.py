from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ForecastResponse(BaseModel):
    id: int
    plant_id: int
    forecast_timestamp: datetime
    generated_at: datetime
    p10_mw: float
    p50_mw: float
    p90_mw: float
    model_version: str

    model_config = ConfigDict(from_attributes=True)
