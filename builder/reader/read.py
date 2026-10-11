"""Brief reader v0: documents + OpenAPI -> PolicyIR (validated).

Stages
  0  deterministic normalisation (stage0.py): numbered sentences, parsed tables, OpenAPI vocabulary
  1  rule inventory (LLM): every normative unit with its sentence ids and type; amendments as edit records
  2  compile (LLM): PolicyIR in the rule language (language.md), citing sentence ids
  3  static validation (validate.py) + repair rounds (LLM) with the concrete problems as counterexamples
Usage:
  python -m reader.read OUT.json BRIEF.md [BRIEF2.md ...] OPENAPI.json [--example IR.json --example-brief B.md ...]
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from reader import stage0, llm
from reader import shapes as S
from reader.validate import validate
from reader.patch import PATCH_FORMAT, patched

LANG = open(os.path.join(HERE, "language.md"), encoding="utf-8").read()

INVENTORY_SYS = """You read bank call specifications with extreme care. Your job is recall: list EVERY normative unit
(something the phone agent must, must not, or may do; a definition; a value; a table row; an outcome rule;
a precedence statement; an exception; an amendment). Missing one rule fails real customers.
Reply with JSON only."""

INVENTORY_PROMPT = """DOCUMENTS (each line starts with its sentence id; tables are given parsed):
{docs}

TOOLS (from the OpenAPI file; these names and enum values are authoritative):
{tools}

