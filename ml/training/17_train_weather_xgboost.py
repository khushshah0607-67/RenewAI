from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


input_path = Path("data/processed/solar_weather_features.csv")
model_path = Path("ml/models/solar_weather_xgb.joblib")
results_path = Path("data/processed/weather_xgb_results.csv")
predictions_path = Path("data/processed/weather_xgb_predictions.csv")


print("Loading weather-aware feature dataset...")

df = pd.read_csv(input_path)
df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values("timestamp").reset_index(drop=True)


# Chronological train/test split
split_index = int(len(df) * 0.8)

train = df.iloc[:split_index]
test = df.iloc[split_index:]


feature_columns = [
    "ac_power_kw",
    "ambient_temperature",
    "relative_humidity",
    "cloud_cover",
    "shortwave_radiation_w_m2",
    "irradiation",
    "wind_speed",
    "wind_direction",
    "hour",
    "minute",
    "day_of_week",
    "day_of_year",
    "month",
    "hour_decimal",
    "hour_sin",
    "hour_cos",
    "day_of_year_sin",
    "day_of_year_cos",
    "lag_1",
    "lag_2",
    "lag_4",
    "lag_24",
    "lag_96",
    "rolling_mean_4",
    "rolling_mean_12",
    "rolling_mean_24",
    "rolling_std_24"
]

target_column = "target_next_15min"


X_train = train[feature_columns]
y_train = train[target_column]

X_test = test[feature_columns]
y_test = test[target_column]


print(f"Training rows: {len(train)}")
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
        "feature_columns": feature_columns
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