import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Set the path of the feature dataset
input_path = "data/processed/solar_plant1_features.csv"

# Load the feature dataset
print("Loading feature dataset...")

solar = pd.read_csv(input_path)

# Convert timestamp to datetime
solar["timestamp"] = pd.to_datetime(solar["timestamp"])

# Sort the data chronologically
solar = solar.sort_values("timestamp").reset_index(drop=True)

# Create persistence predictions
# The previous generation is used as the prediction
solar["persistence_prediction"] = solar["ac_power_kw"].shift(1)

# Remove the first row because it has no previous observation
solar = solar.dropna(
    subset=["persistence_prediction", "target_ac_power_kw"]
).copy()

# Calculate MAE
mae = mean_absolute_error(
    solar["target_ac_power_kw"],
    solar["persistence_prediction"]
)

# Calculate RMSE
rmse = np.sqrt(
    mean_squared_error(
        solar["target_ac_power_kw"],
        solar["persistence_prediction"]
    )
)

# Estimate plant capacity from observed maximum generation
plant_capacity_kw = solar["ac_power_kw"].max()

# Calculate normalized RMSE
nrmse = (
    rmse / plant_capacity_kw
) * 100

# Display results
print("\nPersistence baseline results:")

print("MAE:", round(mae, 2), "kW")
print("RMSE:", round(rmse, 2), "kW")
print("nRMSE:", round(nrmse, 2), "%")

print("\nEstimated plant capacity:")
print(round(plant_capacity_kw, 2), "kW")

# Display a few predictions versus actual values
comparison = solar[
    [
        "timestamp",
        "persistence_prediction",
        "target_ac_power_kw"
    ]
].head(10)

print("\nPrediction vs actual examples:")
print(comparison)

# Save baseline results
results = pd.DataFrame({
    "model": ["Persistence"],
    "MAE_kW": [mae],
    "RMSE_kW": [rmse],
    "nRMSE_percent": [nrmse]
})

results.to_csv(
    "data/processed/persistence_baseline_results.csv",
    index=False
)

print("\nBaseline results saved successfully!")

print("\nPersistence baseline completed!")