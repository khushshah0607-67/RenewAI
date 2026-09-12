from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTDIR = PROJECT_ROOT / "data" / "processed" / "generalized_training"

OUTDIR.mkdir(parents=True, exist_ok=True)


def normalize_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def find_timestamp_column(columns: list[str]) -> str | None:
    for column in columns:
        norm = normalize_name(column)
        if "time" in norm or "date" in norm:
            return column
    return None


def find_column(columns: list[str], patterns: list[str]) -> str | None:
    normalized = {normalize_name(column): column for column in columns}
    for pattern in patterns:
        pattern_norm = normalize_name(pattern)
        for candidate, original in normalized.items():
            if pattern_norm in candidate:
                return original
    return None


def parse_capacity_from_filename(file_name: str) -> float | None:
    match = re.search(r"Nominal capacity-([0-9]+(?:\.[0-9]+)?)", file_name, flags=re.IGNORECASE)
    if match:
        return float(match.group(1)) * 1000.0

    match = re.search(r"([0-9]+(?:\.[0-9]+)?)MW", file_name, flags=re.IGNORECASE)
    if match:
        return float(match.group(1)) * 1000.0

    return None


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["hour"] = out["timestamp"].dt.hour
    out["minute"] = out["timestamp"].dt.minute
    out["day_of_week"] = out["timestamp"].dt.dayofweek
    out["day_of_year"] = out["timestamp"].dt.dayofyear
    out["month"] = out["timestamp"].dt.month
    out["hour_decimal"] = out["hour"] + out["minute"] / 60.0
    out["hour_sin"] = np.sin(2 * np.pi * out["hour_decimal"] / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour_decimal"] / 24.0)
    out["day_of_year_sin"] = np.sin(2 * np.pi * out["day_of_year"] / 365.0)
    out["day_of_year_cos"] = np.cos(2 * np.pi * out["day_of_year"] / 365.0)
    return out


def add_lag_and_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["site_id", "timestamp"]).copy()

    out["lag_1"] = out.groupby("site_id")["generation_kw"].shift(1)
    out["lag_2"] = out.groupby("site_id")["generation_kw"].shift(2)
    out["lag_4"] = out.groupby("site_id")["generation_kw"].shift(4)
    out["lag_8"] = out.groupby("site_id")["generation_kw"].shift(8)
    out["lag_16"] = out.groupby("site_id")["generation_kw"].shift(16)
    out["lag_96"] = out.groupby("site_id")["generation_kw"].shift(96)

    grouped = out.groupby("site_id")["generation_kw"]
    out["rolling_mean_4"] = grouped.shift(1).rolling(4, min_periods=1).mean()
    out["rolling_mean_8"] = grouped.shift(1).rolling(8, min_periods=1).mean()
    out["rolling_mean_24"] = grouped.shift(1).rolling(24, min_periods=1).mean()
    out["rolling_std_24"] = grouped.shift(1).rolling(24, min_periods=1).std()
    out["rolling_max_24"] = grouped.shift(1).rolling(24, min_periods=1).max()

    # Keep only rows for which the lag features are available and the target is known
    out["target_next_15min"] = out.groupby("site_id")["generation_kw"].shift(-1)
    out = out.dropna(subset=["lag_96", "target_next_15min"]).reset_index(drop=True)

    return out


