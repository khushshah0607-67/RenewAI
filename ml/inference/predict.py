import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.uncertainty.residual_intervals import enforce_interval_constraints

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATHS = [
    PROJECT_ROOT / "ml" / "models" / "renewai_generalized_xgb.joblib",
    PROJECT_ROOT / "ml" / "models" / "solar_weather_xgb.joblib",
]
UNCERTAINTY_CALIBRATION_PATH = (
    PROJECT_ROOT / "data" / "processed" / "uncertainty_calibration.json"
)
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "test_inference_output.csv"

FORECAST_POINTS = 96


def _load_model_payload():
    for model_path in MODEL_PATHS:
        if not model_path.exists():
            continue

        payload = joblib.load(model_path)
        if isinstance(payload, dict) and "model" in payload and payload.get("feature_columns"):
            return payload

    raise FileNotFoundError("No valid RenewAI model artifact was found under ml/models/.")


def _load_uncertainty_calibration() -> dict[str, float]:
    if not UNCERTAINTY_CALIBRATION_PATH.exists():
        return {"residual_q10": 0.0, "residual_q90": 0.0}

    try:
        calibration = json.loads(UNCERTAINTY_CALIBRATION_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"residual_q10": 0.0, "residual_q90": 0.0}

    return {
        "residual_q10": float(calibration.get("residual_q10", 0.0)),
        "residual_q90": float(calibration.get("residual_q90", 0.0)),
    }


def _prepare_history(historical_data):
    history = historical_data.copy()

    missing_history = [column for column in ["timestamp", "ac_power_kw"] if column not in history.columns]
    if missing_history:
        raise ValueError(f"Missing historical column(s): {', '.join(missing_history)}")

    history["timestamp"] = pd.to_datetime(history["timestamp"], errors="coerce")
    history["ac_power_kw"] = pd.to_numeric(history["ac_power_kw"], errors="coerce")
    history = history.dropna(subset=["timestamp", "ac_power_kw"]).sort_values("timestamp").drop_duplicates("timestamp")

    if len(history) < 97:
        raise ValueError("At least 97 historical generation rows are required for lag_96.")

    return history.reset_index(drop=True)


def _prepare_weather(weather_data):
    weather = weather_data.copy()

    required_weather = [
        "timestamp",
        "ambient_temperature",
        "relative_humidity",
        "cloud_cover",
        "shortwave_radiation_w_m2",
        "irradiation",
        "wind_speed",
        "wind_direction",
    ]

    missing_weather = [column for column in required_weather if column not in weather.columns]
    if missing_weather:
        raise ValueError(f"Missing weather column(s): {', '.join(missing_weather)}")

    weather["timestamp"] = pd.to_datetime(weather["timestamp"], errors="coerce")
    weather = weather.dropna(subset=["timestamp"]).sort_values("timestamp").drop_duplicates("timestamp")

    for column in required_weather[1:]:
        weather[column] = pd.to_numeric(weather[column], errors="coerce")

    weather = weather.set_index("timestamp").resample("15min").interpolate(method="time")
    weather = weather.dropna().reset_index()

    if len(weather) < FORECAST_POINTS:
        raise ValueError(
            f"Need at least {FORECAST_POINTS} future weather points, but only {len(weather)} are available."
        )

    return weather.iloc[:FORECAST_POINTS].copy()


