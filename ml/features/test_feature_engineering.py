import sys
from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.features.feature_engineering import (
    MODEL_FEATURE_COLUMNS,
    create_weather_features,
)


ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "processed" / "solar_weather_merged.csv"
MODEL_PATH = ROOT / "ml" / "models" / "solar_weather_xgb.joblib"


def main():
    assert len(MODEL_FEATURE_COLUMNS) == 27, (
        f"Expected 27 model feature columns, got {len(MODEL_FEATURE_COLUMNS)}"
    )

    df = pd.read_csv(INPUT_PATH)
    engineered = create_weather_features(df)

    expected_columns = [
        "timestamp",
        "ac_power_kw",
        "target_next_15min",
        *MODEL_FEATURE_COLUMNS[1:],
    ]

    assert list(engineered.columns) == expected_columns, (
        "Feature dataset column order does not match the expected deterministic order."
    )

    missing = [column for column in MODEL_FEATURE_COLUMNS if column not in engineered.columns]
    assert not missing, f"Missing expected model features: {missing}"

    unexpected = [
        column for column in engineered.columns if column not in expected_columns
    ]
    assert not unexpected, f"Unexpected columns found: {unexpected}"

    saved_model = joblib.load(MODEL_PATH)
    saved_feature_columns = saved_model["feature_columns"]

    assert saved_feature_columns == MODEL_FEATURE_COLUMNS, (
        "Saved model feature order does not match MODEL_FEATURE_COLUMNS."
    )

    print("Feature engineering validation passed.")
    print(f"Model feature count: {len(MODEL_FEATURE_COLUMNS)}")
    print("Model feature order:")
    print(MODEL_FEATURE_COLUMNS)
    print(f"Engineered rows: {len(engineered)}")


if __name__ == "__main__":
    main()
