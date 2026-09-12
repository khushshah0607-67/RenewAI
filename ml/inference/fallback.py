from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_METADATA_PATH = PROJECT_ROOT / "ml" / "models" / "model_metadata.json"


class ContractError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def error_response(code: str, message: str) -> dict[str, Any]:
    return {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
    }


def load_model_metadata() -> dict[str, Any]:
    if not MODEL_METADATA_PATH.exists():
        raise ContractError(
            "MODEL_ERROR",
            f"Missing model metadata file: {MODEL_METADATA_PATH.relative_to(PROJECT_ROOT)}",
        )

    try:
        metadata = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(
            "MODEL_ERROR",
            f"Invalid model metadata JSON: {MODEL_METADATA_PATH.relative_to(PROJECT_ROOT)}",
        ) from exc

    if not isinstance(metadata, dict):
        raise ContractError(
            "MODEL_ERROR",
            f"Model metadata must be a JSON object: {MODEL_METADATA_PATH.relative_to(PROJECT_ROOT)}",
        )

    if not metadata.get("model_version"):
        raise ContractError(
            "MODEL_ERROR",
            f"Model metadata is missing model_version: {MODEL_METADATA_PATH.relative_to(PROJECT_ROOT)}",
        )

    return metadata


def coerce_dataframe(data: Any, name: str, allow_empty: bool = False) -> pd.DataFrame:
    if data is None:
        if allow_empty:
            return pd.DataFrame()
        raise ContractError("MISSING_DATA", f"{name} is required.")

    if isinstance(data, pd.DataFrame):
        df = data.copy()
    elif isinstance(data, list):
        df = pd.DataFrame(data)
    elif isinstance(data, dict):
        if "records" in data and isinstance(data["records"], list):
            df = pd.DataFrame(data["records"])
        else:
            df = pd.DataFrame([data])
    else:
        raise ContractError(
            "INVALID_INPUT",
            f"{name} must be a pandas DataFrame, list of dictionaries, or dictionary-like object.",
        )

    if df.empty and not allow_empty:
        raise ContractError("MISSING_DATA", f"{name} is empty; please provide at least one row.")

    return df


def validate_required_columns(df: pd.DataFrame, required_columns: list[str], name: str) -> None:
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ContractError(
            "MISSING_DATA",
            f"{name} is missing required columns: {', '.join(missing_columns)}",
        )


def validate_timestamp_columns(df: pd.DataFrame, name: str) -> pd.DataFrame:
    if "timestamp" not in df.columns:
        raise ContractError(
            "MISSING_DATA",
            f"{name} is missing required field: timestamp",
        )

    parsed = pd.to_datetime(df["timestamp"], errors="coerce")
    if parsed.isna().any():
        raise ContractError(
            "INVALID_INPUT",
            f"{name} contains invalid timestamp values.",
        )

    if parsed.duplicated().any():
        raise ContractError(
            "INVALID_INPUT",
            f"{name} contains duplicate timestamps.",
        )

    df = df.copy()
    df["timestamp"] = parsed
    return df.sort_values("timestamp").reset_index(drop=True)


def normalize_plant_data(plant_data: Any) -> dict[str, Any]:
    if not isinstance(plant_data, dict):
        raise ContractError(
            "INVALID_INPUT",
            "plant_data must be a dictionary containing plant_id and plant_capacity_kw.",
        )

    plant_id = plant_data.get("plant_id")
    if not plant_id:
        raise ContractError(
            "MISSING_DATA",
            "plant_data is missing required field: plant_id",
        )

    plant_capacity_kw = plant_data.get("plant_capacity_kw")
    if plant_capacity_kw is None:
        plant_capacity_kw = plant_data.get("capacity_kw")

    if plant_capacity_kw is None:
        raise ContractError(
            "MISSING_DATA",
            "plant_data is missing required field: plant_capacity_kw",
        )

    try:
        plant_capacity_kw = float(plant_capacity_kw)
    except (TypeError, ValueError) as exc:
        raise ContractError(
            "INVALID_INPUT",
            "plant_capacity_kw must be numeric.",
        ) from exc

    if plant_capacity_kw <= 0:
        raise ContractError(
            "INVALID_INPUT",
            "plant_capacity_kw must be greater than zero.",
        )

    return {
        "plant_id": str(plant_id),
        "plant_capacity_kw": plant_capacity_kw,
        "timezone": plant_data.get("timezone") or "UTC",
    }


