"""Builder self-test: write test customers from the brief, run them on the PolicyIR locally, root-cause failures,
repair the IR with concrete counterexamples, keep a held-out split for the final measurement.

Independence: the test writer sees the documents and the IR's INTERFACE only (intent ids + descriptions, slot names,
identity fields), never the rules, so a misread rule cannot "agree with itself".
"""
import json, os, random, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(os.path.dirname(ROOT), "kit", "build-the-builder")
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(KIT, "tools"))
from reader import llm, stage0
from reader.validate import validate
from reader.patch import PATCH_FORMAT, patched
from sim import run_local as RL

GEN_SYS = """You write test customers for a bank phone agent, strictly from the specification. Every expected value must be
derivable from the documents; compute dates exactly (business days, holidays, inclusive bounds, 'after today' does not
count today). Reply with JSON only."""

GEN_PROMPT = """DOCUMENTS:
{docs}

TOOLS (bank API; get_account product fields are what you put in "products"):
{tools}

AGENT INTERFACE (use exactly these ids in sim_script):
intents: {intents}
slots: {slots}
identity slots are named id_<field> with normalised values (dates YYYY-MM-DD, digits as strings).

Write {n} test customers covering, as far as the documents allow: the happy path; a third party (callback inside and
outside the allowed window, wrong number, deceased); identity failure at the limit and any special identity rule;
each band/tier at and just past its deadline; a holiday and a weekend date; a vague date; an amount below the minimum;
'too much'; hardship; dispute; already paid; transfer requests; a tool failure (set "faults": [{{"tool": "create_promise",
"fail_first_n": 1}}], or another tool the documents give a failure rule for); several products with different deadlines (if allowed); and EVERY amended rule.
Use "now" values that make the date rules bite (vary weekdays, include a Friday).

JSON: {{"cases": [{{"id": "T01", "family": "...", "title": "...", "variables": {{call variables incl. the 'now' variable}},
"identity": {{"<field>": "<value>"}}, "products": [{{...get_account fields without product_id...}}],
"script": "what the customer does", "sim_script": [{{"text": "...", "intents": [...], "slots": {{...}}}}],
"expected": {{"outcome": "...", "reason": null|"...", "promises": [{{"product_id": "p1", "amount": 0.0, "date": "YYYY-MM-DD"}}],
"notes": [{{"product_id": "p1", "reason": "..."}}], "callbacks": [{{"date": "...", "time": "HH:MM"}}], "transfers": [{{"queue": "..."}}]}},
"checks": ["..."], "derivation": "how the expected values follow from which sentence ids"}}]}}
Script turns: the agent asks one question per turn in the documents' order; after the script the customer says
"no, that's all" twice. Product ids are p1, p2, ... in list order."""

JUDGE_SYS = """You are the referee between a specification, a test and an agent's behaviour. Decide who is wrong, citing
sentence ids. Reply with JSON only."""

JUDGE_PROMPT = """DOCUMENTS:
{docs}

TEST CASE:
{case}

AGENT TRANSCRIPT (local run):
{transcript}

SCORER DIFFERENCES:
{diff}

Answer JSON: {{"verdict": "agent_wrong" | "test_wrong" | "ambiguous", "why": "...", "sids": ["..."],
"fix_hint": "if agent_wrong: what the rule machine must do differently, concretely (which phase/condition/value)"}}"""

REPAIR_PROMPT = """The PolicyIR fails these concrete counterexamples (verified by a referee against the documents). Fix the
root cause in the IR (the rule, condition, value or phase that is wrong), not the symptom; do not break other behaviour.
""" + PATCH_FORMAT.replace("{", "{{").replace("}", "}}") + """

COUNTEREXAMPLES:
{cex}

DOCUMENTS:
{docs}

CURRENT IR:
{ir}"""


def interface(ir):
    intents = [{"id": i["id"], "description": i.get("description", "")} for i in ir.get("intents", [])]
    slots = {k: {"kind": v.get("kind"), "phases": v.get("phases", [])} for k, v in (ir.get("slots") or {}).items()}
    return json.dumps(intents), json.dumps(slots)


