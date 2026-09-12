from __future__ import annotations

import json
from pathlib import Path

import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_ARTIFACT_PATH = PROJECT_ROOT / "ml" / "models" / "renewai_generalized_xgb.joblib"
METADATA_PATH = PROJECT_ROOT / "ml" / "models" / "model_metadata.json"
FINAL_MODEL_METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "generalized_training" / "final_model_metadata.json"
MODEL_ARTIFACT_RELATIVE_PATH = "ml/models/renewai_generalized_xgb.joblib"


def require_file(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required {description}: {path}")


def load_json(path: Path):
    require_file(path, "JSON artifact")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_model_payload() -> dict:
    require_file(MODEL_ARTIFACT_PATH, "model artifact")
    payload = joblib.load(MODEL_ARTIFACT_PATH)
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected model artifact structure in {MODEL_ARTIFACT_PATH}")

    feature_columns = payload.get("feature_columns")
    if not isinstance(feature_columns, list) or not feature_columns:
        raise ValueError(
            f"Saved model artifact is missing a valid feature_columns list: {MODEL_ARTIFACT_PATH}"
        )

    model_version = payload.get("model_version")
    if not model_version:
        raise ValueError(
            f"Saved model artifact is missing a model_version entry: {MODEL_ARTIFACT_PATH}"
        )

    return payload


def build_metadata() -> dict:
    if FINAL_MODEL_METADATA_PATH.exists():
        metadata = load_json(FINAL_MODEL_METADATA_PATH)
        metadata["model_artifact"] = MODEL_ARTIFACT_RELATIVE_PATH
        metadata["training_timestamp"] = metadata.get("training_date", "unknown")
        return metadata

    model_payload = load_model_payload()
    metadata = model_payload.get("metadata")

    if not isinstance(metadata, dict):
        raise ValueError(
            f"Saved model artifact is missing a metadata dictionary: {MODEL_ARTIFACT_PATH}"
        )

    metadata = dict(metadata)
    metadata["model_version"] = model_payload.get("model_version")
    metadata["model_artifact"] = MODEL_ARTIFACT_RELATIVE_PATH
    metadata["feature_columns"] = list(model_payload["feature_columns"])

    if "training_timestamp" not in metadata:
        metadata["training_timestamp"] = "unknown"

    return metadata


def write_metadata(metadata: dict) -> Path:
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METADATA_PATH.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
        handle.write("\n")

    return METADATA_PATH


def print_summary(metadata: dict) -> None:
    print("Model metadata generated successfully.")
    print("\nVerification summary:")
    print(f"- model version: {metadata.get('model_version')}")
    print(f"- model type: {metadata.get('model_type')}")
    print(f"- number of features: {len(metadata.get('feature_columns', []))}")
    print(f"- artifact path: {metadata.get('model_artifact')}")
    print(f"- metadata file path: ml/models/model_metadata.json")


def main() -> None:
    metadata = build_metadata()
    write_metadata(metadata)
    print_summary(metadata)


if __name__ == "__main__":
    main()