def detect_large_timestamp_gaps(df: pd.DataFrame, gap_minutes: int = 720) -> tuple[bool, dict[str, Any]]:
    if df is None or df.empty:
        return False, {"max_gap_minutes": 0}

    sorted_df = df.sort_values("timestamp").reset_index(drop=True)
    diffs = sorted_df["timestamp"].diff().dropna()

    if diffs.empty:
        return False, {"max_gap_minutes": 0}

    max_gap = diffs.max()
    return bool(max_gap > pd.Timedelta(minutes=gap_minutes)), {
        "max_gap_minutes": int(max_gap.total_seconds() / 60),
    }


def sanitize_prediction(prediction: Any, plant_capacity_kw: float) -> float:
    if prediction is None or pd.isna(prediction):
        raise ContractError(
            "MODEL_ERROR",
            "Model returned a missing prediction value.",
        )

    try:
        prediction_value = float(prediction)
    except (TypeError, ValueError) as exc:
        raise ContractError(
            "MODEL_ERROR",
            "Model returned an invalid prediction value.",
        ) from exc

    if not math.isfinite(prediction_value):
        raise ContractError(
            "MODEL_ERROR",
            "Model returned an invalid prediction value.",
        )

    prediction_value = max(0.0, min(prediction_value, float(plant_capacity_kw)))
    return prediction_value


def build_persistence_fallback(
    plant_data: dict[str, Any],
    historical_data: Any,
    weather_data: Any,
    fallback_reason: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    plant = normalize_plant_data(plant_data)

    historical_df = coerce_dataframe(historical_data, "historical_data", allow_empty=False)
    validate_required_columns(historical_df, ["timestamp", "ac_power_kw"], "historical_data")
    historical_df = validate_timestamp_columns(historical_df, "historical_data")

    historical_df["ac_power_kw"] = pd.to_numeric(
        historical_df["ac_power_kw"], errors="coerce"
    )
    historical_df = historical_df.dropna(subset=["ac_power_kw"]).reset_index(drop=True)

    if historical_df.empty:
        raise ContractError(
            "MISSING_DATA",
            "Insufficient historical generation data for persistence fallback.",
        )

    latest_timestamp = historical_df["timestamp"].iloc[-1]
    latest_valid_generation = float(historical_df["ac_power_kw"].iloc[-1])

    forecast_points = 96
    if weather_data is not None:
        weather_df = coerce_dataframe(weather_data, "weather_data", allow_empty=True)
        if not weather_df.empty:
            forecast_points = max(96, len(weather_df))

    start_timestamp = latest_timestamp + pd.Timedelta(minutes=15)
    forecast = []

    for offset in range(forecast_points):
        point_timestamp = start_timestamp + pd.Timedelta(minutes=15 * offset)
        hour = point_timestamp.hour
        if 6 <= hour < 18:
            forecast_kw = latest_valid_generation
        else:
            forecast_kw = 0.0

        forecast_kw = min(max(float(forecast_kw), 0.0), float(plant["plant_capacity_kw"]))

        forecast.append(
            {
                "timestamp": point_timestamp.isoformat(),
                "forecast_kw": forecast_kw,
                "p10_kw": forecast_kw,
                "p50_kw": forecast_kw,
                "p90_kw": forecast_kw,
            }
        )

    payload = {
        "status": "fallback",
        "fallback_reason": fallback_reason,
        "fallback_method": "persistence",
        "model_version": metadata.get("model_version", "unknown"),
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
            "model_version": metadata.get("model_version", "unknown"),
        },
    }

    json.dumps(payload)
    return payload
