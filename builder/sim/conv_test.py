"""Offline: run the self-test (with the conversation judge) on an existing read, then show whether a hardship-then-
decline customer is still asked for payment. Usage: python sim/conv_test.py <build dir> <brief dir> <openapi>"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reader import stage0
from selftest.gen import selftest
bd, brief_dir, api = sys.argv[1:4]
files = [os.path.join(brief_dir, f) for f in sorted(os.listdir(brief_dir))]
st = stage0.run(files, api)
ir = json.load(open(os.path.join(bd, "policy_ir.json"), encoding="utf-8"))
inv = json.load(open(os.path.join(bd, "inventory.json"), encoding="utf-8"))
cases = json.load(open(os.path.join(bd, "selftest.json"), encoding="utf-8"))["cases"]
t0 = time.time()
new, rep = selftest(ir, st, cases=cases, inventory=inv)
print("seconds %.0f history %s held-out %s" % (time.time() - t0, rep["history"], rep["held_out"]))
json.dump(new, open(os.path.join(bd, "policy_ir_conv.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
