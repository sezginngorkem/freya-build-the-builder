"""Regression gate: one command that measures EVERYTHING and compares it with the last accepted baseline.
A change is accepted only if nothing that passed before fails now (CAR-bench lesson: targeted checks miss collateral
damage; re-measure the whole set every time).

    python sim/gate.py            # run, compare with out/gate_baseline.json, exit 1 on any regression
    python sim/gate.py --accept   # run and, if there is no regression, store the result as the new baseline

Measured: unit tests; every IR below on its cases, through the compiled Freya workflow (emulator), in the plain form
and in the five customer speech styles (sim/styles.py). No model calls, no credits.
"""
import argparse, glob, io, json, os, subprocess, sys, time, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from sim import styles as S
from reader.stage0 import parse_openapi

KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
PUB = os.path.join(KIT, "public-test-set.json")
API = os.path.join(KIT, "tools", "openapi.json")
SYN = os.path.join(ROOT, "synthetic")
# (IR file, cases file, brief filter, openapi)
SUITES = [("ir/brief_a.json", PUB, "A", API), ("ir/brief_b.json", PUB, "B", API)]
SUITES += [("out/cons_a%d.json" % i, PUB, "A", API) for i in (1, 2, 3)] + [("out/ab_v0.json", PUB, "B", API)]
for ir_glob, suite in [("out/s1.json", "S1_company_clean"), ("out/s1_r*.json", "S1_company_clean"), ("out/s2b.json", "S2_raw_material"), ("out/s3.json", "S3_insurance_premium"),
                       ("out/s4_r9.json", "S4_edge_variant"), ("out/s5*.json", "S5_realworld_style"), ("out/s6*.json", "S6_messy_chain"),
                       ("out/s7.json", "S7_unseen_real"), ("out/s7md_v2.json", "S7_single_md")]:
    for f in sorted(glob.glob(os.path.join(ROOT, ir_glob))):
        if not f.endswith((".inventory.json", ".llmtrace.json")):
            SUITES.append((os.path.relpath(f, ROOT), os.path.join(SYN, suite, "cases.json"), "*", os.path.join(SYN, suite, "openapi.json")))
# replays of real Freya failures (what Freya's extractor actually produced): a fixed failure can never come back silently
REPLAYS = os.path.join(SYN, "replays", "cases.json")
SUITES += [(ir, REPLAYS, "*", API) for ir in ("ir/brief_a.json", "out/cons_a1.json", "out/cons_a2.json", "out/cons_a3.json")]
BASE = os.path.join(ROOT, "out", "gate_baseline.json")


def run():
    res = {}
    for t in sorted(glob.glob(os.path.join(ROOT, "tests", "test_*.py"))):
        p = subprocess.run([sys.executable, t], cwd=ROOT, capture_output=True, text=True)
        res["unit:" + os.path.basename(t)] = p.returncode == 0
    for ir_path, cases_path, brief, api in SUITES:
        if not os.path.exists(os.path.join(ROOT, ir_path)):
            continue
        ir = json.load(open(os.path.join(ROOT, ir_path), encoding="utf-8"))
        cases = [c for c in S.load_cases(ir, cases_path, brief) if not c.get("needs_freya")]
        tag = "replay:" if cases_path == REPLAYS else ""
        with contextlib.redirect_stdout(io.StringIO()):
            rep = S.run_styles(ir, cases, parse_openapi(api), [] if tag else S.STYLES, log=lambda m: None)
        for style, r in rep.items():
            failed = set(cid for cid, _ in r["fails"])
            for c in cases:
                cid = c["id"] if style == "plain" else "%s~%s" % (c["id"], style)
                if style != "plain" and S.variant(ir, c, style) is None:
                    continue
                res["%s%s|%s" % (tag, ir_path, cid)] = cid not in failed
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--accept", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    res = run()
    base = json.load(open(BASE)) if os.path.exists(BASE) else {}
    regress = sorted(k for k, ok in res.items() if not ok and base.get(k) is True)
    newfail = sorted(k for k, ok in res.items() if not ok and k not in base)
    fixed = sorted(k for k, ok in res.items() if ok and base.get(k) is False)
    still = sorted(k for k, ok in res.items() if not ok and base.get(k) is False)
    by_ir = {}
    for k, ok in res.items():
        g = k.split("|")[0]
        by_ir.setdefault(g, [0, 0]); by_ir[g][0] += ok; by_ir[g][1] += 1
    for g, (p, n) in sorted(by_ir.items()):
        print("%-28s %4d/%-4d %s" % (g, p, n, "" if p == n else "<-- %d failing" % (n - p)))
    print("\nTOTAL %d/%d checks pass in %.0f s" % (sum(res.values()), len(res), time.time() - t0))
    for name, lst in (("REGRESSIONS (passed before, fail now)", regress), ("new checks failing", newfail),
                      ("fixed since baseline", fixed), ("still failing", still)):
        if lst:
            print("\n%s: %d" % (name, len(lst)))
            for k in lst[:40]:
                print("  ", k)
    if a.accept and not regress:
        json.dump(res, open(BASE, "w"), indent=0, sort_keys=True)
        print("\nbaseline updated (%s)" % os.path.relpath(BASE, ROOT))
    sys.exit(1 if regress else 0)


if __name__ == "__main__":
    main()
