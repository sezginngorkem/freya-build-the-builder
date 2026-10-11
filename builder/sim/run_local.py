"""Run a PolicyIR against the practice cases locally: scripted customers, mock bank, the kit's scorer.
No Freya, no credits. The customer side is structured (intents + slots), so this tests the rule
machine, not language understanding.

    python sim/run_local.py ir/brief_a.json --brief A [-v]
"""
import argparse, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(KIT, "tools"))
from engine.machine import run_script
from sim.mockbank import MockBank
from score import score_ledger

def U(intents=None, text="", **slots):
    return {"intents": intents or [], "text": text, "slots": slots}

# One scripted customer per practice case. Each follows the case's "script" field.
SCRIPTS = {
    "PUB-01": [U(["confirm_identity"], "Yes, that's me."), U(text="14 March 1988", id_date_of_birth="1988-03-14"),
               U(text="4471", id_phone_last4="4471"), U(["yes"], "Yes, I can pay it today."), U(["yes"], "Yes, I confirm.")],
    "PUB-02": [U(["third_party"], "This is her husband. What is this about?"), U(["ask_reason"], "What is it about? I can pay it myself."),
               U(text="She can be reached tomorrow morning around eleven.", callback_date="2026-10-15", callback_time="11:00")],
    "PUB-03": [U(["confirm_identity"], "Yes."), U(text="12 July 1991", id_date_of_birth="1991-07-12"), U(text="21 August 1992", id_date_of_birth="1992-08-21"),
               U(text="21 July 1990", id_date_of_birth="1990-07-21"), U(["other_question"], "How much do I owe?")],
    "PUB-04": [U(["confirm_identity"], "Yes, speaking."), U(text="30 January 1984", id_date_of_birth="1984-01-30"), U(text="2219", id_phone_last4="2219"),
               U(text="My salary arrives on 6 November, I can pay then.", promise_date="2026-11-06"),
               U(["ask_bot"], "Am I talking to a robot?"), U(["yes"], "OK, that works."), U(["yes"], "Yes, I confirm.")],
    "PUB-05": [U(["confirm_identity"], "Yes."), U(text="9 September 1990", id_date_of_birth="1990-09-09"), U(text="8846", id_phone_last4="8846"),
               U(["hardship", "no"], "I lost my job last month, I can't pay anything. Can I get a discount?"), U(["no"], "No, I don't want to be transferred.")],
    "PUB-06": [U(["confirm_identity"], "Yes."), U(text="17 May 1986", id_date_of_birth="1986-05-17"), U(text="1502", id_phone_last4="1502"),
               U(["too_much"], "The full amount is too much right now."), U(["no"], "You tell me."), U(["yes"], "Yes, Friday works."), U(["yes"], "Yes, I confirm.")],
    "PUB-07": [U(["confirm_identity"], "Yes."), U(text="5 December 1975", id_date_of_birth="1975-12-05"), U(text="7093", id_phone_last4="7093"),
               U(["no", "vague_date"], "Not today. The week after next."), U(text="Monday the 26th.", promise_date="2026-10-26"),
               U(["yes"], "OK, the 27th then."), U(["yes"], "Yes, I confirm.")],
    "PUB-08": [U(["confirm_identity"], "Yes."), U(text="28 April 1993", id_date_of_birth="1993-04-28"), U(text="3317", id_phone_last4="3317"),
               U(["paid"], "I paid it in the app this morning.")],
    "PUB-09": [U(["confirm_identity"], "Yes."), U(text="11 August 1981", id_date_of_birth="1981-08-11"), U(text="5560", id_phone_last4="5560"),
               U(["restructure"], "I can't pay this amount, I want lower instalments.")],
    "PUB-10": [U(["confirm_identity"], "Yes."), U(text="23 February 1989", id_date_of_birth="1989-02-23"), U(text="9904", id_phone_last4="9904"),
               U(["no"], "I can't pay today."), U(["yes"], "Yes, Friday, the full amount."), U(["yes"], "Yes, I confirm.")],
    "PUB-11": [U(["confirm_identity"], "Yes."), U(text="3 June 1987", id_date_of_birth="1987-06-03"), U(text="2288", id_phone_last4="2288"),
               U(["no"], "Not today, but I can pay all three this Friday.", promise_date="2026-10-16"), U(["yes"], "Yes, I confirm.")],
    "PUB-12": [U(["confirm_identity"], "Yes."), U(text="19 October 1983", id_date_of_birth="1983-10-19"), U(text="4401", id_phone_last4="4401"),
               U(text="Sorry, 4410", id_phone_last4="4410"), U(["no"], "Not all of them, no."),
               U(text="I can pay the credit card tomorrow.", promise_date="2026-10-15"),
               U(["no"], "No, I won't pay the personal loan."), U(["no"], "No. Whatever you offer, no."),
               U(["no"], "No, not the car loan either."), U(["yes"], "Yes, I confirm.")],
    "PUB-13": [U(["confirm_identity"], "Yes."), U(text="8 January 1991", id_date_of_birth="1991-01-08"), U(text="6604", id_phone_last4="6604"),
               U(["no"], "I can't pay today. I want to pay both on 30 October.", promise_date="2026-10-30"), U(["yes"], "OK, yes, I confirm.")],
}


