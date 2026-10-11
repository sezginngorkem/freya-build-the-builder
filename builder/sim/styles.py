"""Speech-style variants of scripted test customers (no model calls).

A scripted turn carries clean values (slot promise_date = '2026-10-22'). Real callers say them in many ways. This
module rewrites every scripted case into the five customer styles of the official simulator (kit tools/run_cases.py
STYLES) as RAW text, the way Freya's extractor hands it to our glue, so the whole chain (extraction text -> glue
normalisation -> engine -> compiled workflow) is tested against messy speech:

  in_words   every value in words            "the twenty-second of October", "four hundred and fifty-five"
  corrects   a wrong value, then the fix      "the 23rd, sorry, I mean the 22nd"
  talkative  chatter with unrelated dates     "Busy day, my cousin's wedding is on the 30th. I can do the 22nd."
  pieces     long values split over 2 turns   "nineteen eighty..." / "...eight" ; "four four" / "seven one"
  asks_back  a question back before answering "Why do you need that?" then the answer

    python sim/styles.py <ir.json> [--cases cases.json] [--brief A|*] [--styles a,b] [-v]
runs every case in every style through the compiled workflow (emulator) and reports failures per style.
"""
import argparse, copy, datetime as _dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

STYLES = ["in_words", "corrects", "talkative", "pieces", "asks_back"]
_U = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
      "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_T = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}
