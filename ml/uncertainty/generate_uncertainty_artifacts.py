import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.features.feature_engineering import MODEL_FEATURE_COLUMNS
from ml.uncertainty.residual_intervals import (
    calculate_residual_quantiles,
    calculate_residuals,
    create_interval_predictions,
    enforce_interval_constraints,
    evaluate_interval_coverage,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURE_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "solar_weather_features.csv"
MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "solar_weather_xgb.joblib"
CALIBRATION_ARTIFACT_PATH = PROJECT_ROOT / "data" / "processed" / "uncertainty_calibration.json"
EVALUATION_JSON_PATH = PROJECT_ROOT / "data" / "processed" / "uncertainty_evaluation.json"
EVALUATION_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "uncertainty_evaluation.csv"
TARGET_COLUMN = "target_next_15min"
PLANT_CAPACITY_KW = 30000.0


def main():
    df = pd.read_csv(FEATURE_DATA_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    train_end = int(len(df) * 0.60)
    calibration_end = int(len(df) * 0.80)

    train_df = df.iloc[:train_end].copy()
    calibration_df = df.iloc[train_end:calibration_end].copy()
    test_df = df.iloc[calibration_end:].copy()

    model_payload = joblib.load(MODEL_PATH)
    if isinstance(model_payload, dict):
        model = model_payload["model"]
        feature_columns = model_payload.get("feature_columns", MODEL_FEATURE_COLUMNS)
        model_version = model_payload.get("model_version", "solar-weather-xgb-v1")
    else:
        model = model_payload
        feature_columns = MODEL_FEATURE_COLUMNS
        model_version = "solar-weather-xgb-v1"

    calibration_X = calibration_df[feature_columns]
    calibration_y = calibration_df[TARGET_COLUMN].astype(float)

    calibration_predictions = np.maximum(model.predict(calibration_X), 0)
    calibration_predictions = pd.Series(
        calibration_predictions,
        index=calibration_df.index,
    )

    residuals = calculate_residuals(
        calibration_y.reset_index(drop=True),
        calibration_predictions.reset_index(drop=True),
    )
    residual_quantiles = calculate_residual_quantiles(residuals)

    calibration_mae = mean_absolute_error(calibration_y, calibration_predictions)

    calibration_artifact = {
        "method": "residual_based",
        "model_version": model_version,
        "calibration_start": calibration_df["timestamp"].iloc[0].isoformat(),
        "calibration_end": calibration_df["timestamp"].iloc[-1].isoformat(),
        "calibration_rows": len(calibration_df),
        "residual_q10": residual_quantiles["q10"],
        "residual_q90": residual_quantiles["q90"],
        "residual_mean": residual_quantiles["residual_mean"],
        "residual_std": residual_quantiles["residual_std"],
        "calibration_mae": float(calibration_mae),
    }

    CALIBRATION_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALIBRATION_ARTIFACT_PATH.write_text(
        json.dumps(calibration_artifact, indent=2),
        encoding="utf-8",
    )

    test_X = test_df[feature_columns]
    test_actual = test_df[TARGET_COLUMN].astype(float)
    test_predictions = np.maximum(model.predict(test_X), 0)

    interval_df = create_interval_predictions(
        predictions=pd.Series(test_predictions),
        residual_q10=residual_quantiles["q10"],
        residual_q90=residual_quantiles["q90"],
    )

    interval_df = enforce_interval_constraints(
        interval_df,
        capacity_kw=PLANT_CAPACITY_KW,
    )

    evaluation_df = pd.DataFrame({
        "timestamp": test_df["timestamp"].reset_index(drop=True),
        "actual": test_actual.reset_index(drop=True),
        "p10": interval_df["p10"].reset_index(drop=True),
        "p50": interval_df["p50"].reset_index(drop=True),
        "p90": interval_df["p90"].reset_index(drop=True),
    })

    evaluation_df["inside_interval"] = (
        (evaluation_df["p10"] <= evaluation_df["actual"])
        & (evaluation_df["actual"] <= evaluation_df["p90"])
    )

    coverage = evaluate_interval_coverage(
        actual=evaluation_df["actual"],
        p10=evaluation_df["p10"],
        p90=evaluation_df["p90"],
    )

    evaluation_artifact = {
        "method": "residual_based",
        "model_version": model_version,
        "calibration_start": calibration_artifact["calibration_start"],
        "calibration_end": calibration_artifact["calibration_end"],
        "test_rows": coverage["test_rows"],
        "interval_coverage": coverage["interval_coverage"],
        "target_coverage": coverage["target_coverage"],
        "average_interval_width": coverage["average_interval_width"],
        "lower_violation_rate": coverage["lower_violation_rate"],
        "upper_violation_rate": coverage["upper_violation_rate"],
    }

    EVALUATION_JSON_PATH.write_text(
        json.dumps(evaluation_artifact, indent=2),
        encoding="utf-8",
    )

    evaluation_df.to_csv(EVALUATION_CSV_PATH, index=False)

    print("Uncertainty calibration artifact created:")
    print(CALIBRATION_ARTIFACT_PATH)
    print("\nUncertainty evaluation artifacts created:")
    print(EVALUATION_JSON_PATH)
    print(EVALUATION_CSV_PATH)
    print("\nCalibration summary:")
    print(json.dumps(calibration_artifact, indent=2))
    print("\nEvaluation summary:")
    print(json.dumps(evaluation_artifact, indent=2))


if __name__ == "__main__":
    main()
