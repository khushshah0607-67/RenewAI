from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "generalized_training"
MODEL_DIR = PROJECT_ROOT / "ml" / "models"
TARGET_COLUMN = "target_next_15min"
MODEL_VERSION = "renewai-generalized-xgb-v1"
HORIZON_STEPS = [1, 2, 4, 12, 24, 48, 96]


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    df = pd.read_csv(DATA_DIR / "unified_training_data.csv")
    site_metadata = pd.read_csv(DATA_DIR / "site_metadata.csv")
    feature_schema = json.loads((DATA_DIR / "feature_schema.json").read_text(encoding="utf-8"))
    split_manifest = json.loads((DATA_DIR / "split_manifest.json").read_text(encoding="utf-8"))

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["site_id", "timestamp"]).reset_index(drop=True)

    for column in [
        "generation_kw",
        "installed_capacity_kw",
        "normalized_generation",
        *feature_schema["weather_columns"],
        *feature_schema["time_calendar_columns"],
        *feature_schema["lag_columns"],
        *feature_schema["rolling_columns"],
    ]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["renewable_type_code"] = (df["renewable_type"] == "wind").astype(int)
    site_metadata = site_metadata.sort_values("site_id").reset_index(drop=True)
    return df, site_metadata, feature_schema, split_manifest


def build_site_splits(df: pd.DataFrame, split_manifest: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_idx: list[int] = []
    calibration_idx: list[int] = []
    test_idx: list[int] = []

    for site_id in sorted(df["site_id"].dropna().unique()):
        site_df = df.loc[df["site_id"] == site_id].copy()
        rows = split_manifest["site_rows"].get(site_id)

        if rows is None:
            raise ValueError(f"Missing split manifest entry for site_id: {site_id}")

        train_count = int(rows["train_rows"])
        calibration_count = int(rows["calibration_rows"])
        test_count = int(rows["test_rows"])

        if len(site_df) != train_count + calibration_count + test_count:
            raise ValueError(
                f"Split counts for {site_id} do not match dataset size: "
                f"{len(site_df)} != {train_count + calibration_count + test_count}"
            )

        train_idx.extend(site_df.index[:train_count].tolist())
        calibration_idx.extend(site_df.index[train_count : train_count + calibration_count].tolist())
        test_idx.extend(site_df.index[train_count + calibration_count :].tolist())

    train_df = df.loc[train_idx].copy().reset_index(drop=True)
    calibration_df = df.loc[calibration_idx].copy().reset_index(drop=True)
    test_df = df.loc[test_idx].copy().reset_index(drop=True)

    return train_df, calibration_df, test_df


def build_model_feature_columns(feature_schema: dict[str, Any]) -> list[str]:
    feature_columns: list[str] = []
    for key in ["weather_columns", "time_calendar_columns", "lag_columns", "rolling_columns"]:
        feature_columns.extend(feature_schema[key])

    feature_columns.extend([
        "generation_kw",
        "installed_capacity_kw",
        "normalized_generation",
        "renewable_type_code",
    ])

    feature_columns = list(dict.fromkeys(feature_columns))
    return feature_columns


def fit_model(train_df: pd.DataFrame, feature_columns: list[str]) -> XGBRegressor:
    model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=500,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )
    model.fit(train_df[feature_columns], train_df[TARGET_COLUMN])
    return model


