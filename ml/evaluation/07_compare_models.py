import pandas as pd
import numpy as np
import joblib

from sklearn.metrics import mean_absolute_error, mean_squared_error

# Set the input and model paths
input_path = "data/processed/solar_plant1_features.csv"
model_path = "ml/models/solar_xgb.joblib"

# Load the feature dataset
print("Loading feature dataset...")

solar = pd.read_csv(input_path)

# Convert timestamp to datetime
solar["timestamp"] = pd.to_datetime(solar["timestamp"])

# Sort the data chronologically
solar = solar.sort_values("timestamp").reset_index(drop=True)

print("Feature dataset loaded successfully!")

# Define the target column
target = "target_ac_power_kw"

# Define columns that should not be used as model features
excluded_columns = [
    "timestamp",
    target
]

# Select the same features used by the trained model
feature_columns = [
    column
    for column in solar.columns
    if column not in excluded_columns
]

# Create input features and target
X = solar[feature_columns]
y = solar[target]

# Create the same chronological split used during training
train_end = int(len(solar) * 0.70)
validation_end = int(len(solar) * 0.85)

# Select the test data
X_test = X.iloc[validation_end:]
y_test = y.iloc[validation_end:]

test_data = solar.iloc[validation_end:].copy()

# Load the trained XGBoost model
print("\nLoading trained XGBoost model...")

model = joblib.load(model_path)

print("XGBoost model loaded successfully!")

# Generate XGBoost predictions
xgb_predictions = model.predict(X_test)

# Prevent negative generation predictions
xgb_predictions = np.maximum(xgb_predictions, 0)

# Create persistence predictions
# Current generation is used to predict the next 15-minute generation
persistence_predictions = test_data["ac_power_kw"].values

# Calculate XGBoost MAE
xgb_mae = mean_absolute_error(
    y_test,
    xgb_predictions
)

# Calculate XGBoost RMSE
xgb_rmse = np.sqrt(
    mean_squared_error(
        y_test,
        xgb_predictions
    )
)

# Calculate Persistence MAE
persistence_mae = mean_absolute_error(
    y_test,
    persistence_predictions
)

# Calculate Persistence RMSE
persistence_rmse = np.sqrt(
    mean_squared_error(
        y_test,
        persistence_predictions
    )
)

# Estimate plant capacity from the training period
plant_capacity_kw = solar["ac_power_kw"].iloc[:train_end].max()

# Calculate normalized RMSE for XGBoost
xgb_nrmse = (
    xgb_rmse / plant_capacity_kw
) * 100

# Calculate normalized RMSE for Persistence
persistence_nrmse = (
    persistence_rmse / plant_capacity_kw
) * 100

# Calculate XGBoost improvement over Persistence
mae_improvement = (
    (persistence_mae - xgb_mae)
    / persistence_mae
) * 100

rmse_improvement = (
    (persistence_rmse - xgb_rmse)
    / persistence_rmse
) * 100

# Display the model comparison
print("\nModel comparison")
print("--------------------------------------------")

print(
    "Persistence MAE:",
    round(persistence_mae, 2),
    "kW"
)

print(
    "XGBoost MAE:",
    round(xgb_mae, 2),
    "kW"
)

print(
    "\nPersistence RMSE:",
    round(persistence_rmse, 2),
    "kW"
)

print(
    "XGBoost RMSE:",
    round(xgb_rmse, 2),
    "kW"
)

print(
    "\nPersistence nRMSE:",
    round(persistence_nrmse, 2),
    "%"
)

print(
    "XGBoost nRMSE:",
    round(xgb_nrmse, 2),
    "%"
)

print(
    "\nMAE improvement with XGBoost:",
    round(mae_improvement, 2),
    "%"
)

print(
    "RMSE improvement with XGBoost:",
    round(rmse_improvement, 2),
    "%"
)

# Create a comparison table
results = pd.DataFrame({
    "Model": [
        "Persistence",
        "XGBoost"
    ],
    "MAE_kW": [
        persistence_mae,
        xgb_mae
    ],
    "RMSE_kW": [
        persistence_rmse,
        xgb_rmse
    ],
    "nRMSE_percent": [
        persistence_nrmse,
        xgb_nrmse
    ]
})

# Save the comparison table
results.to_csv(
    "data/processed/model_comparison.csv",
    index=False
)

# Save actual and predicted values
predictions = pd.DataFrame({
    "timestamp": test_data["timestamp"].values,
    "actual_ac_power_kw": y_test.values,
    "persistence_prediction_kw": persistence_predictions,
    "xgb_prediction_kw": xgb_predictions
})

predictions.to_csv(
    "data/processed/test_predictions.csv",
    index=False
)

# Display a few prediction examples
print("\nPrediction examples:")

print(
    predictions.head(10).to_string(index=False)
)

print("\nResults saved successfully!")

print(
    "Saved: data/processed/model_comparison.csv"
)

print(
    "Saved: data/processed/test_predictions.csv"
)

print("\nModel comparison completed!")