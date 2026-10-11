"""Do unit-driven self-test customers tell a good read from a bad one? Writes them for read A's interface, runs them on A
and on B (same suite). Usage: python sim/unit_tests_check.py <suite> <irA> <irB> <tag>"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reader import stage0
from selftest.gen import write_cases, run_cases
suite, a, b, tag = sys.argv[1:5]
d = os.path.join("synthetic", suite)
files = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f not in ("cases.json", "freya_cases.json", "openapi.json", "ANSWER_KEY.md", "FREYA_KEY.md", "SOURCES.md")]
st = stage0.run(files, os.path.join(d, "openapi.json"))
A, B = (json.load(open(p, encoding="utf-8")) for p in (a, b))
inv = json.load(open(sys.argv[5], encoding="utf-8")) if len(sys.argv) > 5 else None
cases = write_cases(A, st, inventory=inv)
json.dump(cases, open("out/ut_%s.json" % tag, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for name, ir in (("A", A), ("B", B)):
    res = run_cases(ir, cases)
    print(name, "%d/%d" % (sum(r["pass"] for r in res), len(res)), "fails:", [r["case"]["id"] + ":" + r["case"].get("family", "")[:14] for r in res if not r["pass"]])
