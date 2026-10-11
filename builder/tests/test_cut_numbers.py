"""A number cut in two by the customer ("463..." then "51", "Tuesday 2" then "7 October") is one number again."""
import os, re, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine import normalize as N

SRC = open(os.path.join(ROOT, "compiler", "glue.py"), encoding="utf-8").read()
NS = {"re": re, "IR": {}, "vars": {}}
exec(SRC[:SRC.index("def _user_event")].split("def _load_engine", 1)[0] + SRC[SRC.index("def _truthy"):SRC.index("def _user_event")], NS)
NOW = "2026-10-14T11:00"


class TestCutNumbers(unittest.TestCase):
    def test_join_cut(self):
        J = NS["_join_cut"]
        self.assertEqual(J("on Tuesday 2", "7 October."), "on Tuesday 27 October.")
        self.assertEqual(J("I can pay 4", "20 today"), "I can pay 420 today")
        self.assertEqual(J("on Friday", "the 16th"), "on Friday the 16th")

    def test_date_split_in_the_day_number(self):
        ev = NS["_join_cut"]("Yes, I can pay on Tuesday 2", "7 October.")
        self.assertEqual(NS["_grounded"](N, "date", "27 October", "2026-10-27", ev, {}, NOW, ""), "2026-10-27")

    def test_amount_split_with_cents(self):
        G = NS["_grounded"]
        self.assertEqual(G(N, "amount", "463.51", 463.51, "463 51", {}, NOW, ""), 463.51)
        self.assertEqual(G(N, "amount", "463.51", 463.51, "four sixty-three... fifty-one", {}, NOW, ""), 463.51)

    def test_numbers_said_apart_are_not_joined(self):
        self.assertIsNone(NS["_grounded"](N, "amount", "420", 420.0, "I can pay 4 on the 20th", {}, NOW, ""))


if __name__ == "__main__":
    unittest.main()
