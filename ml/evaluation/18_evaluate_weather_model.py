from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


input_path = Path("data/processed/weather_xgb_predictions.csv")
output_path = Path("data/processed/weather_xgb_actual_vs_predicted.png")


df = pd.read_csv(input_path)

df["timestamp"] = pd.to_datetime(df["timestamp"])


plt.figure(figsize=(14, 6))

plt.plot(
    df["timestamp"],
    df["actual_generation_kw"],
    label="Actual Generation"
)

plt.plot(
    df["timestamp"],
    df["predicted_generation_kw"],
    label="Weather-Aware XGBoost"
)

plt.xlabel("Time")
plt.ylabel("Solar Generation (kW)")
plt.title("Actual vs Weather-Aware XGBoost Prediction")

plt.legend()
plt.xticks(rotation=45)

plt.tight_layout()

plt.savefig(output_path, dpi=150)

plt.show()

print("Evaluation plot created successfully.")
print(f"Saved to: {output_path}")