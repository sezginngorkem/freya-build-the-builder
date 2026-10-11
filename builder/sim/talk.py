"""Talk to a deployed agent yourself, in the terminal, over Freya's chat API (~0.003 credits per turn).
The bank mock gets a practice session for the chosen case, so the agent sees that customer's accounts.
Type your lines; an empty line or 'quit' ends the call. At the end the bank's ledger and the score are shown.

    python sim/talk.py [slot] [case_id]        e.g.  python sim/talk.py brief_a_c2 PUB-01
"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, KIT); sys.path.insert(0, os.path.join(KIT, "tools")); sys.path.insert(0, ROOT)
import freya
from score import http, score_ledger


def main():
    slot = sys.argv[1] if len(sys.argv) > 1 else "brief_a_c2"
    case_id = sys.argv[2] if len(sys.argv) > 2 else "PUB-01"
    st = json.load(open(os.path.join(ROOT, ".freya-agents.json")))[slot]
    case = [c for c in json.load(open(os.path.join(KIT, "public-test-set.json"))) if c["id"] == case_id][0]
    sess = http("/v1/practice/sessions", {"case": case_id})["variables"]
    print("Agent: %s   Customer: %s %s (%s)   now=%s" % (slot, sess.get("first_name"), sess.get("last_name"), case_id, sess.get("now")))
    print("Case script (what this customer is like): %s\n" % case.get("script", "")[:400])
    call_id = None
    for msg in ["Hello?"] + [None] * 200:
        if msg is None:
            try:
                msg = input("YOU   > ").strip()
            except EOFError:
                msg = ""
            if not msg or msg.lower() == "quit":
                break
        body = {"message": msg, "customerVariables": sess}
        body.update({"callId": call_id} if call_id else {"workflowId": st["workflow_id"]})
        t0 = time.time()
        try:
            r = freya.api("POST", "/api/v2/chat/message", body)
        except Exception as e:
            print("  (Freya error: %s)" % str(e)[:160]); continue
        call_id = r["callId"]
        print("AGENT > %s   [%.1fs]" % (r.get("response"), time.time() - t0))
        if r.get("endedByAgent"):
            print("  (the agent ended the call)"); break
    if call_id:
        try:
            freya.api("POST", "/api/v2/chat/end", {"callId": call_id})
        except Exception:
            pass
    led = http("/v1/practice/ledger/" + sess["customer_id"])
    print("\nBANK LEDGER:")
    for c in led.get("calls", []):
        print("  %s %s -> %s" % (c["tool"], json.dumps(c.get("args") or c.get("request")), json.dumps(c.get("result"))[:160]))
    res = score_ledger(case, led)
    print("LEDGER SCORE vs this case's expected result: %s %s" % ("PASS" if res["pass"] else "FAIL", res["failed"]))


if __name__ == "__main__":
    main()
