import numpy as np
import pandas as pd


TARGET_COLUMN = "target_next_15min"

MODEL_FEATURE_COLUMNS = [
    "ac_power_kw",
    "ambient_temperature",
    "relative_humidity",
    "cloud_cover",
    "shortwave_radiation_w_m2",
    "irradiation",
    "wind_speed",
    "wind_direction",
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
    "lag_24",
    "lag_96",
    "rolling_mean_4",
    "rolling_mean_12",
    "rolling_mean_24",
    "rolling_std_24",
]

WEATHER_FEATURE_COLUMNS = MODEL_FEATURE_COLUMNS

FEATURE_DATA_COLUMNS = [
    "timestamp",
    "ac_power_kw",
    TARGET_COLUMN,
    *MODEL_FEATURE_COLUMNS[1:],
]


def prepare_base_data(df):
    if "timestamp" not in df.columns:
        raise ValueError("Input dataframe must contain a 'timestamp' column.")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    if "ambient_temperature" not in df.columns:
        if "ambient_temperature_y" in df.columns:
            df["ambient_temperature"] = df["ambient_temperature_y"]
        elif "ambient_temperature_x" in df.columns:
            df["ambient_temperature"] = df["ambient_temperature_x"]
        else:
            raise ValueError(
                "Input dataframe must contain 'ambient_temperature' or "
                "'ambient_temperature_y'."
            )

    if "irradiation" not in df.columns:
        if "irradiation_y" in df.columns:
            df["irradiation"] = df["irradiation_y"]
        elif "irradiation_x" in df.columns:
            df["irradiation"] = df["irradiation_x"]
        else:
            raise ValueError(
                "Input dataframe must contain 'irradiation' or "
                "'irradiation_y'."
            )

    required_numeric = [
        "ac_power_kw",
        "relative_humidity",
        "cloud_cover",
        "shortwave_radiation_w_m2",
        "wind_speed",
        "wind_direction",
    ]

    for column in required_numeric:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def add_time_features(df):
    df = df.copy()

    df["hour"] = df["timestamp"].dt.hour
    df["minute"] = df["timestamp"].dt.minute
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["day_of_year"] = df["timestamp"].dt.dayofyear
    df["month"] = df["timestamp"].dt.month

    df["hour_decimal"] = df["hour"] + df["minute"] / 60

    df["hour_sin"] = np.sin(2 * np.pi * df["hour_decimal"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_decimal"] / 24)

    df["day_of_year_sin"] = np.sin(
        2 * np.pi * df["day_of_year"] / 365
    )
    df["day_of_year_cos"] = np.cos(
        2 * np.pi * df["day_of_year"] / 365
    )

    return df


def add_generation_lags(df):
    df = df.copy()

    df["lag_1"] = df["ac_power_kw"].shift(1)
    df["lag_2"] = df["ac_power_kw"].shift(2)
    df["lag_4"] = df["ac_power_kw"].shift(4)
    df["lag_24"] = df["ac_power_kw"].shift(24)
    df["lag_96"] = df["ac_power_kw"].shift(96)

    return df


def add_rolling_features(df):
    df = df.copy()

    shifted_generation = df["ac_power_kw"].shift(1)

    df["rolling_mean_4"] = shifted_generation.rolling(4).mean()
    df["rolling_mean_12"] = shifted_generation.rolling(12).mean()
    df["rolling_mean_24"] = shifted_generation.rolling(24).mean()
    df["rolling_std_24"] = shifted_generation.rolling(24).std()

    return df


def create_weather_features(df):
    df = prepare_base_data(df)

    if TARGET_COLUMN not in df.columns:
        df[TARGET_COLUMN] = df["ac_power_kw"].shift(-1)

    df = add_time_features(df)
    df = add_generation_lags(df)
    df = add_rolling_features(df)

    feature_df = df[FEATURE_DATA_COLUMNS].copy()
    feature_df = feature_df.dropna().reset_index(drop=True)

    return feature_df


def build_prediction_feature_frame(timestamp, weather_row, generation_history):
    if generation_history.empty:
        raise ValueError("generation_history must contain at least one value.")

    if len(generation_history) < 97:
        raise ValueError(
            "At least 97 historical generation rows are required for lag_96."
        )

    values = generation_history.to_numpy(dtype=float)
    current_power = float(values[-1])

    feature_row = {
        "ac_power_kw": current_power,
        "ambient_temperature": weather_row["ambient_temperature"],
        "relative_humidity": weather_row["relative_humidity"],
        "cloud_cover": weather_row["cloud_cover"],
        "shortwave_radiation_w_m2": weather_row["shortwave_radiation_w_m2"],
        "irradiation": weather_row["irradiation"],
        "wind_speed": weather_row["wind_speed"],
        "wind_direction": weather_row["wind_direction"],
        "hour": timestamp.hour,
        "minute": timestamp.minute,
        "day_of_week": timestamp.dayofweek,
        "day_of_year": timestamp.dayofyear,
        "month": timestamp.month,
        "hour_decimal": timestamp.hour + timestamp.minute / 60,
        "hour_sin": np.sin(
            2 * np.pi * (timestamp.hour + timestamp.minute / 60) / 24
        ),
        "hour_cos": np.cos(
            2 * np.pi * (timestamp.hour + timestamp.minute / 60) / 24
        ),
        "day_of_year_sin": np.sin(
            2 * np.pi * timestamp.dayofyear / 365
        ),
        "day_of_year_cos": np.cos(
            2 * np.pi * timestamp.dayofyear / 365
        ),
        "lag_1": values[-2],
        "lag_2": values[-3],
        "lag_4": values[-5],
        "lag_24": values[-25],
        "lag_96": values[-97],
        "rolling_mean_4": generation_history.iloc[-4:].mean(),
        "rolling_mean_12": generation_history.iloc[-12:].mean(),
        "rolling_mean_24": generation_history.iloc[-24:].mean(),
        "rolling_std_24": generation_history.iloc[-24:].std(),
    }

    feature_df = pd.DataFrame([feature_row])
    return feature_df[MODEL_FEATURE_COLUMNS]
