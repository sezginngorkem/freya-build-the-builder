"""H1 experiment: does the engine decide on what an IR MEANS or on how it is WRITTEN?

Each rewrite below keeps the IR's meaning (by the rule language's own definition). Run the original and the rewritten
IR on the same customers (all scripted cases + their 5 speech styles + seeded random customers) and compare the bank
calls. Any difference = the engine depends on surface form = a fragile spot (a patch, not a principle).

  inline_procs   {"run": "p"} replaced by p's actions (one level, then repeated to a fixed point)
  priority_x10   every priority multiplied by 10 (order kept)
  star_expand    phase "*" replaced by the explicit list of all phases
  rename         non-standard intent ids renamed consistently (abc -> abc_x)
  split_phases   a rule with a list of phases becomes one rule per phase

    python sim/metamorph.py [--only s6] [--runs 6]
"""
import argparse, collections, contextlib, copy, io, json, os, random, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from engine.machine import SIDE, POLARITY
from compiler import c2
from sim import fuzz as F, styles as S, gate as G
from sim.mockbank import MockBank
from sim import run_local as R

STANDARD = set(SIDE) | set(POLARITY) | {"confirm_identity", "vague_date", "third_party", "wrong_number", "deceased",
                                        "not_want_talk", "human", "decline", "hardship", "restructure", "paid",
                                        "dispute", "too_much"}


def inline_procs(ir):
    ir = copy.deepcopy(ir)
    procs = ir.get("procedures") or {}

    def walk(xs, depth):
        out = []
        for a in xs or []:
            if isinstance(a, dict) and "run" in a and a["run"] in procs and depth < 6:
                out.extend(walk(copy.deepcopy(procs[a["run"]]), depth + 1))
                continue
            if isinstance(a, dict):
                a = dict(a)
                for k in ("then", "else", "for_each_item"):
                    if isinstance(a.get(k), list):
                        a[k] = walk(a[k], depth)
            out.append(a)
        return out
    for r in ir.get("rules", []):
        r["do"] = walk(r.get("do"), 0)
    return ir


def priority_x10(ir):
    ir = copy.deepcopy(ir)
    for r in ir.get("rules", []):
        if r.get("priority") is not None:
            r["priority"] = int(r["priority"]) * 10
    for i in ir.get("intents", []):
        if i.get("priority") is not None:
            i["priority"] = int(i["priority"]) * 10
    return ir


def star_expand(ir):
    ir = copy.deepcopy(ir)
    phases = c2.phases_of(ir)
    for r in ir.get("rules", []):
        if r.get("phase", "*") == "*" and r.get("on") != "enter":
            nph = r.get("not_phase") or []
            nph = nph if isinstance(nph, list) else [nph]
            r["phase"] = [p for p in phases if p not in nph]
            r.pop("not_phase", None)
    return ir


def rename(ir):
    """Rename only real references to an intent: its declaration, `on: intent:<id>`, and membership tests on the
    intents of the turn ('<id>' in var.intents). Literal codes that merely share the spelling (a close reason
    'insolvency') are not intent references and stay as they are."""
    ir = copy.deepcopy(ir)
    ids = [i["id"] for i in ir.get("intents", []) if i["id"] not in STANDARD]
    ren = {i: i + "_x" for i in ids}
    for i in ir.get("intents", []):
        i["id"] = ren.get(i["id"], i["id"])
    pat = re.compile(r"""(['"])(%s)\1(\s+(?:not\s+)?in\s+var\.intents)""" % "|".join(map(re.escape, ids))) if ids else None

    def fix(x, key=None):
        if isinstance(x, dict):
            return {k: fix(v, k) for k, v in x.items()}
        if isinstance(x, list):
            return [fix(v) for v in x]
        if isinstance(x, str):
            if key == "on" and x.startswith("intent:"):
                return "intent:" + ren.get(x[7:], x[7:])
            if pat is not None:
                return pat.sub(lambda m: m.group(1) + ren[m.group(2)] + m.group(1) + m.group(3), x)
        return x
    ir["rules"] = fix(ir.get("rules", []))
    ir["procedures"] = fix(ir.get("procedures", {}))
    return ir, ren


