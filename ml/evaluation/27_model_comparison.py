import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.features.feature_engineering import MODEL_FEATURE_COLUMNS

FEATURE_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "solar_weather_features.csv"
PERSISTENCE_RESULTS_PATH = PROJECT_ROOT / "data" / "processed" / "persistence_baseline_results.csv"
MODEL_COMPARISON_OUTPUT = PROJECT_ROOT / "data" / "processed" / "model_comparison.csv"
HORIZON_OUTPUT = PROJECT_ROOT / "data" / "processed" / "horizon_evaluation.csv"
SUMMARY_OUTPUT = PROJECT_ROOT / "data" / "processed" / "model_evaluation_summary.txt"
LEAKAGE_AUDIT_PATH = PROJECT_ROOT / "data" / "processed" / "leakage_audit.json"
WEATHER_MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "solar_weather_xgb.joblib"
BASIC_MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "solar_xgb.joblib"
TARGET_COLUMN = "target_next_15min"


def load_feature_frame():
    df = pd.read_csv(FEATURE_DATA_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


PLANT_CAPACITY_KW = 30000.0


def safe_nrmse(rmse, plant_capacity_kw=PLANT_CAPACITY_KW):
    if pd.isna(plant_capacity_kw) or plant_capacity_kw <= 0:
        return np.nan
    return (rmse / plant_capacity_kw) * 100


def safe_nmae(mae, plant_capacity_kw=PLANT_CAPACITY_KW):
    if pd.isna(plant_capacity_kw) or plant_capacity_kw <= 0:
        return np.nan
    return (mae / plant_capacity_kw) * 100


def load_basic_model_predictions(test_df):
    basic_model_path = BASIC_MODEL_PATH
    if not basic_model_path.exists():
        return None

    try:
        model = joblib.load(basic_model_path)
    except Exception:
        return None

    if not hasattr(model, "predict"):
        return None

    if not hasattr(model, "feature_names_in_"):
        return None

    basic_feature_columns = list(model.feature_names_in_)
    missing_columns = [column for column in basic_feature_columns if column not in test_df.columns]

    if missing_columns:
        return None

    try:
        predictions = np.maximum(model.predict(test_df[basic_feature_columns]), 0)
        return pd.Series(predictions, name="prediction")
    except Exception:
        return None


def evaluate_predictions(actual, predicted, capacity_kw):
    actual = pd.to_numeric(actual, errors="coerce")
    predicted = pd.to_numeric(predicted, errors="coerce")

    aligned = pd.DataFrame({"actual": actual, "predicted": predicted}).dropna()
    if aligned.empty:
        raise ValueError("No valid predictions available for evaluation.")

    mae = mean_absolute_error(aligned["actual"], aligned["predicted"])
    rmse = np.sqrt(mean_squared_error(aligned["actual"], aligned["predicted"]))

    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "nrmse": float(safe_nrmse(rmse, capacity_kw)),
        "nmae": float(safe_nmae(mae, capacity_kw)),
    }


def model_metrics_df(df):
    test_df = df.copy()
    capacity_kw = max(1.0, float(test_df["ac_power_kw"].max()))

    results = []

    persistence_predictions = test_df["ac_power_kw"].shift(1).ffill()
    persistence_df = pd.DataFrame({
        "actual": test_df[TARGET_COLUMN],
        "predicted": persistence_predictions,
    }).dropna()

    persistence_metrics = evaluate_predictions(
        persistence_df["actual"],
        persistence_df["predicted"],
        capacity_kw,
    )

    results.append({
        "model": "Persistence",
        **persistence_metrics,
    })

    weather_model_payload = joblib.load(WEATHER_MODEL_PATH)
    if isinstance(weather_model_payload, dict):
        weather_model = weather_model_payload["model"]
        feature_columns = weather_model_payload.get("feature_columns", MODEL_FEATURE_COLUMNS)
    else:
        weather_model = weather_model_payload
        feature_columns = MODEL_FEATURE_COLUMNS

    weather_predictions = np.maximum(
        weather_model.predict(test_df[feature_columns]),
        0,
    )

    weather_metrics = evaluate_predictions(
        test_df[TARGET_COLUMN],
        weather_predictions,
        capacity_kw,
    )

    results.append({
        "model": "Weather_Aware_XGBoost",
        **weather_metrics,
    })

    basic_predictions = load_basic_model_predictions(test_df)
    if basic_predictions is not None:
        basic_metrics = evaluate_predictions(
            test_df[TARGET_COLUMN],
            basic_predictions,
            capacity_kw,
        )
        results.append({
            "model": "Basic_XGBoost",
            **basic_metrics,
        })

    comparison_df = pd.DataFrame(results)
    comparison_df = comparison_df.sort_values("mae", ascending=True)
    return comparison_df


