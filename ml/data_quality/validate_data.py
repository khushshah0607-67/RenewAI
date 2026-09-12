import math

import pandas as pd


GENERATION_REQUIRED_COLUMNS = ["timestamp", "ac_power_kw"]
MERGED_REQUIRED_COLUMNS = [
    "timestamp",
    "ac_power_kw",
    "ambient_temperature",
    "relative_humidity",
    "cloud_cover",
    "shortwave_radiation_w_m2",
    "irradiation",
    "wind_speed",
    "wind_direction",
]

EXPECTED_FREQUENCY = "15min"
PLANT_CAPACITY_KW = 30000.0


def _normalize_columns(df):
    normalized = df.copy()

    aliases = {
        "ambient_temperature": [
            "ambient_temperature",
            "ambient_temperature_y",
            "ambient_temperature_x",
        ],
        "irradiation": [
            "irradiation",
            "irradiation_y",
            "irradiation_x",
        ],
    }

    for canonical_name, alias_candidates in aliases.items():
        if canonical_name in normalized.columns:
            continue

        for alias in alias_candidates:
            if alias in normalized.columns:
                normalized[canonical_name] = normalized[alias]
                break

    return normalized


def _validate_required_columns(df, required_columns):
    missing_columns = [column for column in required_columns if column not in df.columns]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )


def _to_datetime_series(df):
    return pd.to_datetime(df["timestamp"], errors="coerce")


def _coerce_timestamp_column(df):
    if "timestamp" not in df.columns:
        raise ValueError("Missing required column: timestamp")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def _report_missing_values(df):
    missing_values = {}
    for column in df.columns:
        count = int(df[column].isna().sum())
        if count:
            missing_values[column] = count
    return missing_values


def _report_infinite_values(df):
    infinite_values = {}

    for column in df.columns:
        numeric_series = pd.to_numeric(df[column], errors="coerce")
        infinite_mask = numeric_series.map(
            lambda value: isinstance(value, (float, int)) and not math.isfinite(value)
        )

        if infinite_mask.any():
            infinite_values[column] = int(infinite_mask.sum())

    return infinite_values


def _build_coverage_metrics(df):
    timestamps = _to_datetime_series(df).dropna().sort_values().drop_duplicates()

    if timestamps.empty:
        return {
            "start_timestamp": None,
            "end_timestamp": None,
            "duration_days": 0.0,
            "row_count": len(df),
            "expected_intervals": 0,
            "actual_intervals": 0,
            "coverage_percentage": 0.0,
        }

    start_timestamp = timestamps.iloc[0]
    end_timestamp = timestamps.iloc[-1]

    expected_intervals = 0
    if len(timestamps) > 1:
        expected_intervals = int(
            ((end_timestamp - start_timestamp).total_seconds() / 60 / 15) + 1
        )
    else:
        expected_intervals = 1

    actual_intervals = int(timestamps.shape[0])

    coverage_percentage = 0.0
    if expected_intervals > 0:
        coverage_percentage = (actual_intervals / expected_intervals) * 100

    duration_days = (end_timestamp - start_timestamp).total_seconds() / 86400

    return {
        "start_timestamp": start_timestamp.isoformat(),
        "end_timestamp": end_timestamp.isoformat(),
        "duration_days": duration_days,
        "row_count": len(df),
        "expected_intervals": expected_intervals,
        "actual_intervals": actual_intervals,
        "coverage_percentage": coverage_percentage,
    }


def _check_timezone_consistency(df):
    timestamps = _to_datetime_series(df)
    valid_timestamps = timestamps.dropna()

    if valid_timestamps.empty:
        return True, []

    tz_types = {getattr(ts, "tzinfo", None) for ts in valid_timestamps}

    if len(tz_types) <= 1:
        return True, []

    mixed_aware_issues = []
    aware_zones = {str(ts.tzinfo) for ts in valid_timestamps if getattr(ts, "tzinfo", None) is not None}
    if aware_zones:
        mixed_aware_issues.append(
            f"Timezone inconsistency detected across timestamps: {sorted(aware_zones)}"
        )

    return False, mixed_aware_issues


