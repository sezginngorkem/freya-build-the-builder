# Runtime glue executed inside the Freya code nodes (init and brain). Stdlib only.
# The compiler provides: SOURCES (dict module -> source), IR (PolicyIR dict, runtime part), CFG (dict).
# It reads/writes the Freya variable table through `vars`.
import json, base64, re, sys, types

def _load_engine():
    # cache keyed by the code itself: a warm interpreter that ran another version must never reuse its modules
    import hashlib
    P = "policy_engine_rt_" + hashlib.sha1("".join(SOURCES[k] for k in sorted(SOURCES)).encode("utf-8")).hexdigest()[:12]
    if P + ".machine" in sys.modules and P + ".normalize" in sys.modules:
        return sys.modules[P + ".machine"], sys.modules[P + ".normalize"], sys.modules[P + ".dates"]
    pkg = types.ModuleType(P); pkg.__path__ = []; sys.modules[P] = pkg
    for name in ["dates", "normalize", "expr", "machine"]:
        mod = types.ModuleType(P + "." + name); mod.__package__ = P
        sys.modules[P + "." + name] = mod
        exec(compile(SOURCES[name], P + "/" + name + ".py", "exec"), mod.__dict__)
        setattr(pkg, name, mod)
    return sys.modules[P + ".machine"], sys.modules[P + ".normalize"], sys.modules[P + ".dates"]


def _truthy(v):
    return str(v).strip().lower() in ("true", "yes", "1")


def _blank(v):
    return v is None or str(v).strip() in ("", "None", "null") or "{{" in str(v)


def _call_vars(ir):
    keep = {}
    for k, v in vars.items():
        if k.startswith("_") or "." in k or k.startswith(("i_", "s_", "say_", "next_", "a_")):
            continue
        keep[k] = v
    return keep


def _tool_event(name):
    raw = vars.get("_tool_result")
    data, ok = None, True
    if not _blank(raw):
        try:
            env = json.loads(raw)
            if isinstance(env, dict) and "data" in env:
                ok = str(env.get("status", "success")) == "success" and int(env.get("status_code") or 200) < 400
                data = env.get("data")
            else:
                data = env
        except Exception:
            data = None
    if data is None:
        # fallback: flattened keys <tool>_response.data.<field>
        prefix = "api_" + name + "_response.data."
        alt = name + "_response.data."
        d = {}
        for k, v in vars.items():
            for p in (prefix, alt):
                if k.startswith(p) and v not in (None, ""):      # wiped before the call: only this call's answer
                    d[k[len(p):]] = v
        data = d or None
        if data is None:
            ok = False
    wire = (((IR.get("vocabulary") or {}).get("tools") or {}).get(name) or {}).get("wire") or {}
    if wire.get("resp_wrap"):
        # envelope answers: {"data": {...}, "result": {"code", "message", ...}}; the fields are inside "data"; an error has
        # only "result" (its code and text are what the brief's rules branch on)
        body = data if isinstance(data, dict) else None
        res = (body or {}).get("result") if body else None
        if not isinstance(res, dict):
            code = msg_ = typ = None
            for pre in ("api_" + name + "_response.", name + "_response."):
                for suffix in ("data.result.", "result."):
                    code = code or vars.get(pre + suffix + "code")
                    msg_ = msg_ or vars.get(pre + suffix + "message")
                    typ = typ or vars.get(pre + suffix + "type")
            res = {"code": code, "message": msg_, "type": typ} if code else None
            if not res:
                # an HTTP error: Freya gives no body, only "API request failed: {<the body as a Python dict>}" in .message
                import ast
                for pre in ("api_" + name + "_response.", name + "_response."):
                    txt = vars.get(pre + "message")
                    if isinstance(txt, str) and "{" in txt:
                        try:
                            b2 = ast.literal_eval(txt[txt.index("{"):])
                        except Exception:
                            try:
                                b2 = json.loads(txt[txt.index("{"):])
                            except Exception:
                                b2 = None
                        if isinstance(b2, dict) and isinstance(b2.get("result"), dict):
                            res = b2["result"]
                            break
        inner = (body or {}).get(wire["resp_wrap"])
        if isinstance(inner, dict) and ok:
            data = inner
        elif res:
            data, ok = {"ok": False, "code": res.get("code"), "message": res.get("message"), "type": res.get("type")}, False
    lost = False
    if data is None:
        # no answer body: did the BANK answer (its own error, e.g. {'ok': False, 'error': ...} with a 500) or did the
        # request get no bank answer at all (a gateway's HTML error page, a timeout)? Only the second is "lost".
        msg = ""
        try:
            msg = str((json.loads(raw) or {}).get("message") or "") if not _blank(raw) else ""
        except Exception:
            msg = ""
        msg = msg or str(vars.get("api_" + name + "_response.message") or "")
        ctype = str(vars.get("api_" + name + "_response.header.Content-Type") or "").lower()
        low = msg.lower()
        lost = "html" in ctype or "<!doctype" in low or "<html" in low or "{" not in msg
    if isinstance(data, dict):
        for k in list(data.keys()):
            if str(data[k]) in ("true", "True"):
                data[k] = True
            elif str(data[k]) in ("false", "False"):
                data[k] = False
    vars["_tool_result"] = ""
    return {"type": "tool", "name": name, "ok": ok and isinstance(data, dict), "data": data if isinstance(data, dict) else {"ok": False},
            "no_response": lost}


