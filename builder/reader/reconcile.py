"""Two independent reads of one brief, reconciled where they disagree.

Two reads of the same brief differ (S7: one read 14/14, another 11/14 on the same answer key; the self-test passed both,
because its own cases did not touch the misread rules). Where two independent reads give the same behaviour they are
very likely right; where they differ, at least one is wrong -- and those places are exactly where a misreading sits.
A referee call gets the documents and both IRs, lists the behavioural differences, decides each one from the documents
(citing sentence ids), and returns a PATCH for read A that takes B's behaviour wherever B is right. The result goes
through the same validator; a reconciliation that adds static problems is not kept.
(Execution/agreement-based selection among several candidates: CodeT, MBR-exec, CHASE-SQL; notes/okuyucu-sota.md.)"""
import json
from reader import llm
from reader.patch import PATCH_FORMAT, patched

SYS = ("You compare two compilations of the same bank call documents into PolicyIR and correct the first one. You are "
       "exact and literal: the documents decide, not habit or plausibility. Reply with one JSON object only.")

PROMPT = """The DOCUMENTS below were compiled twice, independently, into PolicyIR (IR A and IR B). Both pass a static
checker. Where they behave differently for some customer, at least one of them misreads the documents.

1. List every BEHAVIOURAL difference: a different value, date, deadline, band, holiday or calendar handling, number of
   attempts, condition, which rule applies first, what is said where the documents fix the words, which tool is called
   with what, which outcome/reason/note is recorded, how an amendment (a later memo) is applied. Ignore differences of
   naming, structure or wording that give the same behaviour.
2. For each difference decide from the DOCUMENTS which IR is right (cite the sentence ids). If neither is, say so and
   say what the documents require.
3. Return a patch for IR A that makes A right wherever it is not (take B's behaviour, or the documents' where neither
   is right), written in A's own names (its intent ids, slot names, template names, procedure names). Change nothing
   else in A. If A is right everywhere, the patch is {{}}.

Answer JSON: {{"differences": [{{"what": "...", "right": "A" | "B" | "neither", "sids": ["..."], "why": "..."}}],
 "patch": <patch>}}
""" + PATCH_FORMAT.replace("{", "{{").replace("}", "}}") + """

DOCUMENTS:
{docs}

IR A:
{a}

IR B:
{b}"""


def _strip(ir):
    return {k: v for k, v in ir.items() if not k.startswith("_") and k not in ("coverage",)}


def reconcile(ir_a, ir_b, docs, problems_of, log=print):
    """(IR, report). problems_of(ir) -> list of static problems."""
    reply = llm.extract_json(llm.call(SYS, PROMPT.format(docs=docs, a=json.dumps(_strip(ir_a), ensure_ascii=False),
                                                         b=json.dumps(_strip(ir_b), ensure_ascii=False)),
                                      purpose="reconcile two reads"))
    diffs = reply.get("differences") or []
    for d in diffs:
        log("reconcile: %s right=%s %s" % (str(d.get("what"))[:140], d.get("right"), ",".join(d.get("sids") or [])[:60]))
    patch = reply.get("patch") or {}
    if not patch:
        return ir_a, {"differences": diffs, "applied": False}
    try:
        new = patched(ir_a, patch)
    except ValueError as e:
        log("reconcile: patch does not fit (%s): keeping read A" % e)
        return ir_a, {"differences": diffs, "applied": False}
    before, after = len(problems_of(ir_a)), len(problems_of(new))
    if after > before:
        log("reconcile: patch adds static problems (%d -> %d): keeping read A" % (before, after))
        return ir_a, {"differences": diffs, "applied": False}
    log("reconcile: %d differences, patch applied (static problems %d -> %d)" % (len(diffs), before, after))
    return new, {"differences": diffs, "applied": True}
