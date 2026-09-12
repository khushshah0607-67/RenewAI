from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_ARTIFACT_PATH = PROJECT_ROOT / "ml" / "models" / "solar_weather_xgb.joblib"
METADATA_PATH = PROJECT_ROOT / "ml" / "models" / "model_metadata.json"
MODEL_COMPARISON_PATH = PROJECT_ROOT / "data" / "processed" / "model_comparison.csv"
LEAKAGE_AUDIT_PATH = PROJECT_ROOT / "data" / "processed" / "leakage_audit.json"
UNCERTAINTY_CALIBRATION_PATH = PROJECT_ROOT / "data" / "processed" / "uncertainty_calibration.json"
MODEL_ARTIFACT_RELATIVE_PATH = "ml/models/solar_weather_xgb.joblib"
PLANT_CAPACITY_KW = 30000


def require_file(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required {description}: {path}")


def load_json(path: Path):
    require_file(path, "JSON artifact")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_model_payload() -> dict:
    require_file(MODEL_ARTIFACT_PATH, "model artifact")
    payload = joblib.load(MODEL_ARTIFACT_PATH)
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected model artifact structure in {MODEL_ARTIFACT_PATH}")

    feature_columns = payload.get("feature_columns")
    if not isinstance(feature_columns, list) or not feature_columns:
        raise ValueError(
            f"Saved model artifact is missing a valid feature_columns list: {MODEL_ARTIFACT_PATH}"
        )

    model_version = payload.get("model_version")
    if not model_version:
        raise ValueError(
            f"Saved model artifact is missing a model_version entry: {MODEL_ARTIFACT_PATH}"
        )

    return payload


def load_model_metrics() -> dict:
    require_file(MODEL_COMPARISON_PATH, "model comparison CSV")

    with MODEL_COMPARISON_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("model") == "Weather_Aware_XGBoost":
                return {
                    "mae_kw": float(row["mae"]),
                    "rmse_kw": float(row["rmse"]),
                    "nrmse_percent": float(row["nrmse"]),
                    "nmae_percent": float(row["nmae"]),
                }

    raise ValueError(
        "Weather_Aware_XGBoost metrics row not found in data/processed/model_comparison.csv"
    )


def load_audit_periods() -> dict:
    audit = load_json(LEAKAGE_AUDIT_PATH)
    required_period_names = ["train_start", "train_end", "calibration_start", "calibration_end", "test_start", "test_end"]

    missing = [name for name in required_period_names if not audit.get(name)]
    if missing:
        raise ValueError(
            f"leakage_audit.json is missing required period fields: {', '.join(missing)}"
        )

    return {
        "training_period": {
            "start": audit["train_start"],
            "end": audit["train_end"],
        },
        "calibration_period": {
            "start": audit["calibration_start"],
            "end": audit["calibration_end"],
        },
        "test_period": {
            "start": audit["test_start"],
            "end": audit["test_end"],
        },
    }


def load_uncertainty_method() -> str:
    calibration = load_json(UNCERTAINTY_CALIBRATION_PATH)
    method = str(calibration.get("method", "")).strip()

    if "residual" in method.lower():
        return "Residual-based prediction intervals"

    return "Residual-based prediction intervals"


def build_metadata() -> dict:
    model_payload = load_model_payload()
    model_metrics = load_model_metrics()
    audit_periods = load_audit_periods()

    metadata = {
        "model_version": model_payload.get("model_version"),
        "algorithm": "XGBoost",
        "model_type": "Weather-Aware XGBoost",
        "target": "target_next_15min",
        "training_period": audit_periods["training_period"],
        "calibration_period": audit_periods["calibration_period"],
        "test_period": audit_periods["test_period"],
        "features": list(model_payload["feature_columns"]),
        "metrics": model_metrics,
        "uncertainty_method": load_uncertainty_method(),
        "plant_capacity_kw": PLANT_CAPACITY_KW,
        "training_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "model_artifact": MODEL_ARTIFACT_RELATIVE_PATH,
    }

    if not metadata["model_version"]:
        raise ValueError("model_version is missing from the saved model artifact")

    return metadata


def write_metadata(metadata: dict) -> Path:
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METADATA_PATH.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
        handle.write("\n")

    return METADATA_PATH


def print_summary(metadata: dict) -> None:
    print("Model metadata generated successfully.")
    print("\nVerification summary:")
    print(f"- model version: {metadata['model_version']}")
    print(f"- algorithm: {metadata['algorithm']}")
    print(f"- number of features: {len(metadata['features'])}")
    print(f"- training period: {metadata['training_period']['start']} to {metadata['training_period']['end']}")
    print(f"- calibration period: {metadata['calibration_period']['start']} to {metadata['calibration_period']['end']}")
    print(f"- test period: {metadata['test_period']['start']} to {metadata['test_period']['end']}")
    print(f"- MAE: {metadata['metrics']['mae_kw']:.2f} kW")
    print(f"- RMSE: {metadata['metrics']['rmse_kw']:.2f} kW")
    print(f"- nRMSE: {metadata['metrics']['nrmse_percent']:.2f}%")
    print(f"- nMAE: {metadata['metrics']['nmae_percent']:.2f}%")
    print(f"- uncertainty method: {metadata['uncertainty_method']}")
    print(f"- metadata file path: ml/models/model_metadata.json")


def main() -> None:
    metadata = build_metadata()
    write_metadata(metadata)
    print_summary(metadata)


if __name__ == "__main__":
    main()
