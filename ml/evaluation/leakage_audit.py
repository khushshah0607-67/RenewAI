import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.features.feature_engineering import MODEL_FEATURE_COLUMNS

FEATURE_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "solar_weather_features.csv"
MODEL_ARTIFACT_PATH = PROJECT_ROOT / "ml" / "models" / "solar_weather_xgb.joblib"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "leakage_audit.json"
TARGET_COLUMN = "target_next_15min"


def load_feature_dataset(path: Path = FEATURE_DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def load_model_inputs(path: Path = MODEL_ARTIFACT_PATH) -> List[str]:
    payload = joblib.load(path)

    if isinstance(payload, dict):
        return list(payload.get("feature_columns", MODEL_FEATURE_COLUMNS))

    return list(MODEL_FEATURE_COLUMNS)


def _split_frames(df: pd.DataFrame):
    train_end = int(len(df) * 0.60)
    calibration_end = int(len(df) * 0.80)

    train_df = df.iloc[:train_end].copy()
    calibration_df = df.iloc[train_end:calibration_end].copy()
    test_df = df.iloc[calibration_end:].copy()

    return train_df, calibration_df, test_df


def run_leakage_audit(
    feature_df: Optional[pd.DataFrame] = None,
    model_inputs: Optional[List[str]] = None,
) -> Dict[str, object]:
    if feature_df is None:
        feature_df = load_feature_dataset()

    if model_inputs is None:
        model_inputs = load_model_inputs()

    train_df, calibration_df, test_df = _split_frames(feature_df)

    train_start = train_df["timestamp"].iloc[0].isoformat()
    train_end = train_df["timestamp"].iloc[-1].isoformat()
    calibration_start = calibration_df["timestamp"].iloc[0].isoformat()
    calibration_end = calibration_df["timestamp"].iloc[-1].isoformat()
    test_start = test_df["timestamp"].iloc[0].isoformat()
    test_end = test_df["timestamp"].iloc[-1].isoformat()

    overlapping_timestamps = int(
        len(
            set(train_df["timestamp"])
            & set(calibration_df["timestamp"])
            & set(test_df["timestamp"])
        )
    )

    overlapping_timestamps = max(overlapping_timestamps, 0)

    target_in_features = TARGET_COLUMN in model_inputs

    future_feature_leakage = (
        target_in_features
        or any(
            column.startswith("lead_") or column.startswith("future_")
            for column in model_inputs
        )
    )

    split_order_valid = (
        train_df["timestamp"].iloc[-1] < calibration_df["timestamp"].iloc[0]
        and calibration_df["timestamp"].iloc[-1] < test_df["timestamp"].iloc[0]
        and overlapping_timestamps == 0
    )

    leakage_status = "PASS" if (
        split_order_valid
        and not future_feature_leakage
        and not target_in_features
        and overlapping_timestamps == 0
    ) else "FAIL"

    report = {
        "train_start": train_start,
        "train_end": train_end,
        "calibration_start": calibration_start,
        "calibration_end": calibration_end,
        "test_start": test_start,
        "test_end": test_end,
        "train_rows": int(len(train_df)),
        "calibration_rows": int(len(calibration_df)),
        "test_rows": int(len(test_df)),
        "overlapping_timestamps": overlapping_timestamps,
        "target_in_features": target_in_features,
        "future_feature_leakage": future_feature_leakage,
        "split_order_valid": split_order_valid,
        "leakage_status": leakage_status,
    }

    return report


def main():
    feature_df = load_feature_dataset()
    model_inputs = load_model_inputs()
    audit = run_leakage_audit(feature_df=feature_df, model_inputs=model_inputs)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print(json.dumps(audit, indent=2))
    print(f"\nLeakage audit saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
