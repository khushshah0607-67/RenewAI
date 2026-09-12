import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.data_quality.validate_data import validate_merged_weather_generation_data


ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "data" / "processed" / "solar_weather_merged.csv"
REPORT_JSON_PATH = ROOT / "data" / "processed" / "data_quality_report.json"
REPORT_TXT_PATH = ROOT / "data" / "processed" / "data_quality_report.txt"


def main():
    df = pd.read_csv(DATASET_PATH)
    report = validate_merged_weather_generation_data(
        df,
        dataset_name="solar_weather_merged.csv",
    )

    REPORT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    text_lines = [
        "RenewAI Data Quality Report",
        f"Dataset: {report['dataset_name']}",
        f"Status: {report['status']}",
        f"Rows: {report['row_count']}",
        f"Start timestamp: {report['start_timestamp']}",
        f"End timestamp: {report['end_timestamp']}",
        f"Historical coverage: {report['duration_days']:.2f} days",
        f"Expected frequency: {report['expected_frequency']}",
        f"Coverage percentage: {report['coverage_percentage']:.2f}%",
        f"Duplicate timestamps: {report['duplicate_count']}",
        f"Timestamp gaps: {report['gap_count']}",
        f"Missing values: {report['missing_values']}",
        f"Infinite values: {report['infinite_values']}",
        f"Target statistics: {report['target_statistics']}",
        f"Weather statistics: {report['weather_statistics']}",
        "",
        "Production-grade suitability:",
        (
            "The current dataset has only about 34 days of historical coverage, so it is not suitable "
            "for production-grade forecasting training without additional historical data."
        ),
    ]

    REPORT_TXT_PATH.write_text("\n".join(text_lines), encoding="utf-8")

    print("Data quality report generated.")
    print(REPORT_JSON_PATH)
    print(REPORT_TXT_PATH)


if __name__ == "__main__":
    main()