def _validate_timestamp_quality(df):
    errors = []
    warnings = []

    timestamps = _to_datetime_series(df)

    missing_timestamps = int(timestamps.isna().sum())
    if missing_timestamps:
        errors.append(
            f"Missing or invalid timestamps detected: {missing_timestamps}"
        )

    valid_timestamps = timestamps.dropna().sort_values()

    if valid_timestamps.empty:
        errors.append("No valid timestamps available.")
        return {
            "missing_timestamps": missing_timestamps,
            "invalid_timestamps": missing_timestamps,
            "duplicate_intervals": 0,
            "missing_intervals": 0,
            "gap_count": 0,
            "timezone_consistent": True,
            "timezone_issues": [],
            "timestamp_errors": errors,
            "timestamp_warnings": warnings,
        }

    duplicate_intervals = int(valid_timestamps.duplicated().sum())
    if duplicate_intervals:
        errors.append(
            f"Duplicate timestamps detected: {duplicate_intervals}"
        )

    original_order = valid_timestamps.copy()
    sorted_valid = valid_timestamps.sort_values()
    if not original_order.reset_index(drop=True).equals(sorted_valid.reset_index(drop=True)):
        warnings.append("Timestamps were not sorted in ascending order.")

    gap_count = 0
    if len(valid_timestamps) > 1:
        diffs = sorted_valid.diff().dropna()
        gap_count = int((diffs != pd.Timedelta(minutes=15)).sum())
        if gap_count:
            errors.append(f"Timestamp gaps detected: {gap_count}")

    timezone_consistent, timezone_issues = _check_timezone_consistency(df)
    if not timezone_consistent:
        errors.extend(timezone_issues)

    coverage = _build_coverage_metrics(df)
    missing_intervals = max(
        coverage["expected_intervals"] - coverage["actual_intervals"],
        0,
    )

    return {
        "missing_timestamps": missing_timestamps,
        "invalid_timestamps": missing_timestamps,
        "duplicate_intervals": duplicate_intervals,
        "missing_intervals": missing_intervals,
        "gap_count": gap_count,
        "timezone_consistent": timezone_consistent,
        "timezone_issues": timezone_issues,
        "timestamp_errors": errors,
        "timestamp_warnings": warnings,
    }


def _validate_numeric_quality(df):
    errors = []
    warnings = []
    anomaly_details = {
        "impossible_generation_values": 0,
        "generation_above_capacity": 0,
        "negative_generation": 0,
        "missing_weather": 0,
        "abnormal_weather_values": 0,
    }

    numeric_columns = [
        "ac_power_kw",
        "ambient_temperature",
        "relative_humidity",
        "cloud_cover",
        "shortwave_radiation_w_m2",
        "irradiation",
        "wind_speed",
        "wind_direction",
    ]

    numeric_df = df.copy()
    for column in numeric_columns:
        if column in numeric_df.columns:
            numeric_df[column] = pd.to_numeric(numeric_df[column], errors="coerce")

    missing_weather = 0
    abnormal_weather = 0
    row_mask = pd.Series(False, index=df.index)

    for column in [
        "ac_power_kw",
        "ambient_temperature",
        "relative_humidity",
        "cloud_cover",
        "shortwave_radiation_w_m2",
        "irradiation",
        "wind_speed",
        "wind_direction",
    ]:
        if column not in numeric_df.columns:
            continue

        missing_count = int(numeric_df[column].isna().sum())
        if missing_count:
            warnings.append(
                f"Column '{column}' has {missing_count} missing values."
            )
            if column != "ac_power_kw":
                missing_weather += missing_count
            else:
                missing_weather += missing_count

        infinite_mask = numeric_df[column].map(
            lambda value: isinstance(value, (float, int)) and not math.isfinite(value)
        )
        infinite_count = int(infinite_mask.sum())
        if infinite_count:
            errors.append(
                f"Column '{column}' contains {infinite_count} infinite values."
            )

        if column == "ac_power_kw":
            negative_generation = int((numeric_df[column] < 0).sum())
            if negative_generation:
                errors.append(
                    f"Column '{column}' contains {negative_generation} negative generation values."
                )
                anomaly_details["negative_generation"] = negative_generation
                row_mask |= numeric_df[column] < 0

            generation_above_capacity = int(
                (numeric_df[column] > PLANT_CAPACITY_KW).sum()
            )
            if generation_above_capacity:
                errors.append(
                    f"Column '{column}' contains {generation_above_capacity} values above the assumed plant capacity ({PLANT_CAPACITY_KW} kW)."
                )
                anomaly_details["generation_above_capacity"] = generation_above_capacity
                row_mask |= numeric_df[column] > PLANT_CAPACITY_KW

            impossible_generation = int(
                (numeric_df[column] < 0).sum() + (numeric_df[column] > PLANT_CAPACITY_KW).sum()
            )
            anomaly_details["impossible_generation_values"] = impossible_generation

        if column == "irradiation":
            negative_irradiation = int((numeric_df[column] < 0).sum())
            if negative_irradiation:
                errors.append(
                    f"Column '{column}' contains {negative_irradiation} negative irradiation values."
                )

        if column == "shortwave_radiation_w_m2":
            negative_shortwave = int((numeric_df[column] < 0).sum())
            if negative_shortwave:
                errors.append(
                    f"Column '{column}' contains {negative_shortwave} negative shortwave radiation values."
                )

    abnormal_weather = 0

    weather_bound_checks = {
        "ambient_temperature": (-50, 100),
        "relative_humidity": (0, 100),
        "cloud_cover": (0, 100),
        "shortwave_radiation_w_m2": (0, 1500),
        "irradiation": (0, 2),
        "wind_speed": (0, 100),
        "wind_direction": (0, 360),
    }

    for column, (lower, upper) in weather_bound_checks.items():
        if column not in numeric_df.columns:
            continue

        out_of_bounds = numeric_df[column].map(
            lambda value: pd.notna(value) and (value < lower or value > upper)
        )
        out_of_bounds_count = int(out_of_bounds.sum())
        if out_of_bounds_count:
            abnormal_weather += out_of_bounds_count
            errors.append(
                f"Column '{column}' contains {out_of_bounds_count} abnormal values outside the expected plausible range."
            )
            row_mask |= out_of_bounds

    anomaly_details["missing_weather"] = missing_weather
    anomaly_details["abnormal_weather_values"] = abnormal_weather

    return {
        "numeric_errors": errors,
        "numeric_warnings": warnings,
        "anomaly_details": anomaly_details,
        "anomaly_rows": row_mask,
    }


