from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.explainability import ExplanationResponse
from app.services.explainability.prototype_explainability_service import PrototypeExplainabilityService
from app.services.plant_service import PlantService

router = APIRouter(prefix="/plants", tags=["explainability"])


@router.get("/{plant_id}/explanation", response_model=ExplanationResponse)
def get_plant_explanation(
    plant_id: int,
    db: Session = Depends(get_db),
) -> dict:
    plant_service = PlantService(db)
    plant = plant_service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    service = PrototypeExplainabilityService(db)
    try:
        return service.explain_plant(plant)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