SIDE_PATTERNS = [
    ("ask_bot", r"\b(robot|a bot|chat ?bot|machine|computer|automated|recording|real person|human being|an ai\b|artificial|"
                r"are you (a )?(real|person|human|live))"),
    ("ask_scam", r"\b(scam|fraud|legit|legitimate|phishing|how (do|can) i know (this|you|it)|is this (real|genuine))"),
    # not "why do you need that?": that asks about the agent's own question (clarify), and the model reads it so
    # (343/343 on Freya); adding ask_reason to it sent it down another path
    ("ask_reason", r"\b(why are you calling|what('s| is) this (call )?(about|regarding)|what is it about|who('s| is) (this|calling))"),
]


def _pack(state):
    """The engine state, compressed: Freya echoes every variable in each code step's output, and a large output was
    seen to come back unparseable (a recorded promise then looked failed). Smaller variables, smaller output."""
    import zlib
    return "z:" + base64.b64encode(zlib.compress(json.dumps(state, separators=(",", ":")).encode("utf-8"), 9)).decode("ascii")


def _unpack(raw):
    import zlib
    raw = str(raw)
    if raw.startswith("z:"):
        return json.loads(zlib.decompress(base64.b64decode(raw[2:])).decode("utf-8"))
    return json.loads(raw)


def _unfinished(text):
    """The message stops mid-sentence or trails off: the customer has not finished."""
    t = str(text or "").strip()
    return bool(t) and (not re.search(r"[.!?]['\")\]]*$", t) or t.endswith(("...", "…")))


def _said(raw, text):
    a = " ".join(re.sub(r"[^\w]+", " ", str(raw).lower()).split())
    b = " ".join(re.sub(r"[^\w]+", " ", str(text).lower()).split())
    return bool(a) and (" " + a + " ") in (" " + b + " ")


def _join_cut(a, b):
    """Two parts of what the customer said, read as one text. A number cut in the middle is one number again: "on
    Tuesday 2" + "7 October" is "on Tuesday 27 October" (seen on Freya: read as "2 ... 7 October", the model's right
    "27 October" was taken for an invented value and the promise went to another day)."""
    a, b = str(a or "").rstrip(), str(b or "").lstrip()
    if not a or not b:
        return a or b
    return a + b if re.search(r"\d$", a) and re.match(r"\d", b) else a + " " + b


