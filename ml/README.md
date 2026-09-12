# RenewAI ML Handoff README

## Public ML entry point

Use `ml.inference.predict_generation.predict_generation(plant_data, historical_data, weather_data)` for backend-facing prediction requests.

### Inputs

- `plant_data`: dictionary with at least `plant_id`, `plant_capacity_kw`, and optional `timezone`
- `historical_data`: historical generation table containing `timestamp` and `ac_power_kw`
- `weather_data`: future forecast weather table containing the required forecast weather columns:
  - `timestamp`
  - `ambient_temperature`
  - `relative_humidity`
  - `cloud_cover`
  - `shortwave_radiation_w_m2`
  - `irradiation`
  - `wind_speed`
  - `wind_direction`

### Outputs

The function returns a structured dictionary with one of three top-level statuses:

- `success`: normal forecast response
- `fallback`: safe persistence fallback, returned when weather is missing or timestamp gaps are too large for reliable inference
- `error`: contract/input validation failure with a clean machine-readable error payload

Success payload fields are:

- `status`
- `model_version`
- `plant_id`
- `forecast` (array of points with `timestamp`, `forecast_kw`, `p10_kw`, `p50_kw`, `p90_kw`)
- `metadata` (forecast horizon, interval, units, timezone, uncertainty method, model version)

## Current model

- Model version: `renewai-generalized-xgb-v1`
- Production artifact: `ml/models/renewai_generalized_xgb.joblib`
- Metadata artifact: `ml/models/model_metadata.json`
- Feature count: 40
- Forecast horizon: 24 hours (96 x 15-minute points)
- Units: kW
- Uncertainty method: residual-based prediction intervals
- Supported renewable types: solar and wind

## Forecast behavior

- Nighttime periods with `shortwave_radiation_w_m2 <= 1` are forced to zero output by the existing inference logic.
- Prediction intervals are clipped to remain non-negative and within plant capacity.
- `p10 <= p50 <= p90` is enforced before returning forecast rows.
- The current production model is generalized across solar and wind sites and uses the unified feature schema generated in `data/processed/generalized_training/`.

## Fallback behavior

The wrapper automatically returns a persistence fallback when:

- `weather_data` is missing or empty
- `weather_data` contains large timestamp gaps
- required historical or weather inputs are invalid

Fallback responses preserve a consistent payload shape and do not expose stack traces.

## ML responsibilities

The ML layer is responsible for:

- shared feature engineering
- generalized weather-aware XGBoost inference
- residual-based uncertainty intervals
- metadata generation
- stable input/output contract
- fallback helpers and clean error payloads

## Backend responsibilities

Backend work should remain focused on:

- calling the ML prediction endpoint with real plant, historical, and weather payloads
- handling the returned `success`, `fallback`, or `error` status appropriately
- storing or surfacing the forecast payload and metadata in downstream APIs or UI flows
- maintaining ingestion, orchestration, and data pipeline operations outside the ML package

## Validation artifacts

Current verified artifacts already exist under `data/processed/`:

- `generalized_training/feature_schema.json`
- `generalized_training/site_metadata.csv`
- `generalized_training/model_training_report.json`
- `generalized_training/final_model_metadata.json`
- `generalized_training/shap_feature_contributions.csv`
- `uncertainty_calibration.json`
- `ml_final_validation_report.json`
- `ml_final_validation_report.txt`

## Known limitations

- The current evaluation remains a short-horizon prototype with a modest historical span for some sites, so the main production confidence is strongest for the generalized training and validation artifacts already generated.
- Future forecast weather must still be supplied at inference time; the trained model does not infer future weather automatically.
- The horizon summary is alignment-based rather than a recursive multi-step forecasting implementation.
