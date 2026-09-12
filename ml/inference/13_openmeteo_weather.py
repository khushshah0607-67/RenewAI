import json
from urllib.parse import urlencode
from urllib.request import urlopen
from pathlib import Path

import pandas as pd

# Enter the actual Plant 1 location
LATITUDE = 14.9185
LONGITUDE = 78.2867

if LATITUDE == 0.0 or LONGITUDE == 0.0:
    raise ValueError(
        "Please enter the actual Plant 1 latitude and longitude "
        "in LATITUDE and LONGITUDE."
    )

params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
    "hourly": ",".join([
        "temperature_2m",
        "relative_humidity_2m",
        "cloud_cover",
        "shortwave_radiation",
        "wind_speed_10m",
        "wind_direction_10m",
        "precipitation_probability",
        "is_day"
    ]),
    "forecast_days": 2,
    "timezone": "auto"
}

url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)

print("Fetching weather data from Open-Meteo...")

with urlopen(url, timeout=30) as response:
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
# This keeps the scale approximately compatible with the Kaggle irradiation values.
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
        "precipitation_probability",
        "is_day"
    ]
]

output_path = Path("data/processed/openmeteo_forecast_weather.csv")
output_path.parent.mkdir(parents=True, exist_ok=True)

weather.to_csv(output_path, index=False)

print("\nWeather data downloaded successfully.")
print(f"Rows: {len(weather)}")
print(f"Start: {weather['timestamp'].min()}")
print(f"End: {weather['timestamp'].max()}")
print(f"\nSaved to: {output_path}")

print("\nFirst 10 rows:")
print(weather.head(10))