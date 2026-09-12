import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load the cleaned solar dataset
data_path = "data/processed/solar_plant1_clean.csv"

solar = pd.read_csv(data_path)

# Convert timestamp to datetime
solar["timestamp"] = pd.to_datetime(solar["timestamp"])

# Display basic information
print("Cleaned dataset loaded successfully!")
print("\nDataset shape:", solar.shape)

print("\nColumns:")
print(solar.columns.tolist())

print("\nFirst five rows:")
print(solar.head())

# Display statistical summary
print("\nStatistical summary:")
print(solar.describe())

# Check missing values
print("\nMissing values:")
print(solar.isna().sum())

# Check duplicate rows
print("\nDuplicate rows:", solar.duplicated().sum())

# Check timestamp range
print("\nStart timestamp:", solar["timestamp"].min())
print("End timestamp:", solar["timestamp"].max())

# Plot plant-level solar generation over time
plt.figure(figsize=(14, 5))
plt.plot(
    solar["timestamp"],
    solar["ac_power_kw"]
)

plt.title("Solar Plant AC Power Generation Over Time")
plt.xlabel("Time")
plt.ylabel("AC Power (kW)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Plot irradiation over time
plt.figure(figsize=(14, 5))
plt.plot(
    solar["timestamp"],
    solar["irradiation"]
)

plt.title("Solar Irradiation Over Time")
plt.xlabel("Time")
plt.ylabel("Irradiation")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Plot irradiation versus AC power
plt.figure(figsize=(7, 5))
plt.scatter(
    solar["irradiation"],
    solar["ac_power_kw"],
    alpha=0.4
)

plt.title("Irradiation vs Solar Generation")
plt.xlabel("Irradiation")
plt.ylabel("AC Power (kW)")
plt.tight_layout()
plt.show()

# Plot ambient temperature versus AC power
plt.figure(figsize=(7, 5))
plt.scatter(
    solar["ambient_temperature"],
    solar["ac_power_kw"],
    alpha=0.4
)

plt.title("Ambient Temperature vs Solar Generation")
plt.xlabel("Ambient Temperature")
plt.ylabel("AC Power (kW)")
plt.tight_layout()
plt.show()

# Create hour column for daily generation pattern
solar["hour"] = solar["timestamp"].dt.hour

hourly_generation = (
    solar
    .groupby("hour")["ac_power_kw"]
    .mean()
)

# Plot average generation by hour
plt.figure(figsize=(10, 5))
plt.plot(
    hourly_generation.index,
    hourly_generation.values,
    marker="o"
)

plt.title("Average Solar Generation by Hour")
plt.xlabel("Hour of Day")
plt.ylabel("Average AC Power (kW)")
plt.xticks(range(24))
plt.grid(True)
plt.tight_layout()
plt.show()

print("\nEDA completed successfully!")