def transcript_text(tr):
    out = []
    for who, x in tr:
        if who == "agent" and "say" in x:
            out.append("AGENT: " + x["say"])
        elif who == "agent" and "instruct" in x:
            # worded on the call by the dialogue model; the judge reads what it may say, not the instruction itself
            # (seen: the raw instruction, with its list of earlier lines, was judged as the agent's words -> false flags)
            ins = x.get("instruct", "")
            m = re.search(r'If they do not, say exactly: "(.*?)"\.', ins)
            then = re.search(r'Then say exactly: "(.*?)"$', ins)
            if m:
                out.append('AGENT: [answers the question only from its own earlier lines in this call; if they do not '
                           'answer it, says exactly: "%s"]%s' % (m.group(1), (' "%s"' % then.group(1)) if then else ""))
            else:
                out.append("AGENT: [worded on the call: %s]" % ins[:300])
        elif who == "user":
            out.append("CUSTOMER: %s %s %s" % (x.get("text"), x.get("intents") or "", x.get("slots") or ""))
        elif who == "tool":
            out.append("TOOL %s %s -> %s" % (x["name"], json.dumps(x["args"]), json.dumps(x["data"])[:300]))
    return "\n".join(out)


CONV_SYS = """You are the judge of a bank's collection calls. You read what the AGENT said in test calls and check it against
the documents' rules about what the agent must and must not say or ask. You flag only clear breaches, citing sentence
ids. Reply with JSON only."""

CONV_PROMPT = """DOCUMENTS:
{docs}

TEST CALLS (customer lines are scripted; judge only the AGENT). Each call lists CHECKS written from the documents.
{calls}

For each call, go through its CHECKS one by one and decide from the transcript whether each one holds; report every
check broken by what the AGENT said or did (a forbidden request, persuasion attempt or proposal made, a required sentence
or offer left out, something asked more often than allowed, a question left unanswered). Checks only about the bank's
records (tool calls, notes, close codes) are scored elsewhere: skip them. Report also any other clear breach of the
documents' rules about the conversation; do not flag wording or politeness. Answer JSON: {{"violations": [{{"case": "<id>", "rule": "...", "sids": ["..."], "agent_said": "..."}}]}}"""


_CONV_CACHE = {}    # (case id, transcript) -> the referee-confirmed breaches: an unchanged call is not judged again


def judge_conversations(results, docs, log=print, per_call=None):
    """Conversation rules are half of what is scored (policy, honesty), and a ledger check cannot see them: a read that
    asks for payment after a hardship disclosure records the same ledger. The test calls are judged against the
    documents (LLM judge on simulated dialogues, as tau-bench / IntellAgent do); a breach fails the test and goes to the
    referee and the repair like any other failure."""
    todo = []
    for r in results:
        if not (r["pass"] and r.get("transcript")):
            continue
        key = (r["case"]["id"], r["transcript"])
        if key in _CONV_CACHE:
            if _CONV_CACHE[key]:
                r["pass"] = False
                r["diff"] = list(r.get("diff") or []) + _CONV_CACHE[key]
            continue
        todo.append(r)
    if not todo:
        return results
    # one call per judge request: judged in groups of 3, a persuasion attempt after a hardship decline (S8 T204, the
    # PUB-05 kind) was missed in every run; judged alone it is caught, with the other known misreads (sim/judge_recall.py)
    per_call = per_call or int(os.environ.get("BUILDER_JUDGE_PER_CALL", "1"))
    groups = [todo[i:i + per_call] for i in range(0, len(todo), per_call)]
    jobs = [(lambda g=g: llm.extract_json(llm.call(CONV_SYS, CONV_PROMPT.format(docs=docs, calls="\n\n".join(
        "=== CALL %s (%s) ===\nCHECKS:\n%s\nTRANSCRIPT:\n%s" % (
            r["case"]["id"], str(r["case"].get("title") or "")[:80],
            "\n".join("- " + str(x) for x in (r["case"].get("checks") or [])), r["transcript"][-5000:]) for r in g)),
        purpose="self-test: judge the conversation of %d calls" % len(g)))) for g in groups]
    by_id = {r["case"]["id"]: r for r in todo}
    flagged = {}
    unjudged = set()
    for g, res in zip(groups, llm.parallel(jobs)):
        if isinstance(res, Exception):   # not judged (no time, machine short of memory): not remembered as clean
            unjudged.update(r["case"]["id"] for r in g)
            continue
        for v in res.get("violations") or []:
            r = by_id.get(str(v.get("case")))
            if r is not None:
                flagged.setdefault(r["case"]["id"], []).append("conversation: %s (%s) -- agent: %s" % (
                    str(v.get("rule"))[:200], ",".join(v.get("sids") or []), str(v.get("agent_said"))[:200]))
    # a flag counts only when the referee, reading the documents, agrees the AGENT is wrong: the judge alone is noisy
    # (the same transcripts got 7, 8 and 9 flags in three runs, and a good repair was rejected on three false flags)
    ids = sorted(flagged)
    verdicts = llm.parallel([(lambda cid=cid: llm.extract_json(llm.call(JUDGE_SYS, JUDGE_PROMPT.format(
        docs=docs, case=json.dumps(by_id[cid]["case"], ensure_ascii=False), transcript=by_id[cid]["transcript"][:6000],
        diff="\n".join(flagged[cid])), purpose="self-test referee (conversation) %s" % cid))) for cid in ids])
    found = 0
    confirmed = {}
    for cid, v in zip(ids, verdicts):
        if isinstance(v, dict) and v.get("verdict") == "agent_wrong":
            r = by_id[cid]
            r["pass"] = False
            r["diff"] = list(r.get("diff") or []) + flagged[cid]
            r["referee"] = v
            confirmed[cid] = flagged[cid]
            found += 1
    referee_failed = {cid for cid, v in zip(ids, verdicts) if not isinstance(v, dict)}
    for cid, r in by_id.items():
        if cid not in unjudged and cid not in referee_failed:
            _CONV_CACHE[(cid, r["transcript"])] = confirmed.get(cid, [])
    log("selftest conversation judge: %d calls, %d flagged, %d confirmed by the referee" % (len(todo), len(ids), found))
    return results


