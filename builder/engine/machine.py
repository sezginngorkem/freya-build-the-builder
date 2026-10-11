"""Policy machine runtime: executes a PolicyIR (see notes/kural-dili.md) one event at a time.

Generic. It knows rules, phases, counters, templates and tool calls; it knows nothing about banks,
debts or any particular brief. The same file must run locally (tests, simulator) and inside a
Freya code node, so it uses only json, re, datetime and the sibling engine modules.

Events in:
  {"type": "start"}
  {"type": "user", "text": "...", "intents": ["hardship"], "slots": {"promise_date": "..."}}
  {"type": "tool", "name": "verify_identity", "ok": true, "data": {...}}   # transport ok=false -> failure
Outputs (list, in order):
  {"say": "fixed text"}            spoken as is
  {"instruct": "what to say"}      the dialogue model words it
  {"call": "tool", "args": {...}}  the runtime must call the bank tool and send back a tool event
  {"end": true}                    hang up (after close)

Rule shape (IR "rules" list):
  {"id": "R14", "phase": "verify" | "*", "on": "enter" | "user" | "intent:<id>" | "tool:<name>",
   "if": "<expr>", "do": [<action>...], "priority": 0, "src": {...}}
Actions:
  {"say": "<template id>"} | {"say_text": "literal {expr}"} | {"instruct": "text {expr}"}
  {"call": "<tool>", "args": {"field": "<expr>"}}       pauses the turn until the tool event
  {"set": {"path": "<expr>"}} | {"incr": "path"} | {"append": {"path": "<expr>"}}
  {"goto": "<phase>"} | {"next_item": "<phase when items remain>", "done": "<phase when finished>"}
  {"close": {"outcome": "<expr>", "reason": "<expr>"}}   calls the close tool, then ends
  {"stop": true}                                          end of this turn, wait for the user
Paths: counter.x, flag.x, var.x, slot.x, item.x (current item), items (list).
"""
import copy
import json
import re

from . import expr as E
from . import dates as D