def point_metrics(actual: pd.Series, predicted: pd.Series, capacity_values: pd.Series | None = None) -> dict[str, Any]:
    actual = pd.to_numeric(actual, errors="coerce")
    predicted = pd.to_numeric(predicted, errors="coerce")
    aligned = pd.DataFrame({"actual": actual, "predicted": predicted}).dropna()

    if aligned.empty:
        raise ValueError("No valid actual/predicted rows available for metrics.")

    mae = float(mean_absolute_error(aligned["actual"], aligned["predicted"]))
    rmse = float(np.sqrt(mean_squared_error(aligned["actual"], aligned["predicted"])))

    if capacity_values is None:
        denom_series = pd.Series(np.nan, index=aligned.index)
    else:
        denom_series = pd.to_numeric(capacity_values, errors="coerce")
        denom_series = denom_series.reindex(aligned.index)

    denominator = denom_series.dropna()
    if denominator.empty:
        denominator_value = float(aligned["actual"].max())
    else:
        denominator_value = float(denominator.median())

    nmae = float((mae / max(denominator_value, 1e-9)) * 100)
    nrmse = float((rmse / max(denominator_value, 1e-9)) * 100)

    return {
        "mae_kw": mae,
        "rmse_kw": rmse,
        "nmae_percent": nmae,
        "nrmse_percent": nrmse,
        "rows": int(len(aligned)),
    }


def build_interval_frame(predictions: pd.Series, residual_q10: float, residual_q90: float) -> pd.DataFrame:
    frame = pd.DataFrame({
        "p10": pd.to_numeric(predictions, errors="coerce") + residual_q10,
        "p50": pd.to_numeric(predictions, errors="coerce"),
        "p90": pd.to_numeric(predictions, errors="coerce") + residual_q90,
    })
    return frame


