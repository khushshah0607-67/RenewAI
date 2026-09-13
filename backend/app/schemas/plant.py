from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

<<<<<<< Updated upstream
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator
=======
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
>>>>>>> Stashed changes


class PlantType(str, Enum):
    SOLAR = "SOLAR"
    WIND = "WIND"


class PlantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    plant_type: PlantType
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
<<<<<<< Updated upstream
    installed_capacity_mw: float = Field(
        ...,
        gt=0,
        validation_alias=AliasChoices("installed_capacity_mw", "capacity_mw"),
=======
    capacity_mw: float = Field(
        ...,
        gt=0,
        validation_alias=AliasChoices("capacity_mw", "installed_capacity_mw"),
>>>>>>> Stashed changes
    )
    export_limit_mw: float | None = Field(default=None, gt=0)
    timezone: str = Field(..., min_length=1, max_length=64)

<<<<<<< Updated upstream
    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except Exception as exc:  # pragma: no cover - validation error path
            raise ValueError(f"Invalid timezone '{value}'.") from exc
        return value

    @model_validator(mode="after")
    def validate_export_limit(self):
        if self.export_limit_mw is not None and self.export_limit_mw > self.installed_capacity_mw:
            raise ValueError("export limit cannot be greater than installed capacity.")
        return self

=======
>>>>>>> Stashed changes
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PlantCreate(PlantBase):
    pass


class PlantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    plant_type: PlantType | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
<<<<<<< Updated upstream
    installed_capacity_mw: float | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices("installed_capacity_mw", "capacity_mw"),
=======
    capacity_mw: float | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices("capacity_mw", "installed_capacity_mw"),
>>>>>>> Stashed changes
    )
    export_limit_mw: float | None = Field(default=None, gt=0)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

<<<<<<< Updated upstream
    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except Exception as exc:  # pragma: no cover - validation error path
            raise ValueError(f"Invalid timezone '{value}'.") from exc
        return value

    @model_validator(mode="after")
    def validate_export_limit(self):
        if self.installed_capacity_mw is not None and self.export_limit_mw is not None and self.export_limit_mw > self.installed_capacity_mw:
            raise ValueError("export limit cannot be greater than installed capacity.")
        return self

=======
>>>>>>> Stashed changes
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PlantResponse(PlantBase):
    id: int
    created_at: datetime

<<<<<<< Updated upstream
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def capacity_mw(self) -> float:
        return self.installed_capacity_mw
=======
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)
>>>>>>> Stashed changes
