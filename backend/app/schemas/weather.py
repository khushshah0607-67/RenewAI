from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WeatherDataResponse(BaseModel):
    id: int | None = None
    plant_id: int
    timestamp: datetime
    temperature_c: float | None = None
    humidity_percent: float | None = None
    wind_speed_mps: float | None = None
    wind_direction_deg: float | None = None
    cloud_cover_percent: float | None = None
    precipitation_mm: float | None = None
    radiation_w_m2: float | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
