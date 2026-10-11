"""Per customer turn of a Freya call: the extracted variables (what the language layer understood) and where the
engine went next.   python sim/show_extract.py <call_id>"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder"))
import freya
for m in freya.get_call(sys.argv[1])["messages"]:
    msg = m.get("message")
    if m["role"] in ("user", "assistant"):
        print("%s: %s" % ("CUSTOMER" if m["role"] == "user" else "agent   ", msg))
    elif m["role"] == "system" and isinstance(msg, str) and msg.startswith("{"):
        e = json.loads(msg)
        if e.get("event") == "variable_extracted" and e["name"] != "s__utterance" and e.get("value") not in ("", None, False):
            print("      %s = %r" % (e["name"], e["value"]))
        elif e.get("event") == "function_call_complete" and e.get("result", {}).get("validation_errors"):
            print("      !! %s" % e["result"]["validation_errors"])