def _grounded(N, kind, raw, val, text, sspec, now, heard=""):
    """Who resolves what. The model reads meaning ("the full amount", "this evening", a brief's own "next Monday");
    calendar arithmetic on a day number the customer said, and a birth date, must not get parts nobody said.
    Seen on Freya: "Monday the twenty sixth" -> "2024-05-26" (month and year invented). So:
    - a date: when the customer said a day number (our calendar reads it as an absolute date), the month and year are
      ours unless the customer said them; the model's other parts are dropped;
    - a birth date: day, month and year must each have been said; otherwise nothing is taken (asked again / joined
      with the next part).
    Other values and relative expressions keep the model's reading. Returns the value to use or None."""
    if kind == "date":
        r = N.parse_calendar_date(text, now, sspec.get("numeric_order", "DMY"), (IR.get("calendar") or {}).get("weekday_words"))
        own = r.get("date")
        if own and r.get("kind") == "weekday_bare" and not N.numbers_said(text):   # a bare "Tuesday", not "next Monday"
            # a bare weekday that is the weekday of the date the agent has just proposed refers to that date (the
            # customer takes up the offer: "Tuesday 27 October?" -> "Yes, on Tuesday"), not to the nearest such
            # weekday (seen on Freya: read back as Tuesday 20 October)
            prop = N.parse_calendar_date(str(heard or "").split(" | ")[-1], now, sspec.get("numeric_order", "DMY"),
                                         (IR.get("calendar") or {}).get("weekday_words")).get("date")
            try:
                import datetime as _dt
                if prop and prop != own and _dt.date.fromisoformat(prop).weekday() == _dt.date.fromisoformat(own).weekday():
                    return prop
            except ValueError:
                pass
    if kind == "amount":
        # money, not a count, checked BEFORE taking a value because it was said: a quantifier with a small bare number and
        # no money word ("all three", "both", "the two of them") counts things (products). Seen on Freya: "I will pay
        # all three this Friday" -> 3.00, below the floor, and the floor was offered and recorded instead of the amounts.
        try:
            v0 = float(val)
        except (TypeError, ValueError):
            v0 = None
        r0 = " " + " ".join(re.sub(r"[^\w.$£€]+", " ", str(raw).lower()).split()) + " "
        if v0 is not None and v0 < 10 and re.search(r" (all|both|each|every|these|those|the) ", r0) and                 not re.search(r"(dollar|pound|euro|cent|pence|hundred|thousand|[$£€]|\d\.\d)", r0):
            return None
    if _said(raw, text):
        return val
    if kind == "amount":
        # an amount is a number the customer said, or one they heard from the agent and refer to ("the full amount",
        # "that amount"); never one nobody said (seen: "I cannot pay anything" -> 0, taken as a promise amount)
        try:
            v = float(val)
        except (TypeError, ValueError):
            return None
        if any(abs(v - x) < 0.005 for x in N.numbers_said(text) | N.numbers_said(heard)):
            return val
        # an amount said in two parts with its cents ("four sixty-three..." + "fifty-one" -> 463.51): its digits are
        # the digits the customer said, in order, across the cut
        dig = re.sub(r"\D", "", ("%.2f" % v).rstrip("0").rstrip("."))
        if dig and (dig in re.findall(r"\d+", str(text)) or dig == (N.parse_digits(text) or "")):
            return val
        return None
    y, m, d = (int(x) for x in str(val)[:10].split("-"))
    nums = N.numbers_said(text)
    said_m = N.month_said(text)
    if kind == "birth_date":
        ok = d in nums and (y in nums or y % 100 in nums) and (said_m == m or (said_m is None and m in nums))
        return val if ok else (N.parse_birth_date(text, sspec.get("numeric_order", "DMY")) or None)
    if kind == "date":
        r = N.parse_calendar_date(text, now, sspec.get("numeric_order", "DMY"), (IR.get("calendar") or {}).get("weekday_words"))
        own = r.get("date")
        if own and own != val:
            # the model does not know today's date: a day relative to today ("today", "Friday", "next week's Monday")
            # or a day number without month/year can only be resolved by our calendar. Keep the model's date only
            # when every part of it was said (it picked another date of the same message).
            if r.get("kind") == "absolute" and d in nums and said_m == m and y in nums:
                return val
            return own
        heard_last = str(heard or "").split(" | ")[-1]
        if d in N.numbers_said(heard_last) and N.month_said(heard_last) == m:
            # the day the agent just proposed (the customer took it up, maybe without saying all of it): its day and
            # month were said by the agent, its year comes from our calendar, not from the model
            names = [k for k, v in N.MONTHS.items() if v == m and len(k) > 3]
            return N.parse_calendar_date("the %dth of %s" % (d, names[0]), now, sspec.get("numeric_order", "DMY"),
                                         (IR.get("calendar") or {}).get("weekday_words")).get("date")
        if r.get("kind") == "none" and not r.get("vague") and not nums and not said_m:
            return None       # no date words at all in what was said ("Yes, I can do that"): the model invented it
    return val


