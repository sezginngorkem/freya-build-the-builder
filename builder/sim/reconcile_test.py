"""Offline test of reader/reconcile.py: reconcile(A, B) in both directions on two existing reads of one suite."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reader import stage0, llm
from reader.reconcile import reconcile
from reader.read import _problems
suite, a_path, b_path, tag = sys.argv[1:5]
d = os.path.join("synthetic", suite)
files = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f not in ("cases.json", "freya_cases.json", "openapi.json", "ANSWER_KEY.md", "FREYA_KEY.md", "SOURCES.md")]
st = stage0.run(files, os.path.join(d, "openapi.json"))
docs = stage0.render_for_llm(st)
A, B = (json.load(open(p, encoding="utf-8")) for p in (a_path, b_path))
t0 = time.time()
ir, rep = reconcile(A, B, docs, lambda x: _problems(x, st), log=print)
print("seconds %.0f applied=%s" % (time.time() - t0, rep["applied"]))
json.dump(ir, open("out/rec_%s.json" % tag, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
