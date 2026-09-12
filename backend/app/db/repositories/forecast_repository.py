from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.forecast import Forecast


class ForecastRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_plant(
        self,
        plant_id: int,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Forecast]:
        stmt = select(Forecast).where(Forecast.plant_id == plant_id)

        if start is not None:
            stmt = stmt.where(Forecast.forecast_timestamp >= start)
        if end is not None:
            stmt = stmt.where(Forecast.forecast_timestamp <= end)

        stmt = stmt.order_by(Forecast.forecast_timestamp.asc())
        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.db.scalars(stmt).all())

    def replace_for_plant(self, plant_id: int, records: list[Forecast]) -> None:
        self.db.execute(delete(Forecast).where(Forecast.plant_id == plant_id))
        if records:
            self.db.add_all(records)
        self.db.commit()

    def count_for_plant(self, plant_id: int) -> int:
        return self.db.query(Forecast).filter(Forecast.plant_id == plant_id).count()
