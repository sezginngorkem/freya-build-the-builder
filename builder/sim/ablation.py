"""Ablation: switch off one engine mechanism at a time and measure what changes (no model calls, no credits).
For every mechanism: scripted checks (gate: all suites x 6 speech styles + Freya replays) and brief-independent
invariants over random customers (fuzz). A mechanism whose removal changes nothing is dead weight or overfitted; one
whose removal breaks many checks is load-bearing; one whose removal IMPROVES the invariants is harmful.

    python sim/ablation.py [--runs 10]
"""
import argparse, json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FLAGS = ["content_first", "pending_polarity", "specific_polarity", "side_with_answer", "act_gating", "carry_over", "rewind",
         "confirm_conflict", "side_unhandled", "no_silence", "containment"]


def run(off, runs):
    env = dict(os.environ, ENGINE_ABLATE=off)
    g = subprocess.run([sys.executable, "sim/gate.py"], cwd=ROOT, env=env, capture_output=True, text=True)
    m = re.search(r"TOTAL (\d+)/(\d+)", g.stdout)
    reg = re.findall(r"^\s{3}(\S+)$", g.stdout.split("REGRESSIONS")[1].split("\n\n")[0], re.M) if "REGRESSIONS" in g.stdout else []
    f = subprocess.run([sys.executable, "sim/fuzz.py", "--runs", str(runs), "--out", os.path.join(ROOT, "out", "fuzz_abl_%s.json" % (off or "none"))],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    viol = dict((k, int(v)) for k, v in re.findall(r"^\s+(\w+)\s+(\d+)\s+in", f.stdout, re.M))
    return {"gate": (int(m.group(1)), int(m.group(2))) if m else None, "regressions": reg, "fuzz": viol}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--runs", type=int, default=10); a = ap.parse_args()
    res = {}
    for off in [""] + FLAGS:
        t0 = time.time()
        res[off or "ALL_ON"] = run(off, a.runs)
        r = res[off or "ALL_ON"]
        print("%-18s gate %s  regressions %3d  fuzz %s  (%.0fs)" % (off or "ALL_ON", r["gate"], len(r["regressions"]),
              json.dumps(r["fuzz"], sort_keys=True), time.time() - t0), flush=True)
    json.dump(res, open(os.path.join(ROOT, "out", "ablation.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
