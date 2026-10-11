"""Stress test of the decision chain with random customers and brief-independent invariants (no model calls).

Scripted tests only check the paths someone thought of. Here a random customer talks to every IR: at each turn it either
follows the case script or says random things the CURRENT phase listens to (exactly what Freya's extractor could report
there: random intents, random values for the listened slots, right/wrong/partial identity answers, side questions, topic
changes), and bank tools fail at random. Nobody knows the expected ledger of such a call, so we check properties that
must hold for ANY brief:

  crash            the engine raises
  rule_error       a rule condition raised and was skipped (a hidden bug in the IR or the engine)
  expr_error       an action/template expression raised (contained by the engine, but the IR did not foresee this state)
  render_none      a spoken sentence had a hole: a placeholder had no value
  silent           the customer spoke, the call is not over, and the agent said nothing
  close_once       the closing tool is called exactly once and last; nothing after it
  hangup_silent    the call was closed without any goodbye/explanation in that turn
  account_early    get_account before identity was verified
  amount_early     a money amount spoken before identity was verified
  promise_no_yes   create_promise without an explicit yes in that customer turn
  promise_date     a promise dated in the past or on a non-business day
  promise_amount   a promise above the product's largest amount field, or <= 0
  promise_twice    two successful promises for one product
  outcome_enum     close outcome/reason not allowed by the OpenAPI
  outcome_honest   outcome 'promise' without a recorded promise (or a recorded promise but outcome no_promise/refused...)
  stuck            the customer answered and the agent repeated the exact same words 3 turns in a row
  state_size       the persisted state grew beyond 60 KB (Freya variables)

Differential mode (--diff N): the same realised conversation is replayed through the COMPILED Freya workflow (emulator,
real glue + code node); any difference in tool calls or outcome is a seam bug between engine and Freya layer.

    python sim/fuzz.py [--runs 20] [--diff 1] [--only s6] [--seed 1]
"""
import argparse, collections, contextlib, copy, datetime as _dt, io, json, os, random, re, sys, time, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from engine.machine import Machine, SIDE, POLARITY
from compiler import c2
from reader.stage0 import parse_openapi
from sim.mockbank import MockBank
from sim import styles as S
from sim import gate as G

MONEY = re.compile(r"(\$|£|€)\s?\d|\b\d+\.\d{2}\b|\b\d[\d,]*\s?(dollars|pounds|euros)\b", re.I)
CLOSE = "close_call"


class FlakyBank(object):
    """MockBank wrapper: each tool call (except close) fails with probability p, as transport error or ok=false."""
    def __init__(self, case, rng, p):
        self.bank = MockBank(case)
        self.rng, self.p = rng, p

    def __call__(self, tool, args):
        if tool != CLOSE and self.rng.random() < self.p:
            if self.rng.random() < 0.5:
                return False, {"ok": False, "error": "500"}
            return True, {"ok": False, "error": "service failed"}
        return self.bank(tool, args)


def _listen(cfg, phase):
    return set(cfg["intents_by_phase"].get(phase, [])), list(cfg["slots_by_phase"].get(phase, []))


def _rand_value(rng, kind, slot, case, today):
    ident = case.get("identity") or {}
    prods = case.get("products") or [{}]
    nums = [float(v) for p in prods for k, v in p.items() if isinstance(v, (int, float)) and not isinstance(v, bool)
            and not re.search(r"day|dpd|late|count|broken", k)]
    if slot.startswith("id_"):
        true = str(ident.get(slot[3:], ""))
        if kind == "birth_date" and true:
            d = _dt.date.fromisoformat(true)
            other = (d - _dt.timedelta(days=rng.randint(1, 4000))).isoformat()
            swapped = _dt.date(d.year, d.day, d.month).isoformat() if d.day <= 12 else other
            return rng.choice([true, true, true, other, swapped])
        if true:
            # what the glue can deliver: a complete number (right or wrong); a part is held back by the glue
            wrong = "".join(str(rng.randint(0, 9)) for _ in true)
            return rng.choice([true, true, true, wrong])
        return str(rng.randint(1000, 9999))
    if kind == "date":
        return (today + _dt.timedelta(days=rng.randint(-3, 45))).isoformat()
    if kind == "amount":
        full = max(nums) if nums else 500.0
        floor = min(nums) if nums else 50.0
        return rng.choice([full, floor, round(floor - 1, 2), full + 100, round(full / 2, 2), 1.0, round(floor * 0.5, 2)])
    if kind == "time":
        return "%02d:%02d" % (rng.randint(7, 21), rng.choice([0, 15, 30, 45]))
    if kind == "digits":
        return "".join(str(rng.randint(0, 9)) for _ in range(rng.randint(3, 8)))
    words = [str(v) for p in prods for k, v in p.items() if isinstance(v, str)] + ["the other one", "that"]
    return rng.choice(words)


