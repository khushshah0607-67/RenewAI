from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HistoricalGenerationBase(BaseModel):
    timestamp: datetime
    generation_mw: float = Field(..., ge=0)

    model_config = ConfigDict(extra="forbid")


class HistoricalGenerationResponse(HistoricalGenerationBase):
    id: int
    plant_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerationUploadSummary(BaseModel):
    plant_id: int
    rows_received: int
    rows_inserted: int
    rows_rejected: int
    duplicate_count: int
    gap_count: int = 0
    detected_resolution: str | None = None
    min_timestamp: datetime | None = None
    max_timestamp: datetime | None = None
    valid_row_count: int = 0
    ml_ready_15min: bool = False
    errors: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)
