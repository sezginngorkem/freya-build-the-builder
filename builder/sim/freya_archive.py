"""Every Freya simulation, kept and scored: nothing we ran may go unreviewed.

    python sim/freya_archive.py            # archive every finished simulation not yet in out/sim_archive/
    python sim/freya_archive.py --report   # one line per simulation + every failing call (case, style, judge reason)

For each finished simulation: its runs, each call's transcript (customer/agent lines, node, tool events), the bank
customer id read from the call, the bank ledger and the official ledger score when the case is known (kit public set,
synthetic freya_cases files). Written once to out/sim_archive/<simulation_id>.json; out/sim_archive/index.json lists
them with pass counts and a 'reviewed' field that is set by hand in notes/sim-inceleme.md's workflow
(`--mark <sim_id> "<note>"`).
"""
import argparse, glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, KIT); sys.path.insert(0, os.path.join(KIT, "tools"))
import freya
from score import http, score_ledger

ARCH = os.path.join(ROOT, "out", "sim_archive")
INDEX = os.path.join(ARCH, "index.json")
CASE_FILES = [os.path.join(KIT, "public-test-set.json")] + glob.glob(os.path.join(ROOT, "synthetic", "*", "freya_cases.json"))
CID = re.compile(r'customer_id\\*"\s*:\s*(?:\{\\*"value\\*"\s*:\s*)?\\*"(c_[0-9a-f-]+)')


def all_cases():
    out = {}
    for f in CASE_FILES:
        for c in json.load(open(f, encoding="utf-8")):
            out.setdefault(c["id"], c)
    return out


def simulations():
    out, off = [], 0
    while True:
        r = freya.api("GET", "/api/v2/simulations", limit=100, offset=off)
        items = r.get("simulations") or []
        out += items
        if len(items) < 100:
            return out
        off += 100


def transcript(call):
    turns, tools = [], []
    for m in call.get("messages", []):
        role, msg = m.get("role"), m.get("message")
        if role in ("assistant", "user", "bot", "customer"):
            turns.append({"role": "agent" if role in ("assistant", "bot") else "customer", "text": msg, "node": m.get("nodeId")})
        elif role == "system" and isinstance(msg, str) and msg.startswith("{"):
            try:
                e = json.loads(msg)
            except ValueError:
                continue
            if e.get("event") in ("function_call_start", "function_call_complete") and e.get("function") != "code_exec":
                tools.append({"event": e["event"], "function": e.get("function"), "args": e.get("args"),
                              "result": str(e.get("result"))[:400], "node": m.get("nodeId")})
            elif e.get("event") == "function_call_complete" and (e.get("result") or {}).get("status") != "success":
                tools.append({"event": "code_exec_failed", "result": str(e.get("result"))[:400], "node": m.get("nodeId")})
    return turns, tools


def archive(sim, cases):
    sid = sim["id"]
    its = freya.api("GET", "/api/v2/simulations/%s/iterations" % sid)
    its = its.get("iterations") or its.get("items") or its
    runs = []
    for it in its:
        for x in freya.get_iteration(sid, it["id"])["runs"]:
            r = {k: x.get(k) for k in ("personaName", "outcome", "reason", "callId", "turnCount", "agentName", "agentId")}
            call = None
            if x.get("callId"):
                try:
                    call = freya.get_call(x["callId"])
                except RuntimeError as e:   # 413: a call too long to fetch (e.g. a 37-times repeated question)
                    r["fetch_error"] = str(e)[:160]
            if call is not None:
                ev = (call.get("analysis") or {}).get("successEvaluation") or {}
                if r.get("outcome") not in ("pass", "fail") and "success" in ev:
                    r["outcome"], r["reason"] = ("pass" if ev["success"] else "fail"), ev.get("reason")
                r["turns"], r["tools"] = transcript(call)
                r["endedReason"] = call.get("endedReason")
                m = CID.search(json.dumps(call))
                r["customer_id"] = m.group(1) if m else None
            case = (x.get("personaName") or "").split(" ")[0]
            r["case"] = case
            if r.get("customer_id") and case in cases:
                try:
                    led = http("/v1/practice/ledger/" + r["customer_id"])
                    r["ledger"] = led
                    r["ledger_failed"] = score_ledger(cases[case], led)["failed"]
                except Exception as e:          # the practice bank may have dropped an old session
                    r["ledger_error"] = str(e)[:200]
            r["pass"] = r.get("outcome") == "pass" and not r.get("ledger_failed")
            runs.append(r)
    doc = {"id": sid, "name": sim.get("name"), "agentId": sim.get("agentId"), "status": sim.get("status"),
           "createdAt": sim.get("createdAt"), "runs": runs}
    json.dump(doc, open(os.path.join(ARCH, sid + ".json"), "w", encoding="utf-8"), indent=1)
    return doc