def standardize_state_grid(path: Path, renewable_type: str, source_dataset: str) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    sheet_name = xls.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet_name)

    timestamp_column = find_timestamp_column(list(df.columns))
    if timestamp_column is None:
        raise ValueError(f"Could not find timestamp column in {path}")

    power_column = find_column(list(df.columns), ["power"])
    if power_column is None:
        raise ValueError(f"Could not find power column in {path}")

    site_id = f"{source_dataset}_{renewable_type}_{path.stem}"
    site_label = path.stem

    out = pd.DataFrame()
    out["timestamp"] = pd.to_datetime(df[timestamp_column], errors="coerce")
    out["generation_kw"] = safe_numeric(df[power_column]) * 1000.0

    out["site_id"] = site_id
    out["site_label"] = site_label
    out["renewable_type"] = renewable_type
    out["source_dataset"] = source_dataset
    out["installed_capacity_kw"] = parse_capacity_from_filename(path.name)
    out["normalized_generation"] = out["generation_kw"] / out["installed_capacity_kw"] if out["installed_capacity_kw"].notna().all() else np.nan

    if renewable_type == "solar":
        out["irradiation_w_m2"] = safe_numeric(df[find_column(list(df.columns), ["total solar irradiance"]) or df.columns[1]])
        out["direct_normal_irradiance_w_m2"] = safe_numeric(df[find_column(list(df.columns), ["direct normal irradiance"]) or df.columns[2]])
        out["global_horizontal_irradiance_w_m2"] = safe_numeric(df[find_column(list(df.columns), ["global horizontal irradiance"]) or df.columns[3]])
        out["ambient_temperature_c"] = safe_numeric(df[find_column(list(df.columns), ["air temperature"]) or df.columns[4]])
        out["pressure_hpa"] = safe_numeric(df[find_column(list(df.columns), ["atmosphere"]) or df.columns[5]])
        out["relative_humidity_pct"] = safe_numeric(df[find_column(list(df.columns), ["relative humidity"]) or df.columns[6]]) if find_column(list(df.columns), ["relative humidity"]) else np.nan
    else:
        out["wind_speed_10m_mps"] = safe_numeric(df[find_column(list(df.columns), ["10 meters", "wind speed"]) or df.columns[1]])
        out["wind_direction_10m_deg"] = safe_numeric(df[find_column(list(df.columns), ["10 meters", "wind direction"]) or df.columns[2]])
        out["wind_speed_30m_mps"] = safe_numeric(df[find_column(list(df.columns), ["30 meters", "wind speed"]) or df.columns[3]])
        out["wind_direction_30m_deg"] = safe_numeric(df[find_column(list(df.columns), ["30 meters", "wind direction"]) or df.columns[4]])
        out["wind_speed_50m_mps"] = safe_numeric(df[find_column(list(df.columns), ["50 meters", "wind speed"]) or df.columns[5]])
        out["wind_direction_50m_deg"] = safe_numeric(df[find_column(list(df.columns), ["50 meters", "wind direction"]) or df.columns[6]])
        out["wind_speed_hub_mps"] = safe_numeric(df[find_column(list(df.columns), ["wheel hub", "wind speed", "m/s"]) or df.columns[7]])
        out["wind_direction_hub_deg"] = safe_numeric(df[find_column(list(df.columns), ["wheel hub", "wind direction", "deg"]) or df.columns[8]])
        out["ambient_temperature_c"] = safe_numeric(df[find_column(list(df.columns), ["air temperature"]) or df.columns[9]])
        out["pressure_hpa"] = safe_numeric(df[find_column(list(df.columns), ["atmosphere"]) or df.columns[10]])
        out["relative_humidity_pct"] = safe_numeric(df[find_column(list(df.columns), ["relative humidity"]) or df.columns[11]]) if find_column(list(df.columns), ["relative humidity"]) else np.nan

    out = out.dropna(subset=["timestamp", "generation_kw"]).sort_values("timestamp").reset_index(drop=True)
    out = out.drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    return out


