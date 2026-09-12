import pandas as pd
import numpy as np

# Set the paths of the input CSV files
generation_path = "data/raw/Plant_1_Generation_Data.csv"
weather_path = "data/raw/Plant_1_Weather_Sensor_Data.csv"

# Load the generation and weather datasets
print("Loading datasets...")

generation = pd.read_csv(generation_path)
weather = pd.read_csv(weather_path)

print("\nDatasets loaded successfully!")

# Display the number of rows and columns
print("\nDataset shapes:")

print("Generation data shape:", generation.shape)
print("Weather data shape:", weather.shape)

# Display the column names
print("\nGeneration columns:")
print(generation.columns.tolist())

print("\nWeather columns:")
print(weather.columns.tolist())

# Display the first five rows
print("\nFirst five rows of generation data:")
print(generation.head())

print("\nFirst five rows of weather data:")
print(weather.head())

# Display data types and non-null information
print("\nGeneration data information:")
generation.info()

print("\nWeather data information:")
weather.info()

# Check for missing values
print("\nMissing values:")

print("\nGeneration data:")
print(generation.isna().sum())

print("\nWeather data:")
print(weather.isna().sum())

# Check for completely duplicated rows
print("\nDuplicate rows:")

print("Generation duplicate rows:", generation.duplicated().sum())
print("Weather duplicate rows:", weather.duplicated().sum())

# Display statistical summary of numerical columns
print("\nGeneration data statistics:")
print(generation.describe())

print("\nWeather data statistics:")
print(weather.describe())

# Check the beginning and ending timestamps
print("\nTimestamp range:")

print("Generation start:", generation["DATE_TIME"].min())
print("Generation end:", generation["DATE_TIME"].max())

print("Weather start:", weather["DATE_TIME"].min())
print("Weather end:", weather["DATE_TIME"].max())

# Display unique plant IDs
print("\nPlant IDs:")
print(generation["PLANT_ID"].unique())

# Count the number of unique inverters
print("\nNumber of unique inverters:")
print(generation["SOURCE_KEY"].nunique())

# Check for negative generation values
print("\nNegative values:")

for column in ["DC_POWER", "AC_POWER", "DAILY_YIELD", "TOTAL_YIELD"]:
    if column in generation.columns:
        negative_count = (generation[column] < 0).sum()
        print(column, "negative values =", negative_count)

# Check how many rows have zero AC power
print("\nZero AC power:")

if "AC_POWER" in generation.columns:
    zero_ac_power = (generation["AC_POWER"] == 0).sum()

    print("Rows with AC_POWER = 0:", zero_ac_power)

    print(
        "Percentage of rows with AC_POWER = 0:",
        round(zero_ac_power / len(generation) * 100, 2),
        "%"
    )

# Display all unique inverter identifiers
print("\nInverter identifiers:")
print(generation["SOURCE_KEY"].unique())

# Confirm that the inspection is complete
print("\nSolar data inspection completed!")