from app.db.repositories.plant_repository import PlantRepository
from app.db.models.plant import Plant
from app.schemas.plant import PlantCreate, PlantUpdate


class PlantService:
    def __init__(self, db):
        self.repository = PlantRepository(db)

    def list_plants(self) -> list[Plant]:
        return list(self.repository.list())

    def get_plant(self, plant_id: int) -> Plant | None:
        return self.repository.get_by_id(plant_id)

    def create_plant(self, plant_data: PlantCreate) -> Plant:
        return self.repository.create(plant_data)

    def update_plant(self, plant: Plant, plant_data: PlantUpdate) -> Plant:
        return self.repository.update(plant, plant_data)

    def delete_plant(self, plant: Plant) -> None:
        self.repository.delete(plant)