PROFILES = ["cooperative", "mixed", "chaotic", "late_chaos"]


def _p_random(profile, turn, switch):
    """How often the customer says something random instead of following the script, by customer profile. Measured:
    a single high rate leaves the deep phases (read-back, promise) almost untested (6% of calls reached a promise)."""
    if profile == "cooperative":
        return 0.1
    if profile == "mixed":
        return 0.3
    if profile == "chaotic":
        return 0.6
    return 0.03 if turn < switch else 0.65          # late_chaos: behave, then go off the rails deep in the call


def realise(ir, cfg, case, rng, p_random=None, max_turns=24, p_fail=0.08, profile=None):
    """Drive the engine with an adaptive random customer. Returns (machine, transcript, events) where events are the
    customer turns actually heard (after Freya-like filtering), replayable through the emulator."""
    spec = ir.get("slots") or {}
    call_vars = dict(case["variables"]); call_vars.setdefault("customer_id", "c_" + case["id"])
    m = Machine(ir, call_vars)
    today = _dt.date.fromisoformat(m.s["today"])
    bank = FlakyBank(case, rng, p_fail)
    tr, events = [], []
    script = list(case.get("sim_script") or [])

    def pump(outs):
        guard = 0
        while outs:
            guard += 1
            if guard > 200:
                raise RuntimeError("tool loop")
            nxt = []
            for o in outs:
                tr.append(("agent", o))
                if "call" in o:
                    ok, data = bank(o["call"], o["args"])
                    tr.append(("tool", {"name": o["call"], "args": o["args"], "ok": ok, "data": data}))
                    nxt.extend(m.handle({"type": "tool", "name": o["call"], "ok": ok, "data": data}))
            outs = nxt

    pump(m.handle({"type": "start"}))
    si = 0
    profile = profile or rng.choice(PROFILES)
    switch = rng.randint(3, 9)
    for turn in range(max_turns):
        if m.s["ended"]:
            break
        li, ls = _listen(cfg, m.s["phase"])
        pr = p_random if p_random is not None else _p_random(profile, turn, switch)
        if si < len(script) and rng.random() > pr:
            t = script[si]; si += 1
            ev = {"text": t.get("text", ""), "intents": list(t.get("intents") or []), "slots": dict(t.get("slots") or {})}
        else:
            pool = sorted(li)
            k = rng.choice([0, 1, 1, 1, 2])
            ints = rng.sample(pool, min(k, len(pool))) if pool else []
            slots = {}
            for sn in ls:
                if rng.random() < 0.35:
                    slots[sn] = _rand_value(rng, (spec.get(sn) or {}).get("kind", "text"), sn, case, today)
            ev = {"text": "(random)", "intents": ints, "slots": slots}
        ev["intents"] = [i for i in ev["intents"] if i in li]           # Freya only hears what the phase listens to
        ev["slots"] = {k: v for k, v in ev["slots"].items() if k in ls and v not in (None, "")}
        ev["act"] = "answer" if ev["slots"] else rng.choice(["other", "refuse", "question", "inform", "request", "answer"])
        events.append(ev)
        tr.append(("user", ev))
        pump(m.handle(dict(ev, type="user")))
    for polite in ({"text": "No, that's all.", "intents": ["no"], "slots": {}, "act": "refuse"},
                   {"text": "Goodbye.", "intents": ["no"], "slots": {}, "act": "other"}):
        if m.s["ended"]:
            break
        li, _ = _listen(cfg, m.s["phase"])
        ev = dict(polite, intents=[i for i in polite["intents"] if i in li], polite=True)
        events.append(ev); tr.append(("user", ev))
        pump(m.handle(dict(ev, type="user")))
    return m, tr, events, bank


