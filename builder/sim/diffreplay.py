"""Differential replay on real Freya conversations: did a code change alter what the agent does, and where?

Every archived Freya call is replayed locally, turn by turn, with the language layer's REAL output of that call (the
variables Freya's extractor wrote at each customer turn), through two compiled workflows (old code, new code). The
first turn where the two agents say or do something different is a behaviour change caused by the code change: each one
is either a fix or a regression and is read by hand. Turns after the first divergence are not comparable (the real
customer answered the old agent), so only first divergences count. Fidelity check: the old workflow's replay must say
what the agent really said on Freya; calls where it does not are reported separately (replay not faithful there).

    python sim/diffreplay.py out/wf_reader_a7.json out/wf_new.json --sims c2c28061,9d796592
No credits: Freya calls are read once and cached in out/sim_archive/calls/.
"""
import argparse, glob, io, json, os, re, sys, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, ROOT); sys.path.insert(0, KIT)
from sim.emu import route, subst
from sim.mockbank import MockBank

CACHE = os.path.join(ROOT, "out", "sim_archive", "calls")


def recorded_turns(call_id):
    """[(customer text, {extracted var: value}), ...] and the agent lines, from the real call."""
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, call_id + ".json")
    if os.path.exists(f):
        msgs = json.load(open(f, encoding="utf-8"))
    else:
        import freya
        msgs = [{k: m.get(k) for k in ("role", "message", "nodeId")} for m in freya.get_call(call_id).get("messages", [])]
        json.dump(msgs, open(f, "w", encoding="utf-8"))
    turns, agent = [], []
    for m in msgs:
        msg = m.get("message")
        if m["role"] == "user":
            turns.append([msg, {}])
        elif m["role"] == "assistant":
            agent.append(msg)
        elif m["role"] == "system" and isinstance(msg, str) and '"variable_extracted"' in msg and turns:
            try:
                e = json.loads(msg)
            except ValueError:
                continue
            turns[-1][1][e["name"]] = e.get("value")
    return turns, agent


def run(wf, case, turns, variables):
    """Run a compiled workflow on recorded extractions; returns the agent's lines and tool calls, in order."""
    bank = MockBank(case)
    vars = dict(wf.get("test_variables") or {})
    vars.update(variables)
    nodes, cur, steps, ti, out, node_turns = wf["nodes"], wf["initial_node"], 0, 0, [], {}
    while steps < 600:
        steps += 1
        n = nodes[cur]
        t = n["node_type"]
        if t == "code":
            code = n["pre_actions"][0]["function"]["parameters"]["properties"]["code"]["default"]
            g = {"__name__": "freya_code"}
            exec("def __user_main__(vars):\n" + "\n".join("    " + ln for ln in code.splitlines()) + "\n", g)
            before = dict(vars)
            g["__user_main__"](vars)
            for k, v in list(vars.items()):
                if k.startswith("i_") and v == "" and before.get(k) not in (None, ""):
                    vars[k] = before[k]
            cur = route(n, vars, node_turns)
        elif t == "api_request":
            fn = n["pre_actions"][0]
            props = fn["function"]["parameters"]["properties"]
            body = {k: subst(v.get("default", ""), vars) for k, v in props["body"]["properties"].items()}
            config = {"url": props["url"]["default"], "method": props["method"]["default"], "body": body}
            exec(fn.get("pre_process_code") or "", {"vars": vars, "config": config})
            ok, data = bank(fn["function"]["name"], config["body"])
            out.append("TOOL %s %s" % (fn["function"]["name"], json.dumps(config["body"], sort_keys=True)))
            result = {"status": "success" if ok else "error", "data": data if ok else None, "status_code": 200 if ok else 500, "header": {}}
            exec(fn.get("post_process_code") or "", {"vars": vars, "result": result})
            cur = route(n, vars, node_turns)
        elif t == "conversation":
            ent = n.get("on_enter") or {}
            txt = subst(ent.get("text", ""), vars) if ent.get("type") == "tts" else "[LLM] " + subst(ent.get("prompt", ""), vars)
            if txt.strip():
                out.append("SAY " + txt.strip())
            if n.get("passthrough"):
                cur = route(n, vars, node_turns)
                continue
            if ti >= len(turns):
                break
            text, ex = turns[ti]; ti += 1
            out.append("USER " + str(text))
            for f in n.get("extraction_schema", []):
                nm = f["name"]
                if nm in ex:
                    v = ex[nm]
                    vars[nm] = ("true" if v else "false") if isinstance(v, bool) else ("" if v is None else v)
                elif nm.startswith("i_"):
                    vars[nm] = "false"
                elif nm == "s__utterance":
                    vars[nm] = text
                else:
                    vars[nm] = vars.get(nm, "")
            node_turns[cur + ".current_turns"] = 1
            nxt = route(n, vars, node_turns)
            node_turns[cur + ".current_turns"] = 0
            cur = nxt
        elif t == "end_call":
            break
    return out


