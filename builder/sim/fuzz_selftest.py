"""Test of the stress test: plant known defects into a correct IR and check that sim/fuzz.py detects each one.
A detector that misses a planted defect is blind; its silence about real IRs would mean nothing.

    python sim/fuzz_selftest.py
"""
import copy, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from sim import fuzz as F, styles as S
from compiler import c2
from reader.stage0 import parse_openapi
from engine import machine as M

KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")


def plant(ir, kind):
    ir = copy.deepcopy(ir)
    rules = ir["rules"]
    if kind == "account_early":      # call get_account as soon as the call starts
        start = [r for r in rules if r.get("on") == "enter" and r.get("phase") == ir.get("initial_phase")][0]
        start["do"] = [{"call": "get_account", "args": {"customer_id": "call.customer_id"}}] + start["do"]
    elif kind == "promise_no_yes":   # read-back accepts a 'no' as consent
        for r in rules:
            if r.get("on") == "intent:yes" and "create_promise" in json.dumps(ir.get("procedures", {})) + json.dumps(r):
                r["on"] = "intent:no"
    elif kind == "outcome_enum":     # misspelt outcome code
        s = json.dumps(ir).replace('"\'promise\'"', '"\'promised\'"')
        ir = json.loads(s)
    elif kind == "amount_early":     # an amount in the opening line
        t = ir["templates"]
        k = [r for r in rules if r.get("on") == "enter" and r.get("phase") == ir.get("initial_phase")][0]["do"]
        tid = next(a["say"] for a in k if "say" in a)
        if isinstance(t[tid], dict):
            t[tid]["text"] = t[tid]["text"] + " You owe $420.00."
        else:
            t[tid] = t[tid] + " You owe $420.00."
    return ir


def main():
    ir0 = json.load(open(os.path.join(ROOT, "ir", "brief_a.json"), encoding="utf-8"))
    voc = parse_openapi(os.path.join(KIT, "tools", "openapi.json"))
    cases = S.load_cases(ir0, os.path.join(KIT, "public-test-set.json"), "A")
    ok_all = True
    for kind in ["account_early", "promise_no_yes", "outcome_enum", "amount_early", "silent"]:
        ir = plant(ir0, kind) if kind != "silent" else ir0
        _, cfg = c2.phase_cfg(ir)
        orig = M.Machine.handle
        if kind == "silent":          # the engine forgets to answer a 'no'
            def handle(self, ev, _o=orig):
                out = _o(self, ev)
                return [] if ev.get("type") == "user" and "no" in (ev.get("intents") or []) and not self.s["ended"] else out
            M.Machine.handle = handle
        hits = 0
        try:
            for c in cases:
                for k in range(10):
                    m, tr, ev, b = F.realise(ir, cfg, c, random.Random(k), p_fail=0)
                    hits += sum(1 for n, _ in F.check(ir, voc, c, m, tr) if n == kind)
        finally:
            M.Machine.handle = orig
        print("%-16s planted -> detected %d times %s" % (kind, hits, "" if hits else "  <-- BLIND"))
        ok_all = ok_all and hits > 0
    print("detector OK" if ok_all else "detector has blind spots")


if __name__ == "__main__":
    main()
