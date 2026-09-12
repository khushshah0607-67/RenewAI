import pandas as pd
import numpy as np

# Set the input and output paths
input_path = "data/processed/solar_plant1_clean.csv"
output_path = "data/processed/solar_plant1_features.csv"

# Load the cleaned dataset
print("Loading cleaned solar dataset...")

solar = pd.read_csv(input_path)

# Convert timestamp to datetime
solar["timestamp"] = pd.to_datetime(solar["timestamp"])

# Sort the data chronologically
solar = solar.sort_values("timestamp").reset_index(drop=True)

# Create basic time features
solar["hour"] = solar["timestamp"].dt.hour
solar["day_of_week"] = solar["timestamp"].dt.dayofweek
solar["day_of_year"] = solar["timestamp"].dt.dayofyear
solar["month"] = solar["timestamp"].dt.month

# Create cyclical hour features
solar["hour_sin"] = np.sin(
    2 * np.pi * solar["hour"] / 24
)

solar["hour_cos"] = np.cos(
    2 * np.pi * solar["hour"] / 24
)

# Create cyclical yearly features
solar["day_of_year_sin"] = np.sin(
    2 * np.pi * solar["day_of_year"] / 365
)

solar["day_of_year_cos"] = np.cos(
    2 * np.pi * solar["day_of_year"] / 365
)

# Create lag features using previous generation values
solar["lag_1"] = solar["ac_power_kw"].shift(1)
solar["lag_2"] = solar["ac_power_kw"].shift(2)
solar["lag_4"] = solar["ac_power_kw"].shift(4)
solar["lag_24"] = solar["ac_power_kw"].shift(24)
solar["lag_96"] = solar["ac_power_kw"].shift(96)

# Create rolling generation statistics using only previous values
solar["rolling_mean_4"] = (
    solar["ac_power_kw"]
    .shift(1)
    .rolling(window=4)
    .mean()
)

solar["rolling_mean_12"] = (
    solar["ac_power_kw"]
    .shift(1)
    .rolling(window=12)
    .mean()
)

solar["rolling_mean_24"] = (
    solar["ac_power_kw"]
    .shift(1)
    .rolling(window=24)
    .mean()
)

solar["rolling_std_24"] = (
    solar["ac_power_kw"]
    .shift(1)
    .rolling(window=24)
    .std()
)

# Create the forecasting target
# The model will predict the next 15-minute generation
solar["target_ac_power_kw"] = (
    solar["ac_power_kw"].shift(-1)
)

# Remove rows created by lag, rolling, and target shifting
solar = solar.dropna().reset_index(drop=True)

# Display the feature dataset information
print("\nFeature engineering completed!")

print("\nFeature dataset shape:")
print(solar.shape)

print("\nFeature columns:")
print(solar.columns.tolist())

print("\nFirst five rows:")
print(solar.head())

print("\nMissing values:")
print(solar.isna().sum())

# Save the feature dataset
solar.to_csv(
    output_path,
    index=False
)

print("\nFeature dataset saved successfully!")
print("Saved to:", output_path)