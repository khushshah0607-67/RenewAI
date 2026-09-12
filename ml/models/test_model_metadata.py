import json
import unittest

from ml.models.create_model_metadata import METADATA_PATH, load_model_payload


class TestModelMetadata(unittest.TestCase):
    def setUp(self):
        self.metadata_path = METADATA_PATH

    def test_metadata_json_exists(self):
        self.assertTrue(self.metadata_path.exists(), f"Metadata file is missing: {self.metadata_path}")

    def test_required_top_level_fields_exist(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        required_fields = [
            "model_name",
            "model_version",
            "model_type",
            "renewable_types_supported",
            "training_data_sources",
            "feature_columns",
            "target_definition",
            "units",
            "capacity_handling",
            "training_date",
            "evaluation_metrics",
            "limitations",
            "explainability",
        ]

        for field in required_fields:
            self.assertIn(field, metadata, f"Missing required field: {field}")

    def test_model_version_exists(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertTrue(metadata["model_version"])

    def test_model_type_exists(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertEqual(metadata["model_type"], "XGBoostRegressor")

    def test_features_exists_and_is_non_empty(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertIsInstance(metadata["feature_columns"], list)
        self.assertTrue(metadata["feature_columns"])

    def test_evaluation_metrics_exist(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertIsInstance(metadata["evaluation_metrics"], dict)
        self.assertIn("seen_site_test", metadata["evaluation_metrics"])

    def test_model_artifact_uses_project_relative_path(self):
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertTrue(metadata["model_artifact"].endswith("renewai_generalized_xgb.joblib"))
        self.assertFalse(metadata["model_artifact"].startswith(("C:\\", "/")))

    def test_feature_order_matches_saved_model_when_available(self):
        payload = load_model_payload()

        with self.metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        self.assertEqual(metadata["feature_columns"], payload["feature_columns"])


if __name__ == "__main__":
    unittest.main()
