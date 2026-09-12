import pandas as pd
import numpy as np
import joblib
import shap
import matplotlib.pyplot as plt

# Set the input and model paths
input_path = "data/processed/solar_plant1_features.csv"
model_path = "ml/models/solar_xgb.joblib"

# Load the feature dataset
print("Loading feature dataset...")

solar = pd.read_csv(input_path)

# Convert timestamp to datetime
solar["timestamp"] = pd.to_datetime(
    solar["timestamp"]
)

# Sort the data chronologically
solar = solar.sort_values(
    "timestamp"
).reset_index(drop=True)

# Define the target column
target = "target_ac_power_kw"

# Define columns that should not be used as features
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

# Create feature data
X = solar[feature_columns]

# Use the final 15% of data for explanation
test_start = int(len(solar) * 0.85)

X_test = X.iloc[test_start:].copy()

# Load the trained XGBoost model
print("Loading trained XGBoost model...")

model = joblib.load(model_path)

print("Model loaded successfully!")

# Use a limited sample to keep SHAP fast
sample_size = min(500, len(X_test))

X_sample = X_test.iloc[:sample_size]

print(
    "\nCalculating SHAP values for",
    sample_size,
    "test samples..."
)

# Create the SHAP explainer
explainer = shap.TreeExplainer(model)

# Calculate SHAP values
shap_values = explainer.shap_values(
    X_sample
)

print("SHAP calculation completed!")

# Create the SHAP summary plot
plt.figure(figsize=(10, 7))

shap.summary_plot(
    shap_values,
    X_sample,
    show=False
)

plt.title(
    "SHAP Feature Importance for Solar Generation Forecast"
)

plt.tight_layout()

# Save the SHAP plot
output_path = "data/processed/shap_feature_importance.png"

plt.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print("\nSHAP plot saved successfully!")
print("Saved to:", output_path)

# Calculate average absolute SHAP importance
importance = np.abs(shap_values).mean(axis=0)

importance_df = pd.DataFrame({
    "feature": feature_columns,
    "mean_absolute_shap": importance
})

# Sort features by importance
importance_df = importance_df.sort_values(
    "mean_absolute_shap",
    ascending=False
).reset_index(drop=True)

# Display feature importance
print("\nTop features according to SHAP:")

print(
    importance_df.head(15).to_string(index=False)
)

# Save SHAP feature importance
importance_df.to_csv(
    "data/processed/shap_feature_importance.csv",
    index=False
)

print("\nSHAP feature importance saved successfully!")

print("\nSHAP explainability completed!")