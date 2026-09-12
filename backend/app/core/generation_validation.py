from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone


class GenerationDataContract:
    MINUTES_PER_STEP = 15

    def __init__(self, installed_capacity_mw: float):
        if installed_capacity_mw <= 0:
            raise ValueError("installed_capacity_mw must be greater than zero.")
        self.installed_capacity_mw = float(installed_capacity_mw)

    @staticmethod
    def detect_resolution(timestamps: Iterable[datetime]) -> str:
        values = sorted({ts.astimezone(timezone.utc) for ts in timestamps if ts is not None})
        if len(values) < 2:
            return "unknown"

        deltas = [
            (current - previous).total_seconds() / 60.0
            for previous, current in zip(values, values[1:])
        ]
        unique_deltas = sorted(set(round(delta, 6) for delta in deltas if delta > 0))
        if not unique_deltas:
            return "unknown"
        if unique_deltas == [15.0]:
            return "15min"
        if unique_deltas == [60.0]:
            return "60min"
        return "irregular"

    @staticmethod
    def has_gap(timestamps: Iterable[datetime]) -> bool:
        values = sorted({ts.astimezone(timezone.utc) for ts in timestamps if ts is not None})
        if len(values) < 2:
            return False
        return any((current - previous) > timedelta(minutes=15) for previous, current in zip(values, values[1:]))

    @staticmethod
    def sort_records(records: Iterable[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
        return sorted(
            records,
            key=lambda item: item[0].astimezone(timezone.utc),
        )

    def validate_generation_row(self, timestamp: datetime, generation_mw: float) -> float:
        if generation_mw < 0:
            raise ValueError("generation_mw must be non-negative.")
        if generation_mw > self.installed_capacity_mw:
            raise ValueError(
                f"generation_mw {generation_mw} exceeds installed capacity {self.installed_capacity_mw} MW. "
                "Rejecting physically impossible generation value."
            )
        if timestamp.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware.")
        return float(generation_mw)

    @staticmethod
    def normalize_to_utc_timestamp(timestamp: datetime, plant_timezone: str | None = None) -> datetime:
        from app.core.time_utils import normalize_datetime_to_utc

        return normalize_datetime_to_utc(timestamp, plant_timezone)
