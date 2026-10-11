"""The reader must never crash on the shape of a model's answer (2026-10-11: non_normative as a list of triples killed
the whole build). A fake model returns known shape variations; read() must finish with an IR."""
import json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from reader import read as R, llm, shapes as S

KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
GOLD = json.load(open(os.path.join(ROOT, "ir", "brief_a.json"), encoding="utf-8"))


class FakeModel(object):
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def __call__(self, system, prompt, purpose, **k):
        self.calls.append(purpose)
        reply = self.script.pop(0) if self.script else "{}"
        return reply if isinstance(reply, str) else json.dumps(reply)


class ReaderShapes(unittest.TestCase):
    def run_read(self, script):
        fake = FakeModel(script)
        old = llm.call
        llm.call = fake
        try:
            ir, st, inv = R.read([os.path.join(KIT, "briefs", "brief-a.md")], os.path.join(KIT, "tools", "openapi.json"),
                                 max_repairs=1, log=lambda m: None)
        finally:
            llm.call = old
        return ir, inv, fake

    def test_variations_do_not_crash(self):
        gold_wrapped = {"policy_ir": dict(GOLD, templates=[dict(v if isinstance(v, dict) else {"text": v}, id=k)
                                                           for k, v in GOLD["templates"].items()])}
        script = [
            {"inventory": {"units": [{"sids": ["D1.s001"], "kind": "x"}], "non_normative": [["D1.s002", "heading", "x"]]}},
            {"units": [], "non_normative": [["D1.s003", "intro"]]},           # gap fill (the exact crash shape)
            "sorry, here is my answer without JSON",                           # compile: unusable -> asked again
            gold_wrapped,                                                      # compile retry: wrapped + templates as list
            "not json either",                                                 # repair: unusable -> asked again
            "still not json",                                                  # repair retry fails -> keep best IR
        ]
        ir, inv, fake = self.run_read(script)
        self.assertTrue(ir.get("rules"))
        self.assertIsInstance(ir["templates"], dict)
        self.assertIn("D1.s002", inv["non_normative"])
        self.assertTrue(any("retry" in c for c in fake.calls))

    def test_inventory_total_failure_still_compiles(self):
        ir, inv, fake = self.run_read(["???", "???", GOLD, GOLD, GOLD])
        self.assertTrue(ir.get("rules"))
        self.assertEqual(inv["units"], [])


if __name__ == "__main__":
    unittest.main()
