from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlantType(str, Enum):
    SOLAR = "SOLAR"
    WIND = "WIND"


class PlantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    plant_type: PlantType
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    capacity_mw: float = Field(..., gt=0)
    timezone: str = Field(..., min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid")


class PlantCreate(PlantBase):
    pass


class PlantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    plant_type: PlantType | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    capacity_mw: float | None = Field(default=None, gt=0)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid")


class PlantResponse(PlantBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
