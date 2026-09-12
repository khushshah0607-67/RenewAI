from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
    db: Session = Depends(get_db),
) -> list:
    plant_service = PlantService(db)
    if plant_service.get_plant(plant_id) is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    service = BaselineForecastService(db)
    return service.list_for_plant(plant_id)


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