def _user_event(ir, phase, N, now):
    slots, intents, grounding, raw_of = {}, [], [], {}
    spec = ir.get("slots") or {}
    parts0 = {k: vars.get(k) for k in vars if str(k).startswith("_partial_")}
    text = "" if _blank(vars.get("s__utterance")) else str(vars.get("s__utterance"))
    act = "" if _blank(vars.get("s__act")) else str(vars.get("s__act")).strip().lower()
    fin = "" if _blank(vars.get("s__finished")) else str(vars.get("s__finished")).strip().lower()
    vars["s__finished"] = ""
    reply = "" if _blank(vars.get("s__reply")) else str(vars.get("s__reply")).strip().lower()
    reply = reply if reply in ("answer", "non_answer", "question", "none") else ""
    words = "" if _blank(vars.get("s__reply_words")) else " ".join(str(vars.get("s__reply_words")).lower().split())
    # the evidence must really be in what the customer said (a deterministic check of the model's claim)
    reply_ok = bool(words) and words.strip(" .,!?") in " ".join(text.lower().split())
    vars["s__utterance"] = ""
    vars["s__act"] = ""
    vars["s__reply"] = ""
    vars["s__reply_words"] = ""
    for iid in CFG["intents_by_phase"].get(phase, []):
        k = "i_" + iid
        if _truthy(vars.get(k)):
            intents.append(iid)
        vars[k] = False   # boolean variable: Freya ignores "" for it, so a stale True would stick
    choice = "" if _blank(vars.get("s__intent")) else str(vars.get("s__intent")).strip().strip("'\" .").lower()
    vars["s__intent"] = ""
    if CFG.get("intent_choice") and choice in CFG["intents_by_phase"].get(phase, []) and choice not in intents             and act != "answer":
        # the choice-form reading names an intent the yes/no readings missed: the message carries it (an answer with
        # a value is left to the yes/no readings and the engine's act gating, as before)
        intents.append(choice)
    contributes = bool(text) and bool(N.numbers_said(text) or N.month_said(text))
    # what the customer said to this same question in the last few messages: EVIDENCE only (was a value the model
    # assembled across messages really said?), never used to decide which value a fragment belongs to (the model does)
    rc = str(vars.get("_recent") or "")
    recent = rc.split("	", 1)[1] if rc.startswith(phase + "	") else ""
    vars["_recent"] = phase + "	" + ((recent + " | ") if recent else "") + text[-200:] if text else rc
    vars["_recent"] = vars["_recent"][-700:]
    for sname in CFG["slots_by_phase"].get(phase, []):
        k = "s_" + sname
        raw = vars.get(k)
        vars[k] = ""
        kind = (spec.get(sname) or {}).get("kind", "text")
        if _blank(raw):
            continue
        said = _join_cut(vars.get("_partial_" + sname) or "", text)   # the customer's words for it, all parts
        # the messages of this attempt, each said once (the held part is one of them), a cut number made whole again
        evidence = _join_cut(re.sub(r"(\d) \| (?=\d)", r"\1", recent), text) if recent else said
        val = _normalize(N, kind, _canon(raw, kind, spec.get(sname) or {}), spec.get(sname) or {}, now, sname)
        if kind == "birth_date":
            iso = str(vars.get(k + "__iso") or "").strip()
            vars[k + "__iso"] = ""
            if val in (None, "") and re.match(r"^\d{4}-\d{2}-\d{2}$", iso):
                val = N.parse_birth_date(iso)
                vars["_partial_" + sname] = ""
        raw_of[sname] = raw
        if kind == "digits" and text:
            # digits are the customer's words of THIS attempt (since the agent's last question), in the order said:
            # the model may join parts across messages, but not with an earlier attempt's digits (seen on Freya: after
            # "does not match ... again?", "Forty-four." + "Ten." was given as 440110 = the earlier 4401 + 10, and the
            # phone question went round 37 times). Reading spoken digits is deterministic, so our reader is the check
            # and, when the model's value is not what was said, the reading -- only if it has the field's length.
            attempt = (recent + " " + text).strip()
            said_d = N.parse_digits(attempt) or ""
            got = re.sub(r"\D", "", str(val or ""))
            if not got or (got not in said_d and got not in (N.parse_digits(evidence) or "")):
                length = (spec.get(sname) or {}).get("length")
                own = said_d if (said_d and length and len(said_d) == int(length)) else None
                if own != val:
                    grounding.append({"slot": sname, "model": str(raw)[:40], "value": val, "kept": own})
                val = own
        if val not in (None, "") and text and kind in ("date", "birth_date", "amount"):
            g = _grounded(N, kind, raw, val, evidence, spec.get(sname) or {}, now, str(vars.get("_agent_said") or ""))
            if g != val:
                grounding.append({"slot": sname, "model": str(raw)[:40], "value": val, "kept": g})
                val = g
                if g in (None, ""):   # e.g. "It is 14 March" + a year the model added: keep the words, join the rest
                    vars["_partial_" + sname] = said[-160:]
        if kind == "date" and val in (None, "") and "vague_date" not in intents and \
                any(i.get("id") == "vague_date" for i in ir.get("intents", [])) and \
                N.parse_calendar_date(str(raw), now, (spec.get(sname) or {}).get("numeric_order", "DMY"), (ir.get("calendar") or {}).get("weekday_words")).get("vague"):
            intents.append("vague_date")   # "the week after next": a period, not a day (the parser knows; say so)
            vars["_partial_" + sname] = ""
        if val not in (None, ""):
            slots[sname] = val
    # second, deterministic reading of the closed set of side questions ("...I can pay then. Am I talking to a robot?"):
    # in a message that carries an answer too, the model tends to report the answer and drop the question
    listened = set(CFG["intents_by_phase"].get(phase, []))
    if text and "?" in text:
        for sid, pat in SIDE_PATTERNS:
            if sid in listened and sid not in intents and re.search(pat, text.lower()):
                intents.append(sid)
    # whether a day is exact or vague is calendar work, ours: when our calendar read a date slot of this message as an
    # exact day, the model's "vague period" flag is dropped (seen on Freya: "I can pay the minimum this Friday" was
    # flagged vague -> "Which exact day?" -> "This Friday." -> the deadline was proposed instead of Friday)
    date_given = [sn for sn, v in slots.items() if (spec.get(sn) or {}).get("kind") == "date" and v not in (None, "")]
    if date_given and "vague_date" in intents:
        intents.remove("vague_date")
    # second, deterministic reading of the verbatim message: a period ("the week after next") the model did not report
    date_slots = [sn for sn in CFG["slots_by_phase"].get(phase, []) if (spec.get(sn) or {}).get("kind") == "date"]
    if text and date_slots and not any(sn in slots for sn in date_slots) and "vague_date" not in intents and \
            any(i.get("id") == "vague_date" for i in ir.get("intents", [])) and N.is_vague_period(text):
        intents.append("vague_date")
    # values held from the first part of this same message (it was cut off; the agent only said "Please go on"): the
    # message has continued now, so they belong to it. A value said again in the continuation wins (it is newer).
    # Seen on Freya: "21 July. / 1990. Look, this is getting ridiculous, / how much do I owe?" lost the date.
    try:
        held0 = json.loads(vars.get("_held") or "{}")
    except Exception:
        held0 = {}
    vars["_held"] = ""
    # a held value belongs with its own reference: "I will pay the credit card tomorrow. I am not paying" + "the
    # personal loan or the car loan." -- the continuation is about other products, so "tomorrow" must not be applied
    # to them (seen on Freya: it was applied to all three products). Then the held values are not released.
    held0 = held0 if isinstance(held0, dict) else {}
    refs = [sn for sn in held0 if (spec.get(sn) or {}).get("kind") == "text" and sn.endswith("_ref")]
    if any(slots.get(sn) not in (None, "") and str(slots.get(sn)).strip().lower() != str(held0[sn]).strip().lower() for sn in refs):
        held0 = {}
    released = []
    for sn, v in held0.items():
        if sn in CFG["slots_by_phase"].get(phase, []) and sn not in slots and v not in (None, ""):
            slots[sn] = v
            released.append(sn)
    ev = {"type": "user", "text": text, "intents": intents, "slots": slots, "act": act, "reply": reply, "reply_ok": reply_ok,
          "choice": choice}
    # an unfinished message (cut off mid-sentence, or the first part of a value): the customer has not finished
    t = text.strip()
    ev["incomplete"] = (fin == "no") if fin in ("yes", "no") else _unfinished(t)
    if ev["incomplete"] and released and not [sn for sn in slots if sn in raw_of] and reply == "none":
        # the customer said the value, then moved on to other talk (this message does not touch the question): the
        # message that held the value is over and the value stands as said (seen on Freya: "...twenty one July nineteen
        # ninety, and how much do I" + small talk, cut again and again -- the date was never checked)
        ev["incomplete"] = False
    if ev["incomplete"]:
        # nothing said in an unfinished message is acted on: every value waits for the rest of the message (no guess
        # from word counts whether one value was finished: "on Thursday, sorry I" was about to be corrected). The
        # values are released with the continuation (`_held`), where a value said again wins; the parts are joined
        # for the model's next reading. Its intents wait too ("No, I can pay the week after" is a date being said).
        for sn in [sn for sn in slots if sn in raw_of]:   # only words said in THIS message are parts (a held value
            # released and held again is not new: counting it again looked like progress and the agent waited forever)
            vars["_partial_" + sn] = ((vars.get("_partial_" + sn) or "") + " " + str(raw_of[sn])).strip()[-160:]
        done = {}
        ev["held"] = {"slots": {k: v for k, v in slots.items() if k not in done}, "intents": list(intents)}
        vars["_held"] = json.dumps(ev["held"]["slots"]) if ev["held"]["slots"] else ""
        ev["slots"] = done
        if not done:
            # a cut-off message is not a decision: no yes/no and nothing the brief acts on with a bank tool or by ending
            # the call (from the IR's own rules: transfer, close, note). Seen on Freya: "You tell me what the minimum is
            # for this Thursday," (cut) -> transfer to restructuring. Topic statements that only change words stand.
            heavy = set(CFG.get("consequential") or []) | {"yes", "no", "decline", "not_want_talk", "confirm_identity"}
            side = ("ask_bot", "ask_scam", "ask_reason", "other_question", "clarify")   # = engine SIDE + clarify: a
            ev["intents"] = [i for i in intents if i not in heavy or i in side]       # question is answered in words
    ev["partial"] = any(vars.get("_partial_" + sn) for sn in CFG["slots_by_phase"].get(phase, []))
    # the customer is answering with a value that is not whole yet ("The fourteenth." for a date of birth): number or
    # month words in a reply to the question, but no usable value
    ev["value_started"] = bool(contributes) and reply == "answer" and not ev.get("slots")
    ev["partial_grew"] = any(vars.get("_partial_" + sn) and vars.get("_partial_" + sn) != parts0.get("_partial_" + sn)
                             for sn in CFG["slots_by_phase"].get(phase, []))
    if grounding:
        ev["grounding"] = grounding
    return ev


