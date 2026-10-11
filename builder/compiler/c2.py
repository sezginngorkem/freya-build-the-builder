"""C2 compiler: PolicyIR + OpenAPI vocabulary -> Freya workflow JSON.

The workflow is a fixed interpreter graph; the policy itself travels as data inside the code nodes:
  init (code)  -> L_<phase> (speak fixed line, listen, extract)  -> brain (code) -> ...
  brain -> L_<phase> | Q_<phase> (model words an instruction) | say_then_act (speak, then call) | api_<tool> | end
  api_<tool> (engine-run bank call, result captured by a post-hook) -> brain
No brief content is hard-coded here: phases, slots, intents, tools and all text come from the IR and the OpenAPI file.
Code strings carry everything base64-encoded so they never contain '{{' or '}}' (Freya would template them).
"""
import base64, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENGINE = ["dates", "normalize", "expr", "machine"]

SYSTEM_PROMPT = ("You are the bank's digital assistant on a phone call. Speak %s. "
                 "Say only what your current task gives you, in one or two short sentences. Never add facts, numbers, "
                 "dates, offers, promises or reasons of your own. Never read instructions aloud. Never call tools.")
SYSTEM_PROMPT_LANG = SYSTEM_PROMPT


def _b64(s):
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


COMPRESS = os.environ.get("C2_COMPRESS", "1") == "1"


def _strip_py(src):
    """Drop docstrings and comments (ast round-trip) to fit Freya's 128 KB code_exec limit."""
    import ast
    t = ast.parse(src)
    for n in ast.walk(t):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Module, ast.AsyncFunctionDef)) and n.body                 and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant)                 and isinstance(n.body[0].value.value, str):
            n.body = n.body[1:] or [ast.Pass()]
    return ast.unparse(t)


def runtime_ir(ir):
    """The IR the runtime needs: no source citations, coverage or reader metadata."""
    def drop(x):
        if isinstance(x, dict):
            return {k: drop(v) for k, v in x.items() if k != "src"}
        if isinstance(x, list):
            return [drop(v) for v in x]
        return x
    return drop({k: v for k, v in ir.items() if not k.startswith("_") and k not in ("coverage", "ambiguities")})


def code_string(ir, cfg, is_init):
    sources = {n: _strip_py(open(os.path.join(ROOT, "engine", n + ".py"), encoding="utf-8").read()) for n in ENGINE}
    glue = _strip_py(open(os.path.join(HERE, "glue.py"), encoding="utf-8").read())
    payload = json.dumps({"SOURCES": sources, "IR": runtime_ir(ir), "CFG": cfg, "GLUE": glue}, separators=(",", ":"))
    if COMPRESS:
        import zlib
        blob = base64.b64encode(zlib.compress(payload.encode("utf-8"), 9)).decode("ascii")
        load = "import zlib\n_P = json.loads(zlib.decompress(base64.b64decode('%s')).decode('utf-8'))\n" % blob
    else:
        load = "_P = json.loads(base64.b64decode('%s').decode('utf-8'))\n" % _b64(payload)
    code = (SANITIZE + "import base64, json\n" + load +
            "_G = {'SOURCES': _P['SOURCES'], 'IR': _P['IR'], 'CFG': _P['CFG'], 'vars': vars, '__name__': 'policy_glue'}\n"
            "CFG = _P['CFG']\n"
            "exec(compile(_P['GLUE'], 'glue.py', 'exec'), _G)\n"
            "try:\n"
            "    _G['run_brain'](%s)\n"
            "except Exception as _e:\n"
            "    import traceback\n"
            "    vars['_error'] = traceback.format_exc()[-1500:]\n"
            "    vars['say_text'] = CFG.get('fallback_text', 'Sorry, could you repeat that?')\n"
            "    vars['next_node'] = 'L_' + str(vars.get('phase') or CFG.get('initial_phase'))\n"
            % ("True" if is_init else "False"))
    assert "{{" not in code and "}}" not in code
    return code


def _eq(var, val):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "equals", "operand": val}]}


def _gt(var, n):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "greater_than", "operand": n}]}


FAULT_LIMIT = 2      # failures of one tool in one call before the call is ended gracefully