# Test scripts name intents one way, a reader may name the same intent another way (Freya matches by the
# description, so names do not matter there). Map known synonyms to the IR's own id.
INTENT_ALIASES = [{"stop_calling", "cease", "cease_contact", "stop_contact"}, {"third_party", "spouse_partner", "relative"},
                  {"restructure", "restructuring"}, {"human", "ask_human", "agent_request"}]


_STOP = {"the", "a", "an", "of", "to", "or", "and", "is", "be", "that", "this", "for", "with", "by", "in", "on", "customer",
         "member", "says", "asks", "person", "caller", "they", "their", "not", "no", "yes", "has", "have", "who", "what"}


def _toks(text):
    out = set()
    for w in re.findall(r"[a-z]+", str(text or "").lower().replace("_", " ")):
        if len(w) > 2 and w not in _STOP:
            out.add(w[:6])          # crude stem: 'counselling'/'counsellor', 'represented'/'representing'
    return out


def map_intents(ir, script):
    """A test script names an intent its own way; the reader may have named the same concept differently (Freya does
    not care: it matches the description). Map an unknown name to the IR intent whose id + description share the most
    words with it (unique best match), after the known synonym groups."""
    intents = ir.get("intents", [])
    ids = set(i["id"] for i in intents)
    for u in script:
        out = []
        for i in u.get("intents") or []:
            if i not in ids:
                i2 = next((x for g in INTENT_ALIASES if i in g for x in sorted(g) if x in ids), None)
                if i2 is None:
                    want = _toks(i)
                    # a shared word in the intent's own name counts more than one in its description
                    scored = sorted(((2 * len(want & _toks(x["id"])) + len(want & _toks(str(x.get("description", "")))), x["id"])
                                     for x in intents), reverse=True)
                    if scored and scored[0][0] > 0 and (len(scored) == 1 or scored[1][0] < scored[0][0]):
                        i2 = scored[0][1]
                i = i2 or i
            out.append(i)
        u["intents"] = out
    return script


def run_case(ir, case, verbose=False):
    bank = MockBank(case)
    call_vars = dict(case["variables"], customer_id="c_" + case["id"])
    # after its script a real customer still answers politely ("no, that's all"); two such turns at most
    tail = [U(["no"], "No, that's all, thank you."), U(["no"], "Goodbye.")]
    script = [U(t.get("intents"), t.get("text", ""), **(t.get("slots") or {})) for t in case["sim_script"]] if case.get("sim_script") else SCRIPTS.get(case["id"], [])
    script = map_intents(ir, [dict(u) for u in script])
    m, tr = run_script(ir, call_vars, bank, script + tail)
    res = score_ledger(case, bank.ledger)
    viol = m.s["var"].get("_violations") or []
    if viol:   # words the spec restricts in time, said too early
        res["pass"] = False
        res["failed"] = list(res.get("failed") or []) + ["restricted word: " + v for v in viol]
    if verbose or not res["pass"]:
        for who, x in tr:
            if who == "agent":
                if "say" in x or "instruct" in x:
                    print("     AGENT:", x.get("say") or "[instr] " + x.get("instruct"))
            elif who == "user":
                print("     USER :", x.get("text"), x.get("intents") or "", {k: v for k, v in x.get("slots", {}).items()} or "")
            elif who == "tool":
                print("     TOOL :", x["name"], x["args"], "->", x["data"])
        errs = [t for t in m.s["trace"] if t["kind"] == "rule_error"]
        for e in errs:
            print("     RULE ERROR:", e)
    return res, bank.ledger, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ir"); ap.add_argument("--brief", default="A"); ap.add_argument("--only"); ap.add_argument("-v", action="store_true")
    ap.add_argument("--cases", default=os.path.join(KIT, "public-test-set.json"))
    a = ap.parse_args()
    ir = json.load(open(a.ir, encoding="utf-8"))
    cases = [c for c in json.load(open(a.cases, encoding="utf-8")) if (a.brief == "*" or c["brief"] == a.brief) and (not a.only or c["id"] in a.only.split(","))]
    n = 0
    for c in cases:
        try:
            res, led, m = run_case(ir, c, a.v)
        except Exception as e:
            import traceback; traceback.print_exc()
            res, led = {"pass": False, "failed": ["crash: %s" % e]}, {"calls": []}
        n += res["pass"]
        print(("PASS" if res["pass"] else "FAIL"), c["id"], c["family"], "|", " > ".join(x["tool"] for x in led["calls"]))
        for f in res["failed"]:
            print("       -", f)
    print("\n%d / %d passed (ledger checks only; conversation checks need the judge)" % (n, len(cases)))


if __name__ == "__main__":
    main()