def _build_feature_row(timestamp, weather_row, generation_history, capacity_kw, renewable_type_code):
    values = generation_history.to_numpy(dtype=float)
    current_power = float(values[-1])

    recent_values = generation_history.iloc[-24:]
    recent_values = recent_values.dropna()

    def safe_last(values_series, offset):
        if len(values_series) <= offset:
            return float(values_series.iloc[0]) if len(values_series) else current_power
        return float(values_series.iloc[-offset - 1])

    feature_row = {
        "ambient_temperature_c": float(weather_row.get("ambient_temperature", weather_row.get("ambient_temperature_c", np.nan))),
        "module_temperature_c": float(weather_row.get("module_temperature_c", weather_row.get("ambient_temperature", np.nan))),
        "irradiation_w_m2": float(weather_row.get("irradiation_w_m2", weather_row.get("irradiation", np.nan))),
        "direct_normal_irradiance_w_m2": float(
            weather_row.get(
                "direct_normal_irradiance_w_m2",
                weather_row.get("irradiation", weather_row.get("shortwave_radiation_w_m2", np.nan)),
            )
        ),
        "global_horizontal_irradiance_w_m2": float(
            weather_row.get(
                "global_horizontal_irradiance_w_m2",
                weather_row.get("shortwave_radiation_w_m2", weather_row.get("irradiation", np.nan)),
            )
        ),
        "pressure_hpa": float(weather_row.get("pressure_hpa", 1013.25)),
        "relative_humidity_pct": float(weather_row.get("relative_humidity_pct", weather_row.get("relative_humidity", np.nan))),
        "wind_speed_10m_mps": float(weather_row.get("wind_speed_10m_mps", weather_row.get("wind_speed", np.nan))),
        "wind_direction_10m_deg": float(weather_row.get("wind_direction_10m_deg", weather_row.get("wind_direction", np.nan))),
        "wind_speed_30m_mps": float(weather_row.get("wind_speed_30m_mps", weather_row.get("wind_speed", np.nan))),
        "wind_direction_30m_deg": float(weather_row.get("wind_direction_30m_deg", weather_row.get("wind_direction", np.nan))),
        "wind_speed_50m_mps": float(weather_row.get("wind_speed_50m_mps", weather_row.get("wind_speed", np.nan))),
        "wind_direction_50m_deg": float(weather_row.get("wind_direction_50m_deg", weather_row.get("wind_direction", np.nan))),
        "wind_speed_hub_mps": float(weather_row.get("wind_speed_hub_mps", weather_row.get("wind_speed", np.nan))),
        "wind_direction_hub_deg": float(weather_row.get("wind_direction_hub_deg", weather_row.get("wind_direction", np.nan))),
        "hour": int(timestamp.hour),
        "minute": int(timestamp.minute),
        "day_of_week": int(timestamp.dayofweek),
        "day_of_year": int(timestamp.dayofyear),
        "month": int(timestamp.month),
        "hour_decimal": float(timestamp.hour + timestamp.minute / 60),
        "hour_sin": float(np.sin(2 * np.pi * (timestamp.hour + timestamp.minute / 60) / 24)),
        "hour_cos": float(np.cos(2 * np.pi * (timestamp.hour + timestamp.minute / 60) / 24)),
        "day_of_year_sin": float(np.sin(2 * np.pi * timestamp.dayofyear / 365)),
        "day_of_year_cos": float(np.cos(2 * np.pi * timestamp.dayofyear / 365)),
        "lag_1": safe_last(generation_history, 1),
        "lag_2": safe_last(generation_history, 2),
        "lag_4": safe_last(generation_history, 4),
        "lag_8": safe_last(generation_history, 8),
        "lag_16": safe_last(generation_history, 16),
        "lag_96": safe_last(generation_history, 96),
        "rolling_mean_4": float(recent_values.tail(4).mean()) if not recent_values.empty else current_power,
        "rolling_mean_8": float(recent_values.tail(8).mean()) if not recent_values.empty else current_power,
        "rolling_mean_24": float(recent_values.tail(24).mean()) if not recent_values.empty else current_power,
        "rolling_std_24": float(recent_values.tail(24).std(ddof=0)) if len(recent_values) >= 2 else 0.0,
        "rolling_max_24": float(recent_values.tail(24).max()) if not recent_values.empty else current_power,
        "generation_kw": current_power,
        "installed_capacity_kw": float(capacity_kw) if capacity_kw is not None else np.nan,
        "normalized_generation": (current_power / float(capacity_kw)) if capacity_kw is not None else np.nan,
        "renewable_type_code": int(renewable_type_code),
    }

    return pd.DataFrame([feature_row])


