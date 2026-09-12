import json
import sys
from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.features.feature_engineering import build_prediction_feature_frame
from ml.uncertainty.residual_intervals import enforce_interval_constraints


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "solar_weather_xgb.joblib"
UNCERTAINTY_CALIBRATION_PATH = (
    PROJECT_ROOT / "data" / "processed" / "uncertainty_calibration.json"
)
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "test_inference_output.csv"

FORECAST_POINTS = 96


def predict_generation(plant_data, historical_data, weather_data):
    model_data = joblib.load(MODEL_PATH)

    if isinstance(model_data, dict):
        model = model_data["model"]
        saved_features = model_data.get("feature_columns")
        model_version = model_data.get(
            "model_version",
            "solar-weather-xgb-v1"
        )
    else:
        model = model_data
        saved_features = None
        model_version = "solar-weather-xgb-v1"

    uncertainty_calibration = {}
    if UNCERTAINTY_CALIBRATION_PATH.exists():
        uncertainty_calibration = json.loads(
            UNCERTAINTY_CALIBRATION_PATH.read_text(encoding="utf-8")
        )

    residual_q10 = float(uncertainty_calibration.get("residual_q10", 0.0))
    residual_q90 = float(uncertainty_calibration.get("residual_q90", 0.0))

    if isinstance(plant_data, dict):
        plant_id = plant_data.get("plant_id", "unknown")
        capacity_kw = plant_data.get("capacity_kw")
    else:
        plant_id = "unknown"
        capacity_kw = None

    history = historical_data.copy()
    weather = weather_data.copy()

    required_history = [
        "timestamp",
        "ac_power_kw"
    ]

    required_weather = [
        "timestamp",
        "ambient_temperature",
        "relative_humidity",
        "cloud_cover",
        "shortwave_radiation_w_m2",
        "irradiation",
        "wind_speed",
        "wind_direction"
    ]

    for column in required_history:
        if column not in history.columns:
            raise ValueError(f"Missing historical column: {column}")

    for column in required_weather:
        if column not in weather.columns:
            raise ValueError(f"Missing weather column: {column}")

    history["timestamp"] = pd.to_datetime(history["timestamp"])
    weather["timestamp"] = pd.to_datetime(weather["timestamp"])

    history = (
        history[required_history]
        .sort_values("timestamp")
        .drop_duplicates("timestamp")
    )

    weather = (
        weather[required_weather]
        .sort_values("timestamp")
        .drop_duplicates("timestamp")
    )

    history["ac_power_kw"] = pd.to_numeric(
        history["ac_power_kw"],
        errors="coerce"
    )

    history = history.dropna(subset=["ac_power_kw"])

    weather_columns = required_weather[1:]

    for column in weather_columns:
        weather[column] = pd.to_numeric(
            weather[column],
            errors="coerce"
        )

    weather = weather.set_index("timestamp")

    weather = weather.resample("15min").interpolate(
        method="time"
    )

    weather = weather.dropna()

    if len(weather) < FORECAST_POINTS:
        raise ValueError(
            f"Need at least {FORECAST_POINTS} future weather points, "
            f"but only {len(weather)} are available."
        )

    future_weather = weather.iloc[:FORECAST_POINTS].copy()

    if len(history) < 97:
        raise ValueError(
            "At least 97 historical generation rows are required "
            "for lag_96."
        )

    generation_history = history.set_index("timestamp")["ac_power_kw"].copy()

    predictions = []

    for timestamp, weather_row in future_weather.iterrows():

        values = generation_history.values

        current_power = values[-1]

        feature_row = {
            "ac_power_kw": current_power,

            "ambient_temperature": weather_row["ambient_temperature"],
            "relative_humidity": weather_row["relative_humidity"],
            "cloud_cover": weather_row["cloud_cover"],
            "shortwave_radiation_w_m2": weather_row[
                "shortwave_radiation_w_m2"
            ],
            "irradiation": weather_row["irradiation"],
            "wind_speed": weather_row["wind_speed"],
            "wind_direction": weather_row["wind_direction"],

            "hour": timestamp.hour,
            "minute": timestamp.minute,
            "day_of_week": timestamp.dayofweek,
            "day_of_year": timestamp.dayofyear,
            "month": timestamp.month,

            "hour_decimal": (
                timestamp.hour
                + timestamp.minute / 60
            ),

            "hour_sin": __import__("numpy").sin(
                2 * __import__("numpy").pi
                * (
                    timestamp.hour
                    + timestamp.minute / 60
                ) / 24
            ),

            "hour_cos": __import__("numpy").cos(
                2 * __import__("numpy").pi
                * (
                    timestamp.hour
                    + timestamp.minute / 60
                ) / 24
            ),

            "day_of_year_sin": __import__("numpy").sin(
                2 * __import__("numpy").pi
                * timestamp.dayofyear / 365
            ),

            "day_of_year_cos": __import__("numpy").cos(
                2 * __import__("numpy").pi
                * timestamp.dayofyear / 365
            ),

            "lag_1": values[-2],
            "lag_2": values[-3],
            "lag_4": values[-5],
            "lag_24": values[-25],
            "lag_96": values[-97],

            "rolling_mean_4": generation_history.iloc[-4:].mean(),
            "rolling_mean_12": generation_history.iloc[-12:].mean(),
            "rolling_mean_24": generation_history.iloc[-24:].mean(),
            "rolling_std_24": generation_history.iloc[-24:].std()
        }

        X = build_prediction_feature_frame(
            timestamp,
            weather_row,
            generation_history
        )

        if saved_features is not None:
            X = X[saved_features]

        if weather_row["shortwave_radiation_w_m2"] <= 1:
            prediction_kw = 0.0
            p10 = 0.0
            p50 = 0.0
            p90 = 0.0
        else:
            prediction_kw = float(model.predict(X)[0])
            prediction_kw = max(0, prediction_kw)

            p50 = prediction_kw
            p10 = p50 + residual_q10
            p90 = p50 + residual_q90

            interval_df = pd.DataFrame({
                "p10": [p10],
                "p50": [p50],
                "p90": [p90],
            })

            interval_df = enforce_interval_constraints(
                interval_df,
                capacity_kw=capacity_kw,
            )

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

        predictions.append({
            "plant_id": plant_id,
            "timestamp": timestamp.isoformat(),
            "p10": round(p10, 4),
            "p50": round(p50, 4),
            "p90": round(p90, 4),
            "model_version": model_version
        })

    return predictions


