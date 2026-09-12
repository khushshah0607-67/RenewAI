from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.forecast import Forecast

DEFAULT_QUERY_LIMIT = 1000
MAX_QUERY_LIMIT = 5000


class ForecastRepository:
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
    ) -> list[Forecast]:
        stmt = select(Forecast).where(Forecast.plant_id == plant_id)

        if start is not None:
            stmt = stmt.where(Forecast.forecast_timestamp >= self._normalize_timestamp(start))
        if end is not None:
            stmt = stmt.where(Forecast.forecast_timestamp <= self._normalize_timestamp(end))

        stmt = stmt.order_by(Forecast.forecast_timestamp.asc())
        stmt = stmt.offset(max(offset, 0)).limit(self._resolve_limit(limit))

        return list(self.db.scalars(stmt).all())

    def replace_for_plant(self, plant_id: int, records: list[Forecast]) -> None:
        self.db.execute(delete(Forecast).where(Forecast.plant_id == plant_id))
        if records:
            self.db.add_all(records)
        self.db.commit()

    def count_for_plant(self, plant_id: int) -> int:
        return self.db.query(Forecast).filter(Forecast.plant_id == plant_id).count()
