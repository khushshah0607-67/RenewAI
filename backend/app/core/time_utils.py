from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo


def normalize_datetime_to_utc(value: datetime | str | Any, plant_timezone: str | None = None) -> datetime:
    if value is None:
        raise ValueError("Datetime value is required.")

    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("Datetime value is required.")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp '{value}'. Use ISO-8601 format.") from exc
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise ValueError(f"Unsupported datetime value: {type(value).__name__}")

    if parsed.tzinfo is None:
        if plant_timezone is None:
            raise ValueError("Naive timestamps require a plant timezone to interpret them as local time.")
        try:
            tzinfo = ZoneInfo(str(plant_timezone))
        except Exception as exc:  # pragma: no cover - invalid timezone path
            raise ValueError(f"Invalid plant timezone '{plant_timezone}'.") from exc
        parsed = parsed.replace(tzinfo=tzinfo)

    return parsed.astimezone(timezone.utc)