def _anchors():
    m = {}
    for f in glob.glob(os.path.join(ROOT, "synthetic", "*scenarios*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for x in (d if isinstance(d, list) else d.get("cases") or d.get("scenarios") or []):
            if isinstance(x, dict) and x.get("id") and x.get("anchor"):
                m[x["id"]] = x["anchor"]
    return m


ANCHORS = _anchors()


def first_diff(a, b):
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("--sims", required=True)
    ap.add_argument("--show", type=int, default=60)
    a = ap.parse_args()
    old, new = (json.load(open(p, encoding="utf-8")) for p in (a.old, a.new))
    kit = {c["id"]: c for c in json.load(open(os.path.join(KIT, "public-test-set.json"), encoding="utf-8"))}
    n = same = faithful = 0
    diffs, unfaithful = [], []
    for sid in a.sims.split(","):
        f = glob.glob(os.path.join(ROOT, "out", "sim_archive", sid + "*.json"))[0]
        doc = json.load(open(f, encoding="utf-8"))
        for r in doc["runs"]:
            case = kit.get(r["case"]) or kit.get(ANCHORS.get(r["case"], ""))   # scenario runs: their anchor kit case
            if not case or not r.get("callId") or not r.get("customer_id"):
                continue
            try:
                turns, real = recorded_turns(r["callId"])
            except Exception as e:      # a call the platform no longer has
                print("skip %s: %s" % (r["callId"][:8], str(e)[:60]))
                continue
            variables = dict(case["variables"]); variables["customer_id"] = r["customer_id"]
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    o = run(old, case, turns, variables)
                    w = run(new, case, turns, variables)
                except Exception as e:
                    print("crash", r["case"], e); continue
            n += 1
            said_old = [x[4:] for x in o if x.startswith("SAY ")]
            if said_old[:len(real)] == real[:len(said_old)] or said_old == real:
                faithful += 1
            else:
                k = first_diff(said_old, real)
                unfaithful.append((r["case"], r.get("personaName", "")[:30], k, (said_old[k] if k is not None and k < len(said_old) else None), (real[k] if k is not None and k < len(real) else None)))
            k = first_diff(o, w)
            if k is None:
                same += 1
                continue
            user = next((x for x in reversed(o[:k]) if x.startswith("USER ")), "")
            diffs.append((r["case"], re.search(r"\[(\w+)\]", r.get("personaName") or "") and re.search(r"\[(\w+)\]", r["personaName"]).group(1),
                          r.get("pass"), user[5:], o[k] if k < len(o) else "(end)", w[k] if k < len(w) else "(end)"))
    print("replayed %d real Freya calls: %d identical, %d changed; old replay faithful to Freya in %d" % (n, same, len(diffs), faithful))
    for d in diffs[:a.show]:
        print("\n%s [%s] (Freya %s) after customer: %r\n   OLD: %s\n   NEW: %s" % (d[0], d[1], "pass" if d[2] else "FAIL", d[3][:110], d[4][:150], d[5][:150]))
    if unfaithful:
        print("\nnot faithful (first difference old replay vs real Freya):")
        for u in unfaithful[:15]:
            print("  ", u[0], u[1], "turn", u[2], "| replay:", str(u[3])[:80], "| freya:", str(u[4])[:80])


if __name__ == "__main__":
    main()
