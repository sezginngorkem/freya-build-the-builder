"""Builder self-test ON FREYA for a brief with no bank sessions: the agent is compiled with the bank embedded as code
(compiler.c2 embedded_bank=True), customers are written by the builder (or taken from a cases file), Freya's own
persona and judge models play and judge the calls, the ledger is read from the call's variables and scored like the
kit does. Used to compare candidate readings of the same brief and to find failures before submission.

    python sim/freya_selftest.py <ir.json> [<ir2.json> ...] --cases cases.json [--styles plain,talkative] [--reps 1] --tag x
One simulation per IR (a workspace runs one at a time). Results: out/selftest_<tag>.json
"""
import argparse, hashlib, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, KIT); sys.path.insert(0, os.path.join(KIT, "tools")); sys.path.insert(0, ROOT)
import freya
import run_cases as RC
from score import score_ledger
from compiler import c2
from reader.stage0 import parse_openapi
from sim import freya_personas as FP

RC.STYLES.update(FP.STYLES)
STORE = os.path.join(ROOT, "out", ".selftest_personas.json")


def ledger_of(call_id):
    """The embedded bank's ledger, from the last variable table of the call that holds it."""
    led = None
    for m in freya.get_call(call_id).get("messages", []):
        msg = m.get("message")
        if isinstance(msg, str) and "bank_ledger" in msg and msg.startswith("{"):
            try:
                vt = json.loads(msg).get("variable_table") or {}
            except ValueError:
                continue
            v = vt.get("bank_ledger")
            v = v.get("value") if isinstance(v, dict) else v
            if v:
                try:
                    led = json.loads(v)
                except (TypeError, ValueError):
                    pass
    return led or {"outcome": None, "reason": None, "promises": [], "notes": [], "callbacks": [], "transfers": [], "calls": []}


def run_one(ir_path, cases, styles, reps, tag, openapi):
    ir = json.load(open(ir_path, encoding="utf-8"))
    wf = c2.compile_workflow(ir, parse_openapi(openapi), embedded_bank=True)
    slot = "selftest_" + re.sub(r"\W+", "_", os.path.basename(ir_path).rsplit(".", 1)[0])
    ids = freya.save_workflow(slot, wf, state_file=os.path.join(ROOT, ".freya-agents.json"))
    store = json.load(open(STORE)) if os.path.exists(STORE) else {}
    items, specs = [], {}
    for c in cases:
        for st in styles:
            for r in range(reps):
                p = RC.persona_for(c, {"identity": c["identity"]}, None if st == "plain" else st)
                p["name"] = "%s #%d [%s] selftest" % (c["id"], r + 1, st)
                key = hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16]
                specs[(c["id"], st, r)] = (key, p, c)
                items.append((c["id"], st, r))
    new = [(k, p) for k, p, _ in specs.values() if k not in store]
    for i in range(0, len(new), 50):
        made = freya.create_personas([p for _, p in new[i:i + 50]])["personas"]
        for (k, _), m in zip(new[i:i + 50], made):
            store[k] = m["id"]
    json.dump(store, open(STORE, "w"), indent=1)
    var_map = {}
    for k in items:
        key, p, c = specs[k]
        v = dict(c["variables"])
        v["customer_id"] = "c_self_%s_%s_%d" % (c["id"], k[1], k[2])
        v["test_case"] = json.dumps({"identity": c["identity"], "products": c["products"], "faults": c.get("faults") or [],
                                     "identity_required": c.get("identity_required")})
        var_map[store[key]] = v
    t0 = time.time()
    sim_id, it_id, status = freya.run_simulation(ids["agent_id"], "selftest %s %s" % (tag, os.path.basename(ir_path)), var_map, max_seconds=420)
    runs = {x["personaId"]: x for x in freya.get_iteration(sim_id, it_id)["runs"]}
    rows = []
    for k in items:
        key, p, c = specs[k]
        j = runs.get(store[key], {})
        led = ledger_of(j["callId"]) if j.get("callId") else {}
        res = score_ledger(c, led) if led else {"failed": ["no ledger"]}
        if j.get("outcome") != "pass":
            res["failed"].append("judge: " + " ".join(str(j.get("reason") or j.get("outcome")).split())[:300])
        rows.append({"case": k[0], "style": k[1], "rep": k[2] + 1, "pass": not res["failed"], "failed": res["failed"], "call_id": j.get("callId")})
    return {"ir": ir_path, "agent_id": ids["agent_id"], "simulation_id": sim_id, "status": status,
            "seconds": round(time.time() - t0), "passed": sum(r["pass"] for r in rows), "total": len(rows), "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("irs", nargs="+"); ap.add_argument("--cases", required=True); ap.add_argument("--brief")
    ap.add_argument("--styles", default="plain"); ap.add_argument("--reps", type=int, default=1); ap.add_argument("--tag", default="x")
    ap.add_argument("--openapi", default=os.path.join(KIT, "tools", "openapi.json"))
    a = ap.parse_args()
    cases = [c for c in json.load(open(a.cases, encoding="utf-8")) if not a.brief or c.get("brief") == a.brief]
    styles = [s for s in a.styles.split(",") if s]
    out = []
    for ir_path in a.irs:
        r = run_one(ir_path, cases, styles, a.reps, a.tag, a.openapi)
        out.append(r)
        print("%-28s %3d/%-3d  (%s s, sim %s)" % (os.path.basename(ir_path), r["passed"], r["total"], r["seconds"], r["simulation_id"][:8]), flush=True)
        for x in r["rows"]:
            if not x["pass"]:
                print("    FAIL %s %-10s #%d %s" % (x["case"], x["style"], x["rep"], x["failed"][0][:160]), flush=True)
        json.dump(out, open(os.path.join(ROOT, "out", "selftest_%s.json" % a.tag), "w"), indent=1)


if __name__ == "__main__":
    main()
