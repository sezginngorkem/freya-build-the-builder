"""Differential check of value grounding (glue._grounded + evidence) between two glue versions, on every customer
message with an extracted date/amount in the archived real Freya calls. Prints every difference.
Usage: python sim/ground_diff.py <old_glue.py> <new_glue.py>"""
import glob, json, os, re, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine import normalize as N
NOW = "2026-10-14T11:00"


def load(path):
    src = open(path, encoding="utf-8").read()
    ns = {"re": re, "IR": {}, "vars": {}}
    exec(src[src.index("def _truthy"):src.index("def _user_event")], ns)
    return ns


old, new = load(sys.argv[1]), load(sys.argv[2])
KIND = {"s_promise_amount": "amount", "s_promise_date": "date", "s_callback_date": "date"}
stats, diffs = collections.Counter(), []
for f in [g for g in glob.glob(os.path.join(ROOT, "out", "sim_archive", "calls", "*.json")) if not g.endswith((".lat.json", ".tools.json"))]:
    try:
        msgs = json.load(open(f, encoding="utf-8"))
    except ValueError:
        continue
    prev_texts, agent = [], ""
    cur = None
    rows = []
    for m in msgs:
        if m["role"] == "assistant":
            if cur:
                rows.append(cur); prev_texts.append(cur["text"])
            cur = None
            agent = str(m.get("message") or "")
            # the same attempt goes on only while the agent waits ("Please go on." or the customer's words said back)
            prev_texts = [] if not agent.strip().endswith(("...?", "Please go on.")) else prev_texts
        elif m["role"] == "user":
            if cur: rows.append(cur); prev_texts.append(cur["text"])
            cur = {"text": str(m.get("message") or ""), "ex": {}, "prev": list(prev_texts), "heard": agent}
        elif m["role"] == "system" and cur and '"variable_extracted"' in str(m.get("message")):
            try:
                e = json.loads(m["message"]); cur["ex"][e["name"]] = e.get("value")
            except ValueError:
                pass
    if cur: rows.append(cur)
    for r in rows:
        for k, kind in KIND.items():
            raw = r["ex"].get(k)
            if raw in (None, ""):
                continue
            if kind == "amount":
                val = N.parse_amount(str(raw)) if hasattr(N, "parse_amount") else None
                try:
                    val = float(val) if val is not None else float(str(raw).replace(",", ""))
                except ValueError:
                    continue
            else:
                d = N.parse_calendar_date(str(raw), NOW, "DMY", None).get("date")
                if not d:
                    continue
                val = d
            recent = " | ".join(r["prev"])
            ev_old = (recent + " " + r["text"]).strip()
            ev_new = new["_join_cut"](re.sub(r"(\d) \| (?=\d)", r"\1", recent), r["text"]) if recent else r["text"]
            try:
                a = old["_grounded"](N, kind, raw, val, ev_old, {}, NOW, r["heard"])
                b = new["_grounded"](N, kind, raw, val, ev_new, {}, NOW, r["heard"])
            except Exception as e:
                stats["error"] += 1
                continue
            stats[kind] += 1
            if a != b:
                stats[kind + "_diff"] += 1
                diffs.append((kind, r["prev"][-1:] , r["text"][:90], raw, a, b))
print(dict(stats))
for d in diffs[:60]:
    print(d)
