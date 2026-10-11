"""Offline test of the unit-by-unit implementation check (G2) + one patch repair from its findings.
Usage: python sim/unit_check_test.py <suite> <ir.json> <inventory.json> <tag>"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reader import stage0, llm, shapes as S
from reader.read import _problems, COMPILE_SYS, REPAIR_PROMPT, LANG, ask
from reader.patch import patched
from reader.unit_check import check_units
suite, irp, invp, tag = sys.argv[1:5]
d = os.path.join("synthetic", suite)
files = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f not in ("cases.json", "freya_cases.json", "openapi.json", "ANSWER_KEY.md", "FREYA_KEY.md", "SOURCES.md")]
st = stage0.run(files, os.path.join(d, "openapi.json"))
docs = stage0.render_for_llm(st)
ir = json.load(open(irp, encoding="utf-8")); inv = json.load(open(invp, encoding="utf-8"))
t0 = time.time()
probs = check_units(ir, inv, docs, LANG)
print("check seconds %.0f findings %d" % (time.time() - t0, len(probs)))
new = ir
if probs:
    t1 = time.time()
    try:
        new = ask(COMPILE_SYS, REPAIR_PROMPT.format(problems="\n".join(probs[:80]), docs=docs, ir=json.dumps(ir, ensure_ascii=False)),
                  "repair from unit check", lambda r: S.policy_ir(patched(ir, r)), log=print)
        b, a = len(_problems(ir, st)), len(_problems(new, st))
        print("repair seconds %.0f static problems %d -> %d" % (time.time() - t1, b, a))
        if a > b:
            new = ir; print("repair rejected")
    except Exception as e:
        print("repair failed", e); new = ir
json.dump(new, open("out/uc_%s.json" % tag, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
