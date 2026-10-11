"""Recall of the conversation judge: the same S8 test calls judged in groups of N vs one by one.
Usage: python sim/judge_recall.py <per_call> [<runs>]"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reader import stage0
from selftest import gen as G
per, runs = int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 1
d = "synthetic/S8_uk_unseen/brief"
st = stage0.run([os.path.join(d, f) for f in sorted(os.listdir(d))], "synthetic/S8_uk_unseen/openapi.json")
docs = stage0.render_for_llm(st)
ir = json.load(open("out/s8_new/policy_ir.json", encoding="utf-8"))
cases = json.load(open("out/s8_new/selftest.json", encoding="utf-8"))["cases"]
base = G.run_cases(ir, cases)
for k in range(runs):
    G._CONV_CACHE.clear()
    res = [dict(r, diff=list(r["diff"])) for r in base]
    t0 = time.time()
    res = G.judge_conversations(res, docs, log=print, per_call=per)
    bad = sorted(r["case"]["id"] for r, b in zip(res, base) if b["pass"] and not r["pass"])
    print("per_call=%d run %d: %.0fs, confirmed %d: %s" % (per, k + 1, time.time() - t0, len(bad), bad))
