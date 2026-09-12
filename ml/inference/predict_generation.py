from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.inference.fallback import (
    ContractError,
    build_persistence_fallback,
    coerce_dataframe,
    detect_large_timestamp_gaps,
    error_response,
    load_model_metadata,
    normalize_plant_data,
    sanitize_prediction,
    validate_required_columns,
    validate_timestamp_columns,
)
from ml.inference.predict import predict_generation as _legacy_predict_generation

REQUIRED_HISTORICAL_COLUMNS = ["timestamp", "ac_power_kw"]
REQUIRED_WEATHER_COLUMNS = [
    "timestamp",
    "ambient_temperature",
    "relative_humidity",
    "cloud_cover",
    "shortwave_radiation_w_m2",
    "irradiation",
    "wind_speed",
    "wind_direction",
]


def _prepare_historical_data(historical_data: Any) -> pd.DataFrame:
    historical_df = coerce_dataframe(historical_data, "historical_data")
    validate_required_columns(historical_df, REQUIRED_HISTORICAL_COLUMNS, "historical_data")
    historical_df = validate_timestamp_columns(historical_df, "historical_data")

    historical_df["ac_power_kw"] = pd.to_numeric(
        historical_df["ac_power_kw"],
        errors="coerce",
    )
    historical_df = historical_df.dropna(subset=["ac_power_kw"]).reset_index(drop=True)

    if historical_df.empty:
        raise ContractError(
            "MISSING_DATA",
            "historical_data does not contain any valid ac_power_kw values.",
        )

    return historical_df


def _prepare_weather_data(weather_data: Any) -> pd.DataFrame | None:
    if weather_data is None:
        return None

    weather_df = coerce_dataframe(weather_data, "weather_data", allow_empty=True)
    if weather_df.empty:
        return None

    validate_required_columns(weather_df, REQUIRED_WEATHER_COLUMNS, "weather_data")
    weather_df = validate_timestamp_columns(weather_df, "weather_data")

    for column in REQUIRED_WEATHER_COLUMNS[1:]:
        weather_df[column] = pd.to_numeric(weather_df[column], errors="coerce")

    if weather_df[REQUIRED_WEATHER_COLUMNS[1:]].isna().any().any():
        raise ContractError(
            "INVALID_INPUT",
            "weather_data contains invalid numeric values for required weather fields.",
        )

    return weather_df


def _build_success_response(
    metadata: dict[str, Any],
    plant: dict[str, Any],
    forecast: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "status": "success",
        "model_version": metadata["model_version"],
        "plant_id": plant["plant_id"],
        "forecast": forecast,
        "metadata": {
            "forecast_horizon_hours": round((len(forecast) * 15) / 60, 2),
            "interval_minutes": 15,
            "unit": "kW",
            "timezone": plant["timezone"],
            "uncertainty_method": metadata.get(
                "uncertainty_method",
                "Residual-based prediction intervals",
            ),
            "model_version": metadata["model_version"],
        },
    }

    json.dumps(payload)
    return payload


def predict_generation(plant_data, historical_data, weather_data):
    """Stable backend-friendly ML prediction interface.

    Returns structured success, fallback, or error responses. The normal success
    response preserves the Step 29 contract, while incomplete weather input or
    irregular timestamps can trigger a clear persistence fallback when it is safe.
    """
    try:
        metadata = load_model_metadata()
        plant = normalize_plant_data(plant_data)

        historical_df = _prepare_historical_data(historical_data)

        if len(historical_df) < 97:
            raise ContractError(
                "MISSING_DATA",
                "Insufficient historical generation data for lag_96 feature generation.",
            )

        weather_df = _prepare_weather_data(weather_data)

        if weather_df is None or weather_df.empty:
            return build_persistence_fallback(
                plant_data,
                historical_df,
                weather_data,
                "WEATHER_UNAVAILABLE",
                metadata,
            )

        has_large_weather_gap, _ = detect_large_timestamp_gaps(weather_df, gap_minutes=720)
        if has_large_weather_gap:
            return build_persistence_fallback(
                plant_data,
                historical_df,
                weather_data,
                "LARGE_TIMESTAMP_GAPS",
                metadata,
            )

        legacy_plant_data = {
            "plant_id": plant["plant_id"],
            "capacity_kw": plant["plant_capacity_kw"],
        }

        raw_results = _legacy_predict_generation(
            legacy_plant_data,
            historical_df,
            weather_df,
        )

        if not isinstance(raw_results, list) or not raw_results:
            raise ContractError(
                "MODEL_ERROR",
                "The existing inference pipeline returned no forecast results.",
            )

        forecast = []
        for row in raw_results:
            if not isinstance(row, dict):
                raise ContractError(
                    "MODEL_ERROR",
                    "The existing inference pipeline returned invalid forecast rows.",
                )

            if not {"timestamp", "p10", "p50", "p90"}.issubset(row.keys()):
                raise ContractError(
                    "MODEL_ERROR",
                    "The existing inference pipeline returned incomplete forecast rows.",
                )

            p10 = sanitize_prediction(row["p10"], plant["plant_capacity_kw"])
            p50 = sanitize_prediction(row["p50"], plant["plant_capacity_kw"])
            p90 = sanitize_prediction(row["p90"], plant["plant_capacity_kw"])

            if p10 > p50:
                p10 = p50
            if p90 < p50:
                p90 = p50

            forecast.append(
                {
                    "timestamp": pd.to_datetime(row["timestamp"]).isoformat(),
                    "forecast_kw": float(p50),
                    "p10_kw": float(p10),
                    "p50_kw": float(p50),
                    "p90_kw": float(p90),
                }
            )

        return _build_success_response(metadata, plant, forecast)

    except ContractError as exc:
        return error_response(exc.code, exc.message)
    except Exception:
        return error_response(
            "MODEL_ERROR",
            "The ML prediction pipeline failed unexpectedly.",
        )


if __name__ == "__main__":
    print("Loading example inputs from processed data...")

    historical_data = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "solar_weather_merged.csv")
    weather_data = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "openmeteo_forecast_weather.csv")

    plant_data = {
        "plant_id": "solar_plant_1",
        "plant_capacity_kw": 30000,
        "timezone": "UTC",
    }

    result = predict_generation(plant_data, historical_data, weather_data)
    print(json.dumps(result, indent=2))
