import json
import unittest
from pathlib import Path

import pandas as pd

from ml.inference.predict_generation import predict_generation
from ml.models.create_model_metadata import METADATA_PATH

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestPredictGenerationContract(unittest.TestCase):
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

    def test_predict_generation_exists_and_is_callable(self):
        self.assertTrue(callable(predict_generation))

    def test_valid_input_produces_success_status(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        self.assertEqual(result["status"], "success")

    def test_output_contains_forecast(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        self.assertIn("forecast", result)
        self.assertTrue(result["forecast"])

    def test_forecast_timestamps_are_iso_strings(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        for item in result["forecast"]:
            self.assertIsInstance(item["timestamp"], str)
            self.assertIn("T", item["timestamp"])

    def test_forecast_contains_forecast_kw(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        for item in result["forecast"]:
            self.assertIn("forecast_kw", item)
            self.assertIsInstance(item["forecast_kw"], (int, float))

    def test_uncertainty_values_are_present_when_available(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        first_point = result["forecast"][0]
        self.assertIn("p10_kw", first_point)
        self.assertIn("p50_kw", first_point)
        self.assertIn("p90_kw", first_point)

    def test_interval_order_is_valid(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        for item in result["forecast"]:
            self.assertLessEqual(item["p10_kw"], item["p50_kw"])
            self.assertLessEqual(item["p50_kw"], item["p90_kw"])

    def test_forecast_values_are_non_negative(self):
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

    def test_output_is_json_serializable(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        serialized = json.dumps(result)
        self.assertTrue(serialized)

    def test_missing_required_input_returns_error(self):
        invalid_plant_data = {"plant_id": "solar_plant_1"}

        result = predict_generation(
            invalid_plant_data,
            self.historical_data,
            self.weather_data,
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "MISSING_DATA")

    def test_error_response_does_not_expose_traceback(self):
        invalid_plant_data = {"plant_id": "solar_plant_1"}

        result = predict_generation(
            invalid_plant_data,
            self.historical_data,
            self.weather_data,
        )

        self.assertNotIn("Traceback", result["error"]["message"])

    def test_model_version_comes_from_metadata_file(self):
        result = predict_generation(
            self.plant_data,
            self.historical_data,
            self.weather_data,
        )

        with METADATA_PATH.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertEqual(result["model_version"], metadata["model_version"])


if __name__ == "__main__":
    unittest.main()
