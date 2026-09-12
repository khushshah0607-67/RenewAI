import json
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from ml.inference.fallback import (
    build_persistence_fallback,
    coerce_dataframe,
    detect_large_timestamp_gaps,
    load_model_metadata,
    normalize_plant_data,
    sanitize_prediction,
)
from ml.inference.predict_generation import predict_generation

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestFallbackHelpers(unittest.TestCase):
    def setUp(self):
        self.plant_data = {
            "plant_id": "solar_plant_1",
            "plant_capacity_kw": 30000,
            "timezone": "UTC",
        }

        self.historical_data = pd.read_csv(
            PROJECT_ROOT / "data" / "processed" / "solar_weather_merged.csv"
        )
        self.weather_data = pd.read_csv(
            PROJECT_ROOT / "data" / "processed" / "openmeteo_forecast_weather.csv"
        )

    def test_load_model_metadata(self):
        metadata = load_model_metadata()
        self.assertEqual(metadata["model_version"], "renewai-generalized-xgb-v1")

    def test_normalize_plant_data(self):
        normalized = normalize_plant_data(self.plant_data)
        self.assertEqual(normalized["plant_id"], "solar_plant_1")
        self.assertEqual(normalized["plant_capacity_kw"], 30000)

    def test_coerce_dataframe(self):
        df = coerce_dataframe(self.historical_data, "historical_data")
        self.assertFalse(df.empty)

    def test_detect_large_timestamp_gaps(self):
        large_gap_df = pd.DataFrame(
            {
                "timestamp": [
                    pd.Timestamp("2020-01-01 00:00:00"),
                    pd.Timestamp("2020-01-01 01:30:00"),
                ]
            }
        )

        has_large_gap, details = detect_large_timestamp_gaps(large_gap_df, gap_minutes=45)
        self.assertTrue(has_large_gap)
        self.assertIn("max_gap_minutes", details)

    def test_sanitize_prediction_rejects_nan(self):
        with self.assertRaises(Exception):
            sanitize_prediction(float("nan"), 30000)

    def test_sanitize_prediction_rejects_inf(self):
        with self.assertRaises(Exception):
            sanitize_prediction(float("inf"), 30000)

    def test_sanitize_prediction_clips_to_capacity(self):
        clipped = sanitize_prediction(50000, 30000)
        self.assertEqual(clipped, 30000.0)

    def test_valid_normal_prediction_still_succeeds(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["forecast"])

    def test_missing_weather_triggers_fallback(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            None,
        )

        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["fallback_reason"], "WEATHER_UNAVAILABLE")
        self.assertTrue(result["forecast"])

    def test_insufficient_history_returns_fallback(self):
        short_history = self.historical_data.head(96).copy()

        result = predict_generation(
            self.plant_data,
            short_history,
            self.weather_data,
        )

        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["fallback_reason"], "INSUFFICIENT_HISTORY")
        self.assertEqual(len(result["forecast"]), 96)

    def test_invalid_timestamp_returns_fallback(self):
        invalid_historical = self.historical_data.copy()
        invalid_historical.loc[0, "timestamp"] = "bad"

        result = predict_generation(
            self.plant_data,
            invalid_historical,
            self.weather_data,
        )

        self.assertEqual(result["status"], "fallback")
        self.assertEqual(result["fallback_reason"], "INVALID_INPUT")
        self.assertEqual(len(result["forecast"]), 96)

    def test_duplicate_timestamps_are_detected(self):
        duplicate_historical = self.historical_data.copy()
        duplicate_historical.loc[1, "timestamp"] = duplicate_historical.loc[0, "timestamp"]

        result = predict_generation(
            self.plant_data,
            duplicate_historical,
            self.weather_data,
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["code"], "INVALID_INPUT")

    def test_model_loading_failure_returns_model_error(self):
        with patch(
            "ml.inference.predict_generation._legacy_predict_generation",
            side_effect=RuntimeError("boom"),
        ):
            result = predict_generation(
                self.plant_data,
                self.historical_data,
                self.weather_data,
            )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["code"], "MODEL_ERROR")
        self.assertNotIn("Traceback", result["error"]["message"])

    def test_nan_prediction_is_rejected(self):
        with patch(
            "ml.inference.predict_generation._legacy_predict_generation",
            return_value=[
                {
                    "timestamp": "2026-09-12T00:00:00",
                    "p10": 0.0,
                    "p50": float("nan"),
                    "p90": 0.0,
                }
            ],
        ):
            result = predict_generation(
                self.plant_data,
                self.historical_data,
                self.weather_data,
            )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["code"], "MODEL_ERROR")

    def test_infinite_prediction_is_rejected(self):
        with patch(
            "ml.inference.predict_generation._legacy_predict_generation",
            return_value=[
                {
                    "timestamp": "2026-09-12T00:00:00",
                    "p10": 0.0,
                    "p50": float("inf"),
                    "p90": 0.0,
                }
            ],
        ):
            result = predict_generation(
                self.plant_data,
                self.historical_data,
                self.weather_data,
            )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["code"], "MODEL_ERROR")

    def test_forecast_never_exceeds_capacity(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        for item in result["forecast"]:
            self.assertLessEqual(item["forecast_kw"], 30000)
            self.assertLessEqual(item["p90_kw"], 30000)

    def test_forecast_never_becomes_negative(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        for item in result["forecast"]:
            self.assertGreaterEqual(item["forecast_kw"], 0)
            self.assertGreaterEqual(item["p10_kw"], 0)
            self.assertGreaterEqual(item["p50_kw"], 0)
            self.assertGreaterEqual(item["p90_kw"], 0)

    def test_nighttime_remains_zero(self):
        weather_df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-09-12 00:00:00", periods=96, freq="15min"),
                "ambient_temperature": 30.0,
                "relative_humidity": 50.0,
                "cloud_cover": 90.0,
                "shortwave_radiation_w_m2": 0.0,
                "irradiation": 0.0,
                "wind_speed": 5.0,
                "wind_direction": 180.0,
            }
        )

        result = predict_generation(
            self.plant_data,
            self.historical_data,
            weather_df,
        )

        self.assertEqual(result["status"], "success")
        for item in result["forecast"]:
            self.assertEqual(item["forecast_kw"], 0.0)

    def test_persistence_fallback_contains_fallback_fields(self):
        metadata = load_model_metadata()
        fallback = build_persistence_fallback(
            self.plant_data,
            self.historical_data,
            self.weather_data,
            "WEATHER_UNAVAILABLE",
            metadata,
        )

        self.assertEqual(fallback["status"], "fallback")
        self.assertEqual(fallback["fallback_reason"], "WEATHER_UNAVAILABLE")
        self.assertTrue(fallback["forecast"])

    def test_fallback_json_serialization(self):
        metadata = load_model_metadata()
        fallback = build_persistence_fallback(
            self.plant_data,
            self.historical_data,
            self.weather_data,
            "WEATHER_UNAVAILABLE",
            metadata,
        )

        serialized = json.dumps(fallback)
        self.assertTrue(serialized)


if __name__ == "__main__":
    unittest.main()
