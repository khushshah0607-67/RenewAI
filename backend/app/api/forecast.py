from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.time_utils import normalize_datetime_to_utc
from app.db.database import get_db
from app.schemas.forecast import ForecastResponse
from app.services.forecasting.baseline_forecast_service import BaselineForecastService
from app.services.plant_service import PlantService

router = APIRouter(prefix="/plants", tags=["forecasting"])


def get_forecast_service(db: Session = Depends(get_db)) -> BaselineForecastService:
    return BaselineForecastService(db)


@router.get("/{plant_id}/forecast", response_model=list[ForecastResponse])
def get_plant_forecast(
    plant_id: int,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list:
    plant_service = PlantService(db)
    plant = plant_service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    try:
        normalized_start = normalize_datetime_to_utc(start, plant.timezone) if start is not None else None
        normalized_end = normalize_datetime_to_utc(end, plant.timezone) if end is not None else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = BaselineForecastService(db)
    return service.list_for_plant(
        plant_id,
        start=normalized_start,
        end=normalized_end,
        limit=limit,
        offset=offset,
    )


@router.post("/{plant_id}/forecast", response_model=list[ForecastResponse], status_code=201)
def generate_plant_forecast(
    plant_id: int,
    db: Session = Depends(get_db),
) -> list:
    plant_service = PlantService(db)
    if plant_service.get_plant(plant_id) is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    service = BaselineForecastService(db)
    return service.generate_for_plant(plant_id)
