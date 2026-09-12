from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
generation_path = ROOT / "data" / "raw" / "kaggle_india" / "Plant_1_Generation_Data.csv"
weather_path = ROOT / "data" / "raw" / "kaggle_india" / "Plant_1_Weather_Sensor_Data.csv"

# Set the path for the cleaned dataset
output_path = ROOT / "data" / "processed" / "solar_plant1_clean.csv"

# Load the raw datasets
print("Loading raw datasets...")

generation = pd.read_csv(generation_path)
weather = pd.read_csv(weather_path)

print("Raw datasets loaded successfully!")

# Display the original dataset sizes
print("\nOriginal dataset sizes:")
print("Generation:", generation.shape)
print("Weather:", weather.shape)

# Convert timestamp columns to datetime format
generation["DATE_TIME"] = pd.to_datetime(
    generation["DATE_TIME"],
    dayfirst=True
)

weather["DATE_TIME"] = pd.to_datetime(
    weather["DATE_TIME"],
    dayfirst=True
)

# Remove completely duplicated rows
generation_duplicates = generation.duplicated().sum()
weather_duplicates = weather.duplicated().sum()

generation = generation.drop_duplicates()
weather = weather.drop_duplicates()

print("\nDuplicate rows removed:")
print("Generation:", generation_duplicates)
print("Weather:", weather_duplicates)

# Check for negative generation values
negative_ac = (generation["AC_POWER"] < 0).sum()
negative_dc = (generation["DC_POWER"] < 0).sum()

print("\nNegative generation values:")
print("Negative AC_POWER:", negative_ac)
print("Negative DC_POWER:", negative_dc)

# Remove rows with negative AC or DC power
generation = generation[
    (generation["AC_POWER"] >= 0) &
    (generation["DC_POWER"] >= 0)
].copy()

# Aggregate inverter-level AC power to plant-level generation
plant_generation = (
    generation
    .groupby("DATE_TIME", as_index=False)
    .agg({
        "AC_POWER": "sum"
    })
)

# Rename columns for clarity
plant_generation = plant_generation.rename(
    columns={
        "DATE_TIME": "timestamp",
        "AC_POWER": "ac_power_kw"
    }
)

# Keep weather measurements at timestamp level
weather_clean = (
    weather[
        [
            "DATE_TIME",
            "AMBIENT_TEMPERATURE",
            "MODULE_TEMPERATURE",
            "IRRADIATION"
        ]
    ]
    .groupby("DATE_TIME", as_index=False)
    .mean()
)

# Rename weather columns
weather_clean = weather_clean.rename(
    columns={
        "DATE_TIME": "timestamp",
        "AMBIENT_TEMPERATURE": "ambient_temperature",
        "MODULE_TEMPERATURE": "module_temperature",
        "IRRADIATION": "irradiation"
    }
)

# Merge plant generation with weather data
solar = pd.merge(
    plant_generation,
    weather_clean,
    on="timestamp",
    how="left"
)

# Sort the dataset chronologically
solar = solar.sort_values("timestamp").reset_index(drop=True)

# Check missing values after merging
print("\nMissing values after merging:")
print(solar.isna().sum())

# Remove rows where generation is missing
solar = solar.dropna(
    subset=["ac_power_kw"]
).copy()

# Fill missing weather values using time interpolation
weather_columns = [
    "ambient_temperature",
    "module_temperature",
    "irradiation"
]

for column in weather_columns:
    solar[column] = solar[column].interpolate(
        method="linear"
    )

# Remove any remaining rows with missing weather data
solar = solar.dropna(
    subset=weather_columns
).copy()

# Check for invalid negative weather values
negative_irradiation = (
    solar["irradiation"] < 0
).sum()

print("\nNegative irradiation values:", negative_irradiation)

# Set negative irradiation values to zero
solar["irradiation"] = solar["irradiation"].clip(lower=0)

# Display the final cleaned dataset information
print("\nFinal cleaned dataset shape:")
print(solar.shape)

print("\nFinal columns:")
print(solar.columns.tolist())

print("\nFirst five rows:")
print(solar.head())

print("\nFinal missing values:")
print(solar.isna().sum())

# Save the cleaned dataset
solar.to_csv(
    output_path,
    index=False
)

print("\nCleaned dataset saved successfully!")
print("Saved to:", output_path)

print("\nSolar data cleaning completed!")