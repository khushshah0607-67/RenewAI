from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.plant import Plant
from app.schemas.plant import PlantCreate, PlantUpdate

DEFAULT_QUERY_LIMIT = 100
MAX_QUERY_LIMIT = 1000


class PlantRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _resolve_limit(limit: int | None) -> int:
        if limit is None:
            return DEFAULT_QUERY_LIMIT
        return min(max(limit, 1), MAX_QUERY_LIMIT)

    def list(self, limit: int | None = None, offset: int = 0) -> Sequence[Plant]:
        stmt = select(Plant).order_by(Plant.id.asc())
        stmt = stmt.offset(max(offset, 0)).limit(self._resolve_limit(limit))
        return self.db.scalars(stmt).all()

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
