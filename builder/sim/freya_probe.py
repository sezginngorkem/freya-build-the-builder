"""X3: measure Freya's perception layer itself, with the official model settings (a simulation, not the chat route).

Each probe persona is a kit case whose customer, at one moment, says one exact sentence; afterwards it follows the case.
We do not score the call; we read what Freya's extractor reported for that sentence (intent flags, values, main act)
from the call's events. Two runs per probe show whether the reading is stable.

    python sim/freya_probe.py <agent_id> [--reps 2] [--tag ra2]
"""
import argparse, collections, hashlib, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, KIT); sys.path.insert(0, os.path.join(KIT, "tools"))
import freya
from score import http

# (probe id, case, when, exact sentence, what a correct reading is)
PROBES = [
    ("P01", "PUB-06", "right after the agent offers you the minimum payment", "Can I make that payment this Friday instead?",
     "a day proposal: no restructure; act answer; promise_date this Friday"),
    ("P02", "PUB-06", "right after the agent offers you the minimum payment", "Could I pay it off in smaller monthly instalments instead?",
     "a real payment-plan request: restructure true; act request"),
    ("P03", "PUB-04", "when the agent asks whether you can pay today", "I can't pay today, I'll have to do it the week after next.",
     "vague period: vague_date (or no date); not a promise"),
    ("P04", "PUB-04", "when the agent asks whether you can pay today",
     "I can't pay today because my salary arrives on the sixth of November. I can pay it then.", "date 6 November (this year), no wrong year"),
    ("P05", "PUB-05", "when the agent asks whether you can pay today", "I lost my job last month, but I could maybe pay fifty dollars on Friday.",
     "hardship true (topic change) + amount 50 + date Friday"),
    ("P06", "PUB-01", "when the agent asks for your date of birth", "It's the fourteenth of March, nineteen eighty-eight. Why do you need that?",
     "the date + a side question; the date must not be lost"),
    ("P07", "PUB-08", "when the agent asks whether you can pay today", "I already paid it this morning in the app, I think. Can you check?",
     "paid true; act inform"),
    ("P08", "PUB-09", "when the agent asks whether you can pay today", "Can I get lower monthly payments?",
     "restructure true; act request"),
    ("P09", "PUB-06", "right after the agent offers you the minimum payment", "Can I get a discount on that?",
     "no restructure (a discount is not a payment plan); act request or question"),
    ("P10", "PUB-07", "when the agent asks whether you can pay today", "Not today. Maybe Friday, or Monday, I'm not sure.",
     "two candidate days, unsure: should not record a promise without a clear choice"),
]


def persona(case, when, sentence):
    import run_cases as RC
    p = RC.persona_for(case, {"identity": case["identity"]})
    p["prompt"] += ("\n\nIMPORTANT FOR THIS CALL: %s, you say exactly these words and nothing else in that turn: \"%s\". "
                    "After that you continue as written above." % (when, sentence))
    p["name"] = "probe " + p["name"][:60]
    return p


def extraction_at(call, sentence):
    """Variables Freya extracted from the user message that contains the probe sentence."""
    msgs = call.get("messages", [])
    key = sentence.lower()[:25]
    found, out = False, {}
    for m in msgs:
        if m.get("role") == "user":
            if found:
                break
            found = key in str(m.get("message", "")).lower()
            continue
        if not found or m.get("role") != "system":
            continue
        try:
            d = json.loads(m.get("message"))
        except Exception:
            continue
        if d.get("event") == "variable_extracted":
            out[d.get("name")] = d.get("value")
    return found, out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("agent_id"); ap.add_argument("--reps", type=int, default=2); ap.add_argument("--tag", default="x")
    a = ap.parse_args()
    cases = {c["id"]: c for c in json.load(open(os.path.join(KIT, "public-test-set.json")))}
    specs = [persona(cases[c], w, s) for _, c, w, s, _ in PROBES]
    made = freya.create_personas(specs)["personas"]
    pids = [p["id"] for p in made]
    results = collections.defaultdict(list)
    for rep in range(a.reps):
        sessions = [http("/v1/practice/sessions", {"case": c})["variables"] for _, c, _, _, _ in PROBES]
        sim_id, it_id, status = freya.run_simulation(a.agent_id, "probe %s" % time.strftime("%H:%M:%S"), dict(zip(pids, sessions)))
        runs = {r["personaId"]: r for r in freya.get_iteration(sim_id, it_id)["runs"]}
        for (pid_, case, when, sent, want), pid in zip(PROBES, pids):
            r = runs.get(pid) or {}
            if not r.get("callId"):
                results[pid_].append({"said": False, "note": "no call"}); continue
            call = freya.get_call(r["callId"])
            found, ex = extraction_at(call, sent)
            results[pid_].append({"said": found, "true": sorted(k for k, v in ex.items() if v is True or str(v).lower() == "true"),
                                  "values": {k: v for k, v in ex.items() if k.startswith("s_") and v not in (None, "", False)},
                                  "call_id": r["callId"]})
    out = os.path.join(ROOT, "out", "probe_%s.json" % a.tag)
    json.dump({"probes": [dict(zip(["id", "case", "when", "sentence", "want"], p)) for p in PROBES], "results": results}, open(out, "w"), indent=1)
    for pid_, case, when, sent, want in PROBES:
        print("\n%s %s  \"%s\"\n   want: %s" % (pid_, case, sent, want))
        for x in results[pid_]:
            print("   got:  said=%s true=%s values=%s" % (x.get("said"), x.get("true"), json.dumps(x.get("values"), ensure_ascii=False)[:220]))


if __name__ == "__main__":
    main()