def _canon(raw, kind, sspec):
    """One textual form for a value however the platform typed it: 4471.0 -> '4471', 7302 for a 5-digit field ->
    '07302'. (Measured: float-typed numbers broke identity checks in 24/30 calls.)"""
    if isinstance(raw, bool):
        return str(raw).lower()
    if isinstance(raw, float) and raw.is_integer():
        raw = int(raw)
    if isinstance(raw, int):
        s = str(raw)
        L = sspec.get("length")
        if kind == "digits" and L and len(s) < int(L):
            s = s.zfill(int(L))
        return s
    s = str(raw)
    if kind == "digits" and re.match(r"^\s*\d+\.0+\s*$", s):
        s = s.strip().split(".")[0]
    return s


def _normalize(N, kind, raw, sspec, now, sname):
    prev = vars.get("_partial_" + sname) or ""
    vars["_partial_" + sname] = ""
    def attempt(s):
        # a number phrase cannot end in a joining word or trail off ("six hundred and...", "the twenty..."): unfinished
        tail = s.strip().lower()
        # the joining words belong to spoken numbers only: a code or a name may end in "oh" (the letter O: "S E one
        # oh") and in digits "oh" is a zero ("four four one oh"); holding those as unfinished waited forever
        joining = {"date": "and|point|of|the|oh", "birth_date": "and|of|the|oh", "amount": "and|point|of|the",
                   "time": "and|past|to|the|oh", "digits": "and"}.get(kind)
        if tail.endswith(("...", "…", "-")) or (joining and re.search(r"\b(" + joining + r")$", tail.rstrip(" ,;:"))):
            return ("partial", None)
        if kind == "birth_date":
            return N.parse_birth_date(s, sspec.get("numeric_order", "DMY"))
        if kind == "date":
            r = N.parse_calendar_date(s, now, sspec.get("numeric_order", "DMY"), (IR.get("calendar") or {}).get("weekday_words"))
            d = r.get("date")
            if d and str(r.get("kind", "")).startswith("weekday") and N.numbers_said(s):
                # "Monday the twenty": a weekday was read but a number in the words was not used: the value is not
                # complete (the customer was cut off, or said more than we read). Keep it and join what follows.
                return ("partial", d)
            # the model sometimes turns "the sixth of November" into an ISO date with a wrong year: a proposed date
            # in the past with a year nobody said means the year was invented
            today = str(now)[:10]
            if d and re.match(r"^\s*\d{4}-\d{2}-\d{2}\s*$", s) and today[:4].isdigit() and d < today and int(d[:4]) != int(today[:4]):
                y = int(today[:4])
                d2 = str(y) + d[4:]
                d = d2 if d2 >= today else str(y + 1) + d[4:]
            return d
        if kind == "amount":
            return N.parse_amount(s)
        if kind == "digits":
            d = N.parse_digits(s, None)
            L = sspec.get("length")
            lo = int(L or sspec.get("min_length") or 0)
            hi = int(L or sspec.get("max_length") or 0)
            if d and lo and len(d) < lo:     # the customer has not finished: keep it and join the next part
                return ("partial", d)
            if d and hi and len(d) > hi:
                return None
            return d
        if kind == "time":
            return N.parse_time(s)
        if kind == "enum" and sspec.get("values"):   # validated here (no platform enum: its reset rule keeps stale values)
            low = s.strip().lower()
            vals = [str(v) for v in sspec["values"]]
            hit = [v for v in vals if v.lower() == low] or [v for v in vals if v.lower() in low]
            return hit[0] if len(hit) == 1 else None
        return s.strip()
    if prev and _said(" ".join(re.sub(r"[^\w]+", " ", prev).split()[-3:]), raw):
        prev = ""   # the language layer already joined the parts ("Tuesday the" -> "Tuesday the 27th"): take its value
    if prev:   # the customer is finishing what they started last turn: read both parts together first
        # ...but for a one-value kind (amount, date, time) a whole value said now is the value (said again, or a
        # correction): "I can pay 400," + "the full four hundred and twenty" is 420, not "400 four hundred and twenty"
        # read as 400 (seen on Freya). Parts are joined when the new part is not whole by itself or plainly goes on
        # ("and fifty", "point five"); digit strings and birth dates are always built from their parts.
        alone = attempt(raw)
        if kind in ("digits", "birth_date") or alone in (None, "") or isinstance(alone, tuple) or                 re.match(r"^\s*(and|point|oh|of|-)\b", str(raw).strip().lower()):
            v2 = attempt(prev + " " + raw)
            if v2 not in (None, "") and not isinstance(v2, tuple):
                return v2
    v = attempt(raw)
    if isinstance(v, tuple):
        if prev:
            v2 = attempt(prev + " " + raw)
            if v2 and not isinstance(v2, tuple):
                return v2
        vars["_partial_" + sname] = prev + " " + raw if prev else raw
        return None
    if v is None and prev:
        v = attempt(prev + " " + raw)
        if isinstance(v, tuple):
            v = None
    if v is None and kind in ("birth_date", "date", "time", "amount"):
        vars["_partial_" + sname] = raw[-120:]
    return v