def run_cases(ir, cases):
    res = []
    for c in cases:
        try:
            bank = RL.MockBank(c)
            call_vars = dict(c["variables"]); call_vars.setdefault("customer_id", "c_" + c["id"])
            script = [RL.U(t.get("intents"), t.get("text", ""), **(t.get("slots") or {})) for t in c.get("sim_script", [])]
            m, tr = RL.run_script(ir, call_vars, bank, script + [RL.U(["no"], "No, that's all, thank you."), RL.U(["no"], "Goodbye.")])
            r = RL.score_ledger(c, bank.ledger)
            res.append({"case": c, "pass": r["pass"], "diff": r["failed"], "transcript": transcript_text(tr)})
        except Exception as e:
            res.append({"case": c, "pass": False, "diff": ["crash: %s" % e], "transcript": ""})
    return res


# Test customers aimed at the brief's own rules, one per rule unit (the inventory), in groups written at the same time.
# A general request ("cover the happy path, a holiday, ...") leaves most rules untested: on S7 a read that broke three
# rules (a holiday under a bare weekday, a memo item, 'next Friday') passed all 16 general cases.
UNIT_GROUPS = [("dates and values", ("deadline", "calendar", "table", "amount", "negotiation", "variable", "definition")),
               ("amendments, exceptions, precedence and records", ("amendment", "exception", "precedence", "outcome", "recording", "multi_item")),
               ("conversation rules", ("intent_response", "identity", "third_party", "confirmation", "say_required", "say_forbidden", "other"))]

UNIT_PROMPT = """

RULE UNITS TO TEST ({group}) -- write one test customer for EACH unit below whose rule changes what the agent records or
does (skip a unit only if no customer can show it), chosen so that THIS unit decides the expected result, with edge
values (the deadline day itself and the day after, a date on a holiday or weekend, a weekday named without a date, the
values a memo changed, the case an exception covers). Ids T<group number><nn>.
{units}"""


def write_cases(ir, st, n_cases=16, inventory=None):
    """Test customers written from the documents and the IR's interface only (so it can run while the IR is repaired).
    With the inventory: one customer per behavioural rule unit, three groups written in parallel."""
    docs = stage0.render_for_llm(st)
    tools = json.dumps({k: {"args": v["args"], "returns": v["returns"]} for k, v in st["vocabulary"]["tools"].items()})
    intents, slots = interface(ir)
    base = GEN_PROMPT.format(docs=docs, tools=tools, intents=intents, slots=slots, n=n_cases)
    units = (inventory or {}).get("units") or []
    if not units:
        gen = llm.extract_json(llm.call(GEN_SYS, base, purpose="self-test: write %d test customers from the brief" % n_cases))
        return [c for c in gen.get("cases", []) if c.get("sim_script") and c.get("expected")]
    jobs = []
    for gi, (gname, types) in enumerate(UNIT_GROUPS, 1):
        us = [u for u in units if u.get("type") in types]
        if not us:
            continue
        text = "\n".join("- [%s] %s (%s)" % (u.get("type"), str(u.get("rule"))[:300], ",".join(u.get("sids") or [])) for u in us)
        prompt = base.replace("Write %d test customers covering" % n_cases, "Write test customers covering") +             UNIT_PROMPT.format(group="%d: %s" % (gi, gname), units=text)
        jobs.append(lambda p=prompt, g=gname: llm.extract_json(llm.call(GEN_SYS, p, purpose="self-test: customers for %s" % g)))
    cases = []
    for res in llm.parallel(jobs):
        if isinstance(res, Exception):
            continue
        cases += [c for c in res.get("cases", []) if c.get("sim_script") and c.get("expected")]
    seen = set()
    for i, c in enumerate(cases):    # ids unique across groups
        if c.get("id") in seen:
            c["id"] = "%s_%d" % (c.get("id"), i)
        seen.add(c.get("id"))
    return cases