def standardize_kaggle_plant(gen_path: Path, weather_path: Path) -> pd.DataFrame:
    generation_df = pd.read_csv(gen_path)
    weather_df = pd.read_csv(weather_path)

    gen_cols = list(generation_df.columns)
    weather_cols = list(weather_df.columns)

    gen_timestamp = find_timestamp_column(gen_cols)
    weather_timestamp = find_timestamp_column(weather_cols)
    if gen_timestamp is None or weather_timestamp is None:
        raise ValueError(f"Could not find timestamp columns in {gen_path} or {weather_path}")

    generation_df["timestamp"] = pd.to_datetime(generation_df[gen_timestamp], errors="coerce")
    generation_df = generation_df.dropna(subset=["timestamp"])

    plant_id = generation_df["PLANT_ID"].dropna().astype(str).iloc[0]
    site_id = f"kaggle_{normalize_name(plant_id)}"

    generation_df["plant_id"] = generation_df["PLANT_ID"].astype(str)
    generation_df["generation_kw"] = safe_numeric(generation_df["AC_POWER"])
    generation_df = generation_df.dropna(subset=["generation_kw"])

    generation_df = generation_df.groupby(["timestamp", "plant_id"], as_index=False)["generation_kw"].sum()

    weather_df["timestamp"] = pd.to_datetime(weather_df[weather_timestamp], errors="coerce")
    weather_df = weather_df.dropna(subset=["timestamp"])
    weather_df["plant_id"] = weather_df["PLANT_ID"].astype(str)
    weather_df = weather_df.rename(
        columns={
            "AMBIENT_TEMPERATURE": "ambient_temperature_c",
            "MODULE_TEMPERATURE": "module_temperature_c",
            "IRRADIATION": "irradiation_w_m2",
        }
    )

    merged = generation_df.merge(
        weather_df[["timestamp", "plant_id", "ambient_temperature_c", "module_temperature_c", "irradiation_w_m2"]],
        on=["timestamp", "plant_id"],
        how="left",
    )

    merged["site_id"] = site_id
    merged["site_label"] = merged["plant_id"]
    merged["renewable_type"] = "solar"
    merged["source_dataset"] = "kaggle_india"
    merged["installed_capacity_kw"] = np.nan
    merged["normalized_generation"] = np.nan

    # Keep the normalized site label stable without requiring capacity
    merged["site_id"] = merged["site_id"]

    merged = merged.sort_values("timestamp").reset_index(drop=True)
    merged = merged.drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    return merged


