import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.data_quality.validate_data import (
    validate_generation_data,
    validate_merged_weather_generation_data,
)


class TestDataQualityValidator(unittest.TestCase):
    def test_required_columns_detected(self):
        df = pd.DataFrame({"timestamp": ["2020-01-01 00:00:00"], "ac_power_kw": [1.0]})

        report = validate_generation_data(df, dataset_name="test_generation")
        self.assertIn(report["status"], {"PASS", "PASS_WITH_WARNINGS"})

        invalid_df = df.drop(columns=["ac_power_kw"])
        with self.assertRaises(ValueError):
            validate_generation_data(invalid_df, dataset_name="test_generation")

    def test_timestamps_are_handled_correctly(self):
        df = pd.DataFrame(
            {
                "timestamp": [
                    "2020-01-01 00:00:00",
                    "2020-01-01 00:15:00",
                    "2020-01-01 00:30:00",
                ],
                "ac_power_kw": [10, 11, 12],
                "ambient_temperature": [1, 2, 3],
                "relative_humidity": [50, 55, 60],
                "cloud_cover": [0, 0, 0],
                "shortwave_radiation_w_m2": [0, 0, 0],
                "irradiation": [0, 0, 0],
                "wind_speed": [1, 1, 1],
                "wind_direction": [0, 0, 0],
            }
        )

        report = validate_merged_weather_generation_data(df, dataset_name="test_merged")
        self.assertEqual(report["row_count"], 3)
        self.assertEqual(report["duplicate_count"], 0)
        self.assertEqual(report["gap_count"], 0)

    def test_duplicate_detection_works(self):
        df = pd.DataFrame(
            {
                "timestamp": [
                    "2020-01-01 00:00:00",
                    "2020-01-01 00:00:00",
                    "2020-01-01 00:15:00",
                ],
                "ac_power_kw": [1, 1, 2],
                "ambient_temperature": [1, 1, 2],
                "relative_humidity": [50, 50, 55],
                "cloud_cover": [0, 0, 0],
                "shortwave_radiation_w_m2": [0, 0, 0],
                "irradiation": [0, 0, 0],
                "wind_speed": [1, 1, 1],
                "wind_direction": [0, 0, 0],
            }
        )

        report = validate_merged_weather_generation_data(df, dataset_name="test_duplicate")
        self.assertEqual(report["duplicate_count"], 1)

    def test_gap_detection_works(self):
        df = pd.DataFrame(
            {
                "timestamp": [
                    "2020-01-01 00:00:00",
                    "2020-01-01 00:15:00",
                    "2020-01-01 00:45:00",
                ],
                "ac_power_kw": [1, 2, 3],
                "ambient_temperature": [1, 2, 3],
                "relative_humidity": [50, 55, 60],
                "cloud_cover": [0, 0, 0],
                "shortwave_radiation_w_m2": [0, 0, 0],
                "irradiation": [0, 0, 0],
                "wind_speed": [1, 1, 1],
                "wind_direction": [0, 0, 0],
            }
        )

        report = validate_merged_weather_generation_data(df, dataset_name="test_gap")
        self.assertGreaterEqual(report["gap_count"], 1)

    def test_missing_value_detection_works(self):
        df = pd.DataFrame(
            {
                "timestamp": ["2020-01-01 00:00:00", "2020-01-01 00:15:00"],
                "ac_power_kw": [1.0, None],
                "ambient_temperature": [1.0, 2.0],
                "relative_humidity": [50.0, 55.0],
                "cloud_cover": [0.0, 0.0],
                "shortwave_radiation_w_m2": [0.0, 0.0],
                "irradiation": [0.0, 0.0],
                "wind_speed": [1.0, 1.0],
                "wind_direction": [0.0, 0.0],
            }
        )

        report = validate_merged_weather_generation_data(df, dataset_name="test_missing")
        self.assertGreaterEqual(report["missing_values"].get("ac_power_kw", 0), 1)

    def test_negative_value_detection_works(self):
        df = pd.DataFrame(
            {
                "timestamp": [
                    "2020-01-01 00:00:00",
                    "2020-01-01 00:15:00",
                ],
                "ac_power_kw": [1.0, -2.0],
                "ambient_temperature": [1.0, 2.0],
                "relative_humidity": [50.0, 55.0],
                "cloud_cover": [0.0, 0.0],
                "shortwave_radiation_w_m2": [0.0, -1.0],
                "irradiation": [0.0, -1.0],
                "wind_speed": [1.0, 1.0],
                "wind_direction": [0.0, 0.0],
            }
        )

        report = validate_merged_weather_generation_data(df, dataset_name="test_negative")
        self.assertGreaterEqual(report["target_statistics"]["negative_generation_records"], 1)
        self.assertTrue(report["validation_errors"])

    def test_coverage_calculation_works(self):
        df = pd.DataFrame(
            {
                "timestamp": [
                    "2020-01-01 00:00:00",
                    "2020-01-01 00:15:00",
                    "2020-01-01 00:30:00",
                ],
                "ac_power_kw": [1, 2, 3],
                "ambient_temperature": [1, 2, 3],
                "relative_humidity": [50, 55, 60],
                "cloud_cover": [0, 0, 0],
                "shortwave_radiation_w_m2": [0, 0, 0],
                "irradiation": [0, 0, 0],
                "wind_speed": [1, 1, 1],
                "wind_direction": [0, 0, 0],
            }
        )

        report = validate_merged_weather_generation_data(df, dataset_name="test_coverage")
        self.assertGreater(report["coverage_percentage"], 0)


if __name__ == "__main__":
    unittest.main()
