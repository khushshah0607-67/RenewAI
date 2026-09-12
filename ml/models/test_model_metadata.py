import json
import unittest
from pathlib import Path

from ml.models.create_model_metadata import METADATA_PATH, build_metadata, load_model_payload


class TestModelMetadata(unittest.TestCase):
    def setUp(self):
        self.metadata_path = METADATA_PATH

    def test_metadata_json_exists(self):
        self.assertTrue(self.metadata_path.exists(), f"Metadata file is missing: {self.metadata_path}")

    def test_required_top_level_fields_exist(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        required_fields = [
            "model_version",
            "algorithm",
            "model_type",
            "target",
            "training_period",
            "calibration_period",
            "test_period",
            "features",
            "metrics",
            "uncertainty_method",
            "plant_capacity_kw",
            "training_timestamp",
            "model_artifact",
        ]

        for field in required_fields:
            self.assertIn(field, metadata, f"Missing required field: {field}")

    def test_model_version_exists(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertTrue(metadata["model_version"])

    def test_algorithm_exists(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertEqual(metadata["algorithm"], "XGBoost")

    def test_features_exists_and_is_non_empty(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertIsInstance(metadata["features"], list)
        self.assertTrue(metadata["features"])

    def test_metrics_exist(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertIsInstance(metadata["metrics"], dict)
        self.assertIn("mae_kw", metadata["metrics"])
        self.assertIn("rmse_kw", metadata["metrics"])
        self.assertIn("nrmse_percent", metadata["metrics"])
        self.assertIn("nmae_percent", metadata["metrics"])

    def test_uncertainty_method_exists(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertTrue(metadata["uncertainty_method"])

    def test_plant_capacity_kw_is_30000(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertEqual(metadata["plant_capacity_kw"], 30000)

    def test_model_artifact_uses_project_relative_path(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertEqual(metadata["model_artifact"], "ml/models/solar_weather_xgb.joblib")
        self.assertFalse(metadata["model_artifact"].startswith(("C:\\", "/")))

    def test_feature_order_matches_saved_model_when_available(self):
        payload = load_model_payload()

        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertEqual(metadata["features"], payload["feature_columns"])


if __name__ == "__main__":
    unittest.main()
