from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.db.database import Base


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plant_type: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    capacity_mw: Mapped[float] = mapped_column(Float, nullable=False)
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
