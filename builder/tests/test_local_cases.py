"""Regression: the gold IRs must pass every practice case in the local simulator (ledger checks)."""
import json, os, sys, unittest
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
from sim import run_local as R

class LocalCases(unittest.TestCase):
    def check(self, ir_file, brief):
        ir = json.load(open(os.path.join(ROOT, "ir", ir_file), encoding="utf-8"))
        cases = [c for c in json.load(open(os.path.join(R.KIT, "public-test-set.json"))) if c["brief"] == brief]
        for c in cases:
            with self.subTest(case=c["id"]):
                res, led, m = R.run_case(ir, c)
                self.assertTrue(res["pass"], "%s: %s" % (c["id"], res["failed"]))
                self.assertFalse([t for t in m.s["trace"] if t["kind"] == "rule_error"], c["id"])

    def test_brief_a(self):
        self.check("brief_a.json", "A")

    def test_brief_b(self):
        self.check("brief_b.json", "B")

if __name__ == "__main__":
    unittest.main()
