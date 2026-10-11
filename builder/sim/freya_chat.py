"""Talk to a deployed workflow over Freya's chat API with natural-language customer lines (cheap: ~0.003 credits/turn).
Creates a practice session on the bank mock for the case, prints the dialogue, the ledger and the credits used.

    python sim/freya_chat.py <slot> <case_id> "line 1" "line 2" ...
"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, KIT); sys.path.insert(0, os.path.join(KIT, "tools")); sys.path.insert(0, ROOT)
import freya
from score import http, score_ledger

STATE = os.path.join(ROOT, ".freya-agents.json")


def credits():
    return freya.api("GET", "/api/v2/workspaces/%s/credits" % freya.workspace_id())["creditsLeft"]


def chat(slot, case_id, lines, show_vars=False):
    st = json.load(open(STATE))[slot]
    case = [c for c in json.load(open(os.path.join(KIT, "public-test-set.json"))) if c["id"] == case_id][0]
    sess = http("/v1/practice/sessions", {"case": case_id})["variables"]
    c0 = credits()
    call_id, errors = None, 0
    for msg in ["Hello?"] + list(lines):
        body = {"message": msg, "customerVariables": sess}
        body.update({"callId": call_id} if call_id else {"workflowId": st["workflow_id"]})
        t0 = time.time()
        try:
            r = freya.api("POST", "/api/v2/chat/message", body)
        except Exception as e:
            errors += 1
            print("ERROR", str(e)[:200])
            if errors >= 2:
                print("stopping after two errors"); break
            continue
        call_id = r["callId"]
        print("[%4.1fs] USER  %s\n        AGENT %s%s" % (time.time() - t0, msg, r.get("response"), "  (ENDED)" if r.get("endedByAgent") else ""))
        if r.get("endedByAgent"):
            break
    if call_id:
        try:
            freya.api("POST", "/api/v2/chat/end", {"callId": call_id})
        except Exception:
            pass
    led = http("/v1/practice/ledger/" + sess["customer_id"])
    res = score_ledger(case, led)
    print("\nLEDGER:", [(c["tool"], c.get("args") or c.get("request"), c.get("result")) for c in led.get("calls", [])])
    print("SCORE:", "PASS" if res["pass"] else "FAIL", res["failed"])
    if call_id:
        time.sleep(2)
        call = freya.get_call(call_id)
        json.dump(call, open(os.path.join(ROOT, "out", "chat-%s.json" % case_id), "w"), indent=1, default=str)
        errs = set()
        for m in call.get("messages", []):
            try:
                vt = json.loads(str(m.get("message"))).get("variable_table") or {}
            except (ValueError, AttributeError):
                continue
            e = vt.get("_error")
            e = e.get("value") if isinstance(e, dict) else e
            if e not in (None, "", "None"):
                errs.add(str(e)[-300:])
        for e in errs:
            print("CODE NODE ERROR:", e)
    print("credits used: %.4f" % (c0 - credits()))
    return call_id


if __name__ == "__main__":
    chat(sys.argv[1], sys.argv[2], sys.argv[3:])