def _fault_guard(var, target):
    """Before any edge into api_<tool>: if that tool already failed more than FAULT_LIMIT times in this call (counted
    by Freya, not by our code), go to the graceful fault end instead of calling it again."""
    tool_node = target
    return {"target_node": "fault_end", "description": "%s keeps failing" % tool_node,
            "condition": {"logic": "or", "conditions": [{"logic": "and", "conditions": [
                {"variable": var, "operator": "equals", "operand": tool_node},
                {"variable": tool_node + "_failure_count", "operator": "greater_than", "operand": FAULT_LIMIT}]}]}}


def _code_node(name, code, targets):
    trans = [_fault_guard("next_node", t) for t in targets if t.startswith("api_")]
    trans += [{"target_node": t, "description": "go to " + t, "condition": _eq("next_node", t)} for t in targets]
    trans.append({"target_node": targets[0], "description": "always", "condition": {"operator": "always"}})
    return {"name": name, "node_type": "code", "passthrough": True, "passthrough_default_transition": targets[0],
            "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
            # the step has no side effect (variables in, variables out): a retry is safe, and Freya's code sandbox was
            # seen failing intermittently ("did not return a parseable result"), which rolled the call back a step
            "pre_actions": [{"type": "function", "config": {"timeoutMs": 20000, "maxRetries": 2},
                             "function": {"name": "code_exec", "handler": "__function__:code_exec",
                             "parameters": {"type": "object", "properties": {"code": {"type": "string", "default": code},
                                                                             "timeout_ms": {"type": "number", "default": 20000}}}}}],
            "transitions": trans}


SLOT_DESC = {
    "birth_date": "The date of birth the customer just gave, written exactly as they said it (words or digits, all parts). Empty if none.",
    "date": "The day the customer just proposed or named for this, in their words (e.g. 'next Friday', 'the 26th', 'tomorrow', '6 November'). If they corrected themselves, only the corrected day. Ignore other dates they mention in passing (birthdays, events). Empty if none.",
    "amount": "The amount of money the customer just proposed, in their words (e.g. 'six hundred', '250 dollars', 'the full amount'). Only money: a number of products, days or payments is not an amount ('all three', 'both', 'two of them' -> empty). If they corrected themselves, only the corrected amount. Empty if none.",
    "digits": "The digits the customer just said, exactly as said (they may say only part of them). Empty if none.",
    "time": "The time of day the customer just named, in their words (e.g. 'around eleven', '3pm'). If they corrected themselves, only the corrected time. Empty if none.",
    "text": "The customer's answer to this question, exactly as said. Empty if none.",
    "enum": "The customer's choice. Empty if unclear.",
}


ACTS = ["answer", "inform", "question", "request", "refuse", "other"]
ACT_DESC = ("What the customer MAINLY does in their LAST message, one word: 'answer' = answers the agent's question or "
            "proposes or accepts a day, amount, time or number, also when they put it as a question ('Can I pay that on "
            "Friday instead?'); 'inform' = tells a fact about themselves or the account "
            "(already paid, lost their job, wrong person, disputes the debt); 'question' = asks something, or asks to be told something ('You tell me what the minimum is'); 'request' = asks "
            "for something new that is not one payment of this debt (a person, a payment plan or instalments, lower "
            "instalments, a discount); 'refuse' = says no or does not want to continue; 'other' = anything else.")


# The engine's own "go on" line (a cut or unfinished message) is not a question. Without saying so, the language layer
# judged the customer's next message against it: measured on Freya, a plain "I do not want to be transferred" was read
# as a "no" in 183/190 messages right after the agent's offer, but in 14/24 after one or more of these lines.
def _continuer(ir=None):
    t = ((ir or {}).get("engine_text") or {}).get("continuer")
    if t:
        return t
    m = re.search(r'^CONTINUER = "([^"]+)"', open(os.path.join(ROOT, "engine", "machine.py"), encoding="utf-8").read(), re.M)
    return m.group(1)


def _continuer_note(ir=None):
    return ("The agent's line '%s', or a line that only repeats the customer's own unfinished words ('...you were "
            "saying...?'), only invites the customer to go on: it is not a question, and what the customer says "
            "after it answers the agent's question or offer before it." % _continuer(ir))


CONTINUER_NOTE = _continuer_note()