if __name__ == "__main__":

    print("Testing RenewAI inference function...\n")

    historical_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "solar_weather_merged.csv"
    )

    weather_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "openmeteo_forecast_weather.csv"
    )

    historical_data = pd.read_csv(historical_path)
    weather_data = pd.read_csv(weather_path)

    plant_data = {
        "plant_id": "solar_plant_1",
        "capacity_kw": 30000
    }

    results = predict_generation(
        plant_data,
        historical_data,
        weather_data
    )

    output_df = pd.DataFrame(results)

    output_df.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print(f"Forecast points generated: {len(output_df)}\n")

    print("First 5 predictions:")
    print(
        output_df[
            [
                "timestamp",
                "p10",
                "p50",
                "p90",
                "model_version"
            ]
        ].head()
    )

    print("\nLast 5 predictions:")
    print(
        output_df[
            [
                "timestamp",
                "p10",
                "p50",
                "p90",
                "model_version"
            ]
        ].tail()
    )

    print(
        f"\nPeak prediction: "
        f"{output_df['p50'].max():.2f} kW"
    )

    print(
        f"Total forecast energy: "
        f"{output_df['p50'].sum() * 0.25 / 1000:.2f} MWh"
    )

    print("\nInference test completed successfully.")

    print(
        f"Output saved to:\n"
        f"{OUTPUT_PATH.relative_to(PROJECT_ROOT)}"
    )