"""Transcripts of the finished runs of the newest simulation (read while it is still running).
Usage: python sim/partial_calls.py [style] [max]"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "kit", "build-the-builder"))
import freya
style = sys.argv[1] if len(sys.argv) > 1 else ""
mx = int(sys.argv[2]) if len(sys.argv) > 2 else 99
name = sys.argv[3] if len(sys.argv) > 3 else ""
sims = freya.api("GET", "/api/v2/simulations", workspaceId=freya.workspace_id(), limit=10)
sims = sims.get("simulations") or sims.get("items") or sims
s = sorted([x for x in sims if name in str(x.get("name"))], key=lambda x: x.get("createdAt") or "")[-1]
its = freya.api("GET", "/api/v2/simulations/%s/iterations" % s["id"]); its = its.get("iterations") or its.get("items") or its
runs = [r for r in freya.get_iteration(s["id"], its[0]["id"])["runs"] if r.get("outcome") not in ("queued", "running")]
print(s.get("name"), "finished", len(runs))
n = 0
for r in runs:
    name = r.get("personaName", "")
    if not r.get("callId") or (style and "[%s]" % style not in name):
        continue
    n += 1
    if n > mx:
        break
    c = freya.get_call(r["callId"])
    print("=====", name[:30], "|", r.get("outcome"), "|", c.get("endedReason"), "|", str((c.get("successCriteriaResult") or {}).get("reason") or "")[:160])
    for m in c.get("messages", []):
        if m["role"] in ("assistant", "user"):
            print(("  A: " if m["role"] == "assistant" else "  C: ") + str(m["message"])[:170])
