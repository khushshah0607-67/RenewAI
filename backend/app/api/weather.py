from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.weather_data import WeatherData
from app.schemas.weather import WeatherDataResponse
from app.services.plant_service import PlantService
from app.services.weather.weather_service import WeatherService

router = APIRouter(prefix="/plants", tags=["weather"])


@router.get("/{plant_id}/weather", response_model=list[WeatherDataResponse])
def get_plant_weather(
    plant_id: int,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> list[WeatherData]:
    plant_service = PlantService(db)
    plant = plant_service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    weather_service = WeatherService(db)
    weather_records = weather_service.fetch_and_store_weather(
        plant_id=plant_id,
        latitude=plant.latitude,
        longitude=plant.longitude,
        timezone=plant.timezone,
    )

    if start is not None or end is not None or limit is not None:
        return weather_service.list_weather(plant_id, start=start, end=end, limit=limit)

    return weather_records
