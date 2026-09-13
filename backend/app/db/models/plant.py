from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Float, String
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.db.database import Base


class Plant(Base):
    __tablename__ = "plants"
    __table_args__ = (
        CheckConstraint("installed_capacity_mw > 0", name="ck_plants_installed_capacity_positive"),
        CheckConstraint("export_limit_mw IS NULL OR export_limit_mw > 0", name="ck_plants_export_limit_positive"),
        CheckConstraint(
            "export_limit_mw IS NULL OR export_limit_mw <= installed_capacity_mw",
            name="ck_plants_export_limit_within_capacity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plant_type: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
<<<<<<< Updated upstream
=======
    capacity_mw: Mapped[float] = mapped_column(Float, nullable=False)
>>>>>>> Stashed changes
    installed_capacity_mw: Mapped[float] = mapped_column(Float, nullable=False)
    export_limit_mw: Mapped[float | None] = mapped_column(Float, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    historical_generation: Mapped[list["HistoricalGeneration"]] = relationship(
        back_populates="plant",
        cascade="all, delete-orphan",
    )
    weather_data: Mapped[list["WeatherData"]] = relationship(
        back_populates="plant",
        cascade="all, delete-orphan",
    )
    forecasts: Mapped[list["Forecast"]] = relationship(
        back_populates="plant",
        cascade="all, delete-orphan",
    )

    @property
    def capacity_mw(self) -> float:
        return self.installed_capacity_mw

    @capacity_mw.setter
    def capacity_mw(self, value: float) -> None:
        self.installed_capacity_mw = value
