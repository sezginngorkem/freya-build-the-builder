"""Many customers in ONE Freya simulation, scored exactly like the kit's run_cases.py (bank ledger + judge).

Why: the workspace runs one simulation at a time and run_cases.py runs one style per simulation, so channels sat idle
between runs. Here every (case, style, repetition) is its own persona with its own bank session, all in one
simulation; the 5 call channels stay busy and each scenario's consistency over 3 runs (the final's 3/3 rule) is
measured directly.

    python sim/freya_batch.py <agent_id> --brief A --styles plain,talkative,pieces --reps 3 --tag a4 [--cases file.json]
Styles: plain, the kit's five (pieces corrects talkative asks_back in_words) and sim/freya_personas.py's eight.
"""
import argparse, collections, hashlib, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, KIT); sys.path.insert(0, os.path.join(KIT, "tools")); sys.path.insert(0, ROOT)
import freya

_api = freya.api


def _api_retry(*args, **kw):
    """Freya sometimes answers a poll with a transient 502/503/504 or times out: try again before giving up the batch
    (seen: a whole 180-call run lost its scoring to one 502 while polling)."""
    for attempt in range(6):
        try:
            return _api(*args, **kw)
        except Exception as e:
            transient = any(c in str(e) for c in (" 502", " 503", " 504", "timed out", "Timeout", "temporarily"))
            if not transient or attempt == 5:
                raise
            time.sleep(10 * (attempt + 1))


freya.api = _api_retry
import run_cases as RC
from score import http, score_ledger
from sim import freya_personas as FP

