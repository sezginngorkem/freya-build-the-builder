"""E1: the final tests run "on several calendar days". Do reader-made IRs decide like the verified gold IR when 'now'
moves? Same customers, same turns, 'now' shifted by -3..+12 days (keeping the time of day); compare the bank calls of
each reader IR with the gold IR. A difference is a date-logic disagreement (usually a misread rule) that the kit's fixed
'now' values never exposed. Customer turns that name an absolute date are shifted along with 'now'.

    python sim/calendar_diff.py [--gold ir/brief_a.json] [--irs out/cons_a1.json,...] [--days -3:12]
"""
import argparse, collections, copy, datetime as _dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from sim import styles as S, run_local as R
from sim.mockbank import MockBank

KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")


def shift_case(c, days):
    c = copy.deepcopy(c)
    now = c["variables"]["now"]
    d0 = _dt.datetime.fromisoformat(now)
    c["variables"]["now"] = (d0 + _dt.timedelta(days=days)).isoformat(timespec="minutes")
    for t in c.get("sim_script", []):
        for k, v in list((t.get("slots") or {}).items()):
            if isinstance(v, str) and len(v) == 10 and v[4] == "-" and k not in ("id_date_of_birth",) and not k.startswith("id_"):
                try:
                    t["slots"][k] = (_dt.date.fromisoformat(v) + _dt.timedelta(days=days)).isoformat()
                except ValueError:
                    pass
    return c


def calls(ir, c):
    bank = MockBank(c)
    cv = dict(c["variables"]); cv.setdefault("customer_id", "c_" + c["id"])
    script = [R.U(t.get("intents"), t.get("text", ""), **(t.get("slots") or {})) for t in c["sim_script"]]
    tail = [R.U(["no"], "No, that's all."), R.U(["no"], "Goodbye.")]
    try:
        m, tr = R.run_script(ir, cv, bank, script + tail)
    except Exception as e:
        return ["crash %s" % str(e)[:80]]
    return [(x["name"], json.dumps({k: v for k, v in x["args"].items() if k != "customer_id"}, sort_keys=True)) for w, x in tr if w == "tool"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="ir/brief_a.json")
    ap.add_argument("--irs", default="out/cons_a1.json,out/cons_a2.json,out/cons_a3.json,out/a_v0.json")
    ap.add_argument("--days", default="-3:12"); ap.add_argument("--brief", default="A")
    a = ap.parse_args()
    lo, hi = [int(x) for x in a.days.split(":")]
    gold = json.load(open(os.path.join(ROOT, a.gold), encoding="utf-8"))
    cases = S.load_cases(gold, os.path.join(KIT, "public-test-set.json"), a.brief)
    irs = {p: json.load(open(os.path.join(ROOT, p), encoding="utf-8")) for p in a.irs.split(",") if os.path.exists(os.path.join(ROOT, p))}
    diff = collections.defaultdict(list)
    n = 0
    for c in cases:
        for d in range(lo, hi + 1):
            cg = shift_case(c, d)
            want = calls(gold, cg)
            for p, ir in irs.items():
                cc = copy.deepcopy(cg)
                cc["sim_script"] = R.map_intents(ir, [dict(t) for t in cc["sim_script"]])
                got = calls(ir, cc)
                n += 1
                if got != want:
                    diff[p].append((c["id"], d, cg["variables"]["now"][:10], want, got))
    print("calendar differential: %d (ir, case, day) runs" % n)
    for p in irs:
        lst = diff.get(p, [])
        print("  %-20s %3d differences" % (p, len(lst)))
        byc = collections.Counter(x[0] for x in lst)
        print("      by case:", dict(byc))
        for cid, d, now, want, got in lst[:4]:
            first = next((i for i, (x, y) in enumerate(zip(want + [None] * 9, got + [None] * 9)) if x != y), None)
            print("      %s now=%s (shift %+d): gold %s | reader %s" % (cid, now, d, (want + [None] * 9)[first], (got + [None] * 9)[first]))
    json.dump({p: diff.get(p, []) for p in irs}, open(os.path.join(ROOT, "out", "calendar_diff.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