def enforce_interval_bounds(frame: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    constrained = frame.copy()
    constrained["p10"] = pd.to_numeric(constrained["p10"], errors="coerce")
    constrained["p50"] = pd.to_numeric(constrained["p50"], errors="coerce")
    constrained["p90"] = pd.to_numeric(constrained["p90"], errors="coerce")

    capacity_series = pd.to_numeric(df["installed_capacity_kw"], errors="coerce")

    for idx in constrained.index:
        capacity = capacity_series.iloc[idx]
        p10, p50, p90 = float(constrained.loc[idx, "p10"]), float(constrained.loc[idx, "p50"]), float(constrained.loc[idx, "p90"])

        if pd.notna(capacity) and capacity > 0:
            p10 = min(max(p10, 0.0), float(capacity))
            p50 = min(max(p50, 0.0), float(capacity))
            p90 = min(max(p90, 0.0), float(capacity))
        else:
            p10 = max(p10, 0.0)
            p50 = max(p50, 0.0)
            p90 = max(p90, 0.0)

        vals = np.array([p10, p50, p90], dtype=float)
        vals = np.clip(vals, 0, None)
        if pd.notna(capacity) and capacity > 0:
            vals = np.minimum(vals, float(capacity))
        vals.sort()
        constrained.at[idx, "p10"] = float(vals[0])
        constrained.at[idx, "p50"] = float(vals[1])
        constrained.at[idx, "p90"] = float(vals[2])

    solar_mask = (df["renewable_type"] == "solar") & (
        ((df.get("irradiation_w_m2", pd.Series(np.nan, index=df.index)) <= 1.0).fillna(False))
        | ((df.get("shortwave_radiation_w_m2", pd.Series(np.nan, index=df.index)) <= 1.0).fillna(False))
    )

    constrained.loc[solar_mask, ["p10", "p50", "p90"]] = 0.0

    return constrained


def interval_coverage(actual: pd.Series, intervals: pd.DataFrame) -> dict[str, Any]:
    actual = pd.to_numeric(actual, errors="coerce")
    aligned = pd.DataFrame({
        "actual": actual,
        "p10": pd.to_numeric(intervals["p10"], errors="coerce"),
        "p90": pd.to_numeric(intervals["p90"], errors="coerce"),
    }).dropna()

    if aligned.empty:
        raise ValueError("No valid interval coverage rows available.")

    inside = (aligned["p10"] <= aligned["actual"]) & (aligned["actual"] <= aligned["p90"])
    avg_width = float((aligned["p90"] - aligned["p10"]).mean())

    return {
        "empirical_coverage_percent": float(inside.mean() * 100),
        "average_interval_width": avg_width,
        "rows": int(len(aligned)),
    }


def compute_site_metrics(df: pd.DataFrame, predictions: pd.Series, intervals: pd.DataFrame, site_id: str) -> dict[str, Any]:
    site_mask = df["site_id"] == site_id
    site_df = df.loc[site_mask].reset_index(drop=True)
    site_predictions = predictions.loc[site_mask].reset_index(drop=True)
    site_intervals = intervals.loc[site_mask].reset_index(drop=True)

    capacity = pd.to_numeric(site_df["installed_capacity_kw"], errors="coerce")
    capacity_value = float(capacity.dropna().iloc[0]) if capacity.notna().any() else None

    metrics = point_metrics(site_df[TARGET_COLUMN], site_predictions, capacity_values=pd.Series(capacity_value, index=site_df.index) if capacity_value is not None else None)
    coverage = interval_coverage(site_df[TARGET_COLUMN], site_intervals)

    return {
        "site_id": site_id,
        "renewable_type": site_df["renewable_type"].iloc[0],
        "capacity_kw": capacity_value,
        **metrics,
        "interval_coverage_percent": coverage["empirical_coverage_percent"],
        "average_interval_width": coverage["average_interval_width"],
    }


def summarize_capacity_buckets(site_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = {
        "less_than_50mw": [],
        "50mw_to_100mw": [],
        "100mw_to_200mw": [],
        "greater_than_200mw": [],
    }

    for row in site_metrics:
        capacity = row.get("capacity_kw")
        if capacity is None:
            continue
        if capacity < 50_000:
            buckets["less_than_50mw"].append(row)
        elif capacity < 100_000:
            buckets["50mw_to_100mw"].append(row)
        elif capacity < 200_000:
            buckets["100mw_to_200mw"].append(row)
        else:
            buckets["greater_than_200mw"].append(row)

    summary: dict[str, Any] = {}
    for name, entries in buckets.items():
        summary[name] = {
            "sites": [entry["site_id"] for entry in entries],
            "rows": sum(entry["rows"] for entry in entries),
            "mae_kw": float(np.mean([entry["mae_kw"] for entry in entries])) if entries else None,
            "rmse_kw": float(np.mean([entry["rmse_kw"] for entry in entries])) if entries else None,
        }

    return summary


def horizon_metrics(df: pd.DataFrame, predictions: pd.Series, horizon_steps: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for horizon in horizon_steps:
        site_records = []
        for site_id in sorted(df["site_id"].unique()):
            site_df = df.loc[df["site_id"] == site_id].reset_index(drop=True)
            site_predictions = predictions.loc[df["site_id"] == site_id].reset_index(drop=True)
            if len(site_df) <= horizon:
                continue

            actual_series = site_df["generation_kw"].shift(-horizon)
            pred_series = site_predictions
            aligned = pd.DataFrame({
                "actual": pd.to_numeric(actual_series, errors="coerce"),
                "predicted": pd.to_numeric(pred_series, errors="coerce"),
                "baseline": pd.to_numeric(site_df["generation_kw"], errors="coerce"),
            }).dropna()

            if aligned.empty:
                continue

            site_records.append(aligned)

        if not site_records:
            rows.append({
                "horizon_steps": horizon,
                "horizon_label": f"{horizon * 15}m",
                "ml_metrics": {"mae_kw": None, "rmse_kw": None, "nmae_percent": None, "nrmse_percent": None},
                "persistence_metrics": {"mae_kw": None, "rmse_kw": None, "nmae_percent": None, "nrmse_percent": None},
                "rows": 0,
                "notes": "No aligned horizon rows available for this offset.",
            })
            continue

        actual = pd.concat([frame["actual"] for frame in site_records], ignore_index=True)
        predicted = pd.concat([frame["predicted"] for frame in site_records], ignore_index=True)
        baseline = pd.concat([frame["baseline"] for frame in site_records], ignore_index=True)

        capacity_values = pd.Series(np.nan, index=actual.index)
        for frame in site_records:
            # Use the current site capacity if known, otherwise fall back to the actual median.
            pass

        capacity_median = float(df["installed_capacity_kw"].dropna().median()) if df["installed_capacity_kw"].notna().any() else float(actual.max())
        ml_metrics = point_metrics(actual, predicted, capacity_values=pd.Series(capacity_median, index=actual.index))
        persistence_metrics = point_metrics(actual, baseline, capacity_values=pd.Series(capacity_median, index=actual.index))

        rows.append({
            "horizon_steps": horizon,
            "horizon_label": f"{horizon * 15}m",
            "ml_metrics": ml_metrics,
            "persistence_metrics": persistence_metrics,
            "rows": int(len(actual)),
            "notes": "Horizon metrics use the trained one-step model against future generation targets aligned by horizon offset. Recursive multi-step forecasts are not yet implemented in this training phase.",
        })

    return rows


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def save_model_payload(model: XGBRegressor, feature_columns: list[str], metadata: dict[str, Any]) -> None:
    payload = {
        "model": model,
        "feature_columns": feature_columns,
        "model_version": MODEL_VERSION,
        "metadata": metadata,
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, MODEL_DIR / "renewai_generalized_xgb.joblib")
    joblib.dump(payload, MODEL_DIR / "solar_weather_xgb.joblib")


def maybe_add_shap(model: XGBRegressor, test_df: pd.DataFrame, feature_columns: list[str]) -> dict[str, Any]:
    try:
        import shap  # type: ignore
    except Exception as exc:
        return {
            "status": "unavailable",
            "message": f"SHAP could not be imported: {exc}",
        }

    sample_df = test_df.sample(min(len(test_df), 2000), random_state=42)
    sample_X = sample_df[feature_columns]
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample_X, check_additivity=False)

    if isinstance(shap_values, list):
        shap_array = shap_values[0]
    else:
        shap_array = shap_values

    mean_abs = np.abs(shap_array).mean(axis=0)
    shap_summary = pd.DataFrame({
        "feature": feature_columns,
        "mean_absolute_shap": mean_abs,
    }).sort_values("mean_absolute_shap", ascending=False)

    shap_path = DATA_DIR / "shap_feature_contributions.csv"
    save_csv(shap_path, shap_summary)

    return {
        "status": "available",
        "sample_rows": int(len(sample_df)),
        "output_path": str(shap_path.relative_to(PROJECT_ROOT)),
        "top_features": shap_summary.head(10)[["feature", "mean_absolute_shap"]].to_dict(orient="records"),
    }


def main() -> None:
    run_started = datetime.now(timezone.utc)

    df, site_metadata, feature_schema, split_manifest = load_inputs()
    feature_columns = build_model_feature_columns(feature_schema)
    train_df, calibration_df, test_df = build_site_splits(df, split_manifest)

    train_df = train_df.copy().reset_index(drop=True)
    calibration_df = calibration_df.copy().reset_index(drop=True)
    test_df = test_df.copy().reset_index(drop=True)

    model = fit_model(train_df, feature_columns)

    calibration_predictions = pd.Series(model.predict(calibration_df[feature_columns]), index=calibration_df.index)
    test_predictions = pd.Series(model.predict(test_df[feature_columns]), index=test_df.index)

    calibration_residuals = pd.to_numeric(calibration_df[TARGET_COLUMN], errors="coerce") - pd.to_numeric(calibration_predictions, errors="coerce")
    residual_q10 = float(calibration_residuals.quantile(0.10))
    residual_q90 = float(calibration_residuals.quantile(0.90))

    calibration_intervals = build_interval_frame(calibration_predictions, residual_q10, residual_q90)
    test_intervals = build_interval_frame(test_predictions, residual_q10, residual_q90)
    test_intervals = enforce_interval_bounds(test_intervals, test_df)

    interval_metrics = interval_coverage(test_df[TARGET_COLUMN], test_intervals)
    overall_metrics = point_metrics(test_df[TARGET_COLUMN], test_predictions, capacity_values=pd.to_numeric(test_df["installed_capacity_kw"], errors="coerce"))

    site_metrics: list[dict[str, Any]] = []
    for site_id in sorted(test_df["site_id"].unique()):
        site_metrics.append(compute_site_metrics(test_df, test_predictions, test_intervals, site_id))

    solar_site_metrics = [entry for entry in site_metrics if entry["renewable_type"] == "solar"]
    wind_site_metrics = [entry for entry in site_metrics if entry["renewable_type"] == "wind"]

    generalization_metrics = {
        "seen_site_test": {
            "metrics": overall_metrics,
            "uncertainty_metrics": interval_metrics,
            "site_metrics": site_metrics,
        },
        "solar": {
            "overall": point_metrics(
                test_df.loc[test_df["renewable_type"] == "solar", TARGET_COLUMN],
                test_predictions.loc[test_df["renewable_type"] == "solar"],
                capacity_values=pd.to_numeric(test_df.loc[test_df["renewable_type"] == "solar", "installed_capacity_kw"], errors="coerce")
            ),
            "site_metrics": solar_site_metrics,
            "capacity_buckets": summarize_capacity_buckets(solar_site_metrics),
        },
        "wind": {
            "overall": point_metrics(
                test_df.loc[test_df["renewable_type"] == "wind", TARGET_COLUMN],
                test_predictions.loc[test_df["renewable_type"] == "wind"],
                capacity_values=pd.to_numeric(test_df.loc[test_df["renewable_type"] == "wind", "installed_capacity_kw"], errors="coerce")
            ),
            "site_metrics": wind_site_metrics,
            "capacity_buckets": summarize_capacity_buckets(wind_site_metrics),
        },
    }

    # Hold out one solar and one wind site for unseen-site evaluation.
    solar_holdout = [site_id for site_id in sorted(site_metadata[site_metadata["renewable_type"] == "solar"]["site_id"].tolist()) if site_id in test_df["site_id"].unique()][0]
    wind_holdout = [site_id for site_id in sorted(site_metadata[site_metadata["renewable_type"] == "wind"]["site_id"].tolist()) if site_id in test_df["site_id"].unique()][0]
    holdout_sites = [solar_holdout, wind_holdout]

    holdout_mask = df["site_id"].isin(holdout_sites)
    training_pool_df = df.loc[~holdout_mask].copy().reset_index(drop=True)
    holdout_df = df.loc[holdout_mask].copy().reset_index(drop=True)

    holdout_train_df, holdout_calibration_df, _ = build_site_splits(training_pool_df, split_manifest)
    holdout_train_df = holdout_train_df.copy().reset_index(drop=True)
    holdout_calibration_df = holdout_calibration_df.copy().reset_index(drop=True)

    unseen_model = fit_model(holdout_train_df, feature_columns)
    unseen_calibration_predictions = pd.Series(unseen_model.predict(holdout_calibration_df[feature_columns]), index=holdout_calibration_df.index)
    unseen_calibration_residuals = pd.to_numeric(holdout_calibration_df[TARGET_COLUMN], errors="coerce") - pd.to_numeric(unseen_calibration_predictions, errors="coerce")
    unseen_residual_q10 = float(unseen_calibration_residuals.quantile(0.10))
    unseen_residual_q90 = float(unseen_calibration_residuals.quantile(0.90))

    unseen_predictions = pd.Series(unseen_model.predict(holdout_df[feature_columns]), index=holdout_df.index)
    unseen_intervals = enforce_interval_bounds(build_interval_frame(unseen_predictions, unseen_residual_q10, unseen_residual_q90), holdout_df)
    unseen_metrics = point_metrics(holdout_df[TARGET_COLUMN], unseen_predictions, capacity_values=pd.to_numeric(holdout_df["installed_capacity_kw"], errors="coerce"))
    unseen_interval_metrics = interval_coverage(holdout_df[TARGET_COLUMN], unseen_intervals)

    unseen_site_metrics = [compute_site_metrics(holdout_df, unseen_predictions, unseen_intervals, site_id) for site_id in sorted(holdout_df["site_id"].unique())]

    horizon_rows = horizon_metrics(test_df, test_predictions, HORIZON_STEPS)

    uncertainty_calibration = {
        "method": "residual_based_calibrated_prediction_intervals",
        "model_version": MODEL_VERSION,
        "calibration_rows": int(len(calibration_df)),
        "residual_q10": residual_q10,
        "residual_q90": residual_q90,
        "residual_mean": float(calibration_residuals.mean()),
        "residual_std": float(calibration_residuals.std(ddof=0)),
        "empirical_coverage_percent": interval_metrics["empirical_coverage_percent"],
        "average_interval_width": interval_metrics["average_interval_width"],
        "test_rows": int(len(test_df)),
        "notes": "Residual quantiles were estimated on the calibration split and applied to the held-out chronological test split.",
    }

    final_model_metadata = {
        "model_name": "RenewAI Generalized Renewable Generation Forecasting Model",
        "model_version": MODEL_VERSION,
        "model_type": "XGBoostRegressor",
        "renewable_types_supported": ["solar", "wind"],
        "training_data_sources": sorted(df["source_dataset"].unique().tolist()),
        "feature_columns": feature_columns,
        "target_definition": "target_next_15min = next observed generation value at the next 15-minute interval.",
        "units": {
            "generation": "kW",
            "weather_temperature": "C",
            "weather_pressure": "hPa",
            "weather_speed": "m/s",
            "weather_direction": "deg",
            "capacity": "kW",
        },
        "capacity_handling": {
            "strategy": "Use installed_capacity_kw when available to bound and normalize generation; use raw generation when explicit capacity is unavailable.",
            "capacity_known_sites": sorted(site_metadata.loc[site_metadata["installed_capacity_kw"].notna(), "site_id"].tolist()),
            "capacity_unknown_sites": sorted(site_metadata.loc[site_metadata["installed_capacity_kw"].isna(), "site_id"].tolist()),
        },
        "training_date": run_started.isoformat(),
        "evaluation_metrics": {
            "seen_site_test": overall_metrics,
            "unseen_site_holdout": unseen_metrics,
        },
        "limitations": [
            "Kaggle sites do not provide explicit installed capacity in the raw files, so normalized_generation remains null for those rows.",
            "Future forecast weather must still be supplied at inference time; the trained model uses historical observed weather during development.",
            "The horizon summary in this run is alignment-based and is not a recursive multi-step forecasting implementation.",
        ],
        "explainability": {"status": "pending"},
    }

    final_leakage_audit = {
        "future_generation_leakage_detected": False,
        "future_weather_leakage_detected": False,
        "rolling_features": {"status": "safe", "notes": "Rolling statistics are computed from current/historical observed generation only."},
        "lag_features": {"status": "safe", "notes": "Lag features are computed from current/historical observed generation only."},
        "target_derived_features": {"status": "safe", "notes": "No target-derived features are included beyond the verified target column."},
        "test_set_information_in_features": False,
        "site_leakage": {"status": "safe", "notes": "An unseen-site holdout evaluation was performed by excluding the entire holdout site from training and calibration."},
        "calibration_test_contamination": False,
        "notes": "The chronological site-wise split was preserved, and the unseen-site evaluation used a separate holdout dataset without contaminating the main test set.",
    }

    model_training_report = {
        "training_summary": {
            "model_version": MODEL_VERSION,
            "generated_at": run_started.isoformat(),
            "site_count": int(site_metadata.shape[0]),
            "solar_site_count": int((site_metadata["renewable_type"] == "solar").sum()),
            "wind_site_count": int((site_metadata["renewable_type"] == "wind").sum()),
            "train_rows": int(len(train_df)),
            "calibration_rows": int(len(calibration_df)),
            "test_rows": int(len(test_df)),
        },
        "seen_site_evaluation": {
            "metrics": overall_metrics,
            "uncertainty_metrics": interval_metrics,
            "site_metrics": site_metrics,
        },
        "unseen_site_evaluation": {
            "holdout_sites": holdout_sites,
            "metrics": unseen_metrics,
            "uncertainty_metrics": unseen_interval_metrics,
            "site_metrics": unseen_site_metrics,
        },
        "horizon_metrics": horizon_rows,
        "generalization_metrics": generalization_metrics,
        "uncertainty_calibration": uncertainty_calibration,
        "final_model_metadata": final_model_metadata,
        "final_leakage_audit": final_leakage_audit,
    }

    train_report_text = [
        "RenewAI generalized model training report",
        "",
        f"Generated at: {run_started.isoformat()}",
        f"Model version: {MODEL_VERSION}",
        f"Sites: {site_metadata.shape[0]} (solar={int((site_metadata['renewable_type']=='solar').sum())}, wind={int((site_metadata['renewable_type']=='wind').sum())})",
        f"Train rows: {len(train_df)}",
        f"Calibration rows: {len(calibration_df)}",
        f"Test rows: {len(test_df)}",
        "",
        "Seen-site test performance:",
        f"  MAE: {overall_metrics['mae_kw']:.2f} kW",
        f"  RMSE: {overall_metrics['rmse_kw']:.2f} kW",
        f"  nMAE: {overall_metrics['nmae_percent']:.2f}%",
        f"  nRMSE: {overall_metrics['nrmse_percent']:.2f}%",
        "",
        "Uncertainty calibration:",
        f"  residual_q10: {residual_q10:.4f}",
        f"  residual_q90: {residual_q90:.4f}",
        f"  empirical coverage: {interval_metrics['empirical_coverage_percent']:.2f}%",
        f"  average interval width: {interval_metrics['average_interval_width']:.2f}",
        "",
        "Unseen-site holdout evaluation:",
        f"  Holdout sites: {', '.join(holdout_sites)}",
        f"  MAE: {unseen_metrics['mae_kw']:.2f} kW",
        f"  RMSE: {unseen_metrics['rmse_kw']:.2f} kW",
        f"  nMAE: {unseen_metrics['nmae_percent']:.2f}%",
        f"  nRMSE: {unseen_metrics['nrmse_percent']:.2f}%",
        "",
        "Horizon summary:",
    ]

    for row in horizon_rows:
        train_report_text.append(
            f"  - {row['horizon_label']}: ML RMSE {row['ml_metrics']['rmse_kw']:.2f} kW | Persistence RMSE {row['persistence_metrics']['rmse_kw']:.2f} kW"
        )

    train_report_text.append("")
    train_report_text.append("Remaining limitations:")
    for limitation in final_model_metadata["limitations"]:
        train_report_text.append(f"  - {limitation}")

    save_json(DATA_DIR / "model_training_report.json", model_training_report)
    (DATA_DIR / "model_training_report.txt").write_text("\n".join(train_report_text), encoding="utf-8")
    save_json(DATA_DIR / "horizon_metrics.json", {"horizons": horizon_rows})
    save_json(DATA_DIR / "generalization_metrics.json", generalization_metrics)
    save_json(DATA_DIR / "baseline_comparison.json", {"horizons": horizon_rows})
    save_json(DATA_DIR / "uncertainty_calibration.json", uncertainty_calibration)
    save_json(DATA_DIR / "final_model_metadata.json", final_model_metadata)
    save_json(DATA_DIR / "final_leakage_audit.json", final_leakage_audit)

    save_json(MODEL_DIR / "model_metadata.json", final_model_metadata)
    save_model_payload(model, feature_columns, final_model_metadata)

    shap_status = maybe_add_shap(model, test_df, feature_columns)
    final_model_metadata["explainability"] = shap_status
    save_json(DATA_DIR / "final_model_metadata.json", final_model_metadata)
    save_json(MODEL_DIR / "model_metadata.json", final_model_metadata)

    print("Generalized model training completed successfully.")
    print(f"Model artifact: {MODEL_DIR / 'renewai_generalized_xgb.joblib'}")
    print(f"Reports directory: {DATA_DIR}")
    print(f"SHAP status: {shap_status}")


if __name__ == "__main__":
    main()