# How the last message relates to the agent's last question: a closed set of relations, not a list of styles
# (notes/cevap-iliskisi-arastirmasi.md; humans agree on this coarse split, kappa 0.97).
REPLY_DESC = ("How the customer's LAST message relates to the agent's LAST question or offer in the conversation. 'answer' = gives "
              "what the question asks for, fully or partly, directly or indirectly (a yes or no, a day, an amount, a "
              "number, a choice, a counter-proposal); 'non_answer' = responds to the question but does not give it: "
              "refuses, says they do not know or cannot say, or leaves the choice to the agent; 'question' = asks the "
              "agent something before answering; 'none' = does not respond to the question yet: talks about something "
              "else, stops mid-sentence, or only says a filler. " + CONTINUER_NOTE)
FINISHED_DESC = ("Did the customer finish what they were saying in their LAST message? 'yes' if it is a complete thought; "
                 "'no' if it stops in the middle of a sentence or of a number, date or name (e.g. 'I can pay on Tuesday "
                 "the', 'six hundred and', 'My cousin's wedding is on the'). One of: yes, no.")
REPLY_WORDS_DESC = ("Only if the message is a non_answer: the customer's exact words that refuse, plead ignorance or hand "
                    "the choice to the agent, copied from their LAST message. Empty otherwise.")


# Freya reads a code step's result after the LAST result marker in its output. A variable that contains the marker
# (e.g. a stored platform error message) poisons every later step (seen: 219 failures in one call). Neutralise it.
SANITIZE = "for _k in list(vars.keys()):\n    _v = vars[_k]\n    if isinstance(_v, str) and '__CODE_EXEC' + '_RESULT__' in _v:\n        vars[_k] = _v.replace('__CODE_EXEC' + '_RESULT__', '[code-exec-result]')\n"


def consequential_intents(ir):
    """Intents whose rules end the call or call a bank tool (transfer, note, close): a wrong reading of these loses the
    customer, so the language layer is told that proposing a day or amount is not one of them."""
    procs = ir.get("procedures") or {}

    def acts(xs, seen):
        for a in xs or []:
            if not isinstance(a, dict):
                continue
            if "close" in a or "call" in a or "stop" in a:
                return True
            if "run" in a and a["run"] not in seen and acts(procs.get(a["run"]), seen | {a["run"]}):
                return True
            for k in ("then", "else", "for_each_item"):
                if isinstance(a.get(k), list) and acts(a[k], seen):
                    return True
        return False
    return set(r["on"][7:] for r in ir.get("rules", []) if str(r.get("on", "")).startswith("intent:") and acts(r.get("do"), set()))


