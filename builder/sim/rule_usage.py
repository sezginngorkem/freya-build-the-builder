"""Which engine mechanisms fire on REAL Freya calls, how often, and on what customer words.

Replays archived calls (recorded extractions, as sim/diffreplay.py does) with a compiled workflow, reads the engine's
trace after every code step and counts the trace kinds. Scenario runs (FR/AD...) are replayed on their anchor kit case.
Use it to see where a new rule acts before deploying it ("does this open a new place to go wrong?").

Usage: python sim/rule_usage.py <wf.json> --sims 667f6778,64d14943 [--kinds question_answered,continuer] [--show 40]
"""
import argparse, base64, collections, glob, io, json, os, sys, zlib, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diffreplay as D


def state_of(vars):
    raw = vars.get("_st")
    if not raw:
        return None
    raw = str(raw)
    try:
        if raw.startswith("z:"):
            return json.loads(zlib.decompress(base64.b64decode(raw[2:])).decode("utf-8"))
        return json.loads(raw)
    except Exception:
        return None


def new_entries(prev, cur):
    """Trace entries added since the previous code step (the trace is trimmed to its tail, so match the overlap)."""
    for k in range(min(len(prev), len(cur)), -1, -1):
        if k == 0 or cur[:k] == prev[-k:]:
            return cur[k:]
    return cur


def scenario_anchors():
    m = {}
    for f in glob.glob(os.path.join(D.ROOT, "synthetic", "*scenarios*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for x in (d if isinstance(d, list) else d.get("cases") or d.get("scenarios") or []):
            if isinstance(x, dict) and x.get("id") and x.get("anchor"):
                m[x["id"]] = x["anchor"]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wf"); ap.add_argument("--sims", required=True)
    ap.add_argument("--kinds", default="")
    ap.add_argument("--show", type=int, default=30)
    a = ap.parse_args()
    wf = json.load(open(a.wf, encoding="utf-8"))
    kit = {c["id"]: c for c in json.load(open(os.path.join(D.KIT, "public-test-set.json"), encoding="utf-8"))}
    anchors = scenario_anchors()
    want = set(k for k in a.kinds.split(",") if k)
    counts, calls_with, examples = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    n = 0
    orig_route = D.route
    for sid in a.sims.split(","):
        doc = json.load(open(glob.glob(os.path.join(D.ROOT, "out", "sim_archive", sid + "*.json"))[0], encoding="utf-8"))
        for r in doc["runs"]:
            cid = r["case"] if r["case"] in kit else anchors.get(r["case"])
            if not cid or cid not in kit or not r.get("callId") or not r.get("customer_id"):
                continue
            try:
                turns, real = D.recorded_turns(r["callId"])
            except Exception:
                continue
            v = dict(kit[cid]["variables"]); v["customer_id"] = r["customer_id"]
            seen, last = set(), {"trace": [], "user": ""}

            def route(node, vars, node_turns, _seen=seen, _last=last, _r=r):
                if node.get("node_type") == "code":
                    st = state_of(vars)
                    if st:
                        tr = st.get("trace") or []
                        for e in new_entries(_last["trace"], tr):
                            k = e.get("kind")
                            counts[k] += 1
                            _seen.add(k)
                            if (not want or k in want) and len(examples[k]) < a.show:
                                examples[k].append("%s %s | %s | %s" % (_r["case"], (_r.get("personaName") or "")[-28:],
                                                   str(st.get("var", {}).get("last_user_text", ""))[:90],
                                                   json.dumps({x: y for x, y in e.items() if x not in ("kind",)})[:120]))
                        _last["trace"] = tr
                return orig_route(node, vars, node_turns)
            D.route = route
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    D.run(wf, kit[cid], turns, v)
            except Exception as e:
                print("crash", r["case"], e)
            finally:
                D.route = orig_route
            n += 1
            for k in seen:
                calls_with[k] += 1
    print("replayed %d real calls" % n)
    for k, c in counts.most_common():
        if not want or k in want:
            print("%-26s fired %4d times in %4d calls" % (k, c, calls_with[k]))
    for k in sorted(examples):
        print("\n== %s" % k)
        for x in examples[k]:
            print("  ", x)


if __name__ == "__main__":
    main()