RC.STYLES.update(FP.STYLES)
STORE = os.path.join(ROOT, "out", ".batch_personas.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_id"); ap.add_argument("--brief", default="A"); ap.add_argument("--styles", default="plain")
    ap.add_argument("--reps", type=int, default=3); ap.add_argument("--tag", default="x")
    ap.add_argument("--cases", default=os.path.join(KIT, "public-test-set.json")); ap.add_argument("--only")
    ap.add_argument("--rescore", help="score a finished simulation id (after a crash of this process)")
    ap.add_argument("--scenarios", help="scenario file (synthetic/competition_scenarios.json): kit case + behaviour, own day")
    ap.add_argument("--priority", type=int, default=9, help="with --scenarios: only scenarios of this priority or better")
    a = ap.parse_args()
    cases = [c for c in json.load(open(a.cases, encoding="utf-8")) if (not a.brief or c.get("brief") == a.brief)
             and (not a.only or c["id"] in a.only.split(","))]
    styles = [s for s in a.styles.split(",") if s]
    if a.scenarios:   # each scenario = its anchor kit case, a behaviour (in the style slot), its own checks and day
        import copy
        kit = {c["id"]: c for c in json.load(open(os.path.join(KIT, "public-test-set.json"), encoding="utf-8"))}
        sc = json.load(open(a.scenarios, encoding="utf-8"))
        sc = sc.get("scenarios") or next(v for k, v in sc.items() if isinstance(v, list))
        cases = []
        for x in sc:
            if x.get("priority", 9) > a.priority or (a.only and x["id"] not in a.only.split(",")) or x["anchor"] not in kit:
                continue
            if a.brief and kit[x["anchor"]].get("brief") != a.brief:
                continue
            c = copy.deepcopy(kit[x["anchor"]])
            c.update({"id": x["id"], "_anchor": x["anchor"], "_now": x.get("now_override"), "_style": "sc_" + x["id"],
                      "title": c["title"] + " / " + x.get("group", "")})
            c["checks"] = (c["checks"] if x["type"] == "scored" else []) + list(x.get("checks") or [])
            if x["type"] != "scored":
                c["expected"] = x.get("expected")
            RC.STYLES["sc_" + x["id"]] = x["behaviour"]
            cases.append(c)
    items = [(c, st, r) for c in cases for st in ([c["_style"]] if c.get("_style") else styles) for r in range(a.reps)]
    ids = json.load(open(STORE)) if os.path.exists(STORE) else {}
    specs = {}
    for c, st, r in items:
        p = RC.persona_for(c, {"identity": c["identity"]}, None if st == "plain" else st)
        p["name"] = "%s #%d [%s] %s" % (c["id"], r + 1, st, os.path.basename(a.cases)[:20])
        key = hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16]
        specs[(c["id"], st, r)] = (key, p)
    new = [(k, p) for k, p in specs.values() if k not in ids]
    for i in range(0, len(new), 50):
        made = freya.create_personas([p for _, p in new[i:i + 50]])["personas"]
        for (k, _), m in zip(new[i:i + 50], made):
            ids[k] = m["id"]
    json.dump(ids, open(STORE, "w"), indent=1)
    sessions = {}
    for c, st, r in items:
        for attempt in range(4):   # the practice bank sometimes times out: try again before giving up the batch
            try:
                sessions[(c["id"], st, r)] = http("/v1/practice/sessions", {"case": c.get("_anchor", c["id"])})["variables"]
                break
            except Exception as e:
                if attempt == 3:
                    raise
                print("practice session retry %d: %s" % (attempt + 1, str(e)[:120]))
                time.sleep(5 * (attempt + 1))
        if c.get("_now"):
            sessions[(c["id"], st, r)]["now"] = c["_now"]
    pid = {k: ids[specs[k][0]] for k in specs}
    t0 = time.time()
    # persisted before the simulation: if this process dies, --rescore can still score the finished simulation
    json.dump({"|".join(map(str, k)): {"persona": pid[k], "customer_id": sessions[k]["customer_id"]} for k in specs},
              open(os.path.join(ROOT, "out", "batch_%s.sessions.json" % a.tag), "w"), indent=1)
    if a.rescore:
        sim_id, status = a.rescore, "rescored"
        its = freya.api("GET", "/api/v2/simulations/%s/iterations" % sim_id); its = its.get("iterations") or its.get("items") or its
        it_id = its[0]["id"]
    else:
        sim_id, it_id, status = freya.run_simulation(a.agent_id, "batch %s %s" % (a.tag, time.strftime("%H:%M")),
                                                     {pid[k]: sessions[k] for k in specs}, max_seconds=420)
    runs = {x["personaId"]: x for x in freya.get_iteration(sim_id, it_id)["runs"]}
    by_name = {}
    if a.rescore:   # the customer ids of that simulation are in its calls, not in the fresh sessions made above
        for x in runs.values():
            if x.get("callId"):
                vt = {}
                for m in freya.get_call(x["callId"]).get("messages", []):
                    if m.get("role") == "system" and '"variable_table"' in str(m.get("message")):
                        vt = json.loads(m["message"]).get("variable_table") or {}
                        break
                cid = vt.get("customer_id"); cid = cid.get("value") if isinstance(cid, dict) else cid
                by_name[x.get("personaName")] = (x, cid)
    rows = []
    for c, st, r in items:
        k = (c["id"], st, r)
        if a.rescore:
            j, cust = by_name.get(specs[k][1]["name"], ({}, None))
            if not cust:
                continue
            runs[pid[k]] = j
            sessions[k] = {"customer_id": cust}
        led = http("/v1/practice/ledger/" + sessions[k]["customer_id"])
        res = score_ledger(c, led) if c.get("expected") is not None else {"failed": []}
        j = runs.get(pid[k], {})
        if j.get("outcome") not in ("pass", "fail") and j.get("callId"):
            # the run record may stay 'inconclusive'/'running' while the call itself carries the judge's verdict
            try:
                ev = (freya.get_call(j["callId"]).get("analysis") or {}).get("successEvaluation") or {}
                if "success" in ev:
                    j = dict(j, outcome="pass" if ev["success"] else "fail", reason=ev.get("reason"))
            except Exception:
                pass
        if j.get("outcome") != "pass":
            res["failed"].append("conversation: " + " ".join(str(j.get("reason") or "no verdict (%s)" % j.get("outcome")).split())[:400])
        rows.append({"case": c["id"], "style": st, "rep": r + 1, "pass": not res["failed"], "failed": res["failed"],
                     "call_id": j.get("callId"), "judge": j.get("outcome"), "tools": [x["tool"] for x in led.get("calls", [])]})
    out = os.path.join(ROOT, "out", "batch_%s.json" % a.tag)
    json.dump({"agent_id": a.agent_id, "simulation_id": sim_id, "status": status, "seconds": round(time.time() - t0),
               "rows": rows}, open(out, "w"), indent=1)
    agg = collections.defaultdict(list)
    for x in rows:
        agg[(x["case"], x["style"])].append(x["pass"])
    print("batch %s: %d calls, %.0f s, simulation %s (%s)" % (a.tag, len(rows), time.time() - t0, sim_id, status))
    for st in sorted(set(s for _, s in agg)):
        cs = [(cid, v) for (cid, s), v in sorted(agg.items()) if s == st]
        ok3 = sum(1 for _, v in cs if all(v))
        print("  %-12s %2d/%d customers pass %d/%d runs   per case: %s" % (
            st, ok3, len(cs), a.reps, a.reps, " ".join("%s:%d" % (cid[-2:], sum(v)) for cid, v in cs)))
    for x in rows:
        if not x["pass"]:
            print("  FAIL %s %-11s #%d  %s" % (x["case"], x["style"], x["rep"], x["failed"][0][:200]))


if __name__ == "__main__":
    main()
