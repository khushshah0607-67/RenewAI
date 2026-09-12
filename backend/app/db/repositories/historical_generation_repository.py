from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.models.historical_generation import HistoricalGeneration


class HistoricalGenerationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_plant(
        self,
        plant_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[HistoricalGeneration]:
        stmt = select(HistoricalGeneration).where(HistoricalGeneration.plant_id == plant_id)

        if start is not None:
            stmt = stmt.where(HistoricalGeneration.timestamp >= start)
        if end is not None:
            stmt = stmt.where(HistoricalGeneration.timestamp <= end)

        stmt = stmt.order_by(HistoricalGeneration.timestamp.asc())
        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.db.scalars(stmt).all())

    def get_existing_timestamps(self, plant_id: int) -> set[datetime]:
        stmt = select(HistoricalGeneration.timestamp).where(HistoricalGeneration.plant_id == plant_id)
        return {ts for ts in self.db.scalars(stmt).all()}

    def create_many(self, records: list[HistoricalGeneration]) -> None:
        if not records:
            return
        self.db.add_all(records)
        self.db.commit()

    def count_by_plant(self, plant_id: int) -> int:
        return self.db.query(HistoricalGeneration).filter(HistoricalGeneration.plant_id == plant_id).count()