def _summarize_target(df):
    target_series = pd.to_numeric(df["ac_power_kw"], errors="coerce")

    valid_target = target_series.dropna()

    return {
        "min_ac_power_kw": float(valid_target.min()) if not valid_target.empty else None,
        "max_ac_power_kw": float(valid_target.max()) if not valid_target.empty else None,
        "mean_ac_power_kw": float(valid_target.mean()) if not valid_target.empty else None,
        "zero_generation_percentage": (
            (valid_target.eq(0).sum() / len(valid_target)) * 100
            if len(valid_target)
            else 0.0
        ),
        "negative_generation_records": int((valid_target < 0).sum()),
    }


def _summarize_weather(df):
    weather_columns = [
        "ambient_temperature",
        "relative_humidity",
        "cloud_cover",
        "shortwave_radiation_w_m2",
        "irradiation",
        "wind_speed",
        "wind_direction",
    ]

    summary = {}
    missing_values = _report_missing_values(df)

    for column in weather_columns:
        if column not in df.columns:
            continue

        numeric_series = pd.to_numeric(df[column], errors="coerce")
        valid_values = numeric_series.dropna()

        summary[column] = {
            "missing_values": int(missing_values.get(column, 0)),
            "min": float(valid_values.min()) if not valid_values.empty else None,
            "max": float(valid_values.max()) if not valid_values.empty else None,
        }

    return summary


def _assess_status(errors, warnings):
    if errors:
        return "FAIL"
    if warnings:
        return "PASS_WITH_WARNINGS"
    return "PASS"


