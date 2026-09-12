from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.financial import FinancialExposureResponse
from app.services.financial.estimated_exposure_service import EstimatedExposureService
from app.services.plant_service import PlantService

router = APIRouter(prefix="/plants", tags=["financial"])


@router.get("/{plant_id}/financial", response_model=FinancialExposureResponse)
def get_plant_financial_exposure(
    plant_id: int,
    db: Session = Depends(get_db),
) -> dict:
    plant_service = PlantService(db)
    plant = plant_service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    service = EstimatedExposureService(db)
    return service.estimate_exposure(plant)
