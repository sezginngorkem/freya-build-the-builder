"""Static checks on a PolicyIR (no LLM, no Freya). Returns a list of problems; empty = clean.

Checks: structure, every expression compiles and uses known functions and roots, templates exist and
their placeholders compile, goto targets / procedures / tools exist, tool args match the OpenAPI
vocabulary and enum values, phases are reachable and every reachable phase can reach a close,
every rule cites a source, sentence coverage (optional, given stage-0 sentences).
"""
import json, re, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from engine import expr as E

ROOTS = {"call", "today", "counter", "flag", "var", "slot", "items", "item", "result", "tool", "phase", "said", "tables", "const",
         "true", "false", "None", "null", "True", "False"}
ACTION_KEYS = {"say", "say_text", "instruct", "call", "set", "incr", "append", "goto", "next_item", "close", "stop", "if",
               "reprompt", "for_each_item", "set_cursor", "run", "refire"}
SET_ROOTS = {"counter", "flag", "var", "slot", "item", "items"}


def _walk_actions(actions, visit, where):
    for a in actions or []:
        visit(a, where)
        if "if" in a:
            _walk_actions(a.get("then"), visit, where)
            _walk_actions(a.get("else"), visit, where)
        if "for_each_item" in a:
            _walk_actions(a["for_each_item"], visit, where)


