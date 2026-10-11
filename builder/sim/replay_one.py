"""Replay one archived real Freya call with a compiled workflow, turn by turn (customer line, then what the new code
says/calls). Usage: python sim/replay_one.py <wf.json> <sim_id_prefix> <case> <style> [rep]"""
import sys, json, glob, os, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import diffreplay as D

wf = json.load(open(sys.argv[1], encoding="utf-8"))
sim, case_id, style = sys.argv[2], sys.argv[3], sys.argv[4]
rep = sys.argv[5] if len(sys.argv) > 5 else None
kit = {c["id"]: c for c in json.load(open(os.path.join(D.KIT, "public-test-set.json"), encoding="utf-8"))}
doc = json.load(open(glob.glob(os.path.join(D.ROOT, "out", "sim_archive", sim + "*.json"))[0], encoding="utf-8"))
k = 0
for r in doc["runs"]:
    if r["case"] != case_id or ("[" + style + "]") not in (r.get("personaName") or ""):
        continue
    k += 1
    if rep and str(k) != rep:
        continue
    turns, real = D.recorded_turns(r["callId"])
    v = dict(kit[case_id]["variables"]); v["customer_id"] = r["customer_id"]
    with contextlib.redirect_stdout(io.StringIO()):
        out = D.run(wf, kit[case_id], turns, v)
    print("== %s %s #%d %s (Freya %s)" % (case_id, style, k, r["callId"], r.get("verdict") or r.get("status")))
    print("customers:", " / ".join(t[0] for t in turns))
    for x in out:
        print("  ", x[:220])