def extraction_schema(ir, phase, cfg):
    out = []
    intents = {i["id"]: i for i in ir.get("intents", [])}
    for k, v in BUILTIN_INTENTS.items():
        intents.setdefault(k, {"id": k, "description": v})
    heavy = consequential_intents(ir) - {"yes", "no", "confirm_identity"}
    for iid in cfg["intents_by_phase"].get(phase, []):
        desc = intents.get(iid, {}).get("description") or iid
        extra = ""   # no blanket exclusion: it contradicted intents whose meaning is about amounts ("lower instalments"
        #              was not reported on Freya); answer-vs-request is decided by the engine (act gating)
        out.append({"name": "i_" + iid, "type": "boolean",
                    "description": "true only if the customer's LAST message matches this description: \"%s\". A message can say several things: judge each sentence or part of it on its own, and answer true if any part matches this description, whatever the other parts say. A case named after 'not:' does not count on its own. A merely similar request does not count.%s %s Otherwise false." % (desc.rstrip("."), extra, CONTINUER_NOTE),
                    "min_confidence": 0.5})
    names = cfg["intents_by_phase"].get(phase, [])
    if names and cfg.get("intent_choice"):
        # a second, independent reading of the same message as ONE choice among the phase's intents. Measured on
        # Freya: asked as separate yes/no questions, "I cannot pay this amount. I want lower instalments." collapsed to
        # one dominant reading ({no, too_much}, the request lost) in 7/18 calls, while a choice-form field of the same
        # extraction ('request') was right 18/18. Freya's docs too: one extracted choice is more reliable than
        # competing intents. The engine adds the chosen intent if the yes/no readings missed it.
        opts = "; ".join("'%s' = %s" % (i, (intents.get(i, {}).get("description") or i).rstrip(". ")) for i in names)
        out.append({"name": "s__intent", "type": "string", "min_confidence": 0.3,
                    "description": "Which ONE of these names best what the customer's LAST message is mainly about? If it "
                                   "says several things, choose what the customer most wants the agent to act on, and the "
                                   "most specific one that fits. %s; 'none' = none of these. %s Answer with the name only."
                                   % (opts, CONTINUER_NOTE)})
    if out or cfg["slots_by_phase"].get(phase):
        # perception backbone: the verbatim message (our parsers read it too) and the one main act of the message
        out.append({"name": "s__utterance", "type": "string", "min_confidence": 0.0,
                    "description": "The customer's LAST message, word for word, all of it."})
        # no enum constraint on extraction fields: Freya refuses our reset to "" for an enum and keeps the old value
        out.append({"name": "s__act", "type": "string", "min_confidence": 0.3, "description": ACT_DESC + " One of: " + ", ".join(ACTS) + "."})
        out.append({"name": "s__reply", "type": "string", "min_confidence": 0.3,
                    "description": REPLY_DESC + " One of: answer, non_answer, question, none."})
        out.append({"name": "s__reply_words", "type": "string", "min_confidence": 0.0, "description": REPLY_WORDS_DESC})
        out.append({"name": "s__finished", "type": "string", "min_confidence": 0.3, "description": FINISHED_DESC})
    for sname in cfg["slots_by_phase"].get(phase, []):
        s = (ir.get("slots") or {}).get(sname) or {}
        kind = s.get("kind", "text")
        if kind in ("date", "amount", "time", "birth_date", "digits"):
            # the extraction contract for values is the compiler's, never the reader's: the language layer copies the
            # customer's words and our code resolves them (a reader description such as "as YYYY-MM-DD relative to
            # now" made the model invent years: "today" -> 2025-05-14). The reader's text only names what the value is.
            what = " ".join(str(sname).replace("_", " ").split())
            desc = SLOT_DESC[kind] + " (This value is the " + what + ".)"
        else:
            desc = s.get("description") or SLOT_DESC.get(kind, SLOT_DESC["text"])
        # turn assembly is a matter of meaning (which value a fragment belongs to), so the language layer does it
        ent = {"name": "s_" + sname, "type": "string",
               "description": "From the customer's LAST message (if their message just before it stopped mid-sentence or "
                              "gave only the first part of this value, read the two together): " + desc,
               "min_confidence": 0.3}
        if s.get("kind") == "enum" and s.get("values"):   # allowed values in words; glue validates (no platform enum)
            ent["description"] += " One of: " + ", ".join(str(v) for v in s["values"]) + "."
        out.append(ent)
        if s.get("kind") == "birth_date":   # second, independent reading: used only if our parser cannot read the words
            out.append({"name": "s_" + sname + "__iso", "type": "string", "min_confidence": 0.3,
                        "description": "From the customer's LAST message only: the same date of birth written as YYYY-MM-DD, "
                                       "only if they said day, month and year. Empty otherwise."})
    return out


# Built-in intents every listening phase hears, whatever the brief (as VoiceXML's universal 'help' and Rasa's
# clarification pattern). Without them a question about the agent's own question ("why do you need that?") is matched
# to the nearest brief intent (seen on Freya: "asks what the call is about" = a refusal -> the call was closed).
BUILTIN_INTENTS = {
    "clarify": "the customer asks about the agent's LAST question itself instead of answering it: why the agent needs "
               "that information, or what the question means or what exactly is being asked (not: a question about the "
               "call, the bank, the debt, an account or a product; not: asking the agent to say the answer or a part of it, "
               "e.g. 'which number do you have?', 'read me my date of birth'; and not a refusal)",
}


def phases_of(ir):
    ph = set([ir.get("initial_phase")])
    for r in ir.get("rules", []):
        p = r.get("phase", "*")
        for x in (p if isinstance(p, list) else [p]):
            if x != "*":
                ph.add(x)
    txt = json.dumps(ir)
    ph |= set(re.findall(r'"goto": "([^"]+)"', txt)) | set(re.findall(r'"(?:next_item|done)": "([^"]+)"', txt))
    return sorted(p for p in ph if p)


