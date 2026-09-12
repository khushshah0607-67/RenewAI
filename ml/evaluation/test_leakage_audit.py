import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.evaluation.leakage_audit import run_leakage_audit


class TestLeakageAudit(unittest.TestCase):
    def test_run_leakage_audit_detects_clean_split(self):
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2020-01-01", periods=120, freq="15min"),
                "target_next_15min": list(range(120)),
                "ac_power_kw": list(range(120)),
            }
        )

        audit = run_leakage_audit(
            feature_df=df,
            model_inputs=["ac_power_kw"],
        )

        self.assertEqual(audit["leakage_status"], "PASS")
        self.assertFalse(audit["target_in_features"])
        self.assertFalse(audit["future_feature_leakage"])
        self.assertTrue(audit["split_order_valid"])


if __name__ == "__main__":
    unittest.main()