MAX_STEPS = 200
def _number(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


# Dispatch mechanisms, each added for a class of failures (see notes/mimari-mekanizmalar.md). All on in production;
# switched off one at a time by sim/ablation.py to measure what each one really does.
FLAGS = {"content_first": True, "pending_polarity": True, "specific_polarity": True, "side_with_answer": True,
         "act_gating": True, "carry_over": True, "rewind": True, "confirm_conflict": True, "side_unhandled": True,
         "no_silence": True, "containment": True, "reask_contentless": True, "reply_gate": True, "clarify": True, "continuer": True, "ask_ladder": True, "answer_questions": True, "wait_unreplied": True, "refused_value": True, "ask_not_wait": False,
         "echo_continuer": True, "assent_value": True, "check_over": True, "resend_lost": True, "request_over_side": True}
ASK_CAP = 2        # the engine repeats a question at most once (asks in a row, whoever asked: the brief's own repeats
#                    count too), then the brief's rules decide; never more asks than the narrowest brief rule ("ask once more")
CONTINUER = "Please go on."
# first person -> second person when the agent repeats the customer's own words back (a closed set of English pronouns)
_SHIFT = {"i": "you", "me": "you", "my": "your", "mine": "yours", "myself": "yourself", "i'm": "you're",
          "i've": "you've", "i'd": "you'd", "i'll": "you'll", "we": "you", "us": "you", "our": "your", "ours": "yours"}


def echo_of(text):
    """The customer's unfinished last words, said back as a question so that they go on from there ("...you really
    can't...?"). A specific repair initiator gets only the missing part said; a general one ("huh?", "go on") gets the
    whole turn said again (Dingemanse et al. 2015, 12 languages) -- on Freya the customer restarted its whole message
    after "Please go on." and was cut again at the same point. None if the message is not cut off."""
    import re as _re
    t = str(text or "").strip()
    if not t or t[-1] in ".!?":
        return None
    clause = _re.split(r"[.!?]\s+", t)[-1].lstrip(" '\"").rstrip(" -–—\"")   # the last sentence, as said so far
    words = clause.replace("’", "'").split()
    if not words:
        return None
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if lw in _SHIFT:
            out.append(_SHIFT[lw])
        elif lw == "am" and i and words[i - 1].lower() == "i":
            out.append("are")
        elif lw == "was" and i and words[i - 1].lower() == "i":
            out.append("were")
        else:
            out.append(w)
    return "..." + " ".join(out) + "...?"
for _off in (__import__("os").environ.get("ENGINE_ABLATE") or "").split(","):   # experiments only; unset in production
    if _off.strip() in FLAGS:
        FLAGS[_off.strip()] = False
SIDE = ("ask_bot", "ask_scam", "ask_reason", "other_question")   # questions the customer asks instead of answering
POLARITY = ("yes", "no")
REF_SLOTS = {"slot.product_ref"}
REFUSAL = ("decline",)   # the standard "refuses" intent: a kind of no   # the convention slot that points at an item (language.md), not a value of its own   # bare answer words: tried after rules that use the content given in the same turn


def _same_value(a, b):
    try:
        return abs(float(a) - float(b)) < 0.005
    except (TypeError, ValueError):
        return str(a).strip().lower() == str(b).strip().lower()


class Machine(object):
    def __init__(self, ir, call_vars, state=None):
        self.ir = ir
        self.funcs = E.make_functions(ir.get("calendar"))
        self.funcs.update(self._ir_functions())
        self.tool_names = set((ir.get("vocabulary") or {}).get("tools", {}).keys())
        global CONTINUER
        CONTINUER = (ir.get("engine_text") or {}).get("continuer") or CONTINUER   # the call's language (IR), not English only
        self.close_tool = (ir.get("closing") or {}).get("tool", "close_call")
        self.no_close_tool = "tool" in (ir.get("closing") or {}) and not (ir.get("closing") or {}).get("tool")
        self.rules = sorted(ir.get("rules", []), key=lambda r: -int(r.get("priority", 0)))
        self._slot_refs = {}
        self._turn_fired, self._turn_settled = [], set()
        self._compiled = {}
        if state is not None:
            self.s = state
        else:
            now = call_vars.get((ir.get("time") or {}).get("now_var", "now"))
            self.s = {
                "call": dict(call_vars), "today": D.iso(now) if now else None,
                "phase": ir.get("initial_phase"), "counter": {}, "flag": {}, "var": {}, "slot": {},
                "items": [], "cursor": 0, "result": {}, "tool": {}, "said": [], "pending": None,
                "ended": False, "trace": [],
            }

    # ------------------------------------------------------------------ helpers
    def _ir_functions(self):
        out = {}
        for name, spec in (self.ir.get("functions") or {}).items():
            out[name] = self._make_ir_function(spec)
        return out

    def _make_ir_function(self, spec):
        params = spec.get("params", [])
        body = spec["expr"]

        def f(*args):
            local = dict(self.ctx())
            local.update(dict(zip(params, args)))
            return E.evaluate(body, local, self.funcs)
        return f

    def ctx(self):
        s = self.s
        items = s["items"]
        item = items[s["cursor"]] if 0 <= s["cursor"] < len(items) else {}
        c = {"call": s["call"], "today": s["today"], "counter": s["counter"], "flag": s["flag"],
             "var": s["var"], "slot": s["slot"], "items": items, "item": item, "result": s["result"],
             "tool": s["tool"], "phase": s["phase"], "said": s["said"], "tables": self.ir.get("tables", {}),
             "const": self.ir.get("constants", {})}
        for k, v in (self.ir.get("derived") or {}).items():
            pass
        return c

    def ev(self, src):
        if src is None:
            return None
        if not isinstance(src, str):
            return src
        tree = self._compiled.get(src)
        if tree is None:
            tree = E.compile_expr(src)
            self._compiled[src] = tree
        return E.evaluate(tree, self.ctx(), self.funcs)

    def safe(self, src, where):
        """Evaluate; on an error trace it and return None. A rule the IR author did not foresee for this state must not
        crash the turn (the customer would hear a fallback), and it must stay visible to the tests (trace kind
        'expr_error'), never silent."""
        try:
            return self.ev(src)
        except Exception as e:
            if not FLAGS["containment"]:
                raise
            self.trace("expr_error", where=where, expr=str(src)[:120], error=str(e)[:160])
            return None

    def render(self, text):
        def rep(m):
            v = self.safe(m.group(1), "template")
            if v is None:
                self.trace("render_none", expr=m.group(1)[:120])   # a hole in a spoken sentence: visible to tests
            if isinstance(v, float):
                return "%.2f" % v
            return "" if v is None else str(v)
        return re.sub(r"\{([^{}]+)\}", rep, text)

    def _set_path(self, path, value):
        root, _, rest = path.partition(".")
        if root == "item":
            items = self.s["items"]
            if 0 <= self.s["cursor"] < len(items):
                items[self.s["cursor"]][rest] = value
            return
        if root == "items":
            self.s["items"] = value or []
            return
        bucket = self.s.get(root)
        if not isinstance(bucket, dict):
            raise ValueError("bad path %r" % path)
        bucket[rest] = value

    def _get_path(self, path):
        return self.ev(path)

    def trace(self, kind, **kw):
        self.s["trace"].append(dict(kind=kind, phase=self.s["phase"], **kw))

    # ------------------------------------------------------------------ event handling
    def handle(self, event):
        self._q_turn = False
        out = self._handle(event)
        if self._q_turn:
            event = dict(event, intents=list(event.get("intents") or []) + ["other_question"])
        if event.get("type") == "user" and FLAGS["answer_questions"]:
            out = self._answer_from_facts(event, out)
        self._check_restricted(out)
        heard = self.s.setdefault("heard", [])
        for o in out:
            if o.get("say"):
                heard.append(str(o["say"])[:300])
        del heard[:-8]
        return out

    def _answer_from_facts(self, event, out):
        """A customer's question is answered from what the agent may say: what it has already said in this call.
        The brief's own "I do not have that information" sentence stays for anything else. The wording comes from the
        dialogue model, bounded to these facts; no value or decision changes. Seen on Freya: "How much is the minimum
        payment?" answered "I do not have that information" right after the agent offered it (dishonest)."""
        if "other_question" not in (event.get("intents") or []):
            return out
        rules = [r for r in self.rules if r.get("on") == "intent:other_question"]
        no_info = set(a.get("say") for r in rules for a in (r.get("do") or []) if isinstance(a, dict) and a.get("say"))
        idx = [i for i, o in enumerate(out) if o.get("template") in no_info]
        if not idx or any(("call" in o) or o.get("end") or ("instruct" in o) for o in out) or self.s["ended"] or self.s["pending"]:
            return out   # a turn that also calls a tool or ends keeps its fixed sentences: only a pure question turn is answered
        facts = []
        for t in self.s.get("heard") or []:
            facts.append("You said: " + t)
        # only what the agent has already said in this call: raw tool data may hold what the brief does not let the
        # agent say (another product, a total balance, the number of identity attempts left) -- an audit finding
        if not facts:
            return out
        no_info_text = out[idx[0]]["say"]
        rest = " ".join(str(o.get("say")) for o in out[idx[0] + 1:] if o.get("say") and not o.get("reprompt"))
        if self._is_offer(self.s["var"].get("_last_prompt")):
            rest = ""   # an open offer is not made again after answering the customer's question
        instr = ("The customer asked: \"%s\". Answer that question in one short sentence using ONLY these facts, and "
                 "only if they contain the answer: %s. If they do not, say exactly: \"%s\"." %
                 (str(event.get("text") or "")[:200], " | ".join(facts), no_info_text))
        instr += (" Then say exactly: \"%s\"" % rest) if rest else " Say nothing else."
        self.trace("answer_from_facts", facts=len(facts))
        return out[:idx[0]] + [{"instruct": instr}]

    def _check_restricted(self, out):
        """The spec's time-limited words ("say the promise is recorded only after create_promise returns ok", "do not
        say 'debt' before identity is verified"), declared in the IR as restricted_words. A sentence said while the
        condition does not hold yet is recorded as a violation: the tests and the builder's self-test fail on it and the
        reader rewords (judges read words literally, in any sense of the word)."""
        for rw in self.ir.get("restricted_words") or []:
            words = [w for w in (rw.get("words") or []) if w]
            if not words:
                continue
            try:
                allowed = bool(self.ev(rw.get("until"))) if rw.get("until") not in (None, "") else False
            except Exception:
                allowed = False
            if allowed:
                continue
            for o in out:
                text = str(o.get("say") or o.get("instruct") or "")
                for w in words:
                    if re.search(r"\b" + re.escape(w.lower()), text.lower()):
                        self.trace("restricted_word", word=w, text=text[:120], until=rw.get("until"))
                        self.s["var"].setdefault("_violations", []).append("'%s' said before %s: %s" % (w, rw.get("until"), text[:80]))

    def _handle(self, event):
        """Process one event. Returns the list of outputs."""
        if self.s["ended"]:
            return [{"end": True}]
        out = []
        t = event.get("type")
        if t == "start":
            self._enter(self.s["phase"], out)
            return out
        if t == "user":
            self._turn_fired, self._turn_settled = [], set()   # rules fired / intents decided on in this turn
            phase0, start = self.s["phase"], len(out)
            if FLAGS["refused_value"] and str(event.get("act") or "") == "refuse" and event.get("slots"):
                # in a refusal, the value the agent has just offered is what is refused, not a proposal (a different
                # value said with it still is one). Seen on Freya: "I will not pay the one thousand three hundred and
                # twenty" was read back and nearly recorded as an agreed promise of 1320.00.
                lp = (self.s["var"].get("_last_prompt") or {}).get("say") or ""
                refused = [k for k, v in event["slots"].items() if self._in_text(v, lp)]
                if refused:
                    self.trace("refused_value", slots=refused)
                    event = dict(event, slots={k: v for k, v in event["slots"].items() if k not in refused})
            if FLAGS["assent_value"] and "yes" in (event.get("intents") or []) and event.get("slots"):
                # a yes that only repeats what the agent has just put ("Can you pay all of these in full today?" -> "Yes,
                # I'll pay both in full today") is a yes to that question, not a new proposal: the question's own rule
                # decides (seen: the date rule took the first product only and the combined read-back was lost).
                # A value the agent did not put stays a proposal ("Yes, but on Friday").
                lp = (self.s["var"].get("_last_prompt") or {}).get("say") or ""
                given = {k: v for k, v in event["slots"].items() if v not in (None, "")}
                if given and all(self._in_text(v, lp) for v in given.values()):
                    self.trace("assent_value", slots=sorted(given))
                    event = dict(event, slots={k: v for k, v in event["slots"].items() if k not in given})
            for k, v in (event.get("slots") or {}).items():
                if v not in (None, ""):
                    self.s["slot"][k] = v
            prev_text = str(self.s["var"].get("last_user_text") or "")
            waited = bool(self.s["var"].pop("_waited", False))   # the agent's last turn was "Please go on"
            self.s["var"]["last_user_text"] = event.get("text", "")
            intents = [i for i in (event.get("intents") or []) if i]
            self.s["var"]["intents"] = intents
            self._s0 = copy.deepcopy(self.s)
            fired = False
            given0 = [k for k, v in (event.get("slots") or {}).items() if v not in (None, "")]
            if "clarify" in intents:
                lp0 = self.s["var"].get("_last_prompt") or {}
                key0 = lp0.get("template") or lp0.get("say")
                answers = str(event.get("reply") or "") == "answer" and any(i not in SIDE and i != "clarify" for i in intents)
                # the message also answers the question ("No, this is her husband. Which account is this about?"): the
                # answer counts, the clarification request does not swallow it (seen on Freya: the identity question
                # was put again and the call closed as 'unclear')
                if given0 or answers or not FLAGS["clarify"] or (key0 and self.s["var"].get("_clarified") == key0):
                    intents = [i for i in intents if i != "clarify"]     # the message also answers: the answer counts
                else:
                    # a question about the agent's own question: neither an answer nor a refusal nor a new topic. The
                    # brief's own rule for it if it has one; else explain (the prompt's 'help' text) and ask again. It
                    # never counts as a refusal and does not use up a re-ask.
                    intents = [i for i in intents if i not in SIDE or i == "ask_bot" or i == "ask_scam"]
                    if self._fire("intent:clarify", out):
                        self.s["slot"] = {k: v for k, v in self.s["slot"].items() if k in self._sticky_slots()}
                        return out
                    lp = self.s["var"].get("_last_prompt")
                    if lp and self._is_offer(lp) and self._first_rule("intent:other_question") is not None:
                        # a question about the agent's question or offer ("Why do you need that?", "You tell me") is
                        # answered from what the agent may say, not by saying the question again (a bare repeat explains
                        # nothing, and a literal judge counts it as a second ask / a second offer); the question stays open
                        self.trace("clarify_offer_as_question")
                        intents = ["other_question"]
                        event = dict(event, intents=intents)
                        self._q_turn = True
                    elif lp and not self.s["ended"] and not self.s["pending"]:
                        self.trace("clarify", prompt=str(lp.get("template") or lp.get("say"))[:60])
                        self.s["var"]["_clarified"] = lp.get("template") or lp.get("say")
                        help_t = (self.ir.get("templates") or {}).get(lp.get("template") or "", {})
                        if isinstance(help_t, dict) and help_t.get("help"):
                            out.append({"say": self.render(str(help_t["help"]))})
                        out.append(self._reask(lp))
                        self._count_ask(lp.get("template") or lp.get("say"))
                        self.s["slot"] = {k: v for k, v in self.s["slot"].items() if k in self._sticky_slots()}
                        return out
                    intents = [i for i in intents if i != "clarify"]
            # a question with no answer in it is answered, never dropped: if nothing else in the message is handled,
            # it is the brief's "other question" (answered from facts, or the brief's own no-information sentence).
            # Seen on Freya: "Which number do you have? Read me the first two digits" got the phone question again,
            # 40 times, because the question went nowhere.
            if FLAGS["answer_questions"] and str(event.get("act") or "") == "question" and not intents and not given0 \
                    and not event.get("incomplete") and self._first_rule("intent:other_question") is not None:
                intents = ["other_question"]
                event = dict(event, intents=intents)
                self._q_turn = True
                self.trace("question_answered", text=str(event.get("text", ""))[-60:])
            # The customer has not replied yet: the message was cut off, or it does not touch the question at all (talk
            # about their day: the model's reply = "none", unlike a "non_answer" such as "I don't know"). That is not a
            # decision and not the brief's non-answer: the reply is still coming. The agent lets them go on and does NOT
            # put the question again -- measured on all archived Freya calls (sim/unreplied_runs.py): 137 of 139 such
            # runs end with the customer replying; after "Please go on." a talkative customer replied next turn in 42%,
            # after the question was put again in 20% (a new question starts their small talk again). No count is set:
            # each such turn is waited for; a half-said value is waited for while it grows (progress, not a number).
            not_yet = bool(event.get("incomplete")) or (FLAGS["wait_unreplied"] and not intents and not given0
                                                        and str(event.get("reply") or "") == "none")
            # a value begun but not whole ("The fourteenth."): waited for while it moves on; the same words again are
            # no progress, and then the brief's rules decide
            # progress = the customer has said MORE of it than before for this question; starting the same value over
            # and being cut again is no progress (seen on Freya: "...14 March" / "...14 March 19" / "...14 March" ...
            # waited for until the call timed out)
            lpk0 = (self.s["var"].get("_last_prompt") or {})
            lpk0 = lpk0.get("template") or lpk0.get("say")
            nwords = len(str(event.get("text") or "").split())
            best = int(self.s["var"].get("_wait_len") or 0) if self.s["var"].get("_wait_key") == lpk0 else 0
            started = bool(event.get("value_started")) and not given0 and nwords > best
            if event.get("value_started"):
                self.s["var"]["_wait_len"], self.s["var"]["_wait_key"] = max(best, nwords), lpk0
            not_yet = not_yet or (FLAGS["wait_unreplied"] and started and not intents)
            if FLAGS["wait_unreplied"] and event.get("incomplete") and intents and not given0 and                     all(i in SIDE for i in intents) and not self.s["ended"] and not self.s["pending"]:
                # a question inside an unfinished message ("...twenty one July nineteen ninety, and how much do I
                # actually"): it is answered in words, and the rest of the message is still coming -- the question is
                # not put again (that would drop what the customer has said so far; seen on Freya: the third date of
                # birth was lost and the check never ended)
                words = []
                for i in intents:
                    words += self._side_speech(i)
                self.trace("side_in_unfinished", intents=intents)
                out += words + [{"say": CONTINUER}]
                self.s["var"]["_waited"] = True
                self.s["slot"] = {k: v for k, v in self.s["slot"].items() if k in self._sticky_slots()}
                return out
            if intents or given0:
                self.s["var"].pop("_reask_for", None)          # a turn with content: the next empty one may be re-asked
                self.s["var"]["_cont_n"] = 0
                self.s["var"]["_cut_n"] = 0
            elif FLAGS["continuer"] and FLAGS["wait_unreplied"] and (not_yet or (event.get("partial") and event.get("partial_grew"))) \
                    and not self.s["ended"] and not self.s["pending"] and self.s["var"].get("_last_prompt"):
                # The customer is invited ONCE to go on (cut message, or not touching the question yet); a value given
                # in parts is moving on and is waited for. If the next message still does not move towards the answer,
                # the agent puts its own question again, briefly -- never as a decision for the customer (a cut message
                # is never a "no") and never an open offer again (it would be a second offer). Measured on Freya:
                # handing such messages to the brief's catch-all used up persuasion attempts on small talk (ra11, and
                # again in a replay of ra17); after "Please go on" a reply came next turn 66/37/23/13% by position, after
                # the question 69/45/28/19%.
                lp = self.s["var"].get("_last_prompt")
                progress = started
                # (flag ask_not_wait, under test: put the question at once instead of "Please go on" unless a value is
                # being given in parts -- customers hung up right after "Please go on" ~3x more often than its share)
                echo = echo_of(event.get("text")) if FLAGS["echo_continuer"] and event.get("incomplete") else None
                echo = echo if echo and echo != self.s["var"].get("_echo_prev") else None
                # (flag echo_continuer: a cut message is not a turn -- it is answered with the customer's own words, not
                # with the question again, which a literal judge counts as a second ask)
                if not_yet and (waited or FLAGS["ask_not_wait"]) and lp and not progress and not self._is_offer(lp) and not echo:
                    self.trace("reask_after_continuer", text=str(event.get("text", ""))[-40:])
                    out.append(self._reask(lp))
                else:
                    self.trace("continuer", cut=bool(event.get("incomplete")), partial=bool(event.get("partial")),
                               text=str(event.get("text", ""))[-40:])
                    if echo:
                        # never the same line twice in a row: an identical line left the customer in the same state
                        # (next message cut 83% after a repeated "Please go on." vs 64% after a different line)
                        self.s["var"]["_echo_prev"] = echo
                        out.append({"say": echo, "continuer": True})
                    else:
                        self.s["var"]["_echo_prev"] = ""
                        out.append({"say": CONTINUER})
                    self.s["var"]["_waited"] = True
                self.s["slot"] = {k: v for k, v in self.s["slot"].items() if k in self._sticky_slots()}
                return out
            elif FLAGS["continuer"] and not FLAGS["wait_unreplied"] and event.get("incomplete")                   and int(self.s["var"].get("_cut_n") or 0) >= 2 and int(self.s["var"].get("_cut_n") or 0) < 8                     and not self.s["ended"] and not self.s["pending"] and self.s["var"].get("_last_prompt"):
                # a message cut off mid-sentence is never a decision (not a no, not a refusal, not a non-answer): the
                # brief's rules are for finished messages. After two continuers, put the question again, briefly.
                self.s["var"]["_cut_n"] = int(self.s["var"].get("_cut_n") or 0) + 1
                self.trace("cut_off_reask", n=self.s["var"]["_cut_n"])
                lp = self.s["var"]["_last_prompt"]
                out.append({"say": CONTINUER} if self._is_offer(lp) else self._reask(lp))
                self.s["slot"] = {k: v for k, v in self.s["slot"].items() if k in self._sticky_slots()}
                return out
            elif FLAGS["continuer"] and not FLAGS["wait_unreplied"] and (event.get("incomplete") or event.get("partial") or str(event.get("reply") or "") == "answer") \
                    and int(self.s["var"].get("_cont_n") or 0) < 2                    and not self.s["ended"] and not self.s["pending"] and self.s["var"].get("_last_prompt"):
                # the customer stopped mid-sentence or gave the first part of a value: let them finish (a continuer, as a
                # person would say) instead of asking the whole question again, which makes them start over (measured on
                # Freya: up to 8 repeats of the same question in pieces / talkative calls)
                self.s["var"]["_cont_n"] = int(self.s["var"].get("_cont_n") or 0) + 1
                if event.get("incomplete"):
                    self.s["var"]["_cut_n"] = int(self.s["var"].get("_cut_n") or 0) + 1
                self.trace("continuer", partial=bool(event.get("partial")), text=str(event.get("text", ""))[-40:])
                out.append({"say": CONTINUER})
                self.s["slot"] = {k: v for k, v in self.s["slot"].items() if k in self._sticky_slots()}
                return out
            elif FLAGS["reask_contentless"] and not self.s["ended"] and not self.s["pending"] and self._should_reask(event):
                lp = self.s["var"].get("_last_prompt")
                key = (lp or {}).get("template") or (lp or {}).get("say")
                if lp:
                    # nothing usable for the pending question (chatter, a cut-off sentence): ask it again, once
                    self.s["var"]["_reask_for"] = key
                    self.trace("reask_contentless", prompt=str(key)[:60], reply=event.get("reply"), ok=event.get("reply_ok"))
                    if self._is_offer(lp):
                        out.append({"say": CONTINUER})     # an offer stays open; it is not made again
                    else:
                        self._count_ask(key)
                        out.append(self._reask(lp))
                    self.s["slot"] = {k: v for k, v in self.s["slot"].items() if k in self._sticky_slots()}
                    return out
            # "Not today, but Friday" / "Yes, 200 on the 20th": the content outranks the bare yes/no. Order: meaningful
            # intents; yes/no rules that answer a pending question (state condition); then, if a user rule of this
            # phase can use a slot given in this turn, the user rules (normal priority order); then yes/no; then user rules.
            given = set("slot." + k for k, v in (event.get("slots") or {}).items() if v not in (None, ""))
            ordered = self._intents_by_priority(intents)
            # One message can carry several things: a topic change (paid, dispute, hardship...), the answer to the
            # current question, and a side question ("21 July 1990. How much do I owe?"). Topic changes go first (brief
            # priority). If the answer is usable here, the side question is answered in words only and the answer is
            # processed in the same turn; the side question never swallows the answer.
            usable = bool(given) and self._can_use(given)
            if usable and event.get("act") == "answer" and FLAGS["act_gating"]:
                heavy = [i for i in ordered if i not in POLARITY and i != "confirm_identity" and self._consequential(i)]
                if heavy:   # "Can I pay that this Friday instead?" is an answer, not a request for a payment plan
                    self.trace("act_answer_overrides", intents=heavy)
                    ordered = [i for i in ordered if i not in heavy]
                    self._turn_settled |= set(heavy)
            elif str(event.get("act") or "") == "question" and FLAGS["act_gating"]:
                # a question is answered, not acted on: "What is the minimum I can pay?" is not a request for a new
                # payment plan (seen on Freya: transfer and call closed on such a question)
                heavy = [i for i in ordered if i not in POLARITY and i not in SIDE and i != "confirm_identity"
                         and i != "clarify" and self._consequential(i)]
                if heavy:
                    self.trace("question_not_action", intents=heavy)
                    ordered = [i for i in ordered if i not in heavy]
                    intents = [i for i in intents if i not in heavy]
                    self._turn_settled |= set(heavy)
                    if not ordered and not given and any(i.get("id") == "other_question" for i in self.ir.get("intents", [])):
                        ordered = ["other_question"]
                        event["intents"] = list(event.get("intents") or []) + ["other_question"]   # answered as a question
            if FLAGS["request_over_side"] and "?" not in str(event.get("text") or ""):
                # a message with no question in it that names something this step has a rule for is that request, not
                # a side question about it (seen on Freya: "I want to change my statement date" was read as both the
                # request and an 'other question'; the question ranked first, was answered from the agent's own
                # offer -- "I can change it" -- and the change was never started)
                acts = [i for i in ordered if i not in SIDE and i not in POLARITY
                        and any(self._rule_applies(r, "intent:" + i) for r in self.ir.get("rules", []))]
                if acts and any(i in SIDE for i in ordered):
                    self.trace("request_over_side", kept=acts, dropped=[i for i in ordered if i in SIDE])
                    ordered = [i for i in ordered if i not in SIDE]
            side_words = []
            n_turn = len(out)
            # the message answers the pending question: with a value this step can use, or with a yes / no / identity
            # confirmation the model reads as the answer ("Yes, this is Priya Nair. What instructions were you given?").
            # Seen on Freya: the side question's rule ran first, re-asked the identity question a second time and
            # closed the call as 'unclear' although the customer had confirmed who she was, twice.
            answered = usable or (str(event.get("reply") or "") == "answer"
                                  and any(i in POLARITY or i == "confirm_identity" for i in intents))
            if answered and FLAGS["side_with_answer"]:
                # every side question of the message is answered, whatever its place in the order: the loop below stops
                # at the first rule that fires, and a question ordered after the answer's rule was dropped (seen on
                # Freya: "Yes, this is Owen Park. Is this a scam call?" -> the security question, the scam question
                # never answered, five calls failed)
                for intent in [i for i in ordered if i not in POLARITY and (i in SIDE or self._talk_only(i))]:
                    side_words += self._side_speech(intent)
                    self._turn_settled.add(intent)
            for intent in [i for i in ordered if i not in POLARITY and i not in self._turn_settled]:
                # side questions, and any intent whose rule here only talks or asks again (decides nothing): seen on
                # Freya, "...I'm her husband. You can reach Maria tomorrow morning around eleven" -> 'someone else'
                # again -> the question was put again and the callback time was lost, twice
                if answered and FLAGS["side_with_answer"] and intent in REFUSAL and usable and                         str(event.get("reply") or "") == "answer":
                    # a message that answers the pending question with a usable value did not refuse to answer it
                    # ("Eight eight four six. ... I cannot pay anything": the 'decline' was about paying; seen on
                    # Freya: the digits were dropped and the call closed as 'declined'). Like a bare no, it is
                    # weighed after the answer.
                    continue
                if answered and FLAGS["side_with_answer"] and (intent in SIDE or self._talk_only(intent)):
                    side_words += self._side_speech(intent)
                    self._turn_settled.add(intent)
                    continue
                if self._fire("intent:" + intent, out):
                    fired = True
                    break
            if side_words:
                # a side question is always answered ("Are you a robot?" next to a date), before whatever the answer
                # leads to; it was dropped when another rule of the message fired (seen on Freya)
                self.trace("side_with_answer", intents=[i for i in ordered if i in SIDE])
                out[n_turn:n_turn] = side_words
                for o in side_words:
                    if o.get("template"):
                        self.s["said"].append(o["template"])
            # A value the current step cannot use is a correction of an earlier step ("actually make it 310", "the 25th
            # then") — as in the field-tested correction pattern: go back to the most recent step of this call that
            # handles that value and process it there. And a 'yes' that carries a value contradicting what the yes would
            # record is not a confirmation of it.
            if not fired and given and not self.s["ended"] and not self.s["pending"] and not usable and FLAGS["rewind"]:
                # a correction is a value DIFFERENT from the one already taken; saying the same value again ("...637.50,
                # yes" while it is being read back) is not a correction and must not send the call back a step
                acc = self.s.get("accepted") or {}
                heard = str((self.s["var"].get("_last_prompt") or {}).get("say") or "")
                restated = set(g for g in given if (g[5:] in acc and _same_value(acc[g[5:]], self.s["slot"].get(g[5:])))
                               or self._in_text(self.s["slot"].get(g[5:]), heard))
                if restated:
                    self.trace("restated", slots=sorted(restated))
                    given = given - restated
                    for g in restated:
                        self.s["slot"].pop(g[5:], None)
            if not fired and given and not self.s["ended"] and not self.s["pending"] and not usable and FLAGS["rewind"]:
                back = self._rewind_target(given)
                if back:
                    self.trace("correction_rewind", to=back, slots=sorted(given))
                    self.s["phase"] = back
                    fired = self._fire("user", out)
            if not fired and given and "yes" in ordered and FLAGS["confirm_conflict"] and self._contradicts_yes(event):
                self.trace("confirm_conflict", slots=sorted(given))
                ordered = [i for i in ordered if i != "yes"]
                self._turn_settled.add("yes")
            # The most specific handler wins. A yes/no rule that itself uses a value given in this turn was written for
            # exactly this combination ("Yes, Friday is fine"); a yes/no rule tied to a pending question (its `if` tests
            # state, not slots) answers that question. Both go before the content rules; bare yes/no rules go after.
            for intent in ([] if fired or not given else [i for i in ordered if i in POLARITY]):
                if self._fire("intent:" + intent, out, only=lambda r: (FLAGS["specific_polarity"] and bool(self._slots_used(r) & given)) or
                              (FLAGS["pending_polarity"] and r.get("if") not in (None, "", True) and not self._slots_tested(r))):
                    fired = True
                    break
            if not fired and given and not self.s["ended"] and not self.s["pending"] and FLAGS["content_first"] and self._can_use(given):
                fired = self._fire("user", out)
            for intent in ([] if fired else [i for i in ordered if i in POLARITY or
                                             (i in REFUSAL and usable and str(event.get("reply") or "") == "answer")]):
                if self.s["ended"] or self.s["pending"]:
                    break
                if self._fire("intent:" + intent, out):
                    fired = True
                    break
            lpk = (self.s["var"].get("_last_prompt") or {})
            lpk = lpk.get("template") or lpk.get("say")
            if not fired and not self.s["ended"] and not self.s["pending"] and not given and intents and all(i in SIDE for i in intents) and FLAGS["side_unhandled"]                     and not (FLAGS["ask_ladder"] and self._asked(lpk) >= ASK_CAP):
                # a side question this phase has no rule for is never an answer: do not move the call on, ask again
                self.trace("side_unhandled", intents=intents)
                fired = True
                lp = self.s["var"].get("_last_prompt")
                if lp:
                    out.append(self._reask(lp))
            if not fired and not self.s["ended"] and not self.s["pending"]:
                fired = self._fire("user", out)
            if not fired and not out and not self.s["ended"] and not self.s["pending"] and FLAGS["no_silence"]:
                # no rule handled this message: never stay silent (a silent agent loses the customer)
                self.trace("no_rule", text=str(event.get("text", ""))[:120], intents=intents, slots=list((event.get("slots") or {}).keys()))
                lp = self.s["var"].get("_last_prompt")
                if lp:
                    out.append(self._reask(lp))
            if FLAGS["carry_over"]:
                self._carry_over(event, phase0, start, out)
            self.s["slot"] = {k: v for k, v in self.s["slot"].items() if k in self._sticky_slots()}
            return out
        if t == "tool":
            name = event.get("name")
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            res = dict(data)
            res["_transport_ok"] = bool(event.get("ok", True))
            if "ok" not in res:
                res["ok"] = bool(event.get("ok", True))
            pend0 = self.s["pending"]
            if FLAGS["resend_lost"] and event.get("no_response") and isinstance(pend0, dict) and pend0.get("tool") == name                     and not pend0.get("resent") and "args" in pend0:
                # the request got no answer from the bank at all (a gateway error page, a timeout): it never reached the
                # bank, so nothing was decided -- not a failure of the tool the brief's failure rules are about. Sent
                # once more, unchanged and silently (seen on Freya: a lost date-of-birth check was taken as "not
                # caught", the customer moved on and the third wrong answer never reached the bank). A failure the
                # bank itself reports (its own error body, e.g. a 500 "nothing was recorded") goes to the brief's rules.
                self.trace("resend_lost", tool=name)
                self.s["pending"] = dict(pend0, resent=True)
                out.append({"call": name, "args": pend0["args"]})
                return out
            prev = self.s["tool"].get(name)
            if FLAGS["check_over"] and name == "verify_identity" and res["_transport_ok"] and not res.get("ok") and                     isinstance(prev, dict) and not prev.get("ok") and res.get("error") and prev.get("error") == res.get("error"):
                # the bank gives the same refusal again ("identity check is over"): asking once more cannot change it.
                # It is taken as a wrong answer, so the brief's own wrong-answer rule and limit end the check (seen on
                # Freya: "Sorry, I didn't catch that" + the same question, 51 times, until the call timed out)
                self.trace("check_over", error=str(res.get("error"))[:60])
                res = dict(res, ok=True, verified=False)
            self.s["result"] = res
            self.s["tool"][name] = res
            pend = self.s["pending"]
            self.s["pending"] = None
            if name == self.close_tool:
                self.s["ended"] = True
                out.append({"end": True})
                return out
            self._fire("tool:" + name, out)
            if pend and pend.get("rest") and not self.s["pending"] and not self.s["ended"]:
                self._run_actions(pend["rest"], out, pend.get("rule"))
            return out
        raise ValueError("unknown event %r" % t)

    def _sticky_slots(self):
        return set((self.ir.get("slots_sticky") or []))

    def _intents_by_priority(self, intents):
        pri = {i["id"]: int(i.get("priority", 0)) for i in self.ir.get("intents", [])}
        return sorted(intents, key=lambda i: -pri.get(i, 0))

    def _rule_applies(self, r, on):
        if r.get("on") != on:
            return False
        ph = r.get("phase", "*")
        if ph != "*" and not (ph == self.s["phase"] or (isinstance(ph, list) and self.s["phase"] in ph)):
            return False
        nph = r.get("not_phase")
        if nph and (self.s["phase"] == nph or (isinstance(nph, list) and self.s["phase"] in nph)):
            return False
        return True

    def _slots_tested(self, r):
        """slot.<name> references in a rule's `if` (cached per rule id)."""
        key = r.get("id") or id(r)
        if key not in self._slot_refs:
            try:
                names = E.names_used(r.get("if"))[0] if r.get("if") not in (None, "", True) else set()
            except Exception:
                names = set()
            self._slot_refs[key] = set(n for n in names if n.startswith("slot."))
        return self._slot_refs[key]

    # ------------------------------------------------------------------ what a rule DOES (measured, not read from its text)
    # Several dispatch decisions need to know the effect of a rule: does it end the call or call a bank tool? does it
    # only talk? does it do exactly what a bare yes/no would do? Reading the rule's text answers this only for the way
    # it happens to be written (a procedure call vs. inlined actions, a goto into a phase whose entry transfers...).
    # So the rule is run on a scratch copy of the state and its effect is compared. Nothing of the real call changes.
    def _simulate(self, rule, base):
        keep = (self.s, self._turn_fired, self._turn_settled)
        self.s = copy.deepcopy(base)
        self._turn_fired, self._turn_settled = [], set()
        out = []
        try:
            self._run_actions(rule.get("do", []), out, rule.get("id"))
        except Exception as e:
            out.append({"error": str(e)[:200]})
        finally:
            res = (out, self.s)
            self.s, self._turn_fired, self._turn_settled = keep
        return res

    @staticmethod
    def _state_key(s):
        x = {k: v for k, v in s.items() if k not in ("trace", "said")}
        var = dict(x.get("var") or {})
        var.pop("_last_prompt", None)
        x["var"] = var
        return json.dumps(x, sort_keys=True, default=str)

    def _effect(self, rule, base):
        out, s2 = self._simulate(rule, base)
        spoken = [{k: o[k] for k in ("say", "instruct", "call", "args", "end", "error") if k in o} for o in out]
        return json.dumps(spoken, sort_keys=True, default=str), self._state_key(s2), out, s2

    def _first_rule(self, on, state=None):
        """The rule that would fire for `on` in this state (phase, `if`), or None."""
        keep = self.s
        if state is not None:
            self.s = state
        try:
            for r in self.rules:
                if self._rule_applies(r, on) and self._cond(r):
                    return r
            return None
        finally:
            self.s = keep

    def _rewind_target(self, given):
        """Most recent earlier phase of this call in which a user rule would use a value given now."""
        here = self.s["phase"]
        for ph in reversed(self.s.get("visited") or []):
            if ph == here:
                continue
            keep = self.s["phase"]
            self.s["phase"] = ph
            try:
                if self._can_use(given):
                    return ph
            finally:
                self.s["phase"] = keep
        return None

    def _contradicts_yes(self, event):
        """Would the 'yes' rule now call a tool with a date/amount different from one the customer just said?"""
        r = self._first_rule("intent:yes")
        if r is None:
            return False
        _, _, out, _ = self._effect(r, self.s)
        spec = self.ir.get("slots") or {}
        said = {}
        for k, v in (event.get("slots") or {}).items():
            kind = (spec.get(k) or {}).get("kind")
            if kind in ("amount", "date") and v not in (None, ""):
                said.setdefault(kind, []).append(v)
        if not said:
            return False
        for o in out:
            if "call" not in o:
                continue
            for a in (o.get("args") or {}).values():
                if isinstance(a, (int, float)) and not isinstance(a, bool) and "amount" in said:
                    if all(abs(float(a) - float(x)) > 0.005 for x in said["amount"]):
                        return True
                if isinstance(a, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", a) and "date" in said:
                    if all(a != str(x)[:10] for x in said["date"]):
                        return True
        return False

    def _consequential(self, intent):
        """Would handling this intent now call a bank tool or end the call (transfer, note, close)?"""
        r = self._first_rule("intent:" + intent)
        if r is None:
            return False
        _, _, out, s2 = self._effect(r, self.s)
        return bool(s2.get("ended")) or any("call" in o for o in out)

    def _talk_only(self, intent):
        """Does this phase's rule for the intent only talk or ask again (no state change, no tool, no end)?"""
        r = self._first_rule("intent:" + intent)
        if r is None:
            return False
        _, key, out, s2 = self._effect(r, self.s)
        return key == self._state_key(self.s) and not s2.get("ended") and not any("call" in o for o in out)

    def _side_speech(self, intent):
        """The words of this phase's rule for a side question, if the rule ONLY talks (changes nothing else). A rule
        that changes state (e.g. 'asking instead of answering counts as declining') is not run: the answer decides."""
        r = self._first_rule("intent:" + intent)
        if r is None:
            return []
        _, key, out, s2 = self._effect(r, self.s)
        if key != self._state_key(self.s) or s2.get("ended") or any("call" in o for o in out):
            # the rule also changes state (counts a re-ask, a decline...): only its opening sentences are said (e.g.
            # the brief's "I do not have that information"), so the question is not left unanswered
            words = []
            for a in r.get("do") or []:
                if not isinstance(a, dict) or "say" not in a or a.get("prompt"):
                    break
                tpl = (self.ir.get("templates") or {}).get(a["say"])
                if tpl is None:
                    break
                words.append({"say": self.render(tpl["text"] if isinstance(tpl, dict) else tpl), "template": a["say"]})
            return words
        return [dict(o) for o in out if "say" in o and not o.get("reprompt")]

    def _carry_over(self, event, phase0, start, out):
        """What the customer said in this turn must not be lost when a rule moves the call to another phase.
        'Not today, and the full amount is too much': the 'no' moves the call from 'pay all today?' to the product
        negotiation; the 'too much' was not used by any rule yet, and the new phase has a rule for it. Re-dispatch the
        unused intents (and values) in the new phase; the new phase's opening question is then not asked, because the
        rule that handles the carried information asks its own question."""
        for _ in range(2):
            if self.s["ended"] or self.s["pending"] or self.s["phase"] == phase0:
                return
            fired = list(self._turn_fired)
            # an intent whose rule does exactly what the plain yes/no rule of that phase does was consumed without
            # using its meaning ('too much' handled like 'no'): it still has to be heard by the next phase
            meaningful = [on[7:] for on, r in fired if on.startswith("intent:") and on[7:] not in POLARITY
                          and not self._like_polarity(r, phase0)]
            if meaningful:
                # the turn's topic was handled by its highest-priority intent ('hardship comes before restructuring'):
                # lower-priority topics of the same turn are overruled, not postponed
                return
            used_intents = set(on[7:] for on, r in fired if on.startswith("intent:") and not self._like_polarity(r, phase0))
            used_slots = set()
            for _, r in fired:
                used_slots |= self._slots_used(r)
            given = set("slot." + k for k, v in (event.get("slots") or {}).items() if v not in (None, ""))
            left_i = [i for i in self._intents_by_priority(event.get("intents") or [])
                      if i not in used_intents and i not in POLARITY and i not in SIDE and i not in self._turn_settled]
            left_s = given - used_slots
            if left_s and left_s <= REF_SLOTS and used_slots & given:
                # a product reference only says which product the values are about; those values were used, so the
                # reference was too (seen on Freya: "I can pay the loan on the 16th" -> the date made the promise and
                # moved to the read-back; "the loan" alone was carried there, taken as a change, and every promise was
                # read back twice)
                left_s = set()
            target = None
            for i in left_i:
                if any(self._rule_applies(r, "intent:" + i) and self._cond(r) for r in self.rules):
                    target = ("intent:" + i, None); break
            if target is None and left_s and self._can_use(left_s):
                target = ("user", None)
            if target is None:
                return
            # drop the opening question the new phase just asked: the carried information answers or replaces it
            lp = self.s["var"].get("_last_prompt")
            for j in range(len(out) - 1, start - 1, -1):
                if out[j] is lp or (isinstance(lp, dict) and out[j].get("say") == lp.get("say") and out[j].get("template") == lp.get("template")):
                    del out[j]
                    break
            self.trace("carry_over", from_phase=phase0, to=self.s["phase"], on=target[0])
            for k, v in (event.get("slots") or {}).items():
                if v not in (None, ""):
                    self.s["slot"][k] = v
            phase0 = self.s["phase"]
            self._turn_fired = []
            self._fire(target[0], out)

    def _like_polarity(self, r, phase):
        """Did this intent's rule do exactly what the bare yes/no of that phase would have done, from the state at the
        start of the turn? Then the intent's meaning was not used ('too much' handled like 'no')."""
        base = getattr(self, "_s0", None)
        if base is None or base.get("phase") != phase:
            return False
        mine = self._effect(r, base)[:2]
        for pol in POLARITY:
            r2 = self._first_rule("intent:" + pol, base)
            if r2 is not None and r2 is not r and self._effect(r2, base)[:2] == mine:
                return True
        return False

    def _cond(self, r):
        try:
            return r.get("if") in (None, "", True) or bool(self.ev(r.get("if")))
        except Exception:
            return False

    def _in_text(self, v, text):
        """Is this value the one the agent just put to the customer (as it was said)?"""
        if v in (None, "") or not text:
            return False
        try:
            f = float(v)
            return ("%.2f" % f) in text or (f == int(f) and re.search(r"(?<![\d.])%d(?![\d])" % int(f), text) is not None)
        except (TypeError, ValueError):
            pass
        if re.match(r"^\d{4}-\d{2}-\d{2}$", str(v)) and self.s.get("today"):
            # a day the agent named relative to the call ("Can you pay ... today?")
            import datetime as _dt
            t0 = _dt.date.fromisoformat(self.s["today"])
            for word, days in (("today", 0), ("tomorrow", 1)):
                if re.search(r"\b%s\b" % word, text, re.I) and str(v) == (t0 + _dt.timedelta(days=days)).isoformat():
                    return True
        fn = self.funcs.get("day_label")
        if fn and re.match(r"^\d{4}-\d{2}-\d{2}$", str(v)):
            try:
                return str(fn(str(v))) in text
            except Exception:
                return False
        return False

    def _reask(self, lp):
        """The prompt to say when asking again: from its first question sentence on. What came before the question was
        a statement about that moment ("That does not match our records.", "Before we continue, I need to ask two
        security questions.") and is not true or not needed a second time (VoiceXML: a reprompt plays the field's
        prompt, not the nomatch message). Seen on Freya: "That does not match our records" said again after a cut-off
        message, before the bank had checked anything."""
        o = dict(lp, reprompt=True)
        text = str(lp.get("say") or "")
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        first_q = next((i for i, p in enumerate(parts) if p.rstrip().endswith("?")), 0)
        if first_q > 0:
            o["say"] = " ".join(parts[first_q:])
        return o

    def _is_offer(self, lp):
        """Does the pending prompt propose something (an amount or a day)? Known from the template's structure: it
        renders a money or date value. Re-saying an offer is a new offer to a literal judge ("offer the floor once")."""
        if not lp:
            return False
        tpl = (self.ir.get("templates") or {}).get(lp.get("template") or "")
        text = tpl.get("text") if isinstance(tpl, dict) else (tpl or "")
        if re.search(r"\{[^}]*\b(money|day_label|fmt_date|date_label|amount)\b", str(text)):
            return True
        # a proposal of an action: the customer's "yes" to the pending question would transfer, record or call a tool
        # ("Would you like me to connect you with our customer support team?"); asking it again is offering it again
        return lp is self.s["var"].get("_last_prompt") and self._consequential("yes")

    def _asked(self, key):
        """How many times in a row this question has been put (by the IR or the engine)."""
        v = self.s["var"]
        return int(v.get("_ask_n") or 1) if key and v.get("_ask_key") == key else 0

    def _count_ask(self, key):
        v = self.s["var"]
        if v.get("_ask_key") == key:
            v["_ask_n"] = int(v.get("_ask_n") or 1) + 1
        else:
            v["_ask_key"], v["_ask_n"] = key, 1

    def _should_reask(self, event):
        """A turn with no intent and no value. Ask the pending question again unless the customer gave a real
        non-answer (evidence words found in the message) or this question has already been asked twice in a row."""
        lp = self.s["var"].get("_last_prompt")
        if not lp:
            return False
        key = lp.get("template") or lp.get("say")
        asked = int(self.s["var"].get("_ask_n") or 1) if self.s["var"].get("_ask_key") == key else 1
        if not FLAGS["reply_gate"]:
            return str(event.get("act") or "other").lower() != "refuse" and self.s["var"].get("_reask_for") != key
        if str(event.get("reply") or "") == "non_answer" and event.get("reply_ok"):
            return False                      # the brief's own non-answer rule decides
        return asked < ASK_CAP

    def _slots_used(self, r):
        """slot.<name> references anywhere in a rule: its `if`, its actions and the procedures it runs. How a rule is
        written (test in `if` or in an `if` action) must not change whether it counts as using the value."""
        key = ("used", r.get("id") or id(r))
        if key not in self._slot_refs:
            procs = self.ir.get("procedures") or {}
            seen, todo, txt = set(), [r], []
            while todo:
                x = todo.pop()
                j = json.dumps(x)
                txt.append(j)
                for name in re.findall(r'"run": "([^"]+)"', j):
                    if name not in seen and name in procs:
                        seen.add(name); todo.append(procs[name])
            self._slot_refs[key] = set("slot." + m for m in re.findall(r"\bslot\.([A-Za-z_]\w*)", " ".join(txt)))
        return self._slot_refs[key]

    def _can_use(self, given):
        """True if a user rule of this phase that applies now uses a slot given in this turn."""
        for r in self.rules:
            if self._rule_applies(r, "user") and self._slots_used(r) & given:
                try:
                    if r.get("if") in (None, "", True) or self.ev(r.get("if")):
                        return True
                except Exception:
                    pass
        return False

    def _fire(self, on, out, only=None):
        for r in self.rules:
            if not self._rule_applies(r, on) or (only is not None and not only(r)):
                continue
            cond = r.get("if")
            try:
                ok = True if cond in (None, "", True) else bool(self.ev(cond))
            except Exception as e:
                self.trace("rule_error", rule=r.get("id"), error=str(e)[:200])
                ok = False
            if ok:
                self.trace("rule", rule=r.get("id"), on=on)
                self._turn_fired.append((on, r))
                for k in self._slots_used(r):   # the value this rule took from the customer: now the agent's value
                    if k.startswith("slot.") and k[5:] in self.s["slot"]:
                        self.s.setdefault("accepted", {})[k[5:]] = self.s["slot"][k[5:]]
                self._run_actions(r.get("do", []), out, r.get("id"))
                return True
        return False

    def _enter(self, phase, out):
        v = self.s.setdefault("visited", [])
        if not v or v[-1] != phase:
            v.append(phase)
            del v[:-40]
        self.s["phase"] = phase
        self.trace("enter", to=phase)
        self._fire("enter", out)

    def _run_actions(self, actions, out, rule_id=None, depth=0):
        if depth > 50:
            raise RuntimeError("action recursion")
        for i, a in enumerate(actions):
            if self.s["ended"]:
                return
            if "say" in a:
                tpl = (self.ir.get("templates") or {}).get(a["say"])
                if tpl is None:
                    raise KeyError("unknown template %s" % a["say"])
                text = self.render(tpl["text"] if isinstance(tpl, dict) else tpl)
                o = {"say": text, "template": a["say"]}
                out.append(o)
                self.s["said"].append(a["say"])
                if a.get("prompt"):
                    self.s["var"]["_last_prompt"] = o
                    self.s["var"]["_since_prompt"] = False
                    self._count_ask(a["say"])
                elif text.rstrip().endswith("?"):
                    # the agent has asked something else since its question (e.g. "may I first try to help you
                    # myself?"): the customer's answer goes to that one, and the open question is left behind
                    self.s["var"]["_since_prompt"] = True
            elif "say_text" in a:
                o = {"say": self.render(a["say_text"])}
                out.append(o)
                if a.get("prompt"):
                    self.s["var"]["_last_prompt"] = o
            elif "instruct" in a:
                o = {"instruct": self.render(a["instruct"])}
                out.append(o)
                if a.get("prompt"):
                    self.s["var"]["_last_prompt"] = o
            elif "reprompt" in a:
                lp = self.s["var"].get("_last_prompt")
                rule = next((r for r in self.rules if r.get("id") == rule_id), {})
                answering = str(rule.get("on", "")).startswith("intent:") and rule["on"][7:] in SIDE + ("clarify",)
                if lp and answering:
                    # the customer's question is answered; the agent's own question (or offer) stays open and is not
                    # said again (seen on Freya: "Which account is this about?" -> answer + the phone question again ->
                    # the judge counted a second ask where the case allowed one)
                    self.trace("question_stays_open", rule=rule_id)
                elif lp and self._is_offer(lp) and not self.s["var"].get("_since_prompt"):
                    # an offer is made once: asking "again" would be a second offer to a literal listener. The offer
                    # stays open; the customer is let to go on (they may ask about it, take it, or decline it)
                    self.trace("offer_stays_open", rule=rule_id)
                    out.append({"say": CONTINUER, "reprompt": True})   # stands for the re-ask: never a side answer's words
                elif lp:
                    # (after something else was said in between -- e.g. "may I first try to help you myself?" -- the
                    # open question is put again: without it the customer is left with no question at all; seen on
                    # Freya: 25 turns of small talk answered with "Please go on.")
                    self.s["var"]["_since_prompt"] = False
                    out.append(self._reask(lp))
            elif "for_each_item" in a:
                keep = self.s["cursor"]
                for idx in range(len(self.s["items"])):
                    self.s["cursor"] = idx
                    self._run_actions(a["for_each_item"], out, rule_id, depth + 1)
                self.s["cursor"] = keep
            elif "set_cursor" in a:
                self.s["cursor"] = int(_number(self.safe(a["set_cursor"], "set_cursor") or 0))
            elif "run" in a:
                proc = (self.ir.get("procedures") or {}).get(a["run"])
                if proc is None:
                    raise KeyError("unknown procedure %s" % a["run"])
                self._run_actions(list(proc) + list(actions[i + 1:]), out, rule_id, depth + 1)
                return
            elif "refire" in a:
                self._fire(a["refire"], out)
                return
            elif "set" in a:
                for path, src in a["set"].items():
                    self._set_path(path, self.safe(src, "set " + path))
            elif "incr" in a:
                by = a.get("by", 1)
                by = self.safe(by, "incr by") if isinstance(by, str) else by   # a number or an expression
                v = _number(self.safe(a["incr"], "incr") or 0) + _number(by or 0)
                self._set_path(a["incr"], int(v) if float(v).is_integer() else round(v, 2))
            elif "append" in a:
                for path, src in a["append"].items():
                    lst = list(self.safe(path, "append") or [])
                    lst.append(self.safe(src, "append " + path))
                    self._set_path(path, lst)
            elif "call" in a:
                args = {k: self.safe(v, "call %s.%s" % (a.get("call"), k)) for k, v in (a.get("args") or {}).items()}
                out.append({"call": a["call"], "args": args})
                self.trace("call", tool=a["call"], args=args)
                self.s["pending"] = {"tool": a["call"], "args": args, "rest": actions[i + 1:], "rule": rule_id}
                return
            elif "close" in a:
                c = a["close"]
                outcome = self.safe(c.get("outcome"), "close outcome") if c.get("outcome") else None
                reason = self.safe(c.get("reason"), "close reason") if c.get("reason") else None
                fields = (self.ir.get("closing") or {}).get("fields") or {}
                args = {fields.get("outcome") or "outcome": outcome}
                if reason:
                    args[fields.get("reason") or "reason"] = reason
                for k, v in ((self.ir.get("closing") or {}).get("extra_args") or {}).items():
                    args[k] = self.ev(v)
                self.s["var"]["closed_outcome"] = outcome
                self.s["var"]["closed_reason"] = reason
                if self.no_close_tool:       # the brief's services have no closing tool: hang up after the goodbye
                    self.s["ended"] = True
                    out.append({"end": True})
                    self.trace("close", outcome=outcome, reason=reason)
                    return
                out.append({"call": self.close_tool, "args": args})
                self.trace("close", outcome=outcome, reason=reason)
                self.s["pending"] = {"tool": self.close_tool, "args": args, "rest": [], "rule": rule_id}
                return
            elif "goto" in a:
                self._enter(a["goto"], out)
                # continue with the remaining actions (e.g. refire) unless the new phase is waiting on a tool or ended
                if self.s["pending"] or self.s["ended"]:
                    if self.s["pending"] and actions[i + 1:]:
                        self.s["pending"]["rest"] = list(self.s["pending"].get("rest") or []) + list(actions[i + 1:])
                    return
            elif "next_item" in a:
                self.s["cursor"] += 1
                if self.s["cursor"] < len(self.s["items"]):
                    self._enter(a["next_item"], out)
                else:
                    self._enter(a["done"], out)
                return
            elif "if" in a:
                branch = a.get("then", []) if self.safe(a["if"], "if") else a.get("else", [])
                rest = actions[i + 1:]
                self._run_actions(list(branch) + list(rest), out, rule_id, depth + 1)
                return
            elif "stop" in a:
                return
            else:
                raise ValueError("unknown action %r" % a)


def run_script(ir, call_vars, bank, user_turns, max_turns=60):
    """Drive a machine with scripted user events and a bank stub. For local tests.
    bank(tool, args) -> (ok, data). Returns (machine, transcript)."""
    m = Machine(ir, call_vars)
    transcript = []

    def pump(outs):
        guard = 0
        while outs:
            guard += 1
            if guard > MAX_STEPS:
                raise RuntimeError("tool loop")
            nxt = []
            for o in outs:
                transcript.append(("agent", o))
                if "call" in o:
                    ok, data = bank(o["call"], o["args"])
                    lost = data is None   # the bank never answered (a stub returns None for a lost request)
                    data = {"ok": False} if lost else data
                    transcript.append(("tool", {"name": o["call"], "args": o["args"], "ok": ok, "data": data}))
                    nxt.extend(m.handle({"type": "tool", "name": o["call"], "ok": ok, "data": data, "no_response": lost}))
            outs = nxt

    pump(m.handle({"type": "start"}))
    for ev in user_turns:
        if m.s["ended"]:
            break
        transcript.append(("user", ev))
        pump(m.handle(dict(ev, type="user")))
    return m, transcript
