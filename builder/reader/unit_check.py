"""Does the IR really implement each rule of the brief? (unit-by-unit implementation check)

The validator counts a sentence as covered when some IR part cites it; it does not check that the IR does what the
sentence says. LLM-written rules are precise but miss rules (AgentSpec: precision ~96%, recall ~71%); seen here: a read
that never retried a failed promise call, a read that skipped a memo's "no persuasion on hardship" item. Each
behavioural unit of the inventory is checked against the IR (traceability check, LiSSA/TVR; Clover-style consistency),
in groups run at the same time. Findings that say the IR does not do what the unit requires become concrete problems
for the repair. (notes/okuyucu-sota.md, G2)"""
import json
from reader import llm

BEHAVIOURAL = ("deadline", "calendar", "table", "amount", "negotiation", "amendment", "exception", "precedence", "outcome",
               "recording", "multi_item", "intent_response", "identity", "third_party", "confirmation", "say_required",
               "say_forbidden", "variable")

SYS = ("You check a compiled PolicyIR against the rules of a bank call specification, one rule at a time. You are literal "
       "and exact: a rule counts as implemented only if the IR does what it says in the situation it names. You do not "
       "invent requirements. Reply with JSON only.")

PROMPT = """IR LANGUAGE (how the IR runs):
{lang}

DOCUMENTS (for the exact wording; sentence ids in brackets):
{docs}

POLICY IR:
{ir}

RULE UNITS TO CHECK:
{units}

For EACH unit above: find the IR parts that implement it (rule ids, procedure/template/function names) and decide:
"yes" = the IR does what the unit requires, in the situation it names; "partly" = some of it is missing or different;
"no" = nothing in the IR does it; "n/a" = the unit does not change what the agent says, records or does.
For "partly"/"no", say exactly what is missing or wrong and what the IR must do instead, citing the sentence ids.
Answer JSON: {{"checks": [{{"unit": <index>, "verdict": "yes"|"partly"|"no"|"n/a", "ir": ["..."], "problem": "..."}}]}}"""


def _groups(units, size):
    return [units[i:i + size] for i in range(0, len(units), size)]


def check_units(ir, inventory, docs, lang, log=print, group_size=18):
    """[problem strings] for units the IR does not implement as the documents say."""
    units = [u for u in (inventory or {}).get("units") or [] if u.get("type") in BEHAVIOURAL]
    if not units:
        return []
    irj = json.dumps({k: v for k, v in ir.items() if not k.startswith("_") and k != "coverage"}, ensure_ascii=False)
    jobs = []
    for gi, grp in enumerate(_groups(units, group_size)):
        text = "\n".join("%d. [%s] %s (%s)%s" % (i, u.get("type"), u.get("rule"), ",".join(u.get("sids") or []),
                                                  (" -- exceptions: " + str(u["exceptions"])) if u.get("exceptions") else "")
                         for i, u in enumerate(grp))
        jobs.append(lambda t=text, g=gi: llm.extract_json(llm.call(
            SYS, PROMPT.format(lang=lang, docs=docs, ir=irj, units=t), purpose="unit check group %d" % (g + 1))))
    problems = []
    for gi, (grp, res) in enumerate(zip(_groups(units, group_size), llm.parallel(jobs))):
        if isinstance(res, Exception):
            log("unit check group %d failed: %s" % (gi + 1, str(res)[:150]))
            continue
        for c in res.get("checks") or []:
            v = str(c.get("verdict") or "").lower()
            if v in ("partly", "no"):
                try:
                    u = grp[int(c.get("unit"))]
                except (TypeError, ValueError, IndexError):
                    continue
                p = "unit not implemented as written (%s, %s): %s -- %s" % (
                    v, ",".join(u.get("sids") or []), str(u.get("rule"))[:200], str(c.get("problem"))[:400])
                problems.append(p)
                log("unit check: " + p[:260])
    log("unit check: %d units, %d findings" % (len(units), len(problems)))
    return problems