def style_of(name):
    m = re.search(r"\[([a-z_]+)\]", name or "")
    return m.group(1) if m else "plain"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true"); ap.add_argument("--mark", nargs=2, metavar=("SIM_ID", "NOTE"))
    ap.add_argument("--only"); ap.add_argument("--force", help="re-archive this simulation id")
    a = ap.parse_args()
    os.makedirs(ARCH, exist_ok=True)
    index = json.load(open(INDEX, encoding="utf-8")) if os.path.exists(INDEX) else {}
    if a.mark:
        index[a.mark[0]]["reviewed"] = a.mark[1]
        json.dump(index, open(INDEX, "w", encoding="utf-8"), indent=1)
        return
    cases = all_cases()
    if not a.report:
        for sim in simulations():
            have = {} if a.force and sim["id"].startswith(a.force) else index.get(sim["id"], {})
            total = (sim.get("metrics") or {}).get("totalRuns") or 0
            if sim["status"] != "completed" or (have and have.get("runs", 0) >= total and os.path.exists(os.path.join(ARCH, sim["id"] + ".json"))):
                continue          # re-archived when it has more runs than our copy (a simulation read before it ended)
            doc = archive(sim, cases)
            n = len(doc["runs"]); p = sum(r["pass"] for r in doc["runs"])
            index[sim["id"]] = dict(index.get(sim["id"], {}), name=sim.get("name"), agentId=sim.get("agentId"),
                                    createdAt=sim.get("createdAt"), runs=n, passed=p,
                                    agent=next((r.get("agentName") for r in doc["runs"] if r.get("agentName")), None))
            index[sim["id"]].setdefault("reviewed", "")
            print("archived %s %-24s %-28s %d/%d" % (sim["id"][:8], sim.get("name"), index[sim["id"]]["agent"], p, n), flush=True)
            json.dump(index, open(INDEX, "w", encoding="utf-8"), indent=1)
    for sid, e in sorted(index.items(), key=lambda kv: kv[1].get("createdAt") or ""):
        if a.only and not sid.startswith(a.only):
            continue
        print("%s %s %-22s %-28s %3d/%-3d %s" % (sid[:8], (e.get("createdAt") or "")[5:16], e.get("name"), e.get("agent"),
                                                e.get("passed", 0), e.get("runs", 0), "REVIEWED: " + e["reviewed"] if e.get("reviewed") else "** NOT REVIEWED **"))
        if a.report or a.only:
            doc = json.load(open(os.path.join(ARCH, sid + ".json"), encoding="utf-8"))
            for r in doc["runs"]:
                if not r["pass"]:
                    why = (r.get("ledger_failed") or []) + ([] if r.get("outcome") == "pass" else ["judge(%s): %s" % (r.get("outcome"), " ".join(str(r.get("reason")).split())[:300])])
                    print("    FAIL %-8s %-12s %s" % (r["case"], style_of(r.get("personaName")), " | ".join(why)[:420]))


if __name__ == "__main__":
    main()
