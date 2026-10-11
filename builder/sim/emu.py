"""Minimal local emulator of a compiled Freya workflow (C2 graph). It executes the real code-node strings,
the api pre/post hooks and the transitions; extraction is replaced by the scripted turns (intents -> i_* booleans,
slots -> s_* raw strings). Purpose: test compiler + glue offline before spending Freya credits.

    python sim/emu.py out/wf_a.json --brief A
"""
import argparse, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from sim.mockbank import MockBank
from sim import run_local as R
from score import score_ledger


def subst(text, vars):
    return re.sub(r"\{\{([^{}]+)\}\}", lambda m: str(vars.get(m.group(1).split(":")[0].strip(), "{{%s}}" % m.group(1))), text)


def cond_ok(c, vars, node_turns):
    if not c:
        return False
    if c.get("operator") == "always":
        return True
    if "conditions" in c:
        res = [cond_ok(x, vars, node_turns) for x in c["conditions"]]
        return any(res) if c.get("logic", "or") == "or" else all(res)
    var, op, operand = c.get("variable"), c.get("operator"), c.get("operand")
    val = node_turns.get(var, vars.get(var))
    if op == "equals":
        return val is not None and str(val) == str(operand)
    if op == "not_equals":
        return str(val) != str(operand)
    if op == "greater_than":
        try:
            return float(val) > float(operand)
        except (TypeError, ValueError):
            return False
    if op == "is_set":
        return val not in (None, "")
    return False


def route(node, vars, node_turns):
    for t in node.get("transitions", []):
        if cond_ok(t.get("condition"), vars, node_turns):
            return t["target_node"]
    return node.get("passthrough_default_transition")


