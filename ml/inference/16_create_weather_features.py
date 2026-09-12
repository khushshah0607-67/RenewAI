from pathlib import Path

import numpy as np
import pandas as pd


input_path = Path("data/processed/solar_weather_merged.csv")
output_path = Path("data/processed/solar_weather_features.csv")


print("Loading merged dataset...")

df = pd.read_csv(input_path)
df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values("timestamp").reset_index(drop=True)


# Use Open-Meteo weather values
df["ambient_temperature"] = df["ambient_temperature_y"]
df["irradiation"] = df["irradiation_y"]


# Time features
df["hour"] = df["timestamp"].dt.hour
df["minute"] = df["timestamp"].dt.minute
df["day_of_week"] = df["timestamp"].dt.dayofweek
df["day_of_year"] = df["timestamp"].dt.dayofyear
df["month"] = df["timestamp"].dt.month


# Convert time to decimal hour
df["hour_decimal"] = df["hour"] + df["minute"] / 60


# Cyclical time features
df["hour_sin"] = np.sin(2 * np.pi * df["hour_decimal"] / 24)
df["hour_cos"] = np.cos(2 * np.pi * df["hour_decimal"] / 24)

df["day_of_year_sin"] = np.sin(
    2 * np.pi * df["day_of_year"] / 365
)

df["day_of_year_cos"] = np.cos(
    2 * np.pi * df["day_of_year"] / 365
)


# Historical generation features
df["lag_1"] = df["ac_power_kw"].shift(1)
df["lag_2"] = df["ac_power_kw"].shift(2)
df["lag_4"] = df["ac_power_kw"].shift(4)
df["lag_24"] = df["ac_power_kw"].shift(24)
df["lag_96"] = df["ac_power_kw"].shift(96)


# Rolling generation features
df["rolling_mean_4"] = (
    df["ac_power_kw"]
    .shift(1)
    .rolling(4)
    .mean()
)

df["rolling_mean_12"] = (
    df["ac_power_kw"]
    .shift(1)
    .rolling(12)
    .mean()
)

df["rolling_mean_24"] = (
    df["ac_power_kw"]
    .shift(1)
    .rolling(24)
    .mean()
)

df["rolling_std_24"] = (
    df["ac_power_kw"]
    .shift(1)
    .rolling(24)
    .std()
)


# Future target: next 15-minute generation
df["target_next_15min"] = df["ac_power_kw"].shift(-1)


# Keep only useful columns
feature_columns = [
    "timestamp",
    "ac_power_kw",
    "target_next_15min",

    "ambient_temperature",
    "relative_humidity",
    "cloud_cover",
    "shortwave_radiation_w_m2",
    "irradiation",
    "wind_speed",
    "wind_direction",

    "hour",
    "minute",
    "day_of_week",
    "day_of_year",
    "month",
    "hour_decimal",

    "hour_sin",
    "hour_cos",
    "day_of_year_sin",
    "day_of_year_cos",

    "lag_1",
    "lag_2",
    "lag_4",
    "lag_24",
    "lag_96",

    "rolling_mean_4",
    "rolling_mean_12",
    "rolling_mean_24",
    "rolling_std_24"
]

df = df[feature_columns]


# Remove rows created by lag/rolling/target calculations
df = df.dropna().reset_index(drop=True)


df.to_csv(output_path, index=False)


print("\nWeather-aware feature dataset created successfully.")

print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")

print(f"Start: {df['timestamp'].min()}")
print(f"End: {df['timestamp'].max()}")

print("\nMissing values:")
print(df.isnull().sum())

print("\nFeature columns:")
print(df.columns.tolist())

print(f"\nSaved to:")
print(output_path)

print("\nFirst 10 rows:")
print(df.head(10))