_ORD = {1: "first", 2: "second", 3: "third", 5: "fifth", 8: "eighth", 9: "ninth", 12: "twelfth"}
_MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def words(n):
    n = int(n)
    if n < 20:
        return _U[n]
    if n < 100:
        return _T[n // 10] + ("-" + _U[n % 10] if n % 10 else "")
    if n < 1000:
        return _U[n // 100] + " hundred" + (" and " + words(n % 100) if n % 100 else "")
    return words(n // 1000) + " thousand" + ((" and " if n % 1000 < 100 else " ") + words(n % 1000) if n % 1000 else "")


def ordinal(n):
    if n in _ORD:
        return _ORD[n]
    if n < 20:
        w = _U[n]
        return (w[:-1] + "th") if w.endswith("e") and n != 3 else w + "th"
    if n % 10 == 0:
        return _T[n // 10][:-1] + "ieth"
    return _T[n // 10] + "-" + ordinal(n % 10)


def year_words(y):
    if 2000 <= y < 2010:
        return "two thousand" + (" and " + _U[y - 2000] if y > 2000 else "")
    hi, lo = divmod(y, 100)
    return words(hi) + " " + (words(lo) if lo >= 10 else ("oh " + _U[lo] if lo else "hundred"))


def say_amount(v):
    v = round(float(v), 2)
    d, c = int(v), int(round((v - int(v)) * 100))
    return words(d) + (" dollars and " + words(c) + " cents" if c else " dollars")


def say_digits(s):
    return " ".join(_U[int(ch)] for ch in str(s) if ch.isdigit())


def say_date(iso, birth=False):
    d = _dt.date.fromisoformat(str(iso)[:10])
    base = "the %s of %s" % (ordinal(d.day), _MON[d.month - 1])
    return base + (", " + year_words(d.year) if birth else "")


def say_time(t):
    h, m = [int(x) for x in str(t).split(":")[:2]]
    hh = h % 12 or 12
    return words(hh) + (" " + (words(m) if m >= 10 else "oh " + _U[m]) if m else "") + (" in the morning" if h < 12 else " in the afternoon" if h < 17 else " in the evening")


def _kind(ir, slot):
    return ((ir.get("slots") or {}).get(slot) or {}).get("kind") or ("birth_date" if "birth" in slot else "text")


def _wrong(kind, v):
    """A nearby wrong value the caller says first and then corrects."""
    if kind == "date":
        return (_dt.date.fromisoformat(v[:10]) + _dt.timedelta(days=1)).isoformat()
    if kind == "amount":
        return float(v) + 50
    if kind == "time":
        h, m = [int(x) for x in v.split(":")[:2]]
        return "%02d:%02d" % ((h + 1) % 24, m)
    return v


def _plain(kind, v):
    if kind == "date":
        d = _dt.date.fromisoformat(v[:10]); return "the %d%s" % (d.day, "th" if 10 < d.day < 14 else {1: "st", 2: "nd", 3: "rd"}.get(d.day % 10, "th"))
    if kind == "amount":
        return "%g dollars" % float(v)
    return str(v)


def _say(kind, v):
    if kind == "birth_date":
        return say_date(v, birth=True)
    if kind == "date":
        return say_date(v)
    if kind == "amount":
        return say_amount(v)
    if kind == "digits":
        return say_digits(v)
    if kind == "time":
        return say_time(v)
    return str(v)


def _side_intent(ir):
    ids = [i["id"] for i in ir.get("intents", [])]
    return next((i for i in ("ask_reason", "other_question", "ask_bot") if i in ids), None)


def variant(ir, case, style):
    """A copy of case whose sim_script slot values are raw speech in this style. None if the style changes nothing."""
    c = copy.deepcopy(case)
    out, changed = [], False
    side = _side_intent(ir)
    slot_turns = [i for i, t in enumerate(c.get("sim_script", [])) if any(v not in (None, "") for v in (t.get("slots") or {}).values())]
    # the persona asks back twice per call; specs often close the call on a second question during the identity
    # check, so the second one goes before a later (non-identity) answer, if there is one
    script = c.get("sim_script", [])
    later = [i for i in slot_turns if not any(k.startswith("id_") for k in (script[i].get("slots") or {}))]
    ask_at = set(slot_turns[:1] + later[-1:]) if slot_turns else set()
    for ti, t in enumerate(c.get("sim_script", [])):
        slots = dict(t.get("slots") or {})
        vals = {k: v for k, v in slots.items() if v not in (None, "") and _kind(ir, k) in ("birth_date", "date", "amount", "digits", "time")}
        if not vals:
            out.append(t); continue
        if style == "asks_back" and side and ti in ask_at:
            out.append({"text": "Why do you need that?", "intents": [side], "slots": {}})
            out.append(t); changed = True; continue
        if style == "asks_back":
            out.append(t); continue
        if style == "pieces":
            first, second = {}, {}
            for k, v in vals.items():
                kind = _kind(ir, k)
                if kind in ("digits", "birth_date"):
                    s = _say(kind, v).split()
                    cut = max(1, len(s) // 2)
                    first[k], second[k] = " ".join(s[:cut]), " ".join(s[cut:])
            if first:
                rest = {k: v for k, v in slots.items() if k not in first}
                # the customer SAYS the parts (as on Freya: "Forty-four." / "Ten."): the words are in the message text
                out.append({"text": " ".join(first.values()) + "...", "intents": [], "slots": first})   # "12 July..."
                second.update({k: (_say(_kind(ir, k), v) if k in vals else v) for k, v in rest.items()})
                tail = " ".join(second[k] for k in first) + "."
                out.append(dict(t, text=(tail + " " + t["text"]) if rest else tail, slots=second)); changed = True; continue
            out.append(t); continue
        new = dict(slots)
        for k, v in vals.items():
            kind = _kind(ir, k)
            if style == "in_words":
                new[k] = _say(kind, v)
            elif style == "corrects" and kind in ("date", "amount", "time"):
                new[k] = "%s, sorry, I mean %s" % (_plain(kind, _wrong(kind, v)), _plain(kind, v) if kind != "time" else v)
            elif style == "talkative" and kind in ("date", "amount"):
                new[k] = "Busy day, the traffic was awful today. My cousin's wedding is on the 30th. Anyway, %s" % _say(kind, v)
            else:
                continue
            changed = True
        out.append(dict(t, slots=new))
    c["sim_script"] = out
    c["id"] = "%s~%s" % (case["id"], style)
    return c if changed else None


def load_cases(ir, cases_path, brief):
    from sim import run_local as R
    raw = json.load(open(cases_path, encoding="utf-8"))
    cases = raw.get("cases", raw) if isinstance(raw, dict) else raw
    cases = [c for c in cases if brief == "*" or c.get("brief", brief) == brief]
    for c in cases:
        if not c.get("sim_script") and c["id"] in R.SCRIPTS:
            c["sim_script"] = [{"text": u["text"], "intents": list(u["intents"]), "slots": dict(u["slots"])} for u in R.SCRIPTS[c["id"]]]
        c["sim_script"] = R.map_intents(ir, [dict(u) for u in c.get("sim_script", [])])
    return cases


def run_styles(ir, cases, vocabulary, styles=STYLES, verbose=False, log=print):
    """Compile the IR and run every case in every style through the workflow emulator. Returns {style: [(id, failures)]}."""
    from compiler import c2
    from sim import emu
    wf = c2.compile_workflow(ir, vocabulary)
    report = {}
    for style in ["plain"] + list(styles):
        fails, n = [], 0
        for c in cases:
            v = copy.deepcopy(c) if style == "plain" else variant(ir, c, style)
            if v is None:
                continue
            n += 1
            try:
                res, _ = emu.run_case(wf, v, verbose=verbose)
                if not res["pass"]:
                    fails.append((v["id"], res["failed"]))
            except Exception as e:
                fails.append((v["id"], ["crash: %s" % str(e)[:200]]))
        report[style] = {"total": n, "fails": fails}
        log("styles %-10s %d/%d pass%s" % (style, n - len(fails), n, "" if not fails else "  FAIL: " + ", ".join(f[0] for f in fails)))
    return report


def main():
    from reader.stage0 import parse_openapi
    from sim import run_local as R
    ap = argparse.ArgumentParser()
    ap.add_argument("ir"); ap.add_argument("--cases", default=os.path.join(R.KIT, "public-test-set.json"))
    ap.add_argument("--brief", default="A"); ap.add_argument("--openapi")
    ap.add_argument("--styles", default=",".join(STYLES)); ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    ir = json.load(open(a.ir, encoding="utf-8"))
    api = a.openapi or (os.path.join(os.path.dirname(a.cases), "openapi.json") if os.path.exists(os.path.join(os.path.dirname(a.cases), "openapi.json"))
                        else os.path.join(R.KIT, "tools", "openapi.json"))
    rep = run_styles(ir, load_cases(ir, a.cases, a.brief), parse_openapi(api), [s for s in a.styles.split(",") if s], a.v)
    for st, r in rep.items():
        for cid, f in r["fails"]:
            print("  %s: %s" % (cid, "; ".join(str(x)[:160] for x in f)))


if __name__ == "__main__":
    main()
