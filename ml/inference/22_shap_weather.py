from pathlib import Path

import joblib
import pandas as pd
import matplotlib.pyplot as plt
import shap


model_path = Path(
    "ml/models/solar_weather_xgb.joblib"
)

data_path = Path(
    "data/processed/solar_weather_features.csv"
)

output_path = Path(
    "data/processed/shap_weather_feature_importance.png"
)


print("Loading weather-aware XGBoost model...")

model_data = joblib.load(model_path)


# Extract model from saved dictionary
if isinstance(model_data, dict):

    model = model_data["model"]

    saved_features = model_data.get(
        "features"
    )

else:

    model = model_data

    saved_features = None


data = pd.read_csv(data_path)


# Remove target and timestamp
X = data.drop(
    columns=[
        "target_next_15min",
        "timestamp"
    ],
    errors="ignore"
)


# Use the same feature order as training
if saved_features is not None:

    X = X[saved_features]


print(
    f"Features used for SHAP: {X.shape[1]}"
)

print("Calculating SHAP values...")


explainer = shap.TreeExplainer(model)

shap_values = explainer.shap_values(X)


# Generate feature importance plot
plt.figure()

shap.summary_plot(
    shap_values,
    X,
    plot_type="bar",
    show=False
)

plt.title(
    "RenewAI Weather-Aware Model Feature Importance"
)

plt.tight_layout()

plt.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight"
)

plt.close()


print("\nTop features:")


importance = pd.DataFrame({
    "feature": X.columns,
    "importance": abs(shap_values).mean(axis=0)
})


importance = importance.sort_values(
    "importance",
    ascending=False
)


print(
    importance.head(10).to_string(
        index=False
    )
)


print(
    "\nSHAP analysis completed successfully."
)

print(
    f"Plot saved to:\n{output_path}"
)