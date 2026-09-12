from pathlib import Path

import pandas as pd


generation_path = Path("data/processed/solar_plant1_clean.csv")
weather_path = Path("data/processed/openmeteo_historical_weather.csv")

output_path = Path("data/processed/solar_weather_merged.csv")


print("Loading solar generation data...")
generation = pd.read_csv(generation_path)

print("Loading Open-Meteo weather data...")
weather = pd.read_csv(weather_path)


generation["timestamp"] = pd.to_datetime(generation["timestamp"])
weather["timestamp"] = pd.to_datetime(weather["timestamp"])


print("\nGeneration data:")
print(f"Rows: {len(generation)}")
print(f"Start: {generation['timestamp'].min()}")
print(f"End: {generation['timestamp'].max()}")


print("\nWeather data:")
print(f"Rows: {len(weather)}")
print(f"Start: {weather['timestamp'].min()}")
print(f"End: {weather['timestamp'].max()}")


# Keep only weather columns needed for modelling
weather_columns = [
    "timestamp",
    "ambient_temperature",
    "relative_humidity",
    "cloud_cover",
    "shortwave_radiation_w_m2",
    "irradiation",
    "wind_speed",
    "wind_direction"
]

weather = weather[weather_columns]


# Merge using the exact 15-minute timestamp
merged = pd.merge(
    generation,
    weather,
    on="timestamp",
    how="inner"
)


# Sort chronologically
merged = merged.sort_values("timestamp").reset_index(drop=True)


print("\nMerged dataset:")
print(f"Rows: {len(merged)}")
print(f"Columns: {len(merged.columns)}")
print(f"Start: {merged['timestamp'].min()}")
print(f"End: {merged['timestamp'].max()}")


print("\nMissing values:")
print(merged.isnull().sum())


merged.to_csv(output_path, index=False)


print(f"\nMerged dataset saved to:")
print(output_path)


print("\nColumns:")
print(merged.columns.tolist())


print("\nFirst 10 rows:")
print(merged.head(10))