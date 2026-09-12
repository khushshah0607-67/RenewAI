from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.historical_generation import HistoricalGeneration
from app.db.models.plant import Plant
from app.schemas.generation import GenerationUploadSummary, HistoricalGenerationResponse
from app.schemas.plant import PlantCreate, PlantResponse, PlantUpdate
from app.services.generation_service import GenerationService
from app.services.plant_service import PlantService

router = APIRouter(prefix="/plants", tags=["plants"])


def get_plant_service(db: Session = Depends(get_db)) -> PlantService:
    return PlantService(db)


@router.post("", response_model=PlantResponse, status_code=status.HTTP_201_CREATED)
def create_plant(
    plant_data: PlantCreate,
    service: PlantService = Depends(get_plant_service),
) -> Plant:
    return service.create_plant(plant_data)


@router.get("", response_model=list[PlantResponse])
def list_plants(service: PlantService = Depends(get_plant_service)) -> list[Plant]:
    return service.list_plants()


@router.get("/{plant_id}", response_model=PlantResponse)
def get_plant(
    plant_id: int,
    service: PlantService = Depends(get_plant_service),
) -> Plant:
    plant = service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    return plant


@router.patch("/{plant_id}", response_model=PlantResponse)
def update_plant(
    plant_id: int,
    plant_data: PlantUpdate,
    service: PlantService = Depends(get_plant_service),
) -> Plant:
    plant = service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    return service.update_plant(plant, plant_data)


@router.delete("/{plant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plant(
    plant_id: int,
    service: PlantService = Depends(get_plant_service),
) -> Response:
    plant = service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    service.delete_plant(plant)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{plant_id}/generation/upload",
    response_model=GenerationUploadSummary,
    status_code=status.HTTP_200_OK,
)
def upload_generation_csv(
    plant_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
) -> dict:
    service = PlantService(db)
    plant = service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    generation_service = GenerationService(db)
    summary = generation_service.upload_generation_csv(plant_id, file)
    return summary


@router.get("/{plant_id}/generation", response_model=list[HistoricalGenerationResponse])
def list_generation_records(
    plant_id: int,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> list[HistoricalGeneration]:
    service = PlantService(db)
    plant = service.get_plant(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")

    generation_service = GenerationService(db)
    return generation_service.list_generation(plant_id, start=start, end=end, limit=limit)