Return a JSON object:
{{"units": [{{"sids": ["D1.s010"], "type": "<one of: say_required, say_forbidden, identity, third_party, calendar,
 table, deadline, amount, negotiation, intent_response, confirmation, recording, outcome, multi_item, precedence,
 exception, definition, variable, amendment, other>", "rule": "<the rule restated precisely: who, when, condition,
 exact counts, inclusive/exclusive bounds, the exact quoted wording if any>", "exceptions": "<exceptions/precedence if any>"}}],
 "amendments": [{{"sids": [...], "target_sids": [...], "op": "replace|add|delete|scope", "old": "...", "new": "...",
 "scope": "...", "effective": "..."}}],
 "non_normative": {{"<sid>": "<why it is not a rule>"}},
 "ambiguities": [{{"sids": [...], "question": "...", "readings": ["...", "..."]}}]}}
Every sentence id must appear in some unit's sids or in non_normative."""

COMPILE_SYS = "You are a precise compiler from bank call specifications to PolicyIR. Reply with one JSON object only.\n\n" + LANG

COMPILE_PROMPT = """{example}
DOCUMENTS:
{docs}

TOOLS (authoritative names, arguments, enums, return fields):
{tools}

RULE INVENTORY (from a first careful reading; every unit must be implemented and cited by its sids):
{inventory}

Write the complete PolicyIR for these documents. Reason about the call flow first in your head, then output only
the JSON object. Requirements: implement every inventory unit; cite sentence ids in "src"; put non-rule sentences
in "coverage"; use only the functions and actions listed; follow the conventions."""

REPAIR_PROMPT = """The PolicyIR below has problems found by a static checker. Fix ALL of them. Do not remove correct rules.
""" + PATCH_FORMAT.replace("{", "{{").replace("}", "}}") + """

PROBLEMS:
{problems}

DOCUMENTS (for reference):
{docs}

CURRENT IR:
{ir}"""


def tools_view(voc):
    out = {}
    for name, t in voc.get("tools", {}).items():
        out[name] = {"summary": t["summary"], "args": t["args"], "required": t["required"], "returns": t["returns"]}
    return json.dumps(out, indent=1)


def example_block(ex_ir_path, ex_briefs):
    if not ex_ir_path:
        return ""
    ex = json.load(open(ex_ir_path, encoding="utf-8"))
    txt = "\n\n".join(open(p, encoding="utf-8").read() for p in ex_briefs)
    return ("WORKED EXAMPLE (a different specification and its correct PolicyIR; learn the style, do NOT copy its "
            "values, names or rules unless the new documents say the same):\n--- example specification ---\n%s\n"
            "--- example PolicyIR ---\n%s\n--- end of example ---\n" % (txt, json.dumps(ex, ensure_ascii=False)))


def ask(system, prompt, purpose, shape, retries=1, log=print):
    """One model call whose JSON answer is normalised by `shape` (reader/shapes.py). An unusable answer (no JSON, wrong
    shape) is asked again once, with the error; then ShapeError. A model's answer shape varies between runs; trusting
    one exact shape crashed the whole builder once (2026-10-11)."""
    last = None
    for attempt in range(retries + 1):
        p = prompt if last is None else (prompt + "\n\nYOUR PREVIOUS REPLY COULD NOT BE USED: %s\nReply again with the JSON only, "
                                         "in exactly the format asked for." % last)
        try:
            return shape(llm.extract_json(llm.call(system, p, purpose=purpose if attempt == 0 else purpose + " (retry: unusable reply)")))
        except (ValueError, KeyError, TypeError, AttributeError) as e:   # JSON decode errors and ShapeError are ValueErrors
            last = str(e)[:300]
            log("%s: unusable reply (%s)%s" % (purpose, last, "; asking again" if attempt < retries else ""))
    raise S.ShapeError("%s: no usable reply: %s" % (purpose, last))


def _problems(ir, st):
    try:
        return [p for p in validate(ir, st["vocabulary"], st["sentences"]) if not p.startswith("WARN")]
    except Exception as e:      # a validator crash on an unexpected IR shape is itself a problem to repair, not a stop
        return ["validator could not check this IR (%s: %s)" % (type(e).__name__, str(e)[:200])]


def _compile(prompt, st, compiles, log, select=None):
    """The IR from `compiles` independent compile calls run at the same time (BUILDER_COMPILES). The first one with no
    static problems is taken as soon as it is there; otherwise, when all are back, the one with the fewest problems.
    Two reads of one brief differ (seen on Freya: one read's intent wording 14/18, another 0/18 on the same case), and a
    slow call is covered by the other."""
    if compiles <= 1:
        return ask(COMPILE_SYS, prompt, "compile PolicyIR", S.policy_ir, log=log)
    import threading, queue
    q = queue.Queue()
    for i in range(compiles):
        def job(i=i):
            try:
                ir = ask(COMPILE_SYS, prompt, "compile PolicyIR #%d" % (i + 1), S.policy_ir, log=log)
                q.put((i, ir, _problems(ir, st)))
            except Exception as e:
                q.put((i, e, None))
        threading.Thread(target=job, daemon=True).start()   # a call not waited for must not hold the build at exit
    got = []
    for _ in range(compiles):
        left = llm.time_left()
        try:
            i, ir, probs = q.get(timeout=max(1, left) if left is not None else None)
        except Exception:
            log("compile: no more compiles back before the deadline")
            break
        if isinstance(ir, Exception):
            log("compile #%d failed: %s" % (i + 1, str(ir)[:200]))
            continue
        log("compile #%d: %d static problems" % (i + 1, len(probs)))
        got.append((len(probs), i, ir))
        if not probs and select is None:
            break
    if not got:
        raise RuntimeError("every compile call failed")
    if select is not None and len(got) > 1:
        # the reads are told apart by what they DO on test customers written from the brief's own rules (CodeT /
        # MBR-exec style); static problems only break ties. Seen on S7: two reads, both 0 static problems, 14/14 and
        # 11/14 on the answer key; unit-driven tests 107/111 vs 103/111.
        got.sort(key=lambda g: g[1])
        try:
            k = select([g[2] for g in got], [g[0] for g in got])
            n, i, ir = got[k]
            log("compile: using #%d by its tests (%d static problems)" % (i + 1, n))
            return ir
        except Exception as e:
            log("compile: selection by tests failed (%s): fewest static problems" % str(e)[:200])
    n, i, ir = min(got, key=lambda g: (g[0], g[1]))
    log("compile: using #%d (%d problems; %d of %d compiles back)" % (i + 1, n, len(got), compiles))
    return ir


def read(brief_paths, openapi_path, example_ir=None, example_briefs=(), max_repairs=3, log=print, on_compiled=None,
         compiles=None, select=None):
    """select(irs, n_problems, st, inv) -> index: how to choose among several compiles (default: fewest problems)."""
    compiles = int(compiles or os.environ.get("BUILDER_COMPILES", "2"))
    t0 = time.time()
    st = stage0.run(brief_paths, openapi_path)
    docs = stage0.render_for_llm(st)
    tools = tools_view(st["vocabulary"])
    log("stage0: %d sentences, %d tables, %d tools" % (len(st["sentences"]), len(st["tables"]), len(st["vocabulary"]["tools"])))

    try:
        inv = ask(INVENTORY_SYS, INVENTORY_PROMPT.format(docs=docs, tools=tools), "rule inventory", S.inventory, log=log)
    except Exception as e:
        log("inventory failed (%s): compiling from the documents alone" % str(e)[:200])
        inv = S.inventory({})
    covered = set(s for u in inv.get("units", []) for s in u.get("sids", [])) | set(inv.get("non_normative", {}).keys())
    missing = [s for s in st["sentences"] if s not in covered]
    log("inventory: %d units, %d amendments, %d uncovered sentences" % (len(inv.get("units", [])), len(inv.get("amendments", [])), len(missing)))
    if missing:
        try:
            extra = ask(INVENTORY_SYS, "These sentences were not accounted for. Classify each, as units or "
                        "non_normative, in the same JSON format:\n" +
                        "\n".join("%s %s" % (s, st["sentences"][s]["text"]) for s in missing) +
                        "\n\nFull documents for context:\n" + docs, "inventory gap fill", S.inventory, log=log)
            inv["units"].extend(extra["units"])
            inv["non_normative"].update(extra["non_normative"])
        except Exception as e:
            log("inventory gap fill failed (%s): continuing without it" % str(e)[:200])

    ir = _compile(COMPILE_PROMPT.format(example=example_block(example_ir, example_briefs), docs=docs,
                                        tools=tools, inventory=json.dumps(inv, indent=1)), st, compiles, log,
                  select=(lambda irs, ns: select(irs, ns, st, inv)) if select else None)
    if on_compiled is not None:      # e.g. the self-test writer starts now, while the repairs run
        on_compiled(ir, st, inv)
    for nn_sid, why in (inv.get("non_normative") or {}).items():
        ir.setdefault("coverage", {}).setdefault(nn_sid, "non-normative: " + str(why))
    best, best_probs = None, None
    for rnd in range(max_repairs + 1):
        probs = _problems(ir, st)
        log("validation round %d: %d problems" % (rnd, len(probs)))
        if best is None or len(probs) < len(best_probs):     # a repair that makes things worse is not kept
            best, best_probs = ir, probs
        if not probs or rnd == max_repairs:
            break
        try:
            cur = ir
            ir = ask(COMPILE_SYS, REPAIR_PROMPT.format(problems="\n".join(probs[:80]), docs=docs,
                                                       ir=json.dumps(ir, ensure_ascii=False)),
                     "repair IR (%d problems)" % len(probs), lambda reply, cur=cur: S.policy_ir(patched(cur, reply)), log=log)
        except Exception as e:
            log("repair failed (%s): keeping the best IR so far" % str(e)[:200])
            break
    ir, probs = best, best_probs
    ir["_reader"] = {"seconds": round(time.time() - t0, 1), "inventory_units": len(inv.get("units", [])),
                     "remaining_problems": probs, "amendments": inv.get("amendments", []), "ambiguities_seen": inv.get("ambiguities", [])}
    return ir, st, inv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("inputs", nargs="+")
    ap.add_argument("--example"); ap.add_argument("--example-brief", action="append", default=[])
    a = ap.parse_args()
    api = [p for p in a.inputs if p.endswith(".json")]
    briefs = [p for p in a.inputs if not p.endswith(".json")]
    ir, st, inv = read(briefs, api[0] if api else None, a.example, a.example_brief)
    json.dump(ir, open(a.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(inv, open(a.out.replace(".json", ".inventory.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(llm.TRACE, open(a.out.replace(".json", ".llmtrace.json"), "w", encoding="utf-8"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
