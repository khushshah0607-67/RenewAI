import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt

# Set the input and model paths
data_path = "data/processed/solar_plant1_features.csv"
model_path = "ml/models/solar_xgb_tuned.joblib"

# Load the dataset
print("Loading solar dataset...")

solar = pd.read_csv(data_path)

# Convert timestamp to datetime
solar["timestamp"] = pd.to_datetime(
    solar["timestamp"]
)

# Sort data chronologically
solar = solar.sort_values(
    "timestamp"
).reset_index(drop=True)

# Load the trained model
print("Loading trained XGBoost model...")

model = joblib.load(model_path)

print("Model loaded successfully!")

# Define model features
target = "target_ac_power_kw"

excluded_columns = [
    "timestamp",
    target
]

feature_columns = [
    column
    for column in solar.columns
    if column not in excluded_columns
]

# Select the latest available observation
latest_index = len(solar) - 1

latest_row = solar.iloc[
    latest_index
].copy()

# Store historical generation values
generation_history = list(
    solar["ac_power_kw"].values
)

# Store forecast results
forecast_results = []

# Number of 15-minute periods in 24 hours
forecast_steps = 96

# Start forecasting
print("\nStarting 24-hour forecast...")

for step in range(1, forecast_steps + 1):

    # Calculate the future timestamp
    future_timestamp = (
        latest_row["timestamp"]
        + pd.Timedelta(minutes=15 * step)
    )

    # Create a new row for future prediction
    future_row = latest_row.copy()

    # Update timestamp
    future_row["timestamp"] = future_timestamp

    # Create future time features
    future_row["hour"] = future_timestamp.hour

    future_row["day_of_week"] = (
        future_timestamp.dayofweek
    )

    future_row["day_of_year"] = (
        future_timestamp.dayofyear
    )

    future_row["month"] = (
        future_timestamp.month
    )

    # Create cyclical hour features
    future_row["hour_sin"] = np.sin(
        2 * np.pi * future_timestamp.hour / 24
    )

    future_row["hour_cos"] = np.cos(
        2 * np.pi * future_timestamp.hour / 24
    )

    # Create cyclical yearly features
    future_row["day_of_year_sin"] = np.sin(
        2 * np.pi *
        future_timestamp.dayofyear / 365
    )

    future_row["day_of_year_cos"] = np.cos(
        2 * np.pi *
        future_timestamp.dayofyear / 365
    )

    # Update lag features using generation history
    future_row["lag_1"] = generation_history[-1]

    future_row["lag_2"] = generation_history[-2]

    future_row["lag_4"] = generation_history[-4]

    future_row["lag_24"] = generation_history[-24]

    future_row["lag_96"] = generation_history[-96]

    # Update rolling features
    future_row["rolling_mean_4"] = np.mean(
        generation_history[-4:]
    )

    future_row["rolling_mean_12"] = np.mean(
        generation_history[-12:]
    )

    future_row["rolling_mean_24"] = np.mean(
        generation_history[-24:]
    )

    future_row["rolling_std_24"] = np.std(
        generation_history[-24:]
    )

    # Create model input
    model_input = pd.DataFrame(
        [future_row[feature_columns]]
    )

    # Generate prediction
    prediction = model.predict(
        model_input
    )[0]

    # Prevent negative generation
    prediction = max(
        float(prediction),
        0
    )

    # Add prediction to generation history
    generation_history.append(
        prediction
    )

    # Store forecast
    forecast_results.append({
        "timestamp": future_timestamp,
        "predicted_ac_power_kw": prediction
    })

# Convert forecast results to DataFrame
forecast = pd.DataFrame(
    forecast_results
)

# Save forecast
output_path = (
    "data/processed/"
    "solar_24h_forecast.csv"
)

forecast.to_csv(
    output_path,
    index=False
)

# Display forecast
print("\n24-hour forecast completed!")

print("\nFirst 10 forecast values:")

print(
    forecast.head(10).to_string(
        index=False
    )
)

print("\nTotal forecast points:")
print(len(forecast))

print("\nForecast saved to:")
print(output_path)

# Plot the 24-hour forecast
plt.figure(figsize=(14, 6))

plt.plot(
    forecast["timestamp"],
    forecast["predicted_ac_power_kw"],
    marker="o",
    markersize=2
)

plt.title(
    "24-Hour Solar Generation Forecast"
)

plt.xlabel("Time")

plt.ylabel(
    "Predicted AC Power (kW)"
)

plt.xticks(
    rotation=45
)

plt.tight_layout()

# Save forecast plot
plot_path = (
    "data/processed/"
    "solar_24h_forecast.png"
)

plt.savefig(
    plot_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print("\nForecast plot saved to:")
print(plot_path)

print("\n24-hour forecasting completed successfully!")