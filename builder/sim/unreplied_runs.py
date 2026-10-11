"""How long do real Freya customers go on without replying to the agent's question, and do they reply in the end?

A turn is "not yet replied" when the language layer says the message is unfinished (s__finished = no) or that it
does not touch the question at all (s__reply = none) and it carries no intent and no value. For every run of such
turns in a row we record its length, the persona style, and what ended it: a turn with content (the customer did
reply), or the end of the call. Data only: this is how the waiting rule is decided, not by a guess.

Usage: python sim/unreplied_runs.py            (all cached calls in out/sim_archive/calls)
"""
import collections, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "out", "sim_archive", "calls")


def persona_of():
    m = {}
    for f in glob.glob(os.path.join(ROOT, "out", "sim_archive", "*.json")):
        try:
            doc = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for r in doc.get("runs", []) if isinstance(doc, dict) else []:
            if r.get("callId"):
                st = re.search(r"\[(\w+)\]", r.get("personaName") or "")
                m[r["callId"]] = (st.group(1) if st else "scenario", r.get("case"), bool(r.get("pass")))
    return m


def turns_of(msgs):
    turns = []
    for x in msgs:
        if x["role"] == "user":
            turns.append({"text": x.get("message"), "v": {}})
        elif x["role"] == "system" and turns and isinstance(x.get("message"), str) and '"variable_extracted"' in x["message"]:
            try:
                e = json.loads(x["message"])
            except ValueError:
                continue
            turns[-1]["v"][e["name"]] = e.get("value")
    return turns


def not_yet(v):
    fin = str(v.get("s__finished") or "").lower()
    rep = str(v.get("s__reply") or "").lower()
    content = any(k.startswith("i_") and v[k] in (True, "true", "True") for k in v) or \
        any(k.startswith("s_") and not k.startswith("s__") and not k.endswith("__iso") and str(v[k]).strip() for k in v)
    if fin == "no":
        return "cut"
    if rep == "none" and not content:
        return "unreplied"
    return None


def main():
    who = persona_of()
    runs = []                       # (style, length, kinds, ended_by)
    for f in glob.glob(os.path.join(CACHE, "*.json")):
        cid = os.path.basename(f)[:-5]
        msgs = json.load(open(f, encoding="utf-8"))
        ts = turns_of(msgs)
        if not any("s__finished" in t["v"] for t in ts):
            continue                # calls from before s__finished existed
        style = who.get(cid, ("?",))[0]
        cur = []
        for t in ts:
            k = not_yet(t["v"])
            if k:
                cur.append(k)
            elif cur:
                runs.append((style, len(cur), tuple(cur), "replied"))
                cur = []
        if cur:
            runs.append((style, len(cur), tuple(cur), "call_ended"))
    by = collections.defaultdict(list)
    for r in runs:
        by[r[0]].append(r)
    print("runs of not-yet-replied turns (cut = unfinished message; unreplied = finished, does not touch the question)")
    for style in sorted(by):
        rs = by[style]
        lens = collections.Counter(r[1] for r in rs)
        rep = [r for r in rs if r[3] == "replied"]
        print("%-10s runs %4d  replied in the end %4d (%.0f%%)  length: %s  max %d" % (
            style, len(rs), len(rep), 100.0 * len(rep) / max(1, len(rs)),
            " ".join("%d:%d" % (k, lens[k]) for k in sorted(lens)), max(lens)))
        unr = [r for r in rs if "unreplied" in r[2]]
        if unr:
            print("           with a finished unreplied turn: %d, replied in the end %d" % (
                len(unr), sum(1 for r in unr if r[3] == "replied")))
    allr = runs
    print("ALL runs %d, replied %d, ended unreplied %d" % (
        len(allr), sum(1 for r in allr if r[3] == "replied"), sum(1 for r in allr if r[3] != "replied")))


if __name__ == "__main__":
    main()
