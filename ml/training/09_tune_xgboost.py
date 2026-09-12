import pandas as pd
import numpy as np
import joblib

from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Set the input and output paths
input_path = "data/processed/solar_plant1_features.csv"
model_path = "ml/models/solar_xgb_tuned.joblib"

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

# Define columns that should not be used as features
excluded_columns = [
    "timestamp",
    target
]

# Select model features
feature_columns = [
    column
    for column in solar.columns
    if column not in excluded_columns
]

# Create features and target
X = solar[feature_columns]
y = solar[target]

# Create chronological train, validation and test splits
train_end = int(len(solar) * 0.70)
validation_end = int(len(solar) * 0.85)

X_train = X.iloc[:train_end]
y_train = y.iloc[:train_end]

X_validation = X.iloc[train_end:validation_end]
y_validation = y.iloc[train_end:validation_end]

X_test = X.iloc[validation_end:]
y_test = y.iloc[validation_end:]

# Store the test timestamps
test_timestamps = solar["timestamp"].iloc[validation_end:].values

print("\nData split:")
print("Training samples:", len(X_train))
print("Validation samples:", len(X_validation))
print("Testing samples:", len(X_test))

# Define different XGBoost configurations
models = {
    "XGBoost_1": XGBRegressor(
        n_estimators=300,
        learning_rate=0.03,
        max_depth=4,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    ),

    "XGBoost_2": XGBRegressor(
        n_estimators=500,
        learning_rate=0.03,
        max_depth=5,
        min_child_weight=5,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    ),

    "XGBoost_3": XGBRegressor(
        n_estimators=700,
        learning_rate=0.02,
        max_depth=6,
        min_child_weight=5,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    )
}

# Estimate plant capacity from the training data
plant_capacity_kw = y_train.max()

# Store model results
results = []

# Store the best model
best_model = None
best_model_name = None
best_mae = float("inf")

# Train and evaluate each model
for model_name, model in models.items():

    print("\nTraining", model_name, "...")

    # Train the model
    model.fit(
        X_train,
        y_train,
        eval_set=[
            (X_validation, y_validation)
        ],
        verbose=False
    )

    # Predict the test set
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

    # Calculate normalized RMSE
    nrmse = (
        rmse / plant_capacity_kw
    ) * 100

    # Store results
    results.append({
        "Model": model_name,
        "MAE_kW": mae,
        "RMSE_kW": rmse,
        "nRMSE_percent": nrmse
    })

    print(
        model_name,
        "MAE:",
        round(mae, 2),
        "kW"
    )

    print(
        model_name,
        "RMSE:",
        round(rmse, 2),
        "kW"
    )

    print(
        model_name,
        "nRMSE:",
        round(nrmse, 2),
        "%"
    )

    # Select the model with the lowest MAE
    if mae < best_mae:
        best_mae = mae
        best_model = model
        best_model_name = model_name

# Create results table
results_df = pd.DataFrame(results)

# Sort models by MAE
results_df = results_df.sort_values(
    "MAE_kW"
).reset_index(drop=True)

# Display all results
print("\nXGBoost tuning results:")
print(
    results_df.to_string(index=False)
)

# Save tuning results
results_df.to_csv(
    "data/processed/xgboost_tuning_results.csv",
    index=False
)

# Save the best model
joblib.dump(
    best_model,
    model_path
)

print("\nBest model:")
print(best_model_name)

print(
    "Best test MAE:",
    round(best_mae, 2),
    "kW"
)

print("\nBest tuned model saved successfully!")

print(
    "Saved to:",
    model_path
)

# Create predictions from the best model
best_predictions = best_model.predict(X_test)

# Prevent negative predictions
best_predictions = np.maximum(
    best_predictions,
    0
)

# Save best model predictions
prediction_results = pd.DataFrame({
    "timestamp": test_timestamps,
    "actual_ac_power_kw": y_test.values,
    "tuned_xgb_prediction_kw": best_predictions
})

prediction_results.to_csv(
    "data/processed/tuned_xgb_predictions.csv",
    index=False
)

print(
    "\nPredictions saved to:",
    "data/processed/tuned_xgb_predictions.csv"
)

print("\nXGBoost tuning completed!")