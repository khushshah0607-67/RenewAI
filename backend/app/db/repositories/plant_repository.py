from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.plant import Plant
from app.schemas.plant import PlantCreate, PlantUpdate


class PlantRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> Sequence[Plant]:
        return self.db.scalars(select(Plant).order_by(Plant.id)).all()

    def get_by_id(self, plant_id: int) -> Plant | None:
        return self.db.get(Plant, plant_id)

    def create(self, plant_data: PlantCreate) -> Plant:
        plant = Plant(**plant_data.model_dump(mode="json"))
        self.db.add(plant)
        self.db.commit()
        self.db.refresh(plant)
        return plant

    def update(self, plant: Plant, plant_data: PlantUpdate) -> Plant:
        for field, value in plant_data.model_dump(exclude_unset=True, mode="json").items():
            setattr(plant, field, value)

        self.db.commit()
        self.db.refresh(plant)
        return plant

    def delete(self, plant: Plant) -> None:
        self.db.delete(plant)
        self.db.commit()
