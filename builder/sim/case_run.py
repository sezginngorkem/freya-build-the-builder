"""Run a scripted chat on the final-case agent and print the server-side transcript (survives chat 504s).
python sim/case_run.py <slot> <customerNumber> <now> "line" ..."""
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
    try:
        r = freya.api("POST", "/api/v2/chat/message", body)
        cid = r["callId"]
        if r.get("endedByAgent"):
            break
    except Exception as e:
        time.sleep(12)   # the turn still runs server-side; give it time before the next line
time.sleep(3)
c = freya.get_call(cid)
for m in c["messages"]:
    if m["role"] in ("assistant", "user") and str(m["message"]) not in ("Alo?", "Hello."):
        print(("M: " if m["role"] == "user" else "A: ") + str(m["message"])[:330])