def validate_dataset(
    df,
    dataset_name="solar_weather_merged.csv",
    required_columns=None,
    expected_frequency=EXPECTED_FREQUENCY,
):
    if df is None or not isinstance(df, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")

    if required_columns is None:
        required_columns = MERGED_REQUIRED_COLUMNS

    normalized_df = _normalize_columns(df)

    _validate_required_columns(normalized_df, required_columns)

    normalized_df = _coerce_timestamp_column(normalized_df)
    normalized_df = normalized_df.copy()

    errors = []
    warnings = []

    timestamp_details = _validate_timestamp_quality(normalized_df)
    errors.extend(timestamp_details["timestamp_errors"])
    warnings.extend(timestamp_details["timestamp_warnings"])

    numeric_details = _validate_numeric_quality(normalized_df)
    errors.extend(numeric_details["numeric_errors"])
    warnings.extend(numeric_details["numeric_warnings"])

    missing_values = _report_missing_values(normalized_df)
    if missing_values:
        warnings.append(
            f"Missing values detected: {missing_values}"
        )

    infinite_values = _report_infinite_values(normalized_df)
    if infinite_values:
        errors.append(
            f"Infinite values detected: {infinite_values}"
        )

    coverage = _build_coverage_metrics(normalized_df)

    if expected_frequency != EXPECTED_FREQUENCY:
        warnings.append(
            f"Expected frequency override requested: {expected_frequency}"
        )

    duration_days = coverage["duration_days"]
    if duration_days < 90:
        warnings.append(
            f"Historical coverage is only {duration_days:.2f} days; this is below a typical production-grade target for a renewable forecasting model."
        )

    row_count = len(normalized_df)

    duplicate_mask = normalized_df["timestamp"].duplicated(keep=False)
    duplicate_intervals = int(duplicate_mask.sum())

    invalid_timestamp_mask = normalized_df["timestamp"].isna()
    row_mask = invalid_timestamp_mask.copy()
    row_mask |= duplicate_mask

    for column in ["ac_power_kw", "ambient_temperature", "relative_humidity", "cloud_cover", "shortwave_radiation_w_m2", "irradiation", "wind_speed", "wind_direction"]:
        if column in normalized_df.columns:
            row_mask |= normalized_df[column].isna()

    for column in ["ac_power_kw", "ambient_temperature", "relative_humidity", "cloud_cover", "shortwave_radiation_w_m2", "irradiation", "wind_speed", "wind_direction"]:
        if column in normalized_df.columns:
            numeric_series = pd.to_numeric(normalized_df[column], errors="coerce")
            row_mask |= numeric_series.isna()

    anomaly_mask = numeric_details["anomaly_rows"]
    row_mask |= anomaly_mask

    rows_valid = int((~row_mask).sum())
    rows_rejected = int(row_mask.sum())

    anomaly_count = int(anomaly_mask.sum())
    if anomaly_count == 0:
        anomaly_count = sum(numeric_details["anomaly_details"].values())

    data_quality_score = 0.0
    if row_count:
        data_quality_score = round(
            (rows_valid / row_count) * coverage["coverage_percentage"],
            2,
        )

    report = {
        "status": _assess_status(errors, warnings),
        "dataset_name": dataset_name,
        "rows_received": row_count,
        "rows_valid": rows_valid,
        "rows_rejected": rows_rejected,
        "row_count": row_count,
        "start_timestamp": coverage["start_timestamp"],
        "end_timestamp": coverage["end_timestamp"],
        "duration_days": duration_days,
        "expected_frequency": expected_frequency,
        "expected_intervals": coverage["expected_intervals"],
        "actual_intervals": coverage["actual_intervals"],
        "duplicate_count": int(normalized_df["timestamp"].duplicated().sum()),
        "duplicate_intervals": duplicate_intervals,
        "missing_intervals": timestamp_details["missing_intervals"],
        "missing_timestamps": timestamp_details["missing_timestamps"],
        "invalid_timestamps": timestamp_details["invalid_timestamps"],
        "missing_values": missing_values,
        "infinite_values": infinite_values,
        "gap_count": timestamp_details["gap_count"],
        "coverage_percentage": coverage["coverage_percentage"],
        "anomaly_count": anomaly_count,
        "anomaly_details": numeric_details["anomaly_details"],
        "data_quality_score": data_quality_score,
        "timezone_consistent": timestamp_details["timezone_consistent"],
        "timezone_issues": timestamp_details["timezone_issues"],
        "target_statistics": _summarize_target(normalized_df),
        "weather_statistics": _summarize_weather(normalized_df),
        "plant_capacity_kw": PLANT_CAPACITY_KW,
        "validation_errors": errors,
        "validation_warnings": warnings,
    }

    return report


def validate_generation_data(df, dataset_name="generation_data.csv"):
    return validate_dataset(
        df,
        dataset_name=dataset_name,
        required_columns=GENERATION_REQUIRED_COLUMNS,
    )


def validate_merged_weather_generation_data(df, dataset_name="merged_data.csv"):
    return validate_dataset(
        df,
        dataset_name=dataset_name,
        required_columns=MERGED_REQUIRED_COLUMNS,
    )