def phase_cfg(ir):
    phases = phases_of(ir)
    intents_by, slots_by = {}, {}
    all_intents = [i["id"] for i in ir.get("intents", [])]
    for ph in phases:
        used = set()
        for r in ir.get("rules", []):
            p = r.get("phase", "*")
            plist = p if isinstance(p, list) else [p]
            npl = r.get("not_phase") or []
            npl = npl if isinstance(npl, list) else [npl]
            if (ph in plist or "*" in plist) and ph not in npl and str(r.get("on", "")).startswith("intent:"):
                used.add(r["on"][7:])
        slots_by[ph] = [s for s, spec in (ir.get("slots") or {}).items() if ph in (spec.get("phases") or []) or not spec.get("phases")]
        listens = bool(used) or bool(slots_by[ph]) or any(r.get("on") == "user" and (r.get("phase", "*") in (ph, "*") or ph in (r.get("phase") if isinstance(r.get("phase"), list) else []))
                                                         for r in ir.get("rules", []))
        if listens:   # a side question must be heard everywhere, or it is mistaken for an answer; yes/no too, so the
            # engine always sees a refusal even where the IR handles it with a catch-all rule (contentless-turn re-ask)
            used |= set(i for i in ("ask_bot", "ask_scam", "ask_reason", "other_question", "yes", "no") if i in all_intents)
            used |= set(BUILTIN_INTENTS)
        intents_by[ph] = [i for i in all_intents + [b for b in BUILTIN_INTENTS if b not in all_intents] if i in used]
    return phases, {"intents_by_phase": intents_by, "slots_by_phase": slots_by, "initial_phase": ir.get("initial_phase"),
                    "consequential": sorted(consequential_intents(ir)), "intent_choice": os.environ.get("C2_INTENT_CHOICE", "1") == "1",
                    "flags": dict((kv.split("=")[0], kv.split("=")[1] == "1") for kv in os.environ.get("C2_FLAGS", "").split(",") if "=" in kv),
                    "fallback_text": (ir.get("engine_text") or {}).get("fallback") or "Sorry, could you say that again?"}


def api_node(tool, spec):
    props = {"url": {"type": "string", "default": spec["url"]}, "method": {"type": "string", "default": spec.get("method", "POST")},
             "headers": {"type": "object", "properties": {"Content-Type": {"type": "string", "default": "application/json"}}}}
    body = {}
    numeric = []
    for field, a in spec.get("args", {}).items():
        default = "{{customer_id}}" if field == "customer_id" else "{{a_%s_%s}}" % (tool, field)
        body[field] = {"type": "string", "default": default}
        if a.get("description"):
            body[field]["description"] = a["description"][:200]
        if a.get("type") in ("number", "integer"):
            numeric.append(field)
    wrap = (spec.get("wire") or {}).get("req_wrap")
    if wrap:     # the fields travel inside the envelope's "data" object, next to its constant metadata object(s)
        nested = {wrap["key"]: {"type": "object", "properties": body}}
        for k, sub in (wrap.get("extra") or {}).items():
            nested[k] = {"type": "object", "properties": {kk: {"type": "string", "default": str(vv)} for kk, vv in sub.items()}}
        props["body"] = {"type": "object", "properties": nested, "required": []}
    else:
        props["body"] = {"type": "object", "properties": body, "required": []}
    # before the call, the previous answer of this tool is wiped: when a call gets no answer (a timeout), the old one
    # was read as this call's (seen on Freya: the date-of-birth check's 'verified: true' taken for the phone check,
    # and the account was read before the second security answer was checked)
    stale = ("for _k in list(vars.keys()):\n"
             "    if _k.startswith('api_%s_response.') or _k.startswith('%s_response.'):\n"
             "        vars[_k] = ''\n"
             "vars['_tool_result'] = ''\n" % (tool, tool))
    pre = (SANITIZE + stale + "try:\n"
           "    b = config.get('body')\n"
           "    def _clean(b):\n"
           "        for k in list(b.keys()):\n"
           "            v = b[k]\n"
           "            if isinstance(v, dict):\n"
           "                _clean(v)\n"
           "                continue\n"
           "            if v is None or (isinstance(v, str) and (v.strip() in ('', 'None') or v.startswith('{' + '{'))):\n"
           "                b.pop(k)\n"
           "            elif k in %r:\n"
           "                try:\n"
           "                    f = float(b[k]); b[k] = int(f) if f == int(f) and isinstance(b[k], str) and '.' not in b[k] else f\n"
           "                except Exception:\n"
           "                    pass\n"
           "    if isinstance(b, dict):\n"
           "        _clean(b)\n"
           "except Exception:\n"
           "    pass\n" % (numeric,))
    post = (SANITIZE + "try:\n"
            "    import json as _j\n"
            "    if isinstance(result, dict):\n"
            "        result.pop('header', None)\n"
            "    vars['_tool_result'] = _j.dumps(result)\n"
            "except Exception:\n"
            "    pass\n")
    return {"name": "api_" + tool, "node_type": "api_request", "passthrough": True, "passthrough_default_transition": "brain",
            "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True, "suppress_tool_results": True,
            "pre_actions": [{"type": "function", "config": {"timeoutMs": 15000, "maxRetries": 0},
                             "function": {"name": tool, "handler": "__function__:api_call", "description": spec.get("summary", tool)[:200],
                                          "parameters": {"type": "object", "properties": props}},
                             "pre_process_code": pre, "post_process_code": post}],
            "transitions": [{"target_node": "brain", "description": "always", "condition": {"operator": "always"}}]}


