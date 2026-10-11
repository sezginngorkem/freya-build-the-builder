"""Replay one real Freya call (by call id) with a compiled workflow. Usage: python sim/replay_call.py <wf.json> <case> <call_id>"""
import sys, json, os, re, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diffreplay as D
import freya
wf = json.load(open(sys.argv[1], encoding="utf-8"))
kit = {c["id"]: c for c in json.load(open(os.path.join(D.KIT, "public-test-set.json"), encoding="utf-8"))}
case, cid = sys.argv[2], sys.argv[3]
m = re.search(r'"(c_[0-9a-f-]{10,})"', json.dumps(freya.get_call(cid)))
turns, real = D.recorded_turns(cid)
v = dict(kit[case]["variables"]); v["customer_id"] = m.group(1) if m else "c_x"
with contextlib.redirect_stdout(io.StringIO()):
    out = D.run(wf, kit[case], turns, v)
for x in out:
    print("  ", x[:200])
