from pathlib import Path
import pandas as pd


input_path = Path(
    "data/processed/renewai_action_recommendations.csv"
)

output_path = Path(
    "data/processed/renewai_financial_impact.csv"
)


# Demo assumptions
ENERGY_VALUE_INR_PER_KWH = 5.0
GRID_EXPORT_LIMIT_KW = 20000


print("Loading RenewAI recommendations...")

forecast = pd.read_csv(input_path)

forecast["timestamp"] = pd.to_datetime(
    forecast["timestamp"]
)


# Calculate generation above export limit
forecast["excess_generation_kw"] = (
    forecast["forecast_generation_kw"]
    - GRID_EXPORT_LIMIT_KW
).clip(lower=0)


# Convert excess generation to 15-minute energy
forecast["potential_excess_energy_kwh"] = (
    forecast["excess_generation_kw"] * 0.25
)


# Estimate financial exposure
forecast["potential_financial_exposure_inr"] = (
    forecast["potential_excess_energy_kwh"]
    * ENERGY_VALUE_INR_PER_KWH
)


# Daily totals
total_excess_energy_kwh = (
    forecast["potential_excess_energy_kwh"].sum()
)

total_excess_energy_mwh = (
    total_excess_energy_kwh / 1000
)

total_financial_exposure = (
    forecast["potential_financial_exposure_inr"].sum()
)


# Number of affected intervals
affected_intervals = (
    forecast["potential_excess_energy_kwh"] > 0
).sum()


# Highest exposure interval
peak_exposure_row = forecast.loc[
    forecast["potential_financial_exposure_inr"].idxmax()
]


# Save results
forecast.to_csv(
    output_path,
    index=False
)


print("\nRenewAI Financial Impact Analysis")
print("-----------------------------------")

print(
    f"Assumed energy value: "
    f"₹{ENERGY_VALUE_INR_PER_KWH:.2f}/kWh"
)

print(
    f"Grid export limit: "
    f"{GRID_EXPORT_LIMIT_KW:.0f} kW"
)

print(
    f"\nPotential excess energy: "
    f"{total_excess_energy_mwh:.2f} MWh"
)

print(
    f"Estimated financial exposure: "
    f"₹{total_financial_exposure:,.2f}"
)

print(
    f"Affected 15-minute intervals: "
    f"{affected_intervals}"
)


print("\nHighest exposure interval:")

print(
    f"Time: "
    f"{peak_exposure_row['timestamp']}"
)

print(
    f"Forecast generation: "
    f"{peak_exposure_row['forecast_generation_kw']:.2f} kW"
)

print(
    f"Excess generation: "
    f"{peak_exposure_row['excess_generation_kw']:.2f} kW"
)

print(
    f"Potential excess energy: "
    f"{peak_exposure_row['potential_excess_energy_kwh']:.2f} kWh"
)

print(
    f"Estimated exposure: "
    f"₹{peak_exposure_row['potential_financial_exposure_inr']:,.2f}"
)


print("\nFinancial impact data saved to:")

print(output_path)

print("\nStep 21 completed successfully.")