import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


LATITUDE = 14.9185
LONGITUDE = 78.2867

START_DATE = "2020-05-15"
END_DATE = "2020-06-17"


params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "hourly": ",".join([
        "temperature_2m",
        "relative_humidity_2m",
        "cloud_cover",
        "shortwave_radiation",
        "wind_speed_10m",
        "wind_direction_10m",
        "precipitation_probability"
    ]),
    "timezone": "auto"
}

url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(params)

print("Fetching historical weather data from Open-Meteo...")
print(f"Location: {LATITUDE}, {LONGITUDE}")
print(f"Period: {START_DATE} to {END_DATE}")

with urlopen(url, timeout=60) as response:
    data = json.load(response)

weather = pd.DataFrame(data["hourly"])

weather["timestamp"] = pd.to_datetime(weather["time"])

weather = weather.rename(columns={
    "temperature_2m": "ambient_temperature",
    "relative_humidity_2m": "relative_humidity",
    "shortwave_radiation": "shortwave_radiation_w_m2",
    "wind_speed_10m": "wind_speed",
    "wind_direction_10m": "wind_direction"
})

# Convert radiation from W/m² to kW/m²
weather["irradiation"] = (
    weather["shortwave_radiation_w_m2"] / 1000
)

weather = weather[
    [
        "timestamp",
        "ambient_temperature",
        "relative_humidity",
        "cloud_cover",
        "shortwave_radiation_w_m2",
        "irradiation",
        "wind_speed",
        "wind_direction",
        "precipitation_probability"
    ]
]

# Convert hourly weather to 15-minute intervals
weather = weather.set_index("timestamp")

numeric_columns = weather.select_dtypes(include="number").columns

weather = (
    weather[numeric_columns]
    .resample("15min")
    .interpolate(method="time")
    .reset_index()
)

output_path = Path("data/processed/openmeteo_historical_weather.csv")
output_path.parent.mkdir(parents=True, exist_ok=True)

weather.to_csv(output_path, index=False)

print("\nHistorical weather downloaded successfully.")
print(f"Rows: {len(weather)}")
print(f"Start: {weather['timestamp'].min()}")
print(f"End: {weather['timestamp'].max()}")

print(f"\nSaved to: {output_path}")

print("\nFirst 10 rows:")
print(weather.head(10))

print("\nWeather columns:")
print(weather.columns.tolist())