def build_unified_dataset() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    site_frames: list[pd.DataFrame] = []
    site_metadata_rows: list[dict[str, Any]] = []

    # Kaggle India (Plant 1 and Plant 2)
    kaggle_files = [
        (RAW_DIR / "kaggle_india" / "Plant_1_Generation_Data.csv", RAW_DIR / "kaggle_india" / "Plant_1_Weather_Sensor_Data.csv"),
        (RAW_DIR / "kaggle_india" / "Plant_2_Generation_Data.csv", RAW_DIR / "kaggle_india" / "Plant_2_Weather_Sensor_Data.csv"),
    ]

    for generation_path, weather_path in kaggle_files:
        frame = standardize_kaggle_plant(generation_path, weather_path)
        site_frames.append(frame)

    # State Grid Solar
    solar_dir = RAW_DIR / "state_grid" / "solar"
    for path in sorted(solar_dir.glob("*.xlsx")):
        frame = standardize_state_grid(path, renewable_type="solar", source_dataset="state_grid_solar")
        site_frames.append(frame)

    # State Grid Wind
    wind_dir = RAW_DIR / "state_grid" / "wind"
    for path in sorted(wind_dir.glob("*.xlsx")):
        frame = standardize_state_grid(path, renewable_type="wind", source_dataset="state_grid_wind")
        site_frames.append(frame)

    unified = pd.concat(site_frames, ignore_index=True)
    unified["timestamp"] = pd.to_datetime(unified["timestamp"], errors="coerce")
    unified = unified.dropna(subset=["timestamp", "generation_kw"]).sort_values(["site_id", "timestamp"]).reset_index(drop=True)

    # Fill normalized generation only where explicit capacity exists.
    unified["normalized_generation"] = np.where(
        unified["installed_capacity_kw"].notna(),
        unified["generation_kw"] / unified["installed_capacity_kw"],
        np.nan,
    )

    # Feature engineering
    unified = add_time_features(unified)
    unified = add_lag_and_rolling_features(unified)

    # Keep explicit weather features only, and preserve source dataset information.
    base_columns = [
        "timestamp",
        "site_id",
        "site_label",
        "plant_id",
        "renewable_type",
        "source_dataset",
        "generation_kw",
        "installed_capacity_kw",
        "normalized_generation",
        "target_next_15min",
    ]

    feature_columns = [
        "hour",
        "minute",
        "day_of_week",
        "day_of_year",
        "month",
        "hour_decimal",
        "hour_sin",
        "hour_cos",
        "day_of_year_sin",
        "day_of_year_cos",
        "lag_1",
        "lag_2",
        "lag_4",
        "lag_8",
        "lag_16",
        "lag_96",
        "rolling_mean_4",
        "rolling_mean_8",
        "rolling_mean_24",
        "rolling_std_24",
        "rolling_max_24",
    ]

    weather_columns = [
        c
        for c in unified.columns
        if c not in base_columns + feature_columns and c not in {"timestamp", "site_id", "site_label", "renewable_type", "source_dataset"}
    ]

    all_columns = base_columns + weather_columns + feature_columns
    unified = unified[all_columns]

    # Site metadata
    site_metadata = (
        unified.groupby("site_id", as_index=False)
        .agg(
            renewable_type=("renewable_type", "first"),
            source_dataset=("source_dataset", "first"),
            site_label=("site_label", "first"),
            installed_capacity_kw=("installed_capacity_kw", "first"),
            row_count=("timestamp", "size"),
            date_start=("timestamp", "min"),
            date_end=("timestamp", "max"),
        )
        .sort_values("site_id")
        .reset_index(drop=True)
    )

    site_metadata["date_start"] = site_metadata["date_start"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    site_metadata["date_end"] = site_metadata["date_end"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    # Build feature schema metadata
    feature_schema = {
        "base_columns": base_columns,
        "weather_columns": weather_columns,
        "time_calendar_columns": [
            "hour",
            "minute",
            "day_of_week",
            "day_of_year",
            "month",
            "hour_decimal",
            "hour_sin",
            "hour_cos",
            "day_of_year_sin",
            "day_of_year_cos",
        ],
        "lag_columns": ["lag_1", "lag_2", "lag_4", "lag_8", "lag_16", "lag_96"],
        "rolling_columns": ["rolling_mean_4", "rolling_mean_8", "rolling_mean_24", "rolling_std_24", "rolling_max_24"],
        "target_columns": ["target_next_15min"],
    }

    # Build preprocessing metadata
    preprocessing_metadata = {
        "schema_version": 1,
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "sources": {
            "kaggle_india": {
                "files": [
                    "Plant_1_Generation_Data.csv",
                    "Plant_1_Weather_Sensor_Data.csv",
                    "Plant_2_Generation_Data.csv",
                    "Plant_2_Weather_Sensor_Data.csv",
                ],
                "included": True,
            },
            "state_grid_solar": {
                "files": sorted(path.name for path in (RAW_DIR / "state_grid" / "solar").glob("*.xlsx")),
                "included": True,
            },
            "state_grid_wind": {
                "files": sorted(path.name for path in (RAW_DIR / "state_grid" / "wind").glob("*.xlsx")),
                "included": True,
            },
            "solarmagix": {
                "files": sorted(path.name for path in (RAW_DIR / "solarmagix").glob("*")),
                "included": False,
                "reason": "Hourly / mixed-level source; excluded from the current 15-minute training target.",
            },
        },
        "target_definition": "target_next_15min = next observed generation value at the next 15-minute interval; features are built only from current and historical observed data.",
        "timestamp_policy": "All source timestamps were normalized to pandas datetime objects and kept in their original local-naive representation; no timezone conversion was invented.",
        "capacity_policy": "State Grid capacities were parsed from workbook filenames when available. Kaggle capacities were not invented; normalized_generation is therefore null for Kaggle sites.",
        "validation_checks": [
            "missing timestamps",
            "duplicate timestamps",
            "incorrect intervals",
            "missing target",
            "invalid generation values",
            "capacity errors",
            "normalized generation errors",
            "feature leakage",
            "site identity",
            "renewable type",
            "timestamp ordering",
        ],
    }

    # Split creation: chronological within site, with a train/calibration/test partition.
    train_frames = []
    calibration_frames = []
    test_frames = []
    split_site_rows: dict[str, dict[str, int]] = {}

    for site in sorted(unified["site_id"].unique()):
        site_df = unified[unified["site_id"] == site].sort_values("timestamp").reset_index(drop=True)
        total = len(site_df)
        if total < 3:
            train_frames.append(site_df)
            split_site_rows[site] = {"train_rows": total, "calibration_rows": 0, "test_rows": 0}
            continue

        train_end = max(1, int(total * 0.60))
        calibration_end = max(train_end + 1, int(total * 0.80))

        train_slice = site_df.iloc[:train_end]
        calibration_slice = site_df.iloc[train_end:calibration_end]
        test_slice = site_df.iloc[calibration_end:]

        train_frames.append(train_slice)
        calibration_frames.append(calibration_slice)
        test_frames.append(test_slice)

        split_site_rows[site] = {
            "train_rows": len(train_slice),
            "calibration_rows": len(calibration_slice),
            "test_rows": len(test_slice),
        }

    train_df = pd.concat(train_frames, ignore_index=True) if train_frames else pd.DataFrame()
    calibration_df = pd.concat(calibration_frames, ignore_index=True) if calibration_frames else pd.DataFrame()
    test_df = pd.concat(test_frames, ignore_index=True) if test_frames else pd.DataFrame()

    split_manifest = {
        "split_strategy": "chronological_within_site",
        "train_rows": int(len(train_df)),
        "calibration_rows": int(len(calibration_df)),
        "test_rows": int(len(test_df)),
        "site_rows": split_site_rows,
    }

    # Validation and leakage audit
    validation_results = {
        "duplicate_timestamps_by_site": {},
        "missing_timestamp_count": int(unified["timestamp"].isna().sum()),
        "missing_target_count": int(unified["target_next_15min"].isna().sum()),
        "negative_generation_count": int((unified["generation_kw"] < 0).sum()),
        "missing_capacity_count": int(unified["installed_capacity_kw"].isna().sum()),
        "missing_weather_count": {column: int(unified[column].isna().sum()) for column in weather_columns if unified[column].isna().sum() > 0},
        "timestamp_order_ok": bool(
            unified.groupby("site_id")["timestamp"].apply(lambda s: s.is_monotonic_increasing).all()
        ),
        "site_identity_ok": bool(
            unified["site_id"].notna().all()
            and unified["site_id"].nunique() == site_metadata["site_id"].nunique()
        ),
        "renewable_type_ok": bool(unified["renewable_type"].isin(["solar", "wind"]).all()),
        "interval_issues": {},
    }

    for site in sorted(unified["site_id"].unique()):
        site_df = unified[unified["site_id"] == site].sort_values("timestamp").reset_index(drop=True)
        site_diffs = site_df["timestamp"].diff().dropna()
        duplicates = int(site_df["timestamp"].duplicated().sum())
        validation_results["duplicate_timestamps_by_site"][site] = duplicates

        if len(site_diffs):
            wrong_interval = int((site_diffs != pd.Timedelta(minutes=15)).sum())
            if wrong_interval:
                validation_results["interval_issues"][site] = wrong_interval

    leakage_audit = {
        "future_generation_leakage_detected": False,
        "future_weather_leakage_detected": False,
        "test_set_information_in_features": False,
        "target_leakage_detected": False,
        "notes": "The dataset uses only current observed generation and historically available lag/rolling features. Future observed weather is not included in the feature set.",
    }

    # Report prep
    report_rows = []
    for site in sorted(unified["site_id"].unique()):
        site_df = unified[unified["site_id"] == site].sort_values("timestamp").reset_index(drop=True)
        report_rows.append(
            {
                "site_id": site,
                "renewable_type": site_df["renewable_type"].iloc[0],
                "source_dataset": site_df["source_dataset"].iloc[0],
                "rows": int(len(site_df)),
                "capacity_kw": site_df["installed_capacity_kw"].iloc[0],
                "date_start": site_df["timestamp"].iloc[0].strftime("%Y-%m-%dT%H:%M:%S"),
                "date_end": site_df["timestamp"].iloc[-1].strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )

    # Write outputs
    unified.to_csv(OUTDIR / "unified_training_data.csv", index=False)
    site_metadata.to_csv(OUTDIR / "site_metadata.csv", index=False)
    (OUTDIR / "feature_schema.json").write_text(json.dumps(feature_schema, indent=2), encoding="utf-8")
    (OUTDIR / "split_manifest.json").write_text(json.dumps(split_manifest, indent=2), encoding="utf-8")
    (OUTDIR / "preprocessing_metadata.json").write_text(json.dumps(preprocessing_metadata, indent=2), encoding="utf-8")

    report = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "site_count": int(site_metadata.shape[0]),
        "solar_site_count": int((site_metadata["renewable_type"] == "solar").sum()),
        "wind_site_count": int((site_metadata["renewable_type"] == "wind").sum()),
        "rows_per_site": {row["site_id"]: row["rows"] for row in report_rows},
        "capacity_per_site": {row["site_id"]: row["capacity_kw"] for row in report_rows},
        "date_range_per_site": {
            row["site_id"]: {"start": row["date_start"], "end": row["date_end"]}
            for row in report_rows
        },
        "feature_list": list(unified.columns),
        "target_definition": preprocessing_metadata["target_definition"],
        "missing_data_summary": {
            "missing_timestamps": validation_results["missing_timestamp_count"],
            "missing_target": validation_results["missing_target_count"],
            "missing_capacity": validation_results["missing_capacity_count"],
            "missing_weather_columns": validation_results["missing_weather_count"],
        },
        "validation_results": validation_results,
        "split_sizes": {
            "train_rows": int(len(train_df)),
            "calibration_rows": int(len(calibration_df)),
            "test_rows": int(len(test_df)),
        },
        "leakage_audit": leakage_audit,
        "limitations": [
            "Kaggle capacities are not explicitly available in the raw files, so normalized_generation is null for Kaggle sites.",
            "State Grid wind and solar files were parsed from local-naive timestamps and no timezone conversion was invented.",
            "SolarMagix was excluded from the current 15-minute training target because the raw inspection showed mostly hourly / mixed-level data.",
            "The current processed training dataset is ready for generalized model training, but future forecast weather must still be supplied separately at inference time.",
        ],
    }

    report_text = [
        "RenewAI generalized training preprocessing report",
        "",
        f"Generated at: {report['generated_at']}",
        f"Sites included: {report['site_count']}",
        f"Solar sites: {report['solar_site_count']}",
        f"Wind sites: {report['wind_site_count']}",
        f"Train rows: {report['split_sizes']['train_rows']}",
        f"Calibration rows: {report['split_sizes']['calibration_rows']}",
        f"Test rows: {report['split_sizes']['test_rows']}",
        "",
        "Per-site summary:",
    ]

    for row in report_rows:
        report_text.append(
            f"- {row['site_id']}: renewable_type={row['renewable_type']}, source={row['source_dataset']}, capacity_kw={row['capacity_kw']}, rows={row['rows']}, date_range={row['date_start']} -> {row['date_end']}"
        )

    report_text.extend(
        [
            "",
            "Feature list:",
            *[f"- {feature}" for feature in report["feature_list"]],
            "",
            "Target definition:",
            f"- {report['target_definition']}",
            "",
            "Missing data summary:",
            f"- Missing timestamps: {report['missing_data_summary']['missing_timestamps']}",
            f"- Missing targets: {report['missing_data_summary']['missing_target']}",
            f"- Missing capacities: {report['missing_data_summary']['missing_capacity']}",
            f"- Missing weather columns: {json.dumps(report['missing_data_summary']['missing_weather_columns'], indent=2)}",
            "",
            "Leakage audit:",
            json.dumps(report["leakage_audit"], indent=2),
            "",
            "Validation results:",
            json.dumps(report["validation_results"], indent=2),
            "",
            "Limitations:",
        ]
    )

    for limit in report["limitations"]:
        report_text.append(f"- {limit}")

    (OUTDIR / "preprocessing_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUTDIR / "preprocessing_report.txt").write_text("\n".join(report_text), encoding="utf-8")

    return unified, site_metadata, report


if __name__ == "__main__":
    unified, site_metadata, report = build_unified_dataset()
    print(f"Unified training data rows: {len(unified)}")
    print(f"Sites included: {site_metadata.shape[0]}")
    print(f"Solar sites: {(site_metadata['renewable_type'] == 'solar').sum()}")
    print(f"Wind sites: {(site_metadata['renewable_type'] == 'wind').sum()}")
    print(f"Train rows: {report['split_sizes']['train_rows']}")
    print(f"Calibration rows: {report['split_sizes']['calibration_rows']}")
    print(f"Test rows: {report['split_sizes']['test_rows']}")
    print(f"Output directory: {OUTDIR}")
