import pandas as pd
import numpy as np
import joblib

from xgboost import XGBRegressor
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

print("Dataset loaded successfully!")
print("Dataset shape:", solar.shape)

# Define the target column
target = "target_ac_power_kw"

# Define columns that should not be used as model features
excluded_columns = [
    "timestamp",
    target
]

# Select the model features
feature_columns = [
    column
    for column in solar.columns
    if column not in excluded_columns
]

# Create input features and target
X = solar[feature_columns]
y = solar[target]

# Calculate chronological split positions
train_end = int(len(solar) * 0.70)
validation_end = int(len(solar) * 0.85)

# Create chronological training data
X_train = X.iloc[:train_end]
y_train = y.iloc[:train_end]

# Create chronological validation data
X_validation = X.iloc[train_end:validation_end]
y_validation = y.iloc[train_end:validation_end]

# Create chronological test data
X_test = X.iloc[validation_end:]
y_test = y.iloc[validation_end:]

print("\nData split:")
print("Training samples:", len(X_train))
print("Validation samples:", len(X_validation))
print("Testing samples:", len(X_test))

print("\nTraining period:")
print(solar["timestamp"].iloc[0])
print("to")
print(solar["timestamp"].iloc[train_end - 1])

print("\nValidation period:")
print(solar["timestamp"].iloc[train_end])
print("to")
print(solar["timestamp"].iloc[validation_end - 1])

print("\nTesting period:")
print(solar["timestamp"].iloc[validation_end])
print("to")
print(solar["timestamp"].iloc[-1])

# Create the XGBoost model
print("\nTraining XGBoost model...")

model = XGBRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=6,
    min_child_weight=3,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1
)

# Train the model
model.fit(
    X_train,
    y_train,
    eval_set=[
        (X_validation, y_validation)
    ],
    verbose=False
)

print("XGBoost training completed!")

# Make predictions on the test data
predictions = model.predict(X_test)

# Prevent negative generation predictions
predictions = np.maximum(predictions, 0)

# Calculate MAE
mae = mean_absolute_error(
    y_test,
    predictions
)

# Calculate RMSE
rmse = np.sqrt(
    mean_squared_error(
        y_test,
        predictions
    )
)

# Estimate plant capacity from training data only
plant_capacity_kw = y_train.max()

# Calculate normalized RMSE
nrmse = (
    rmse / plant_capacity_kw
) * 100

# Display evaluation results
print("\nXGBoost test results:")

print("MAE:", round(mae, 2), "kW")
print("RMSE:", round(rmse, 2), "kW")
print("nRMSE:", round(nrmse, 2), "%")

# Show a few predictions versus actual values
comparison = pd.DataFrame({
    "timestamp": solar["timestamp"].iloc[validation_end:].values,
    "actual_ac_power_kw": y_test.values,
    "predicted_ac_power_kw": predictions
})

print("\nPrediction vs actual:")
print(comparison.head(10))

# Save the trained model
joblib.dump(
    model,
    model_path
)

print("\nModel saved successfully!")
print("Saved to:", model_path)

# Save the feature names used by the model
feature_info = pd.DataFrame({
    "feature": feature_columns
})

feature_info.to_csv(
    "data/processed/xgboost_feature_columns.csv",
    index=False
)

print("Feature list saved successfully!")

print("\nXGBoost training completed!")