def horizon_metrics_df(df):
    horizon_rows = []

    for horizon_name, start_hour, end_hour in [
        ("0_6h", 0, 6),
        ("6_12h", 6, 12),
        ("12_24h", 12, 24),
    ]:
        horizon_df = df.copy()
        horizon_df["hour"] = horizon_df["timestamp"].dt.hour
        horizon_df = horizon_df[(horizon_df["hour"] >= start_hour) & (horizon_df["hour"] < end_hour)].copy()

        if horizon_df.empty:
            horizon_rows.append({
                "horizon": horizon_name,
                "mae": np.nan,
                "rmse": np.nan,
                "nrmse": np.nan,
                "nmae": np.nan,
                "rows": 0,
                "note": "No valid test rows available for this horizon.",
            })
            continue

        weather_model_payload = joblib.load(WEATHER_MODEL_PATH)
        if isinstance(weather_model_payload, dict):
            weather_model = weather_model_payload["model"]
            feature_columns = weather_model_payload.get("feature_columns", MODEL_FEATURE_COLUMNS)
        else:
            weather_model = weather_model_payload
            feature_columns = MODEL_FEATURE_COLUMNS

        predictions = np.maximum(
            weather_model.predict(horizon_df[feature_columns]),
            0,
        )

        metrics = evaluate_predictions(
            horizon_df[TARGET_COLUMN],
            predictions,
            PLANT_CAPACITY_KW,
        )

        horizon_rows.append({
            "horizon": horizon_name,
            "mae": metrics["mae"],
            "rmse": metrics["rmse"],
            "nrmse": metrics["nrmse"],
            "nmae": metrics["nmae"],
            "rows": len(horizon_df),
            "note": "",
        })

    return pd.DataFrame(horizon_rows)


def load_leakage_report():
    if LEAKAGE_AUDIT_PATH.exists():
        return json.loads(LEAKAGE_AUDIT_PATH.read_text(encoding="utf-8"))
    return {"leakage_status": "UNKNOWN"}


def main():
    df = load_feature_frame()
    train_end = int(len(df) * 0.60)
    calibration_end = int(len(df) * 0.80)

    test_df = df.iloc[calibration_end:].copy()

    comparison_df = model_metrics_df(test_df)
    horizon_df = horizon_metrics_df(test_df)

    comparison_df.to_csv(MODEL_COMPARISON_OUTPUT, index=False)
    horizon_df.to_csv(HORIZON_OUTPUT, index=False)

    leakage_report = load_leakage_report()

    best_by_mae = comparison_df.loc[comparison_df["mae"].idxmin()]
    best_by_rmse = comparison_df.loc[comparison_df["rmse"].idxmin()]

    summary_lines = [
        "RenewAI model evaluation summary",
        "",
        f"Leakage audit status: {leakage_report.get('leakage_status', 'UNKNOWN')}",
        f"Best model by MAE: {best_by_mae['model']} ({best_by_mae['mae']:.2f} kW)",
        f"Best model by RMSE: {best_by_rmse['model']} ({best_by_rmse['rmse']:.2f} kW)",
        "",
        "Current weather-aware model performance:",
        (
            f"MAE: {comparison_df.loc[comparison_df['model']=='Weather_Aware_XGBoost', 'mae'].iloc[0]:.2f} kW, "
            f"RMSE: {comparison_df.loc[comparison_df['model']=='Weather_Aware_XGBoost', 'rmse'].iloc[0]:.2f} kW, "
            f"nRMSE: {comparison_df.loc[comparison_df['model']=='Weather_Aware_XGBoost', 'nrmse'].iloc[0]:.2f}%, "
            f"NMAE: {comparison_df.loc[comparison_df['model']=='Weather_Aware_XGBoost', 'nmae'].iloc[0]:.2f}%"
        ),
        "",
        "Horizon performance:",
    ]

    for _, row in horizon_df.iterrows():
        summary_lines.append(
            f"- {row['horizon']}: MAE={row['mae']:.2f} kW, RMSE={row['rmse']:.2f} kW, nRMSE={row['nrmse']:.2f}%, NMAE={row['nmae']:.2f}%"
        )

    summary_lines.extend([
        "",
        "Limitations:",
        "- The dataset spans only about 34 days, so the evaluation should be treated as a short-horizon prototype rather than production-grade evidence.",
        "- Persistence and weather-aware model metrics are compared on the same latest untouched test period where possible.",
        "- The basic XGBoost model is only included when a compatible saved artifact is available.",
    ])

    SUMMARY_OUTPUT.write_text("\n".join(summary_lines), encoding="utf-8")

    print("Model comparison CSV created:", MODEL_COMPARISON_OUTPUT)
    print("Horizon evaluation CSV created:", HORIZON_OUTPUT)
    print("Summary file created:", SUMMARY_OUTPUT)
    print("\nModel comparison table:")
    print(comparison_df.to_string(index=False))
    print("\nHorizon evaluation table:")
    print(horizon_df.to_string(index=False))


if __name__ == "__main__":
    main()