def validate(ir, vocabulary=None, sentences=None):
    P = []
    funcs = set(E.make_functions(ir.get("calendar")).keys()) | set((ir.get("functions") or {}).keys())
    templates = ir.get("templates") or {}
    procs = ir.get("procedures") or {}
    tools_ir = set(((ir.get("vocabulary") or {}).get("tools") or {}).keys())
    vtools = (vocabulary or {}).get("tools") or {}
    intents = {i["id"] for i in ir.get("intents", [])}
    phases_mentioned = {ir.get("initial_phase")}
    gotos = {}          # phase -> set(target phases)
    closes_in = set()   # phases with a close action
    rule_ids = set()

    def check_expr(src, where, params=()):
        if src is None or isinstance(src, (int, float, bool)):
            return
        try:
            names, fs = E.names_used(src)
        except E.ExprError as e:
            P.append("%s: bad expression %r (%s)" % (where, src, e)); return
        for f in fs - funcs:
            P.append("%s: unknown function %s() in %r" % (where, f, src))
        for n in names:
            root = n.split(".")[0]
            if root not in ROOTS and root not in params:
                P.append("%s: unknown name %r in %r" % (where, n, src))

    ww = (ir.get("calendar") or {}).get("weekday_words") or {}
    for key, allowed in (("this", ("calendar_week", "upcoming")), ("next", ("following_calendar_week", "this_plus_7")), ("bare", ("upcoming", "this"))):
        if key in ww and ww[key] not in allowed:
            P.append("calendar.weekday_words.%s must be one of %s" % (key, ", ".join(allowed)))
    for k, rw in enumerate(ir.get("restricted_words") or []):
        if not isinstance(rw, dict) or not isinstance(rw.get("words"), list) or not rw.get("words"):
            P.append("restricted_words[%d]: needs {words: [...], until: <expr>}" % k)
        elif rw.get("until") not in (None, ""):
            check_expr(rw["until"], "restricted_words[%d].until" % k)

    def check_template_text(text, where):
        for m in re.finditer(r"\{([^{}]+)\}", text):
            check_expr(m.group(1), where)

    for tid, t in templates.items():
        text = t["text"] if isinstance(t, dict) else t
        check_template_text(text, "template %s" % tid)

    for fname, f in (ir.get("functions") or {}).items():
        check_expr(f.get("expr"), "function %s" % fname, params=tuple(f.get("params", [])))

    def visit_factory(phase_of):
        def visit(a, where):
            keys = set(a.keys()) & ACTION_KEYS
            if not keys:
                P.append("%s: unknown action %s" % (where, list(a.keys())))
            if "say" in a and a["say"] not in templates:
                P.append("%s: unknown template %r" % (where, a["say"]))
            for k in ("say_text", "instruct"):
                if k in a:
                    check_template_text(a[k], where)
            if "if" in a:
                check_expr(a["if"], where)
            if "set" in a:
                for path, src in a["set"].items():
                    if path.split(".")[0] not in SET_ROOTS:
                        P.append("%s: cannot set %r" % (where, path))
                    check_expr(src, where)
            if "incr" in a and a["incr"].split(".")[0] not in SET_ROOTS:
                P.append("%s: cannot incr %r" % (where, a["incr"]))
            if "incr" in a and isinstance(a.get("by"), str):
                check_expr(a["by"], where)
            if "set_cursor" in a:
                check_expr(a["set_cursor"], where)
            if "call" in a:
                tool = a["call"]
                if tool not in tools_ir:
                    P.append("%s: tool %r not in vocabulary" % (where, tool))
                vt = vtools.get(tool)
                for arg, src in (a.get("args") or {}).items():
                    check_expr(src, where)
                    if vt is not None and arg not in vt.get("args", {}):
                        P.append("%s: %s has no argument %r (openapi)" % (where, tool, arg))
                    if vt is not None:
                        enum = (vt.get("args", {}).get(arg) or {}).get("enum")
                        m = re.fullmatch(r"'([^']*)'", str(src).strip())
                        if enum and m and m.group(1) not in enum:
                            P.append("%s: %s.%s=%r not in enum %s" % (where, tool, arg, m.group(1), enum))
                if vt is not None:
                    for req in vt.get("required", []):
                        if req not in (a.get("args") or {}) and req != "customer_id":
                            P.append("%s: %s missing required arg %r" % (where, tool, req))
            if "close" in a:
                c = a["close"]
                check_expr(c.get("outcome"), where)
                check_expr(c.get("reason"), where)
                closes_in.add(phase_of)
                ct = (ir.get("closing") or {}).get("tool", "close_call")
                from reader.closing import close_fields
                cf = close_fields(ir, vocabulary or {})
                if vtools.get(ct) and not cf.get("outcome"):
                    P.append("%s: no argument of %s carries the outcome (name it in closing.fields.outcome)" % (where, ct))
                if vtools.get(ct) and c.get("reason") and not cf.get("reason"):
                    # the engine would send it under a name the tool does not have, and it would be dropped silently
                    P.append("%s: no argument of %s carries the reason (name it in closing.fields.reason)" % (where, ct))
                enum = ((vtools.get(ct) or {}).get("args", {}).get(cf.get("outcome") or "outcome") or {}).get("enum")
                for lit in [m.group(1) for m in re.finditer(r"(?<![\w(,])(?<!\w\()(?<!,\s)'([^']*)'", str(c.get("outcome")))
                            if not re.search(r"(\w\(|,)\s*$", str(c.get("outcome"))[:m.start()])]:
                    if enum and lit not in enum:
                        P.append("%s: outcome %r not in enum %s" % (where, lit, enum))
            if "goto" in a:
                gotos.setdefault(phase_of, set()).add(a["goto"]); phases_mentioned.add(a["goto"])
            if "next_item" in a:
                for k in ("next_item", "done"):
                    gotos.setdefault(phase_of, set()).add(a[k]); phases_mentioned.add(a[k])
            if "run" in a:
                if a["run"] not in procs:
                    P.append("%s: unknown procedure %r" % (where, a["run"]))
                else:
                    gotos.setdefault(phase_of, set()).add("@" + a["run"])
        return visit

    rule_phases = set()
    for r in ir.get("rules", []):
        rid = r.get("id") or "?"
        if rid in rule_ids:
            P.append("rule %s: duplicate id" % rid)
        rule_ids.add(rid)
        if not r.get("src"):
            P.append("rule %s: no src" % rid)
        on = r.get("on", "")
        if not (on in ("enter", "user") or on.startswith("intent:") or on.startswith("tool:")):
            P.append("rule %s: bad 'on' %r" % (rid, on))
        if on.startswith("intent:") and on[7:] not in intents:
            P.append("rule %s: unknown intent %r" % (rid, on[7:]))
        if on.startswith("tool:") and on[5:] not in tools_ir:
            P.append("rule %s: unknown tool %r" % (rid, on[5:]))
        check_expr(r.get("if"), "rule %s" % rid)
        phs = r.get("phase", "*")
        phs = phs if isinstance(phs, list) else [phs]
        for ph in phs:
            if ph != "*":
                rule_phases.add(ph); phases_mentioned.add(ph)
            _walk_actions(r.get("do"), visit_factory(ph), "rule %s" % rid)

    for pname, acts in procs.items():
        _walk_actions(acts, visit_factory("@" + pname), "procedure %s" % pname)

    # reachability: a procedure node expands to its own gotos
    def succ(node):
        out = set()
        for t in gotos.get(node, set()):
            out.add(t)
        return out

    def expand(node, seen=None):
        seen = seen or set()
        res = set()
        for t in succ(node):
            if t in seen:
                continue
            seen.add(t)
            if t.startswith("@"):
                res |= expand(t, seen)
                if t in closes_in:
                    res.add("#close")
            else:
                res.add(t)
        return res

    all_phases = {p for p in phases_mentioned if p and p != "*"}
    for p in all_phases - rule_phases:
        P.append("phase %r is a goto target but has no rules" % p)
    reach, todo = set(), [ir.get("initial_phase")]
    while todo:
        p = todo.pop()
        if p in reach or p is None:
            continue
        reach.add(p)
        for t in expand(p):
            if t != "#close":
                todo.append(t)
    star_closes = any(("*" == (r.get("phase", "*"))) for r in ir.get("rules", []))
    for p in sorted(rule_phases - reach):
        P.append("WARN phase %r is never reached from %r" % (p, ir.get("initial_phase")))

    def can_close(p, seen):
        if p in closes_in or any(t == "#close" for t in expand(p)):
            return True
        for t in expand(p):
            if t not in seen and t != "#close":
                seen.add(t)
                if can_close(t, seen):
                    return True
        return False
    for p in sorted(reach):
        if not can_close(p, {p}):
            P.append("phase %r cannot reach any close" % p)

    # side questions: every phase that listens to the customer must answer the side-question intents (or a '*' rule does)
    side = [i for i in ("ask_bot", "ask_scam", "ask_reason", "other_question") if i in intents]
    listening = set()
    for r in ir.get("rules", []):
        if r.get("on") == "user" or str(r.get("on", "")).startswith("intent:"):
            ph = r.get("phase", "*")
            for p in (ph if isinstance(ph, list) else [ph]):
                if p != "*":
                    listening.add(p)
    for p in sorted(listening & reach):
        for i in side:
            ok = False
            for r in ir.get("rules", []):
                if r.get("on") != "intent:" + i:
                    continue
                ph = r.get("phase", "*"); ph = ph if isinstance(ph, list) else [ph]
                nph = r.get("not_phase") or []; nph = nph if isinstance(nph, list) else [nph]
                if ("*" in ph or p in ph) and p not in nph:
                    ok = True; break
            if not ok:
                P.append("phase %r listens to the customer but has no rule for side-question intent %r (answer it, then reprompt)" % (p, i))

    # digits slots must say how long the number is (callers say long numbers in pieces)
    for sname, sp in (ir.get("slots") or {}).items():
        if (sp or {}).get("kind") == "digits" and not ((sp or {}).get("length") or (sp or {}).get("min_length")):
            P.append("slot %s: digits slot without length/min_length (take it from the spec)" % sname)
    # slots: every slot used in expressions is declared
    declared = set((ir.get("slots") or {}).keys())
    used = set(re.findall(r"slot\.(\w+)", json.dumps(ir)))
    for s in sorted(used - declared):
        P.append("slot %r used but not declared" % s)

    # coverage
    if sentences:
        cited = set(re.findall(r"\b(D\d+\.s\d{3})\b", json.dumps(ir)))
        cov = ir.get("coverage") or {}
        for sid in sentences:
            if sid not in cited and sid not in cov:
                P.append("sentence %s not covered: %s" % (sid, sentences[sid]["text"][:90]))
    return P


if __name__ == "__main__":
    ir = json.load(open(sys.argv[1], encoding="utf-8"))
    voc = None
    if len(sys.argv) > 2:
        from reader.stage0 import parse_openapi
        voc = parse_openapi(sys.argv[2])
    probs = validate(ir, voc)
    for p in probs:
        print("-", p)
    print("%d problems" % len(probs))
