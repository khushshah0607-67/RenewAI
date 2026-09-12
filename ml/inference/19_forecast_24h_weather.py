from pathlib import Path

import joblib
import numpy as np
import pandas as pd


model_path = Path("ml/models/solar_weather_xgb.joblib")
history_path = Path("data/processed/solar_weather_features.csv")
weather_path = Path("data/processed/openmeteo_forecast_weather.csv")

output_csv = Path("data/processed/solar_24h_weather_forecast.csv")
output_plot = Path("data/processed/solar_24h_weather_forecast.png")


print("Loading weather-aware XGBoost model...")

saved_model = joblib.load(model_path)

model = saved_model["model"]
feature_columns = saved_model["feature_columns"]


print(f"Model loaded successfully.")
print(f"Number of features: {len(feature_columns)}")


# Load historical generation
history = pd.read_csv(history_path)
history["timestamp"] = pd.to_datetime(history["timestamp"])

history = history.sort_values("timestamp").reset_index(drop=True)


# Load future weather
weather = pd.read_csv(weather_path)
weather["timestamp"] = pd.to_datetime(weather["timestamp"])

weather = weather.sort_values("timestamp")


# Convert hourly weather to 15-minute intervals
weather = (
    weather
    .set_index("timestamp")
    .resample("15min")
    .interpolate(method="time")
    .reset_index()
)


# Use the next 24 hours
future_weather = weather.iloc[:96].copy()

if len(future_weather) < 96:
    raise ValueError(
        "Less than 96 future weather points are available."
    )


print("\nFuture weather:")
print(f"Start: {future_weather['timestamp'].min()}")
print(f"End: {future_weather['timestamp'].max()}")
print(f"Points: {len(future_weather)}")


# Create average generation profile by time of day
history["hour"] = history["timestamp"].dt.hour
history["minute"] = history["timestamp"].dt.minute

generation_profile = (
    history
    .groupby(["hour", "minute"])["ac_power_kw"]
    .mean()
)


# Create initial 96-point history using the historical
# average generation profile.
state = []

for i in range(96):
    timestamp = future_weather.iloc[0]["timestamp"] - pd.Timedelta(
        minutes=15 * (96 - i)
    )

    key = (timestamp.hour, timestamp.minute)

    if key in generation_profile.index:
        value = generation_profile.loc[key]
    else:
        value = 0.0

    state.append(float(value))


predictions = []


for _, weather_row in future_weather.iterrows():

    timestamp = weather_row["timestamp"]

    # Historical/recursive generation features
    current_generation = state[-1]

    lag_1 = state[-1]
    lag_2 = state[-2]
    lag_4 = state[-4]
    lag_24 = state[-24]
    lag_96 = state[-96]

    rolling_mean_4 = np.mean(state[-4:])
    rolling_mean_12 = np.mean(state[-12:])
    rolling_mean_24 = np.mean(state[-24:])
    rolling_std_24 = np.std(state[-24:])

    hour = timestamp.hour
    minute = timestamp.minute

    day_of_week = timestamp.dayofweek
    day_of_year = timestamp.dayofyear
    month = timestamp.month

    hour_decimal = hour + minute / 60

    hour_sin = np.sin(
        2 * np.pi * hour_decimal / 24
    )

    hour_cos = np.cos(
        2 * np.pi * hour_decimal / 24
    )

    day_of_year_sin = np.sin(
        2 * np.pi * day_of_year / 365
    )

    day_of_year_cos = np.cos(
        2 * np.pi * day_of_year / 365
    )


    input_row = pd.DataFrame([{
        "ac_power_kw": current_generation,

        "ambient_temperature":
            weather_row["ambient_temperature"],

        "relative_humidity":
            weather_row["relative_humidity"],

        "cloud_cover":
            weather_row["cloud_cover"],

        "shortwave_radiation_w_m2":
            weather_row["shortwave_radiation_w_m2"],

        "irradiation":
            weather_row["irradiation"],

        "wind_speed":
            weather_row["wind_speed"],

        "wind_direction":
            weather_row["wind_direction"],

        "hour": hour,
        "minute": minute,
        "day_of_week": day_of_week,
        "day_of_year": day_of_year,
        "month": month,
        "hour_decimal": hour_decimal,

        "hour_sin": hour_sin,
        "hour_cos": hour_cos,

        "day_of_year_sin":
            day_of_year_sin,

        "day_of_year_cos":
            day_of_year_cos,

        "lag_1": lag_1,
        "lag_2": lag_2,
        "lag_4": lag_4,
        "lag_24": lag_24,
        "lag_96": lag_96,

        "rolling_mean_4":
            rolling_mean_4,

        "rolling_mean_12":
            rolling_mean_12,

        "rolling_mean_24":
            rolling_mean_24,

        "rolling_std_24":
            rolling_std_24
    }])


    # Ensure exact feature order
    input_row = input_row[feature_columns]


    prediction = model.predict(input_row)[0]

    # Solar generation cannot be negative
    prediction = max(0.0, float(prediction))


    predictions.append(prediction)

    # Add prediction to recursive state
    state.append(prediction)


forecast = pd.DataFrame({
    "timestamp": future_weather["timestamp"],
    "forecast_generation_kw": predictions,
    "ambient_temperature": future_weather["ambient_temperature"],
    "irradiation": future_weather["irradiation"],
    "cloud_cover": future_weather["cloud_cover"],
    "wind_speed": future_weather["wind_speed"]
})


forecast.to_csv(output_csv, index=False)


print("\n24-hour forecast generated successfully.")

print(f"Forecast points: {len(forecast)}")
print(f"Start: {forecast['timestamp'].min()}")
print(f"End: {forecast['timestamp'].max()}")

print(
    f"Peak forecast: "
    f"{forecast['forecast_generation_kw'].max():.2f} kW"
)

print(
    f"Average forecast: "
    f"{forecast['forecast_generation_kw'].mean():.2f} kW"
)

print(f"\nSaved forecast to:")
print(output_csv)


# Create forecast plot
import matplotlib.pyplot as plt

plt.figure(figsize=(14, 6))

plt.plot(
    forecast["timestamp"],
    forecast["forecast_generation_kw"],
    label="24-Hour Solar Forecast"
)

plt.xlabel("Time")
plt.ylabel("Forecast Generation (kW)")
plt.title("RenewAI 24-Hour Solar Generation Forecast")

plt.legend()
plt.xticks(rotation=45)

plt.tight_layout()

plt.savefig(output_plot, dpi=150)

plt.show()

print(f"\nForecast graph saved to:")
print(output_plot)