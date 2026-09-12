import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.metrics import mean_absolute_error, mean_squared_error

# Set the prediction file path
prediction_path = "data/processed/tuned_xgb_predictions.csv"

# Load the predictions
print("Loading tuned model predictions...")

data = pd.read_csv(prediction_path)

# Convert timestamp to datetime
data["timestamp"] = pd.to_datetime(
    data["timestamp"]
)

# Calculate MAE
mae = mean_absolute_error(
    data["actual_ac_power_kw"],
    data["tuned_xgb_prediction_kw"]
)

# Calculate RMSE
rmse = np.sqrt(
    mean_squared_error(
        data["actual_ac_power_kw"],
        data["tuned_xgb_prediction_kw"]
    )
)

# Display metrics
print("\nFinal tuned XGBoost evaluation:")
print("MAE:", round(mae, 2), "kW")
print("RMSE:", round(rmse, 2), "kW")

# Plot actual versus predicted generation
plt.figure(figsize=(14, 6))

plt.plot(
    data["timestamp"],
    data["actual_ac_power_kw"],
    label="Actual Generation"
)

plt.plot(
    data["timestamp"],
    data["tuned_xgb_prediction_kw"],
    label="XGBoost Prediction"
)

plt.title(
    "Actual vs Predicted Solar Generation"
)

plt.xlabel("Time")
plt.ylabel("AC Power (kW)")

plt.legend()

plt.xticks(rotation=45)

plt.tight_layout()

# Save the figure
output_path = (
    "data/processed/"
    "actual_vs_predicted_tuned_xgb.png"
)

plt.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print("\nEvaluation plot saved successfully!")
print("Saved to:", output_path)

print("\nTuned model evaluation completed!")