def check(ir, voc, case, m, tr):
    """Brief-independent invariants. Returns a list of (name, detail)."""
    v = []
    outcome_enum = set((voc["tools"].get(CLOSE, {}).get("args", {}).get("outcome") or {}).get("enum") or [])
    verified, closes, after_close, promises = False, 0, False, collections.Counter()
    ok_promise = False
    last_user, turn_says, repeats, last_words = None, [], 0, None
    products = {}
    turn_has_say, saw_user = False, False
    for who, x in tr:
        if who == "user":
            if saw_user and not m.s["ended"] and not turn_has_say and last_user is not None:
                pass
            if saw_user and not turn_has_say:
                v.append(("silent", "after %r" % (last_user.get("intents"), )))
            words = " ".join(turn_says)
            if last_user is not None and (last_user.get("slots") or set(last_user.get("intents") or []) & set(POLARITY)):
                repeats = repeats + 1 if words and words == last_words else 0
                if repeats >= 2:
                    v.append(("stuck", words[:120]))
            last_words, turn_says, turn_has_say = words, [], False
            last_user, saw_user = x, True
            continue
        if who == "agent":
            if "say" in x or "instruct" in x:
                turn_has_say = True
                turn_says.append(x.get("say") or x.get("instruct") or "")
                if not verified and MONEY.search(x.get("say") or ""):
                    v.append(("amount_early", (x.get("say") or "")[:120]))
            if "call" in x and closes:
                after_close = True
            continue
        name, data = x["name"], x.get("data") or {}
        ok = x.get("ok") and data.get("ok", True)
        if name == "verify_identity" and ok and data.get("all_verified"):
            verified = True
        if name == "get_account":
            if not verified:
                v.append(("account_early", ""))
            if ok:
                for p in data.get("products") or []:
                    products[p.get("product_id")] = p
        if name == "create_promise":
            if not last_user or "yes" not in (last_user.get("intents") or []):
                v.append(("promise_no_yes", "user said %r" % ((last_user or {}).get("intents"),)))
            a = x["args"]
            try:
                d = _dt.date.fromisoformat(str(a.get("date"))[:10])
                if d < _dt.date.fromisoformat(m.s["today"]) or not m.funcs["is_business_day"](d.isoformat()):
                    v.append(("promise_date", str(a.get("date"))))
            except Exception:
                v.append(("promise_date", "unreadable %r" % a.get("date")))
            p = products.get(a.get("product_id")) or {}
            nums = [float(val) for k, val in p.items() if isinstance(val, (int, float)) and not isinstance(val, bool)
                    and not re.search(r"day|dpd|late|count|broken", k)]
            try:
                amt = float(a.get("amount"))
                if amt <= 0 or (nums and amt > max(nums) + 0.005):
                    v.append(("promise_amount", "%s of %s" % (amt, max(nums) if nums else "?")))
            except Exception:
                v.append(("promise_amount", "unreadable %r" % a.get("amount")))
            if ok:
                ok_promise = True
                promises[a.get("product_id")] += 1
                if promises[a.get("product_id")] > 1:
                    v.append(("promise_twice", str(a.get("product_id"))))
        if name == CLOSE:
            closes += 1
            out_, reason = x["args"].get("outcome"), x["args"].get("reason")
            if outcome_enum and out_ not in outcome_enum:
                v.append(("outcome_enum", "%r" % out_))
            if out_ == "promise" and not ok_promise:
                v.append(("outcome_honest", "promise without a recorded promise"))
            if ok_promise and out_ in ("no_promise", "not_verified", "not_reached"):
                v.append(("outcome_honest", "recorded promise but outcome %s/%s" % (out_, reason)))
            if not turn_has_say:
                v.append(("hangup_silent", ""))
    if closes > 1:
        v.append(("close_once", "%d closes" % closes))
    if after_close:
        v.append(("close_once", "tool call after close"))
    if m.s["ended"] and closes == 0:
        v.append(("close_once", "ended without close"))
    for kind in ("rule_error", "expr_error", "render_none"):
        errs = [t for t in m.s["trace"] if t.get("kind") == kind]
        if errs:
            e = errs[0]
            v.append((kind, "%s %s: %s" % (e.get("rule") or e.get("where") or "", e.get("expr", ""), e.get("error", "")[:100])))
    size = len(json.dumps(m.s))
    if size > 60000:
        v.append(("state_size", str(size)))
    return v


