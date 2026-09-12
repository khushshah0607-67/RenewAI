import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


DEFAULT_QUANTILES = (0.10, 0.50, 0.90)


def calculate_residuals(actual: pd.Series, predicted: pd.Series) -> pd.Series:
    """Calculate residuals for a paired actual/predicted series."""
    actual_series = pd.to_numeric(pd.Series(actual), errors="coerce")
    predicted_series = pd.to_numeric(pd.Series(predicted), errors="coerce")

    if len(actual_series) != len(predicted_series):
        raise ValueError("actual and predicted series must be the same length.")

    aligned = pd.DataFrame({"actual": actual_series, "predicted": predicted_series}).dropna()

    if aligned.empty:
        return pd.Series(dtype=float)

    return aligned["actual"] - aligned["predicted"]


def calculate_residual_quantiles(residuals: pd.Series) -> Dict[str, float]:
    """Calculate empirical residual quantiles for the 10th and 90th percentile."""
    residual_series = pd.to_numeric(pd.Series(residuals), errors="coerce").dropna()

    if residual_series.empty:
        raise ValueError("Residuals must contain at least one valid value.")

    return {
        "q10": float(residual_series.quantile(0.10)),
        "q90": float(residual_series.quantile(0.90)),
        "residual_mean": float(residual_series.mean()),
        "residual_std": float(residual_series.std(ddof=0)),
    }


def create_interval_predictions(
    predictions: pd.Series,
    residual_q10: float,
    residual_q90: float,
) -> pd.DataFrame:
    """Create P10/P50/P90 predictions from a point forecast and residual quantiles."""
    prediction_series = pd.to_numeric(pd.Series(predictions), errors="coerce")

    if prediction_series.empty:
        raise ValueError("Predictions must contain at least one valid value.")

    p50 = prediction_series.copy()
    p10 = p50 + residual_q10
    p90 = p50 + residual_q90

    result = pd.DataFrame({
        "p10": p10,
        "p50": p50,
        "p90": p90,
    })

    return result


def enforce_interval_constraints(
    intervals: pd.DataFrame,
    capacity_kw: Optional[float] = None,
    force_nighttime_zero: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Clip negative values and preserve ordering of the interval predictions."""
    constrained = intervals.copy()

    constrained["p10"] = constrained["p10"].clip(lower=0)
    constrained["p50"] = constrained["p50"].clip(lower=0)
    constrained["p90"] = constrained["p90"].clip(lower=0)

    if capacity_kw is not None:
        constrained["p10"] = constrained["p10"].clip(upper=float(capacity_kw))
        constrained["p50"] = constrained["p50"].clip(upper=float(capacity_kw))
        constrained["p90"] = constrained["p90"].clip(upper=float(capacity_kw))

    constrained["p10"] = constrained[["p10", "p50", "p90"]].min(axis=1)
    constrained["p90"] = constrained[["p10", "p50", "p90"]].max(axis=1)

    if force_nighttime_zero is not None:
        night_mask = pd.Series(force_nighttime_zero, index=constrained.index).fillna(False).astype(bool)
        constrained.loc[night_mask, ["p10", "p50", "p90"]] = 0.0

    constrained["p10"] = constrained["p10"].clip(lower=0)
    constrained["p50"] = constrained["p50"].clip(lower=0)
    constrained["p90"] = constrained["p90"].clip(lower=0)

    constrained["p10"] = constrained[["p10", "p50", "p90"]].min(axis=1)
    constrained["p90"] = constrained[["p10", "p50", "p90"]].max(axis=1)

    constrained["p10"] = constrained["p10"].clip(lower=0)
    constrained["p50"] = constrained["p50"].clip(lower=0)
    constrained["p90"] = constrained["p90"].clip(lower=0)

    constrained["p10"] = constrained["p10"].where(constrained["p10"] <= constrained["p50"], constrained["p50"])
    constrained["p90"] = constrained["p90"].where(constrained["p90"] >= constrained["p50"], constrained["p50"])

    return constrained


def evaluate_interval_coverage(
    actual: pd.Series,
    p10: pd.Series,
    p90: pd.Series,
) -> Dict[str, float]:
    """Evaluate interval coverage and violation rates on an actual series."""
    actual_series = pd.to_numeric(pd.Series(actual), errors="coerce")
    p10_series = pd.to_numeric(pd.Series(p10), errors="coerce")
    p90_series = pd.to_numeric(pd.Series(p90), errors="coerce")

    aligned = pd.DataFrame({
        "actual": actual_series,
        "p10": p10_series,
        "p90": p90_series,
    }).dropna()

    if aligned.empty:
        raise ValueError("No valid actual/p10/p90 rows available for evaluation.")

    inside_interval = (aligned["p10"] <= aligned["actual"]) & (aligned["actual"] <= aligned["p90"])
    lower_violations = aligned["actual"] < aligned["p10"]
    upper_violations = aligned["actual"] > aligned["p90"]

    interval_coverage = float(inside_interval.mean() * 100)
    lower_violation_rate = float(lower_violations.mean() * 100)
    upper_violation_rate = float(upper_violations.mean() * 100)
    average_interval_width = float((aligned["p90"] - aligned["p10"]).mean())

    return {
        "interval_coverage": interval_coverage,
        "target_coverage": 80.0,
        "average_interval_width": average_interval_width,
        "lower_violation_rate": lower_violation_rate,
        "upper_violation_rate": upper_violation_rate,
        "test_rows": len(aligned),
    }


def save_uncertainty_calibration_artifact(
    output_path: Path,
    model_version: str,
    calibration_start: str,
    calibration_end: str,
    calibration_rows: int,
    residual_q10: float,
    residual_q90: float,
    residual_mean: float,
    residual_std: float,
    calibration_mae: float,
) -> Dict[str, object]:
    artifact = {
        "method": "residual_based",
        "model_version": model_version,
        "calibration_start": calibration_start,
        "calibration_end": calibration_end,
        "calibration_rows": calibration_rows,
        "residual_q10": residual_q10,
        "residual_q90": residual_q90,
        "residual_mean": residual_mean,
        "residual_std": residual_std,
        "calibration_mae": calibration_mae,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    return artifact
