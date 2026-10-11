"""Early customer hang-ups in the running simulation (an environment health check). Usage: python sim/hangup_watch.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "kit", "build-the-builder"))
import freya
sims = freya.api("GET", "/api/v2/simulations", workspaceId=freya.workspace_id(), limit=1)
sims = sims.get("simulations") or sims.get("items") or sims
s = sims[0]
its = freya.api("GET", "/api/v2/simulations/%s/iterations" % s["id"])
its = its.get("iterations") or its.get("items") or its
runs = freya.get_iteration(s["id"], its[0]["id"])["runs"]
done = [r for r in runs if r.get("outcome") not in ("queued", "running")]
hang = [r for r in done if r.get("endedReason") == "customer-ended-call"]
print("%s %s done %d/%d customer hang-ups %d" % (s.get("name", "")[:30], s.get("status"), len(done), len(runs), len(hang)))