def _emit(ir, m, outs):
    texts, instr, call = [], [], None
    for o in outs:
        if "say" in o:
            texts.append(o["say"])
        elif "instruct" in o:
            instr.append(o["instruct"])
        elif "call" in o:
            call = o
    say = " ".join(t.strip() for t in texts if t and t.strip())
    vars["say_text"] = say
    cont = getattr(sys.modules[type(m).__module__], "CONTINUER", None) or "Please go on."
    waiting = say.strip().endswith(cont) or any(o.get("continuer") for o in outs)
    if say and not waiting:   # the agent waits ("...Please go on."): nothing said so far is dropped
        vars["_recent"] = ""   # the agent put a question (again): a new attempt, earlier answers are no evidence for it
        vars["_held"] = ""     # a held value waits only while the agent waits, like the parts
        for k in [k for k in vars if str(k).startswith("_partial_")]:
            vars[k] = ""       # nor are parts of an earlier answer: a part waits only while the agent waits ("Please go on")
    if say:   # figures the customer has heard in this call: a value can refer to them ("the full amount", "that one")
        vars["_agent_said"] = (str(vars.get("_agent_said") or "") + " | " + say)[-600:]
    vars["say_instruction"] = " ".join(instr)
    phase = m.s.get("phase") or ir.get("initial_phase")
    if call is not None:
        tool = call["call"]
        for k, v in (call.get("args") or {}).items():
            vars["a_" + tool + "_" + k] = v if not isinstance(v, (dict, list)) else json.dumps(v)
        vars["_pending_tool"] = tool
        vars["next_node"] = "api_" + tool
        vars["after_say"] = "api_" + tool
        if say:
            vars["next_node"] = "say_then_act"
    elif m.s.get("ended"):
        vars["next_node"] = "end"
        if say:      # the last words of the call (no closing tool to speak them through): say them, then hang up
            vars["after_say"] = "end"
            vars["next_node"] = "say_then_act"
    else:
        vars["_pending_tool"] = ""
        if instr and not say:
            vars["next_node"] = "Q_" + phase
        else:
            if instr:
                vars["say_text"] = say
            vars["next_node"] = "L_" + phase
    vars["phase"] = phase