def predict_generation(plant_data, historical_data, weather_data):
    payload = _load_model_payload()
    model = payload["model"]
    saved_features = payload.get("feature_columns", [])
    model_version = payload.get("model_version", "renewai-generalized-xgb-v1")

    uncertainty_calibration = _load_uncertainty_calibration()
    residual_q10 = float(uncertainty_calibration.get("residual_q10", 0.0))
    residual_q90 = float(uncertainty_calibration.get("residual_q90", 0.0))

    plant = plant_data.copy() if isinstance(plant_data, dict) else {}
    plant_id = str(plant.get("plant_id", "unknown"))
    capacity_kw = plant.get("capacity_kw")
    if capacity_kw is None:
        capacity_kw = plant.get("plant_capacity_kw")
    if capacity_kw is not None:
        capacity_kw = float(capacity_kw)

    renewable_type = plant.get("renewable_type", "solar")
    renewable_type_code = 1 if str(renewable_type).lower() == "wind" else 0

    history = _prepare_history(historical_data)
    weather = _prepare_weather(weather_data)

    generation_history = history.set_index("timestamp")["ac_power_kw"].copy()
    predictions = []

    for _, weather_row in weather.iterrows():
        timestamp = pd.Timestamp(weather_row["timestamp"])
        feature_df = _build_feature_row(
            timestamp,
            weather_row,
            generation_history,
            capacity_kw,
            renewable_type_code,
        )

        feature_df = feature_df[saved_features]

        shortwave_radiation = float(weather_row.get("shortwave_radiation_w_m2", np.nan))
        if np.isnan(shortwave_radiation) or shortwave_radiation <= 1:
            p10 = p50 = p90 = 0.0
        else:
            prediction_kw = float(model.predict(feature_df)[0])
            prediction_kw = max(0.0, min(prediction_kw, float(capacity_kw) if capacity_kw is not None else prediction_kw))
            p50 = prediction_kw
            p10 = p50 + residual_q10
            p90 = p50 + residual_q90

            interval_df = pd.DataFrame({"p10": [p10], "p50": [p50], "p90": [p90]})
            interval_df = enforce_interval_constraints(interval_df, capacity_kw=capacity_kw)
            p10 = float(interval_df.iloc[0]["p10"])
            p50 = float(interval_df.iloc[0]["p50"])
            p90 = float(interval_df.iloc[0]["p90"])

        if capacity_kw is not None:
            p10 = min(p10, float(capacity_kw))
            p50 = min(p50, float(capacity_kw))
            p90 = min(p90, float(capacity_kw))

        p10 = max(0.0, p10)
        p50 = max(0.0, p50)
        p90 = max(0.0, p90)

        generation_history.loc[timestamp] = p50

        predictions.append(
            {
                "plant_id": plant_id,
                "timestamp": timestamp.isoformat(),
                "p10": round(p10, 4),
                "p50": round(p50, 4),
                "p90": round(p90, 4),
                "model_version": model_version,
            }
        )

    return predictions


if __name__ == "__main__":
    print("Testing RenewAI inference function...\n")

    historical_path = PROJECT_ROOT / "data" / "processed" / "solar_weather_merged.csv"
    weather_path = PROJECT_ROOT / "data" / "processed" / "openmeteo_forecast_weather.csv"

    historical_data = pd.read_csv(historical_path)
    weather_data = pd.read_csv(weather_path)

    plant_data = {
        "plant_id": "solar_plant_1",
        "capacity_kw": 30000,
        "renewable_type": "solar",
    }

    results = predict_generation(plant_data, historical_data, weather_data)

    output_df = pd.DataFrame(results)
    output_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Forecast points generated: {len(output_df)}\n")
    print("First 5 predictions:")
    print(output_df[["timestamp", "p10", "p50", "p90", "model_version"]].head())
    print("\nLast 5 predictions:")
    print(output_df[["timestamp", "p10", "p50", "p90", "model_version"]].tail())
    print(f"\nPeak prediction: {output_df['p50'].max():.2f} kW")
    print(f"Total forecast energy: {output_df['p50'].sum() * 0.25 / 1000:.2f} MWh")
    print("\nInference test completed successfully.")
    print(f"Output saved to:\n{OUTPUT_PATH.relative_to(PROJECT_ROOT)}")