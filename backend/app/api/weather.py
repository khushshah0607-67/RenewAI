from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.time_utils import normalize_datetime_to_utc
from app.db.database import get_db
from app.db.models.weather_data import WeatherData
from app.schemas.weather import WeatherDataResponse
from app.services.plant_service import PlantService
from app.services.weather.weather_service import WeatherService

router = APIRouter(prefix="/plants", tags=["weather"])


@router.get("/{plant_id}/weather", response_model=list[WeatherDataResponse])
def get_plant_weather(
    plant_id: int,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[WeatherData]:
    plant_service = PlantService(db)
    plant = plant_service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    try:
        normalized_start = normalize_datetime_to_utc(start, plant.timezone) if start is not None else None
        normalized_end = normalize_datetime_to_utc(end, plant.timezone) if end is not None else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    weather_service = WeatherService(db)
    weather_records = weather_service.fetch_and_store_weather(
        plant_id=plant_id,
        latitude=plant.latitude,
        longitude=plant.longitude,
        timezone=plant.timezone,
    )

    if start is not None or end is not None or limit is not None or offset > 0:
        return weather_service.list_weather(
            plant_id,
            start=normalized_start,
            end=normalized_end,
            limit=limit,
            offset=offset,
            plant_timezone=plant.timezone,
        )

    return weather_records