def differential(ir, voc, wf, case, events, m, tr):
    """Replay the realised customer turns through the compiled workflow; compare tool calls and outcome."""
    from sim import emu
    c = copy.deepcopy(case)
    c["sim_script"] = [dict(e) for e in events if not e.get("polite")]   # the emulator adds its own polite closing turns
    eng_calls = [(x["name"], json.dumps(x["args"], sort_keys=True)) for w, x in tr if w == "tool"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            res, led = emu.run_case(wf, c, verbose=False)
    except Exception as e:
        return [("diff_crash", str(e)[:200])]
    emu_calls = [(x["tool"], json.dumps(x["args"], sort_keys=True)) for x in led["calls"]]
    if eng_calls != emu_calls:
        for i, (a, b) in enumerate(zip(eng_calls + [None] * 9, emu_calls + [None] * 9)):
            if a != b:
                return [("diff_calls", "first difference at call %d: engine %s / freya %s" % (i, a, b))]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=20); ap.add_argument("--diff", type=int, default=0)
    ap.add_argument("--only"); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--fail", type=float, default=0.08)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "fuzz_report.json"))
    a = ap.parse_args()
    t0 = time.time()
    found = collections.defaultdict(list)
    n_runs = 0
    seen_ir = set()
    for ir_path, cases_path, brief, api in G.SUITES:
        if a.only and a.only not in ir_path:
            continue
        if cases_path == G.REPLAYS or not os.path.exists(os.path.join(ROOT, ir_path)):
            continue
        key = ir_path
        if key in seen_ir:
            continue
        seen_ir.add(key)
        ir = json.load(open(os.path.join(ROOT, ir_path), encoding="utf-8"))
        voc = parse_openapi(api)
        _, cfg = c2.phase_cfg(ir)
        wf = c2.compile_workflow(ir, voc) if a.diff else None
        cases = S.load_cases(ir, cases_path, brief)
        for c in cases:
            for k in range(a.runs):
                # stable across processes (hash() of str is randomised per process: ablation runs saw different customers)
                seed = zlib.crc32(("%s|%s|%s|%s" % (a.seed, ir_path.replace("\\", "/"), c["id"], k)).encode())
                rng = random.Random(seed)
                n_runs += 1
                try:
                    m, tr, events, bank = realise(ir, cfg, c, rng, p_fail=a.fail)
                except Exception as e:
                    found["crash"].append({"ir": ir_path, "case": c["id"], "seed": seed, "detail": str(e)[:200]})
                    continue
                for name, detail in check(ir, voc, c, m, tr):
                    found[name].append({"ir": ir_path, "case": c["id"], "seed": seed, "detail": detail})
                if a.diff and k < a.diff and a.fail == 0:
                    for name, detail in differential(ir, voc, wf, c, events, m, tr):
                        found[name].append({"ir": ir_path, "case": c["id"], "seed": seed, "detail": detail})
    print("fuzz: %d random calls over %d IRs in %.0f s" % (n_runs, len(seen_ir), time.time() - t0))
    for name in sorted(found, key=lambda n: -len(found[n])):
        lst = found[name]
        irs = collections.Counter(x["ir"] for x in lst)
        print("  %-15s %5d  in %d IRs  e.g. %s %s: %s" % (name, len(lst), len(irs), lst[0]["ir"], lst[0]["case"], lst[0]["detail"][:110]))
    if not found:
        print("  no invariant violated")
    json.dump(found, open(a.out, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
