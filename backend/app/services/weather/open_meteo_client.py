from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenMeteoClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.weather_provider_base_url.rstrip("/")
        self.timeout_seconds = self.settings.weather_provider_timeout_seconds

    def fetch_hourly_weather(
        self,
        latitude: float,
        longitude: float,
        timezone_name: str,
        start: datetime | None = None,
        end: datetime | None = None,
        forecast_days: int | None = None,
    ) -> list[dict]:
        normalized_timezone = timezone_name or "auto"
        if normalized_timezone not in {"auto"} and "/" not in normalized_timezone and normalized_timezone.upper() not in {"UTC", "GMT"}:
            normalized_timezone = "auto"

        effective_forecast_days = self.settings.weather_forecast_days if forecast_days is None else forecast_days

        params: dict[str, str | float | int] = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": normalized_timezone,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,cloud_cover,precipitation,shortwave_radiation",
            "forecast_days": effective_forecast_days,
        }

        if start is not None:
            params["start_date"] = start.date().isoformat()
        if end is not None:
            params["end_date"] = end.date().isoformat()

        url = f"{self.base_url}?{urlencode({key: str(value) for key, value in params.items()})}"
        logger.info("Open-Meteo request URL: %s", url)

        try:
            with urlopen(url, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                error_body = ""
            raise RuntimeError(
                f"Open-Meteo request failed: HTTP {exc.code} {exc.reason}. Response body: {error_body[:500]}"
            ) from exc
        except (URLError, ValueError) as exc:
            raise RuntimeError(f"Open-Meteo request failed: {exc}") from exc

        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])
        temperatures = hourly.get("temperature_2m", [])
        humidities = hourly.get("relative_humidity_2m", [])
        wind_speeds = hourly.get("wind_speed_10m", [])
        wind_directions = hourly.get("wind_direction_10m", [])
        cloud_cover = hourly.get("cloud_cover", [])
        precipitation = hourly.get("precipitation", [])
        radiation = hourly.get("shortwave_radiation", [])

        records: list[dict] = []
        for index, timestamp in enumerate(times):
            try:
                dt = datetime.fromisoformat(timestamp)
            except ValueError:
                continue

            utc_dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
            records.append(
                {
                    "timestamp": utc_dt,
                    "temperature_c": temperatures[index] if index < len(temperatures) else None,
                    "humidity_percent": humidities[index] if index < len(humidities) else None,
                    "wind_speed_mps": wind_speeds[index] if index < len(wind_speeds) else None,
                    "wind_direction_deg": wind_directions[index] if index < len(wind_directions) else None,
                    "cloud_cover_percent": cloud_cover[index] if index < len(cloud_cover) else None,
                    "precipitation_mm": precipitation[index] if index < len(precipitation) else None,
                    "radiation_w_m2": radiation[index] if index < len(radiation) else None,
                }
            )

        return records
