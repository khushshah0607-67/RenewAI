from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.risk import PlantRiskResponse
from app.services.plant_service import PlantService
from app.services.risk.rule_based_risk_service import RuleBasedRiskService

router = APIRouter(prefix="/plants", tags=["risk"])


@router.get("/{plant_id}/risk", response_model=PlantRiskResponse)
def get_plant_risk(
    plant_id: int,
    db: Session = Depends(get_db),
) -> dict:
    plant_service = PlantService(db)
    plant = plant_service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    service = RuleBasedRiskService(db)
    return service.assess_plant_risk(plant)