def listen_node(ir, phase, cfg, llm):
    name = ("Q_" if llm else "L_") + phase
    node = {"name": name, "node_type": "conversation",
            "task_message": "Say nothing more and wait for the customer." if not llm else
                            "Speak to the customer following exactly this, in at most two short sentences: {{say_instruction}}",
            "extraction_schema": extraction_schema(ir, phase, cfg), "max_node_turns": 60,
            "transitions": [{"target_node": "brain", "description": "the customer spoke", "condition": _gt(name + ".current_turns", 0)}]}
    if llm:
        node["on_enter"] = {"type": "llm", "prompt": "Say to the customer, in at most two short sentences, following exactly this instruction: {{say_instruction}} {{say_text}}"}
    else:
        node["on_enter"] = {"type": "tts", "text": "{{say_text}}"}
    return node


def bank_node(tool):
    """SELF-TEST ONLY: the bank tool runs inside Freya as code (sim/mockbank.py), on the customer data passed in the
    call variable 'test_case'. Lets the builder test its agent on Freya (Freya's persona and judge models) with
    customers it wrote itself, for a brief whose bank sessions do not exist yet. Never used in the submitted agent."""
    import zlib
    src = open(os.path.join(ROOT, "sim", "mockbank.py"), encoding="utf-8").read()
    blob = base64.b64encode(zlib.compress(src.encode("utf-8"), 9)).decode("ascii")
    code = (SANITIZE + "import base64, json, zlib\n"
            "_g = {'__name__': 'mockbank'}\n"
            "exec(compile(zlib.decompress(base64.b64decode('" + blob + "')).decode('utf-8'), 'mockbank.py', 'exec'), _g)\n"
            "_case = json.loads(vars.get('test_case') or '{}')\n"
            "_bank = _g['MockBank'](_case)\n"
            "_st = vars.get('_bank_state')\n"
            "if _st:\n"
            "    _d = json.loads(_st)\n"
            "    _d['passed'] = set(_d.get('passed') or [])\n"
            "    _bank.__dict__.update(_d)\n"
            "_pre = 'a_" + tool + "_'\n"
            "_args = dict((k[len(_pre):], v) for k, v in list(vars.items()) if k.startswith(_pre) and v not in (None, ''))\n"
            "_ok, _data = _bank('" + tool + "', _args)\n"
            "vars['_tool_result'] = json.dumps({'status': 'success' if _ok else 'error', 'data': _data if _ok else None, "
            "'status_code': 200 if _ok else 500})\n"
            "_d = dict(_bank.__dict__)\n"
            "_d.pop('case', None)\n"
            "_d['passed'] = sorted(_d.get('passed') or [])\n"
            "vars['_bank_state'] = json.dumps(_d)\n"
            "vars['bank_ledger'] = json.dumps(_bank.ledger)\n")
    return _code_node("api_" + tool, code, ["brain"])


