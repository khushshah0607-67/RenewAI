import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.features.feature_engineering import (
    MODEL_FEATURE_COLUMNS,
    create_weather_features,
)


input_path = Path("data/processed/solar_weather_features.csv")
model_path = Path("ml/models/solar_weather_xgb.joblib")
results_path = Path("data/processed/weather_xgb_results.csv")
predictions_path = Path("data/processed/weather_xgb_predictions.csv")


print("Loading weather-aware feature dataset...")

df = pd.read_csv(input_path)
df = create_weather_features(df)


# Chronological train/calibration/test split
train_end = int(len(df) * 0.6)
calibration_end = int(len(df) * 0.8)

train = df.iloc[:train_end]
calibration = df.iloc[train_end:calibration_end]
test = df.iloc[calibration_end:]


feature_columns = MODEL_FEATURE_COLUMNS

target_column = "target_next_15min"


X_train = train[feature_columns]
y_train = train[target_column]

X_test = test[feature_columns]
y_test = test[target_column]


print(f"Training rows: {len(train)}")
print(f"Calibration rows: {len(calibration)}")
print(f"Testing rows: {len(test)}")
print(f"Number of features: {len(feature_columns)}")


# Train XGBoost
model = XGBRegressor(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1
)


print("\nTraining weather-aware XGBoost...")

model.fit(X_train, y_train)


# Predictions
predictions = model.predict(X_test)

# Solar generation cannot be negative
predictions = np.maximum(predictions, 0)


# Evaluation
mae = mean_absolute_error(y_test, predictions)

rmse = np.sqrt(
    mean_squared_error(y_test, predictions)
)

plant_capacity = df["ac_power_kw"].max()

nrmse = (rmse / plant_capacity) * 100


print("\nWeather-aware XGBoost Results")
print("--------------------------------")
print(f"MAE   : {mae:.2f} kW")
print(f"RMSE  : {rmse:.2f} kW")
print(f"nRMSE : {nrmse:.2f}%")


# Save model
model_path.parent.mkdir(parents=True, exist_ok=True)

joblib.dump(
    {
        "model": model,
        "feature_columns": feature_columns,
        "model_version": "solar-weather-xgb-v1"
    },
    model_path
)


# Save predictions
prediction_df = pd.DataFrame({
    "timestamp": test["timestamp"].values,
    "actual_generation_kw": y_test.values,
    "predicted_generation_kw": predictions
})

prediction_df.to_csv(
    predictions_path,
    index=False
)


# Save results
results = pd.DataFrame([
    {
        "model": "Weather_Aware_XGBoost",
        "MAE_kW": mae,
        "RMSE_kW": rmse,
        "nRMSE_percent": nrmse
    }
])

results.to_csv(
    results_path,
    index=False
)


print(f"\nModel saved to:")
print(model_path)

print(f"\nPredictions saved to:")
print(predictions_path)

print(f"\nResults saved to:")
print(results_path)

print("\nTraining completed successfully.")