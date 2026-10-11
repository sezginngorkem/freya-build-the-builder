"""Chat with the final-case agent on Freya: python sim/case_chat.py <slot> <customerNumber> <now> "line" ..."""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "kit", "build-the-builder"))
import freya
slot, cno, now = sys.argv[1:4]
wid = json.load(open(".freya-agents.json"))[slot]["workflow_id"]
cv = {"customerNumber": cno, "now": now}
cid = None
for msg in ["Alo?"] + sys.argv[4:]:
    body = {"message": msg, "customerVariables": cv}
    body.update({"callId": cid} if cid else {"workflowId": wid})
    t0 = time.time()
    try:
        r = freya.api("POST", "/api/v2/chat/message", body)
    except Exception as e:
        print("ERROR", str(e)[:200]); continue
    cid = r["callId"]
    print("[%4.1fs] M: %s\n       A: %s%s" % (time.time() - t0, msg, r.get("response"), " (ENDED)" if r.get("endedByAgent") else ""))
    if r.get("endedByAgent"):
        break
