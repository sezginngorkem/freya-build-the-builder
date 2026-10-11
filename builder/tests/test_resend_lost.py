"""A bank request that got no bank answer at all (gateway error page, timeout) is sent once more; a failure the bank
itself reports goes to the brief's own failure rules unchanged (seen on Freya, final_a PUB-03: a lost date-of-birth
check was taken as 'not caught', the third wrong answer never reached the bank)."""
import json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sim import run_local as RL

IR = json.load(open(os.path.join(ROOT, "ir", "brief_a.json"), encoding="utf-8"))
KIT = json.load(open(os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder", "public-test-set.json"), encoding="utf-8"))
CASE = {c["id"]: c for c in KIT}


def run(case_id, faults, turns):
    c = dict(CASE[case_id], faults=faults)
    bank = RL.MockBank(c)
    v = dict(c["variables"]); v.setdefault("customer_id", "c_" + case_id)
    m, tr = RL.run_script(IR, v, bank, [RL.U(t[0], t[1], **(t[2] if len(t) > 2 else {})) for t in turns])
    return bank.ledger, m


PUB03 = [(["confirm_identity"], "Yes, this is Owen Park."),
         ([], "12 July 1991.", {"id_date_of_birth": "1991-07-12"}),
         ([], "21 August 1992.", {"id_date_of_birth": "1992-08-21"}),
         ([], "21 July 1990.", {"id_date_of_birth": "1990-07-21"}),
         ([], "How much do I owe?")]


class TestResendLost(unittest.TestCase):
    def test_lost_answer_is_sent_again_and_counts(self):
        led, m = run("PUB-03", [{"tool": "verify_identity", "fail_first_n": 1, "kind": "lost"}], PUB03)
        answers = [c["args"].get("answer") for c in led["calls"] if c["tool"] == "verify_identity"]
        self.assertEqual(answers[:3], ["1991-07-12", "1992-08-21", "1990-07-21"][:len(answers[:3])])
        self.assertEqual((led["outcome"], led["reason"]), ("not_verified", "failed"))

    def test_bank_reported_failure_is_not_resent(self):
        # PUB-10: the bank itself answers 500 once; the brief's own "try once more" rule handles it (one promise)
        turns = [(["confirm_identity"], "Yes."), ([], "23 February 1989.", {"id_date_of_birth": "1989-02-23"}),
                 ([], "9904", {"id_phone_last4": "9904"}), (["no"], "Not today."),
                 ([], "Friday, the full amount.", {"promise_date": "2026-10-16", "promise_amount": 365.0}), (["yes"], "Yes.")]
        led, m = run("PUB-10", [{"tool": "create_promise", "fail_first_n": 1}], turns)
        self.assertNotIn("resend_lost", [t["kind"] for t in m.s["trace"]])

    def test_lost_twice_goes_to_the_brief_rules(self):
        led, m = run("PUB-03", [{"tool": "verify_identity", "fail_first_n": 2, "kind": "lost"}], PUB03[:2])
        self.assertEqual([t["kind"] for t in m.s["trace"]].count("resend_lost"), 1)


if __name__ == "__main__":
    unittest.main()