def selftest(ir, st, n_cases=16, holdout=0.35, max_rounds=2, log=print, seed=7, cases=None, inventory=None):
    docs = stage0.render_for_llm(st)
    if cases is None:
        cases = write_cases(ir, st, n_cases, inventory=inventory)
    for c in cases:
        c.setdefault("brief", "self")
    random.Random(seed).shuffle(cases)
    k = max(1, int(len(cases) * holdout))
    held, work = cases[:k], cases[k:]
    log("selftest: %d cases (%d working, %d held out)" % (len(cases), len(work), len(held)))
    history = []
    retried = 0
    for rnd in range(max_rounds + 1):
        res = run_cases(ir, work)
        if os.environ.get("BUILDER_CONV_JUDGE", "1") == "1":
            res = judge_conversations(res, docs, log=log)
        fails = [r for r in res if not r["pass"]]
        log("selftest round %d: working %d/%d pass" % (rnd, len(res) - len(fails), len(res)))
        history.append({"round": rnd, "pass": len(res) - len(fails), "total": len(res)})
        if not fails or rnd == max_rounds:
            break
        verdicts = llm.parallel([(lambda r=r: llm.extract_json(llm.call(JUDGE_SYS, JUDGE_PROMPT.format(
            docs=docs, case=json.dumps(r["case"], ensure_ascii=False), transcript=r["transcript"][:6000], diff="\n".join(r["diff"])),
            purpose="self-test referee %s" % r["case"]["id"]))) for r in fails[:6]])
        cex = []
        for r, v in zip(fails, verdicts):
            if isinstance(v, Exception):
                continue
            log("  %s: %s (%s)" % (r["case"]["id"], v.get("verdict"), str(v.get("why"))[:160]))
            if v.get("verdict") == "agent_wrong":
                cex.append({"case": r["case"]["id"], "customer": r["case"].get("script"), "differences": r["diff"],
                            "transcript": r["transcript"][-2500:], "referee": v})
            elif v.get("verdict") == "test_wrong":
                work = [c for c in work if c["id"] != r["case"]["id"]]
        if not cex:
            break
        try:
            new_ir = patched(ir, llm.extract_json(llm.call(llm_sys(), REPAIR_PROMPT.format(
                cex=json.dumps(cex, ensure_ascii=False, indent=1), docs=docs, ir=json.dumps(ir, ensure_ascii=False)),
                purpose="self-test repair from %d counterexamples" % len(cex))))
        except Exception as e:      # no time left, or a reply that does not fit: the IR stays as it is
            log("selftest repair skipped (%s)" % str(e)[:160])
            break
        probs = [p for p in validate(new_ir, st["vocabulary"], st["sentences"]) if not p.startswith("WARN")]
        before = sum(r["pass"] for r in res)            # this round's results: ledger and, if on, the conversation judge
        after_res = run_cases(new_ir, work)
        if os.environ.get("BUILDER_CONV_JUDGE", "1") == "1":
            after_res = judge_conversations(after_res, docs, log=log)
        after = sum(r["pass"] for r in after_res)
        was = {r["case"]["id"]: r["pass"] for r in res}
        now_ = {r["case"]["id"]: r["pass"] for r in after_res}
        fixed = sorted(k for k in now_ if now_[k] and not was.get(k))
        broke = sorted(k for k in now_ if was.get(k) and not now_[k])
        log("selftest repair: static problems=%d, working pass %d -> %d (fixed %s, broke %s)" % (len(probs), before, after, fixed, broke))
        if after > before and len(probs) == 0:
            ir = new_ir
        else:
            log("selftest repair rejected (no improvement or invalid)")
            if retried >= 1:
                break
            retried = 1          # one more try (a repair is a sample; another one may not break what this one broke)
    held_res = run_cases(ir, held)
    hp = sum(r["pass"] for r in held_res)
    log("selftest held-out: %d/%d pass" % (hp, len(held_res)))
    return ir, {"history": history, "held_out": [hp, len(held_res)], "cases": cases}


def llm_sys():
    from reader.read import COMPILE_SYS
    return COMPILE_SYS
