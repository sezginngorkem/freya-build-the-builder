"""The seven tool names stay; their fields can change (kit README). A hidden OpenAPI may use $ref / allOf, answer 201,
and rename the closing tool's fields: the builder must still send the outcome and reason under the tool's own names."""
import json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from reader import stage0
from reader.closing import close_fields
from compiler import c2
from engine.machine import Machine

KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder", "tools", "openapi.json")
MUT = os.path.join(ROOT, "tests", "data", "openapi_mutated.json")
IR = json.load(open(os.path.join(ROOT, "ir", "brief_a.json"), encoding="utf-8"))


class TestOpenapiVariants(unittest.TestCase):
    def test_refs_allof_and_201_read_like_the_plain_file(self):
        a, b = stage0.parse_openapi(KIT), stage0.parse_openapi(MUT)
        for t in a["tools"]:
            if t != "close_call":
                self.assertEqual(a["tools"][t]["args"], b["tools"][t]["args"], t)
            self.assertEqual(a["tools"][t]["returns"], b["tools"][t]["returns"], t)

    def test_renamed_close_fields_are_used(self):
        b = stage0.parse_openapi(MUT)
        self.assertEqual(close_fields(IR, b), {"outcome": "result_code", "reason": "reason_code"})
        self.assertEqual(close_fields(IR, stage0.parse_openapi(KIT)), {"outcome": "outcome", "reason": "reason"})
        wf = c2.compile_workflow(IR, b, name="t")
        body = wf["nodes"]["api_close_call"]["pre_actions"][0]["function"]["parameters"]["properties"]["body"]["properties"]
        self.assertIn("result_code", body)
        ir2 = dict(IR, closing=dict(IR.get("closing") or {}, fields=close_fields(IR, b)))
        m = Machine(ir2, {"customer_id": "c1", "first_name": "A", "last_name": "B", "title": "Mr", "now": "2026-10-14T11:00"})
        m.handle({"type": "start"})
        out = m.handle({"type": "user", "text": "Wrong number.", "intents": ["wrong_number"], "slots": {}})
        calls = [o for o in out if o.get("call") == "close_call"]
        self.assertTrue(calls and "result_code" in calls[0]["args"] and "outcome" not in calls[0]["args"])


if __name__ == "__main__":
    unittest.main()
