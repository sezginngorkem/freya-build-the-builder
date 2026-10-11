"""Print an archived call: python sim/show_call.py <sim_id_prefix> <case> [style]"""
import glob, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
f = glob.glob(os.path.join(ROOT, "out", "sim_archive", sys.argv[1] + "*.json"))[0]
doc = json.load(open(f, encoding="utf-8"))
for r in doc["runs"]:
    if r["case"] != sys.argv[2] or (len(sys.argv) > 3 and "[%s]" % sys.argv[3] not in (r.get("personaName") or "")):
        continue
    print("==", r.get("personaName"), "| judge", r.get("outcome"), "| ledger", r.get("ledger_failed"))
    for t in r.get("turns", []):
        print("%-8s %-14s %s" % (t["role"], t.get("node") or "", t["text"]))
    for t in r.get("tools", []):
        if t["event"] != "function_call_complete":
            print("   TOOL", t.get("function") or t["event"], json.dumps(t.get("args"))[:200] if t.get("args") else t.get("result"))
    print("JUDGE:", r.get("reason"))
