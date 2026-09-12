from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.recommendation import RecommendationResponse
from app.services.plant_service import PlantService
from app.services.recommendation.decision_support_service import DecisionSupportService

router = APIRouter(prefix="/plants", tags=["recommendation"])


@router.get("/{plant_id}/recommendation", response_model=RecommendationResponse)
def get_plant_recommendation(
    plant_id: int,
    db: Session = Depends(get_db),
) -> dict:
    plant_service = PlantService(db)
    plant = plant_service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    service = DecisionSupportService(db)
    return service.build_recommendations(plant)