def run_brain(is_init):
    M, N, D = _load_engine()
    M.FLAGS.update(CFG.get("flags") or {})   # per-workflow engine switches (an A/B arm); set on every run
    ir = IR
    st_raw = vars.get("_st")
    call_vars = _call_vars(ir)
    now = call_vars.get((ir.get("time") or {}).get("now_var", "now"))
    if _blank(st_raw) or is_init:
        m = M.Machine(ir, call_vars)
        outs = m.handle({"type": "start"})
        if not is_init:   # chat route skipped the init node: the first message only starts the call
            for k in list(vars.keys()):
                if str(k).startswith("i_"):
                    vars[k] = False
                elif str(k).startswith("s_"):
                    vars[k] = ""
    else:
        state = _unpack(st_raw)
        m = M.Machine(ir, call_vars, state)
        pend = vars.get("_pending_tool")
        if not _blank(pend):
            ev = _tool_event(str(pend))
            vars["_pending_tool"] = ""
            outs = m.handle(ev)
        else:
            outs = m.handle(_user_event(ir, m.s["phase"], N, now))
    # an end without a pending close: say goodbye and hang up
    _emit(ir, m, outs)
    m.s["trace"] = m.s["trace"][-30:]
    # the state travels in a variable that Freya echoes in every code step's output; an unbounded trace made a long
    # call's output too large to parse (seen: "Sandbox did not return a parseable result"). Keep the recent trace only.
    if isinstance(m.s.get("trace"), list) and len(m.s["trace"]) > 40:
        m.s["trace"] = m.s["trace"][-40:]
    vars["_st"] = _pack(m.s)
    vars["_turn"] = str(int(str(vars.get("_turn") or "0").split(".")[0] or 0) + 1)
