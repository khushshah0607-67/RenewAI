from pathlib import Path

import pandas as pd


input_path = Path(
    "data/processed/solar_24h_weather_forecast.csv"
)

output_path = Path(
    "data/processed/renewai_action_recommendations.csv"
)


# Demo assumptions
PLANT_CAPACITY_KW = 30000
GRID_EXPORT_LIMIT_KW = 20000

HIGH_GENERATION_THRESHOLD = 0.80
LOW_GENERATION_THRESHOLD = 0.25


print("Loading 24-hour forecast...")

forecast = pd.read_csv(input_path)
forecast["timestamp"] = pd.to_datetime(
    forecast["timestamp"]
)


# Calculate thresholds
high_generation_limit = (
    PLANT_CAPACITY_KW *
    HIGH_GENERATION_THRESHOLD
)

low_generation_limit = (
    PLANT_CAPACITY_KW *
    LOW_GENERATION_THRESHOLD
)


# Classify generation conditions
forecast["risk_level"] = "Normal"
forecast["recommended_action"] = "Normal operation"


high_condition = (
    forecast["forecast_generation_kw"]
    >= high_generation_limit
)

# Daytime low-generation condition
daytime_condition = (
    forecast["timestamp"].dt.hour >= 7
) & (
    forecast["timestamp"].dt.hour < 18
)

low_condition = (
    forecast["forecast_generation_kw"]
    <= low_generation_limit
) & daytime_condition

export_condition = (
    forecast["forecast_generation_kw"]
    > GRID_EXPORT_LIMIT_KW
)


forecast.loc[
    high_condition,
    "risk_level"
] = "High Generation"

forecast.loc[
    high_condition,
    "recommended_action"
] = (
    "Charge storage; consider curtailment "
    "if export limit is reached"
)


forecast.loc[
    low_condition,
    "risk_level"
] = "Low Generation"

forecast.loc[
    low_condition,
    "recommended_action"
] = (
    "Prepare storage discharge or backup "
    "generation if demand is not met"
)


forecast.loc[
    export_condition,
    "risk_level"
] = "Potential Over-Generation"

forecast.loc[
    export_condition,
    "recommended_action"
] = (
    "Check grid export limit; use storage "
    "or curtailment if required"
)

# Nighttime is expected zero solar generation
night_condition = (
    (forecast["timestamp"].dt.hour < 7)
    | (forecast["timestamp"].dt.hour >= 18)
)

forecast.loc[
    night_condition &
    (forecast["forecast_generation_kw"] <= 100),
    "risk_level"
] = "Normal Nighttime"

forecast.loc[
    night_condition &
    (forecast["forecast_generation_kw"] <= 100),
    "recommended_action"
] = (
    "No solar generation expected; "
    "normal nighttime operation"
)


# Calculate energy for each 15-minute interval
forecast["energy_kwh"] = (
    forecast["forecast_generation_kw"] *
    0.25
)


# Daily energy estimate
total_energy_kwh = (
    forecast["energy_kwh"].sum()
)

total_energy_mwh = total_energy_kwh / 1000


# Peak and minimum
peak_row = forecast.loc[
    forecast["forecast_generation_kw"].idxmax()
]

minimum_row = forecast.loc[
    forecast["forecast_generation_kw"].idxmin()
]


# Number of risk periods
high_count = (
    forecast["risk_level"]
    .isin([
        "High Generation",
        "Potential Over-Generation"
    ])
    .sum()
)

low_count = (
    forecast["risk_level"]
    == "Low Generation"
).sum()


# Save recommendations
forecast.to_csv(
    output_path,
    index=False
)


print("\nRenewAI Risk & Action Analysis")
print("--------------------------------")

print(
    f"Plant capacity assumption: "
    f"{PLANT_CAPACITY_KW:.0f} kW"
)

print(
    f"Grid export limit assumption: "
    f"{GRID_EXPORT_LIMIT_KW:.0f} kW"
)

print(
    f"\nExpected 24-hour energy: "
    f"{total_energy_mwh:.2f} MWh"
)

print(
    f"Peak generation: "
    f"{peak_row['forecast_generation_kw']:.2f} kW"
)

print(
    f"Peak time: "
    f"{peak_row['timestamp']}"
)

print(
    f"Minimum generation: "
    f"{minimum_row['forecast_generation_kw']:.2f} kW"
)

print(
    f"Minimum time: "
    f"{minimum_row['timestamp']}"
)

print(
    f"\nHigh/over-generation periods: "
    f"{high_count}"
)

print(
    f"Low-generation periods: "
    f"{low_count}"
)


print("\nRisk periods:")

risk_periods = forecast[
    ~forecast["risk_level"].isin([
        "Normal",
        "Normal Nighttime"
    ])
]

if len(risk_periods) == 0:

    print("No major risk periods detected.")

else:

    print(
        risk_periods[
            [
                "timestamp",
                "forecast_generation_kw",
                "risk_level",
                "recommended_action"
            ]
        ].to_string(index=False)
    )


print(
    f"\nRecommendations saved to:"
)

print(output_path)

print("\nStep 20 completed successfully.")