def run_case(wf, case, verbose=False, perturb=None, sandbox_down=None):
    bank = MockBank(case)
    vars = dict(wf.get("test_variables") or {})
    vars.update(case["variables"]); vars["customer_id"] = "c_" + case["id"]
    script = [dict(R.U(t.get("intents"), t.get("text", ""), **(t.get("slots") or {})), **{k: t[k] for k in ("act", "reply", "reply_words", "finished") if t.get(k)})
              for t in case["sim_script"]] if case.get("sim_script") else R.SCRIPTS.get(case["id"], [])
    script = script + [R.U(["no"], "No, that's all, thank you."), R.U(["no"], "Goodbye.")]
    nodes = wf["nodes"]
    cur, steps, turn_i, log = wf["initial_node"], 0, 0, []
    node_turns = {}
    while steps < 400:
        steps += 1
        n = nodes[cur]
        t = n["node_type"]
        if t in ("code", "api_request") and sandbox_down is not None and sandbox_down(steps, cur):
            # Freya could not run/parse the code step: variables stay as they were, Freya counts the failure
            vars[cur + "_failure_count"] = int(vars.get(cur + "_failure_count") or 0) + 1
            log.append(("SANDBOX_FAIL", cur))
            cur = route(n, vars, node_turns)
            continue
        if t == "code":
            code = n["pre_actions"][0]["function"]["parameters"]["properties"]["code"]["default"]
            # Freya runs the snippet inside a function body: emulate that so local-vs-global bugs show up here
            wrapped = "def __user_main__(vars):\n" + "\n".join("    " + ln for ln in code.splitlines()) + "\n"
            g = {"__name__": "freya_code"}
            exec(wrapped, g)
            before = dict(vars)
            g["__user_main__"](vars)
            if any(isinstance(v, str) and "__CODE_EXEC_RESULT__" in v for v in vars.values()):
                # Freya parses the output after the LAST result marker: a variable holding it makes the step fail
                vars.clear(); vars.update(before)
                vars[cur + "_failure_count"] = int(vars.get(cur + "_failure_count") or 0) + 1
                log.append(("SANDBOX_FAIL", cur, "poisoned output"))
                cur = route(n, vars, node_turns)
                continue
            # Freya keeps a boolean variable's old value when code writes "" into it: emulate that
            for k, v in list(vars.items()):
                if k.startswith("i_") and v == "" and before.get(k) not in (None, ""):
                    vars[k] = before[k]
            if vars.get("_error"):
                log.append(("ERROR", vars["_error"])); print("\n".join(str(x) for x in log[-6:])); raise RuntimeError("code node error")
            cur = route(n, vars, node_turns)
        elif t == "api_request":
            fn = n["pre_actions"][0]
            props = fn["function"]["parameters"]["properties"]
            body = {k: subst(v.get("default", ""), vars) for k, v in props["body"]["properties"].items()}
            config = {"url": props["url"]["default"], "method": props["method"]["default"], "body": body}
            exec(fn.get("pre_process_code") or "", {"vars": vars, "config": config})
            tool = fn["function"]["name"]
            ok, data = bank(tool, config["body"])
            result = {"status": "success" if ok else "error", "data": data if ok else None, "status_code": 200 if ok else 500, "header": {}}
            if not ok:   # as Freya reports it: the bank's own error body, or a gateway's HTML page when it never answered
                result["message"] = ("API request failed: <!DOCTYPE html><html>502</html>" if data is None
                                     else "API request failed: %r" % (data,))
            exec(fn.get("post_process_code") or "", {"vars": vars, "result": result})
            log.append(("TOOL", tool, config["body"], data))
            cur = route(n, vars, node_turns)
        elif t == "conversation":
            ent = n.get("on_enter") or {}
            if ent.get("type") == "tts":
                txt = subst(ent.get("text", ""), vars)
            else:
                txt = "[LLM] " + subst(ent.get("prompt", ""), vars)
            if txt.strip():
                log.append(("AGENT", txt))
            if n.get("passthrough"):
                cur = route(n, vars, node_turns)
                continue
            if turn_i >= len(script):
                log.append(("END", "script exhausted")); break
            u = script[turn_i]; turn_i += 1
            log.append(("USER", u["text"], u["intents"], u["slots"]))
            for f in n.get("extraction_schema", []):
                nm = f["name"]
                if nm.startswith("i_"):
                    vars[nm] = "true" if nm[2:] in u["intents"] else "false"
                elif nm == "s__utterance":
                    vars[nm] = u.get("text", "")
                elif nm == "s__reply":
                    ints = set(u["intents"])
                    vars[nm] = u.get("reply") or ("answer" if any(v not in (None, "") for v in u["slots"].values()) or ints & {"yes", "confirm_identity"}
                                                  else "non_answer" if ints & {"no", "decline", "not_want_talk"}
                                                  else "question" if ints & {"ask_bot", "ask_scam", "ask_reason", "other_question"}
                                                  else "none")
                elif nm == "s__finished":
                    vars[nm] = u.get("finished") or ("no" if str(u.get("text", "")).rstrip().endswith(("...", "…")) else "yes")
                elif nm == "s__reply_words":
                    vars[nm] = u.get("reply_words") or (u.get("text", "") if set(u["intents"]) & {"no", "decline", "not_want_talk"} else "")
                elif nm == "s__act":
                    # the extractor's act, as measured on Freya (2026-10-11): a turn that changes the topic (paid,
                    # lost job, disputes) is 'inform'; a turn that only gives values is 'answer'
                    # the act Freya's extractor gives, as measured (2026-10-11): refusals 'refuse', topic changes
                    # 'inform', side questions 'question', values 'answer', chatter 'other'
                    ints = set(u["intents"])
                    topic = [i for i in ints if i not in ("yes", "no", "decline", "not_want_talk", "confirm_identity", "ask_bot", "ask_scam", "ask_reason", "other_question")]
                    vars[nm] = u.get("act") or ("inform" if topic else "refuse" if ints & {"no", "decline", "not_want_talk"}
                                                else "answer" if any(v not in (None, "") for v in u["slots"].values()) or ints & {"yes", "confirm_identity"}
                                                else "question" if ints & {"ask_bot", "ask_scam", "ask_reason", "other_question"} else "other")
                elif nm.startswith("s_"):
                    v = u["slots"].get(nm[2:])
                    vars[nm] = "" if v is None else str(v)
            if perturb is not None:      # E2: other representations of the same extracted values
                for f in n.get("extraction_schema", []):
                    vars[f["name"]] = perturb(f["name"], vars.get(f["name"]))
            node_turns[cur + ".current_turns"] = 1
            nxt = route(n, vars, node_turns)
            node_turns[cur + ".current_turns"] = 0
            cur = nxt
        elif t == "end_call":
            log.append(("END", "end node")); break
    res = score_ledger(case, bank.ledger)
    try:   # words the spec restricts in time, said too early (engine trace kept in the state)
        raw = str(vars.get("_st") or "{}")
        if raw.startswith("z:"):
            import base64, zlib
            raw = zlib.decompress(base64.b64decode(raw[2:])).decode("utf-8")
        viol = (json.loads(raw).get("var") or {}).get("_violations") or []
    except Exception:
        viol = []
    if viol:
        res["pass"] = False
        res["failed"] = list(res.get("failed") or []) + ["restricted word: " + v for v in viol]
    if verbose or not res["pass"]:
        for x in log:
            print("    ", x[0], ":", " | ".join(str(y) for y in x[1:])[:240])
    return res, bank.ledger


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wf"); ap.add_argument("--brief", default="A"); ap.add_argument("--only"); ap.add_argument("-v", action="store_true")
    ap.add_argument("--cases", default=os.path.join(R.KIT, "public-test-set.json"))
    a = ap.parse_args()
    wf = json.load(open(a.wf, encoding="utf-8"))
    cases = [c for c in json.load(open(a.cases, encoding="utf-8")) if (a.brief == "*" or c["brief"] == a.brief) and (not a.only or c["id"] in a.only.split(","))]
    n = 0
    for c in cases:
        try:
            res, led = run_case(wf, c, a.v)
        except Exception as e:
            import traceback; traceback.print_exc(limit=3)
            res, led = {"pass": False, "failed": ["crash: %s" % e]}, {"calls": []}
        n += res["pass"]
        print(("PASS" if res["pass"] else "FAIL"), c["id"], c["family"], "|", " > ".join(x["tool"] for x in led["calls"]))
        for f in res["failed"]:
            print("       -", f)
    print("\n%d / %d passed in the emulator (ledger checks)" % (n, len(cases)))


if __name__ == "__main__":
    main()
