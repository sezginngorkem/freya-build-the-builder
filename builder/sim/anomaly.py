"""Chat vs code: did the agent on Freya say and do exactly what our code decides?

For every call of the given simulations, the deployed workflow is run again here on the call's own recorded inputs
(the customer's messages and the extraction values Freya produced), and compared with what really happened:
  - each agent line said on Freya vs the line our code produces at that point;
  - the bank tool calls made on Freya (with their arguments) vs the calls our code makes.
Any difference is an anomaly: the platform did something our code did not decide (a line spoken differently, a turn
missing, a tool call lost or changed), or our replay is not faithful. Every anomaly is printed with its context.

    python sim/anomaly.py <deployed wf.json> --sims <sim id prefix>[,<prefix>...] [--show N]
"""
import argparse, contextlib, glob, io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diffreplay as D
import freya


def real_tools(call_id):
    f = os.path.join(D.CACHE, call_id + ".tools.json")
    if os.path.exists(f):
        return json.load(open(f, encoding="utf-8"))
    out = []
    for m in freya.get_call(call_id).get("messages", []):
        if m.get("role") != "system":
            continue
        try:
            e = json.loads(m.get("message") or "")
        except ValueError:
            continue
        if e.get("event") == "function_call_start":
            args = e.get("args") or {}
            url = str(args.get("url") or "")
            if url:
                out.append("TOOL %s %s" % (url.rstrip("/").split("/")[-1], json.dumps(args.get("body") or {}, sort_keys=True)))
    json.dump(out, open(f, "w", encoding="utf-8"))
    return out


def norm_tool(t):
    # compare tool name + arguments, numbers as numbers ("540" vs 540.0)
    m = re.match(r"TOOL (\S+) (.*)", t)
    if not m:
        return t
    try:
        body = json.loads(m.group(2))
    except ValueError:
        return t
    body = {k: (float(v) if isinstance(v, (int, float)) or re.fullmatch(r"-?\d+(\.\d+)?", str(v)) else v)
            for k, v in body.items()}
    return "%s %s" % (m.group(1), json.dumps(body, sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wf"); ap.add_argument("--sims", required=True); ap.add_argument("--show", type=int, default=40)
    ap.add_argument("--cases", default=os.path.join(D.KIT, "public-test-set.json"))
    a = ap.parse_args()
    wf = json.load(open(a.wf, encoding="utf-8"))
    kit = {c["id"]: c for c in json.load(open(a.cases, encoding="utf-8"))}
    n = ok = 0
    anomalies = []
    for sid in a.sims.split(","):
        doc = json.load(open(glob.glob(os.path.join(D.ROOT, "out", "sim_archive", sid + "*.json"))[0], encoding="utf-8"))
        for r in doc["runs"]:
            case = kit.get(r["case"]) or kit.get(D.ANCHORS.get(r["case"], ""))
            if not case or not r.get("callId") or not r.get("customer_id"):
                continue
            try:
                turns, real = D.recorded_turns(r["callId"])
                rtools = [norm_tool(t) for t in real_tools(r["callId"])]
            except Exception as e:
                print("skip %s: %s" % (r["callId"][:8], str(e)[:60]))
                continue
            variables = dict(case["variables"]); variables["customer_id"] = r["customer_id"]
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    out = D.run(wf, case, turns, variables)
                except Exception as e:
                    anomalies.append((r, "replay crashed: %s" % e, [], [])); continue
            n += 1
            said = [x[4:] for x in out if x.startswith("SAY ")]
            tools = [norm_tool(x) for x in out if x.startswith("TOOL ")]
            problems = []
            k = D.first_diff(said[:len(real)], real[:len(said)]) if len(said) != len(real) else D.first_diff(said, real)
            if k is not None:
                problems.append("line %d: code says %r | Freya said %r" % (
                    k, said[k][:150] if k < len(said) else "(nothing)", real[k][:150] if k < len(real) else "(nothing)"))
            if len(said) != len(real):
                problems.append("lines: code %d, Freya %d" % (len(said), len(real)))
            if tools != rtools[:len(tools)] and tools[:len(rtools)] != rtools:
                j = D.first_diff(tools, rtools)
                problems.append("tool %s: code %s | Freya %s" % (j, tools[j] if j is not None and j < len(tools) else "(none)",
                                                                   rtools[j] if j is not None and j < len(rtools) else "(none)"))
            if problems:
                anomalies.append((r, "; ".join(problems), out, real))
            else:
                ok += 1
    print("calls checked %d: code and Freya agree in %d, anomalies in %d" % (n, ok, len(anomalies)))
    for r, why, out, real in anomalies[:a.show]:
        print("\n== %s %s (Freya %s)\n   %s" % (r["case"], (r.get("personaName") or "")[:30], "pass" if r.get("pass") else "FAIL", why))


if __name__ == "__main__":
    main()
