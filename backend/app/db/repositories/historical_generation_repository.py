from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.historical_generation import HistoricalGeneration

DEFAULT_QUERY_LIMIT = 1000
MAX_QUERY_LIMIT = 5000


class HistoricalGenerationRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _normalize_timestamp(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _resolve_limit(limit: int | None) -> int:
        if limit is None:
            return DEFAULT_QUERY_LIMIT
        return min(max(limit, 1), MAX_QUERY_LIMIT)

    def get_for_plant(
        self,
        plant_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[HistoricalGeneration]:
        stmt = select(HistoricalGeneration).where(HistoricalGeneration.plant_id == plant_id)

        if start is not None:
            stmt = stmt.where(HistoricalGeneration.timestamp >= self._normalize_timestamp(start))
        if end is not None:
            stmt = stmt.where(HistoricalGeneration.timestamp <= self._normalize_timestamp(end))

        stmt = stmt.order_by(HistoricalGeneration.timestamp.asc())
        stmt = stmt.offset(max(offset, 0)).limit(self._resolve_limit(limit))

        rows = list(self.db.scalars(stmt).all())
        for row in rows:
            row.timestamp = self._normalize_timestamp(row.timestamp)
        return rows

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
