"""The bank says the identity check is over and keeps saying it: the agent must end the check, not ask forever."""
import json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.machine import Machine

# a read whose "unreadable answer -> ask again" rule has no limit (the call that looped on Freya)
IR = json.load(open(os.path.join(ROOT, "tests", "data", "ir_s8_unread_rule.json"), encoding="utf-8"))
VARS = {"customer_id": "c1", "first_name": "Owen", "last_name": "Park", "title": "Mr", "now": "2026-10-14T11:00"}
OVER = {"ok": False, "verified": False, "wrong_answers_left": 0, "error": "identity check is over"}


class TestCheckOver(unittest.TestCase):
    def test_repeated_check_over_ends_the_call(self):
        m = Machine(IR, VARS)
        m.handle({"type": "start"})
        m.handle({"type": "user", "text": "Yes, this is Owen.", "intents": ["confirm_identity"], "slots": {}})
        calls = 0
        for i in range(12):
            out = m.handle({"type": "user", "text": "6603", "intents": [], "slots": {"id_phone_last4": "66%02d" % i}})
            while any(o.get("call") == "verify_identity" for o in out):
                calls += 1
                out = m.handle({"type": "tool", "name": "verify_identity", "ok": True, "data": dict(OVER)})
            if m.s["ended"] or any(o.get("call") == "close_call" for o in out):
                break
        self.assertTrue(m.s["ended"] or any(o.get("call") == "close_call" for o in out), "the check never ended")
        self.assertLessEqual(calls, 4)


if __name__ == "__main__":
    unittest.main()
