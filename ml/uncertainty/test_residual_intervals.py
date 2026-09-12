import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.uncertainty.residual_intervals import (
    calculate_residual_quantiles,
    calculate_residuals,
    create_interval_predictions,
    enforce_interval_constraints,
    evaluate_interval_coverage,
)


class TestResidualIntervals(unittest.TestCase):
    def test_residual_calculation_works(self):
        actual = pd.Series([10.0, 12.0, 15.0])
        predicted = pd.Series([8.0, 11.0, 14.0])

        residuals = calculate_residuals(actual, predicted)

        self.assertListEqual(residuals.tolist(), [2.0, 1.0, 1.0])

    def test_quantile_calculation_works(self):
        residuals = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        quantiles = calculate_residual_quantiles(residuals)

        self.assertLess(quantiles["q10"], quantiles["q90"])
        self.assertIn("residual_mean", quantiles)

    def test_p10_p50_p90_ordering(self):
        intervals = create_interval_predictions(
            predictions=pd.Series([100.0, 200.0]),
            residual_q10=-5.0,
            residual_q90=10.0,
        )

        self.assertTrue((intervals["p10"] <= intervals["p50"]).all())
        self.assertTrue((intervals["p50"] <= intervals["p90"]).all())

    def test_negative_intervals_are_clipped_to_zero(self):
        intervals = pd.DataFrame({
            "p10": [-50.0, 10.0],
            "p50": [-20.0, 20.0],
            "p90": [-10.0, 30.0],
        })

        constrained = enforce_interval_constraints(intervals)

        self.assertTrue((constrained["p10"] >= 0).all())
        self.assertTrue((constrained["p50"] >= 0).all())
        self.assertTrue((constrained["p90"] >= 0).all())

    def test_capacity_clipping_works(self):
        intervals = pd.DataFrame({
            "p10": [200.0],
            "p50": [250.0],
            "p90": [300.0],
        })

        constrained = enforce_interval_constraints(intervals, capacity_kw=250.0)

        self.assertTrue((constrained["p10"] <= 250.0).all())
        self.assertTrue((constrained["p50"] <= 250.0).all())
        self.assertTrue((constrained["p90"] <= 250.0).all())

    def test_nighttime_values_can_be_forced_to_zero(self):
        intervals = pd.DataFrame({
            "p10": [50.0],
            "p50": [60.0],
            "p90": [70.0],
        })

        constrained = enforce_interval_constraints(
            intervals,
            force_nighttime_zero=pd.Series([True]),
        )

        self.assertEqual(constrained.iloc[0]["p10"], 0.0)
        self.assertEqual(constrained.iloc[0]["p50"], 0.0)
        self.assertEqual(constrained.iloc[0]["p90"], 0.0)

    def test_interval_coverage_calculation_works(self):
        coverage = evaluate_interval_coverage(
            actual=pd.Series([100.0, 200.0, 300.0]),
            p10=pd.Series([80.0, 150.0, 250.0]),
            p90=pd.Series([120.0, 250.0, 350.0]),
        )

        self.assertGreaterEqual(coverage["interval_coverage"], 0.0)
        self.assertEqual(coverage["test_rows"], 3)


if __name__ == "__main__":
    unittest.main()