def compile_workflow(ir, vocabulary, name="agent", embedded_bank=False):
    # the closing tool's own field names for the outcome and the reason (fields can change between briefs)
    from reader.closing import close_fields
    global CONTINUER_NOTE
    CONTINUER_NOTE = _continuer_note(ir)     # the engine's own "go on" line is in the call's language
    ir = dict(ir)
    voc_ir = dict((ir.get("vocabulary") or {}).get("tools") or {})
    ir["vocabulary"] = dict(ir.get("vocabulary") or {}, tools={
        t: dict(v or {}, wire=((vocabulary.get("tools") or {}).get(t) or {}).get("wire") or {}) for t, v in voc_ir.items()})
    ir["closing"] = dict(ir.get("closing") or {}, fields=close_fields(ir, vocabulary))
    phases, cfg = phase_cfg(ir)
    tools = vocabulary.get("tools", {})
    used_tools = sorted(set(re.findall(r'"call": "([^"]+)"', json.dumps(ir))) | ({(ir.get("closing") or {}).get("tool", "close_call")} - {None}))
    targets = ["L_" + p for p in phases] + ["Q_" + p for p in phases] + ["api_" + t for t in used_tools if t in tools] + ["say_then_act", "end"]
    nodes = {}
    nodes["init"] = _code_node("init", code_string(ir, cfg, True), targets)
    nodes["brain"] = _code_node("brain", code_string(ir, cfg, False), targets)
    for p in phases:
        nodes["L_" + p] = listen_node(ir, p, cfg, False)
        nodes["Q_" + p] = listen_node(ir, p, cfg, True)
    for t in used_tools:
        if t in tools:
            nodes["api_" + t] = bank_node(t) if embedded_bank else api_node(t, tools[t])
    nodes["say_then_act"] = {
        "name": "say_then_act", "node_type": "conversation", "passthrough": True,
        "passthrough_default_transition": "api_" + str((ir.get("closing") or {}).get("tool", "close_call")) if (ir.get("closing") or {}).get("tool", "close_call") in tools else "brain",
        "on_enter": {"type": "tts", "text": "{{say_text}}"}, "task_message": "Say nothing more.",
        "disable_inactivity_monitor": True,
        "transitions": [{"target_node": "end", "description": "then hang up", "condition": _eq("after_say", "end")}]
                       + [{"target_node": "api_" + t, "description": "then call " + t, "condition": _eq("after_say", "api_" + t)} for t in used_tools if t in tools]
                       + [{"target_node": "brain", "description": "always", "condition": {"operator": "always"}}]}
    # graceful end when Freya cannot run our code for a tool step (see FAULT_LIMIT); spoken text is brief-independent
    nodes["fault_end"] = {"name": "fault_end", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
                          "transitions": [], "terminal": {"type": "function", "function": {
                              "name": "technical_fault", "handler": "__function__:end_call",
                              "parameters": {"type": "object", "properties": {
                                  "message_mode": {"type": "string", "default": "custom"},
                                  "spoken_message": {"type": "string", "default": (ir.get("engine_text") or {}).get("fault") or "I'm sorry, we are having a technical problem on our side. Goodbye."}}}}}}
    nodes["end"] = {"name": "end", "node_type": "end_call", "on_enter": {"type": "silent"}, "disable_inactivity_monitor": True,
                    "transitions": [], "terminal": {"type": "function", "function": {
                        "name": "call_closed", "handler": "__function__:end_call",
                        "parameters": {"type": "object", "properties": {"message_mode": {"type": "string", "default": "none"}}}}}}
    wf = {"initial_node": "init", "system_prompt": SYSTEM_PROMPT % (ir.get("language") or "English"), "global_nodes": {}, "nodes": nodes,
          "test_variables": {"say_text": "Hello.", "say_instruction": ""}}
    return wf


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ROOT)
    from reader.stage0 import parse_openapi
    ir = json.load(open(sys.argv[1], encoding="utf-8"))
    voc = parse_openapi(sys.argv[2])
    wf = compile_workflow(ir, voc)
    out = sys.argv[3] if len(sys.argv) > 3 else "out/workflow.json"
    json.dump(wf, open(out, "w", encoding="utf-8"), indent=1)
    print("wrote", out, "nodes:", len(wf["nodes"]), "code size:", len(wf["nodes"]["brain"]["pre_actions"][0]["function"]["parameters"]["properties"]["code"]["default"]))
