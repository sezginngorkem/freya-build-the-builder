import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine import expr as E

CAL = {"workdays": ["Mon", "Tue", "Wed", "Thu", "Fri"], "holidays": ["2026-10-26"]}
F = E.make_functions(CAL)
CTX = {"call": {"now": "2026-10-14T11:00"}, "item": {"type": "credit_card", "days_late": 9, "past_due": 220.0, "minimum_payment": 66.0},
       "band": {"deadline_bd": 7}, "counter": {"wrong_answers": 3}, "flag": {"verified": False}, "today": "2026-10-14",
       "items": [{"note": "paid"}, {"note": "refused"}]}


class Expr(unittest.TestCase):
    def ev(self, s):
        return E.evaluate(s, CTX, F)

    def test_basic(self):
        self.assertTrue(self.ev("item.type == 'credit_card'"))
        self.assertTrue(self.ev("counter.wrong_answers >= 3 and not flag.verified"))
        self.assertEqual(self.ev("item.minimum_payment if item.type == 'credit_card' else item.instalment_amount"), 66.0)
        self.assertTrue(self.ev("between(item.days_late, 8, 45)"))
        self.assertFalse(self.ev("between(item.days_late, 1, 7)"))

    def test_dates(self):
        self.assertEqual(self.ev("add_business_days(today, band.deadline_bd)"), "2026-10-23")
        self.assertTrue(self.ev("'2026-10-16' <= add_business_days(today, band.deadline_bd)"))
        self.assertFalse(self.ev("is_business_day('2026-10-26')"))

    def test_lists(self):
        self.assertEqual(self.ev("first_where_not(items, 'note', 'paid')"), {"note": "refused"})
        self.assertFalse(self.ev("all_where(items, 'note', 'paid')"))

    def test_missing_is_none(self):
        self.assertIsNone(self.ev("slot.promise_date"))
        self.assertFalse(self.ev("slot.promise_date <= '2026-10-23'"))

    def test_safety(self):
        for bad in ["__import__('os')", "item.__class__", "open('x')", "[x for x in items]", "lambda: 1"]:
            with self.assertRaises(E.ExprError):
                self.ev(bad)

    def test_names_used(self):
        names, funcs = E.names_used("add_business_days(today, band.deadline_bd) and flag.verified")
        self.assertEqual(names, {"today", "band.deadline_bd", "flag.verified"})
        self.assertEqual(funcs, {"add_business_days"})


if __name__ == "__main__":
    unittest.main()
