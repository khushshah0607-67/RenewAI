from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.financial import FinancialExposureResponse
from app.services.financial.estimated_exposure_service import EstimatedExposureService, FinancialExposureConfig
from app.services.plant_service import PlantService

router = APIRouter(prefix="/plants", tags=["financial"])


@router.get("/{plant_id}/financial", response_model=FinancialExposureResponse)
def get_plant_financial_exposure(
    plant_id: int,
    price: float | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    plant_service = PlantService(db)
    plant = plant_service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    config = FinancialExposureConfig(price_inr_per_mwh=price) if price is not None else None
    service = EstimatedExposureService(db, config=config)
    return service.estimate_exposure(plant)