def inline_half(ir):
    """Asymmetric but meaning-preserving: inline procedures only in rules on non yes/no intents. Tests whether the
    engine compares rules by their text (fragile) or by their meaning."""
    ir = copy.deepcopy(ir)
    full = inline_procs(ir)
    for r, r2 in zip(ir.get("rules", []), full.get("rules", [])):
        on = str(r.get("on", ""))
        if on.startswith("intent:") and on[7:] not in POLARITY:
            r["do"] = r2["do"]
    return ir


def split_phases(ir):
    ir = copy.deepcopy(ir)
    out = []
    for r in ir.get("rules", []):
        if isinstance(r.get("phase"), list) and len(r["phase"]) > 1:
            for p in r["phase"]:
                r2 = copy.deepcopy(r); r2["phase"] = p; r2["id"] = "%s@%s" % (r.get("id"), p)
                out.append(r2)
        else:
            out.append(r)
    ir["rules"] = out
    return ir


def calls_of(ir, case, script):
    bank = MockBank(case)
    cv = dict(case["variables"]); cv.setdefault("customer_id", "c_" + case["id"])
    tail = [R.U(["no"], "No, that's all."), R.U(["no"], "Goodbye.")]
    m, tr = R.run_script(ir, cv, bank, [R.U(t.get("intents"), t.get("text", ""), **(t.get("slots") or {})) for t in script] + tail)
    return [(x["name"], json.dumps(x["args"], sort_keys=True)) for w, x in tr if w == "tool"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only"); ap.add_argument("--runs", type=int, default=6)
    a = ap.parse_args()
    res = collections.defaultdict(lambda: [0, 0])
    examples = collections.defaultdict(list)
    seen = set()
    for ir_path, cases_path, brief, api in G.SUITES:
        if cases_path == G.REPLAYS or ir_path in seen or (a.only and a.only not in ir_path):
            continue
        seen.add(ir_path)
        ir0 = json.load(open(os.path.join(ROOT, ir_path), encoding="utf-8"))
        cases = S.load_cases(ir0, cases_path, brief)
        _, cfg = c2.phase_cfg(ir0)
        variants = {"inline_procs": (inline_procs(ir0), {}), "inline_half": (inline_half(ir0), {}), "priority_x10": (priority_x10(ir0), {}),
                    "star_expand": (star_expand(ir0), {}), "rename": rename(ir0), "split_phases": (split_phases(ir0), {})}
        for c in cases:
            scripts = [("plain", c.get("sim_script") or [])]
            for k in range(a.runs):          # realised random customers (Freya-filtered), replayed on both IRs
                try:
                    m, tr, events, bank = F.realise(ir0, cfg, c, random.Random(k), p_fail=0)
                    scripts.append(("rand%d" % k, [e for e in events if not e.get("polite")]))
                except Exception:
                    pass
            for tag, script in scripts:
                try:
                    base = calls_of(ir0, c, script)
                except Exception as e:
                    base = ["crash " + str(e)[:60]]
                for name, (ir1, ren) in variants.items():
                    sc = [dict(t, intents=[ren.get(i, i) for i in (t.get("intents") or [])]) for t in script]
                    try:
                        got = calls_of(ir1, c, sc)
                    except Exception as e:
                        got = ["crash " + str(e)[:60]]
                    res[name][1] += 1
                    if got != base:
                        res[name][0] += 1
                        if len(examples[name]) < 4:
                            examples[name].append((ir_path, c["id"], tag, str(base)[:160], str(got)[:160]))
    print("H1 metamorphic test: behaviour differences after meaning-preserving rewrites")
    for name, (d, n) in sorted(res.items()):
        print("  %-13s %4d / %4d conversations behave differently" % (name, d, n))
        for ex in examples[name]:
            print("      %s %s %s\n        orig %s\n        new  %s" % ex)


if __name__ == "__main__":
    main()
