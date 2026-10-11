"""Watchdog for Freya practice simulations.

Seen twice (2026-10-10 23:29 and 2026-10-11 00:34): every call of a simulation had ended, but one judge verdict stayed
'inconclusive' and the simulation stayed 'running' forever. The kit's runner waits without a timeout and the workspace
allows one simulation at a time, so every later experiment queued behind it. This closes such simulations (status
'completed', the documented update) once all their calls have ended and nothing changed for STALE minutes, and logs it.

    python sim/freya_watchdog.py [--stale 8] [--every 60]
"""
import argparse, datetime as _dt, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, KIT)
import freya

LOG = os.path.join(ROOT, "out", "watchdog.log")


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def check(stale_min):
    r = freya.api("GET", "/api/v2/simulations?workspaceId=%s&limit=5" % freya.workspace_id())
    for s in (r.get("simulations") or r.get("items") or r)[:5]:
        if s.get("status") != "running":
            continue
        its = freya.api("GET", "/api/v2/simulations/%s/iterations" % s["id"])
        its = its.get("iterations") or its.get("items") or its
        if not its:
            continue
        runs = freya.get_iteration(s["id"], its[0]["id"])["runs"]
        # the simulation's run record may never get its endedAt (seen: verdict 'inconclusive' or 'error' "analysis never
        # arrived") although the call itself ended: take the call's own end time then
        for x in runs:
            if not x.get("endedAt") and x.get("callId"):
                try:
                    x["endedAt"] = freya.get_call(x["callId"]).get("endedAt")
                except Exception:
                    pass
        if not runs or any(not x.get("endedAt") for x in runs):
            continue
        last = max(_dt.datetime.fromisoformat(x["endedAt"].replace("Z", "+00:00")) for x in runs if x.get("endedAt"))
        idle = (_dt.datetime.now(_dt.timezone.utc) - last).total_seconds() / 60.0
        if idle >= stale_min:
            odd = [(x.get("personaName", "")[:24], x.get("outcome")) for x in runs if x.get("outcome") not in ("pass", "fail")]
            freya.api("PUT", "/api/v2/simulations/%s" % s["id"], {"status": "completed"})
            log("closed stalled simulation %s (%s): all %d calls ended %.0f min ago; unfinished verdicts: %s"
                % (s["id"], s.get("name"), len(runs), idle, json.dumps(odd)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--stale", type=float, default=8); ap.add_argument("--every", type=int, default=60)
    a = ap.parse_args()
    while True:
        try:
            check(a.stale)
        except Exception as e:
            log("watchdog error: %s" % str(e)[:200])
        time.sleep(a.every)


if __name__ == "__main__":
    main()
