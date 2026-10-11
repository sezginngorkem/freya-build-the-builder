"""Health board: every failing Freya call of the archive, put into a failure class from its transcript, ledger and
judge text. Classes are observable symptoms (what went wrong in the call), each tied to the root cause we found
for it (notes/hata-haritasi.md). A call can carry several classes.

    python sim/triage.py                 # all archived simulations, newest agents last
    python sim/triage.py --sim c2c28061  # one simulation: classes per call + case x style matrix
"""
import argparse, collections, glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = os.path.join(ROOT, "out", "sim_archive")


def style_of(name):
    m = re.search(r"\[([a-zA-Z_0-9]+)\]", name or "")
    return m.group(1) if m else "plain"


def classes(r):
    """Observable failure classes of one failing call."""
    out = []
    turns = r.get("turns") or []
    agent = [t["text"] for t in turns if t["role"] == "agent"]
    cust = [t["text"] for t in turns if t["role"] == "customer"]
    led = " ".join(r.get("ledger_failed") or [])
    judge = " ".join(str(r.get("reason") or "").split()).lower() if r.get("outcome") != "pass" else ""
    rep = collections.Counter(agent)
    if rep and max(rep.values()) >= 3:
        out.append("loop: same line said 3+ times")
    cut = [c for c in cust if c.strip() and (not re.search(r"[.!?]['\")\]]*$", c.strip()) or c.strip().endswith("..."))]
    if cut:
        out.append("customer turns cut off (%d)" % len(cut))
    if "'not_verified', 'declined'" in led and any(re.search(r"\b(why|which account|what is this)\b", c.lower()) and c.strip().endswith("?") for c in cust):
        out.append("question back counted as refusal")
    if "recorded" in judge and ("message 0" in judge or "greeting" in judge or "opening" in judge or "disclos" in judge):
        out.append("judge: restricted word in a fixed sentence")
    if re.search(r"(robot|digital assistant).*(ignor|did not|failed)|(ignor|did not|failed).*(robot|digital assistant)", judge):
        out.append("side question not answered")
    if "promises [(" in led and "expected [(" in led:
        got = re.search(r"promises \[\('p\d', ([\d.]+), '([\d-]+)'\)", led)
        exp = re.search(r"expected \[\('p\d', ([\d.]+), '([\d-]+)'\)\]", led)
        if got and exp:
            if got.group(2) != exp.group(2):
                out.append("wrong promise date")
            if got.group(1) != exp.group(1):
                out.append("wrong promise amount")
    if "no_promise', 'refused'" in led and "expected ('promise'" in led:
        out.append("promise lost: closed as refused")
    if "transfers [], expected [{'queue'" in led:
        out.append("transfer missed")
    if re.search(r"transfers \[\{'queue': '(\w+)'\}\], expected \[\]", led):
        out.append("transfer not wanted")
    if "callbacks [], expected [{" in led:
        out.append("callback missed")
    if "not closed with close_call" in led:
        out.append("call never closed")
    if re.search(r"offered (twice|two)|more than once|not .*once|only once", judge) and "offer" in judge:
        out.append("offer repeated / count rule")
    if "rest stays overdue" in judge and ("did not include" in judge or "without" in judge):
        out.append("mandatory sentence missing")
    if r.get("outcome") in ("inconclusive", "running", "queued", None):
        out.append("judge: no verdict")
    if not out:
        out.append("other (read it)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim")
    a = ap.parse_args()
    index = json.load(open(os.path.join(ARCH, "index.json"), encoding="utf-8"))
    sims = sorted(index.items(), key=lambda kv: kv[1].get("createdAt") or "")
    if a.sim:
        sims = [(k, v) for k, v in sims if k.startswith(a.sim)]
    total = collections.Counter()
    for sid, e in sims:
        doc = json.load(open(os.path.join(ARCH, sid + ".json"), encoding="utf-8"))
        runs = doc["runs"]
        fails = [r for r in runs if not r["pass"]]
        cnt = collections.Counter()
        for r in fails:
            for c in classes(r):
                cnt[re.sub(r" \(\d+\)", "", c)] += 1
        total.update(cnt)
        print("%s %-22s %-28s %3d/%-3d | %s" % (sid[:8], e.get("name"), e.get("agent"), len(runs) - len(fails), len(runs),
                                                ", ".join("%s %d" % kv for kv in cnt.most_common())))
        if a.sim:
            for r in sorted(fails, key=lambda r: (r["case"], r.get("personaName"))):
                print("    %-7s %-12s %s" % (r["case"], style_of(r.get("personaName")), " | ".join(classes(r))))
            m = collections.defaultdict(list)
            for r in runs:
                m[(r["case"], style_of(r.get("personaName")))].append(r["pass"])
            sts = sorted(set(s for _, s in m))
            print("\n    case    " + " ".join("%-9s" % s[:9] for s in sts))
            for c in sorted(set(c for c, _ in m)):
                print("    %-7s " % c + " ".join("%-9s" % "".join("x" if p else "." for p in m.get((c, s), [])) for s in sts))
    print("\nALL FAILING CALLS BY CLASS:")
    for k, v in total.most_common():
        print("  %4d  %s" % (v, k))


if __name__ == "__main__":
    main()
