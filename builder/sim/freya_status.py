"""One line: the newest Freya simulation and its progress (for a 2-minute monitor)."""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder"))
import freya
try:
    x = freya.api("GET", "/api/v2/simulations", limit=1)["simulations"][0]
    m = x.get("metrics") or {}
    print("%s %s | %s | runs %s pass %s fail %s | personas %s" % (time.strftime("%H:%M"), x["name"], x["status"], m.get("totalRuns"),
          m.get("passedRuns"), m.get("failedRuns"), x.get("personaCount")), flush=True)
except Exception as e:
    print("%s status error %s" % (time.strftime("%H:%M"), str(e)[:100]), flush=True)
