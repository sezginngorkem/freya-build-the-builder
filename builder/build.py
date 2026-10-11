"""The builder: one command, brief in, Freya phone agent out.

    python builder/build.py BRIEF [BRIEF2 ...] OPENAPI.json [--slot NAME] [--no-deploy] [--smoke]

Steps (each logged to the trace):
  1 read     brief + OpenAPI -> PolicyIR (reader: stage 0, rule inventory, compile, static validation + repair)
  2 compile  PolicyIR -> Freya workflow (C2: fixed interpreter graph, engine + IR in the code nodes)
  3 check    static validation again; emulator dry run of the compiled graph (no bank, start event only)
  4 deploy   save + publish on Freya (same slot updates the same workflow), export to submission/<slot>.workflow.json
  5 smoke    optional: one short chat turn on Freya to prove the agent starts
The trace (traces/<slot>.log) holds start/end time, every model call (model + purpose), what was created on
Freya (workflow id, agent id, nodes, tools) and every test with its result. No API keys are written anywhere.
"""
import argparse, json, os, sys, time, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(ROOT, "kit", "build-the-builder")
sys.path.insert(0, HERE); sys.path.insert(0, KIT)

from reader import read as R, llm
from reader.validate import validate
from compiler import c2


class Trace(object):
    def __init__(self, path):
        self.path = path
        self.lines = []
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def log(self, *parts):
        line = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), " ".join(str(p) for p in parts))
        self.lines.append(line)
        print(line, flush=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def _retry(fn, what, tr, attempts=4):
    """Freya calls with back-off: the platform answered 503/504 at times; a lost save means no agent."""
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            tr.log("%s: attempt %d failed: %s" % (what, i + 1, str(e)[:200]))
            if i == attempts - 1:
                raise
            time.sleep(10 * (i + 1))


def classify_inputs(inputs):
    """The brief may come as one file, several files or a folder of raw material (an email, a policy extract, a memo,
    a code list). Folders are opened; the OpenAPI file is recognised by its content (an 'openapi' / 'paths' JSON
    object), not by its extension, so a JSON code list stays brief material. Returns (brief_files, openapi_files)."""
    files = []
    for p in inputs:
        if os.path.isdir(p):
            for d, _, names in sorted(os.walk(p)):
                files += [os.path.join(d, n) for n in sorted(names) if not n.startswith(".")]
        else:
            files.append(p)
    briefs, api = [], []
    for f in files:
        if f.lower().endswith(".json"):
            try:
                doc = json.load(open(f, encoding="utf-8"))
            except Exception:
                doc = None
            if isinstance(doc, dict) and ("openapi" in doc or "swagger" in doc or "paths" in doc):
                api.append(f)
                continue
        briefs.append(f)
    return briefs, api


TEXT_EXT = (".md", ".markdown", ".txt", ".csv", ".tsv", ".json", ".eml", ".rtf", ".html", ".htm")
MAX_BRIEF_BYTES = 150_000


def prepare_briefs(briefs, work, tr):
    """What a case folder holds is not all brief material: a drawing as PDF (its text is read), program code and images
    (skipped), a very large data file such as a customer table (skipped: it is test data, not a rule). Every skip is
    written to the trace."""
    out = []
    for f in briefs:
        low = f.lower()
        try:
            if low.endswith(".pdf"):
                from pypdf import PdfReader
                text = "\n".join((pg.extract_text() or "") for pg in PdfReader(f).pages).strip()
                if not text:
                    tr.log("skipped %s: a PDF without readable text" % f)
                    continue
                dst = os.path.join(work, os.path.basename(f) + ".txt")
                open(dst, "w", encoding="utf-8").write(text)
                tr.log("read the text of %s (%d characters)" % (f, len(text)))
                out.append(dst)
                continue
            if not low.endswith(TEXT_EXT):
                tr.log("skipped %s: not a text document" % f)
                continue
            if os.path.getsize(f) > MAX_BRIEF_BYTES:
                tr.log("skipped %s: %d bytes, too large to be a brief document (data file)" % (f, os.path.getsize(f)))
                continue
        except Exception as e:
            tr.log("skipped %s: %s" % (f, str(e)[:120]))
            continue
        out.append(f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--slot"); ap.add_argument("--no-deploy", action="store_true"); ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-selftest", action="store_true")
    ap.add_argument("--example", help="optional worked-example PolicyIR"); ap.add_argument("--example-brief", action="append", default=[])
    a = ap.parse_args()
    missing = [x for x in a.inputs if not os.path.exists(x)]
    if missing:
        sys.exit("no such file or folder: %s" % ", ".join(missing))
    briefs, api = classify_inputs(a.inputs)
    if len(api) > 1 or not briefs:
        sys.exit("usage: build.py BRIEF|BRIEF_FOLDER [MORE ...] OPENAPI.json  (found %d OpenAPI files, %d brief files)"
                 % (len(api), len(briefs)))
    first = a.inputs[0].rstrip("/\\")
    slot = a.slot or (os.path.basename(first) if os.path.isdir(first) else os.path.splitext(os.path.basename(briefs[0]))[0])
    out_dir = os.path.join(ROOT, "submission"); os.makedirs(out_dir, exist_ok=True)
    work = os.path.join(HERE, "out", slot); os.makedirs(work, exist_ok=True)
    tr = Trace(os.path.join(ROOT, "traces", slot + ".log"))
    t0 = time.time()
    tr.log("START build slot=%s briefs=%s openapi=%s builder_model=%s" % (slot, [os.path.basename(b) for b in briefs], os.path.basename(api[0]) if api else "(to be written from the documents)", llm.MODEL))

    llm.ON_RECORD = lambda e: tr.log("model call: model=%s backend=%s purpose=%r seconds=%s ok=%s usage=%s%s" % (
        e.get("model"), e.get("backend"), e.get("purpose"), e.get("seconds"), e.get("ok"), e.get("usage"),
        "" if e.get("ok") else " error=%r" % e.get("error")))

    # the 30-minute rule: every model call must be over 27 minutes after the start, which leaves the compile, deploy
    # and export (seconds, with retries) inside 30. Optional steps that cannot finish in time are cut, never the agent.
    llm.DEADLINE = t0 + float(os.environ.get("BUILDER_DEADLINE_MIN", "27")) * 60
    tr.log("deadline: model calls end by %s" % time.strftime("%H:%M:%S", time.localtime(llm.DEADLINE)))
    briefs = prepare_briefs(briefs, work, tr)
    if os.environ.get("BANK_BASE_URL"):
        tr.log("service base address for the agent's tools: %s" % os.environ["BANK_BASE_URL"])
    if not api:
        # the services are described in prose only (no OpenAPI file): write the typed interface from the documents first
        from reader.contract2api import make_openapi
        api = [make_openapi(briefs, os.path.join(work, "openapi.generated.json"))]
        tr.log("no OpenAPI file in the case folder: wrote %s from the service documents" % api[0])

    # the self-test's customers are written from the documents and the IR's interface only: they are written while the
    # IR is being repaired (if a repair changes the interface, they are written again)
    import threading
    early = {}

    def start_cases(ir0, st0, inv0=None):
        if a.no_selftest:
            return
        from selftest.gen import write_cases, interface
        if early.get("by_ir") and id(ir0) in early["by_ir"]:      # written already, to choose among the compiles
            early["cases"], early["interface"] = early["by_ir"][id(ir0)], interface(ir0)
            tr.log("selftest: using the %d customers written to choose the read" % len(early["cases"]))
            return

        def job():
            try:
                early["cases"] = write_cases(ir0, st0, inventory=inv0)
            except Exception as e:
                early["error"] = str(e)[:300]
        early["interface"] = interface(ir0)
        early["thread"] = threading.Thread(target=job, daemon=True)
        early["thread"].start()
        tr.log("selftest: writing test customers while the IR is checked and repaired")

    def select(irs, nprobs, st0, inv0):
        """Choose among independent reads by what they do: test customers are written from the brief's rule units for
        each read's interface (all in parallel), every read runs every set, the most passes wins (CodeT/MBR-exec)."""
        from selftest.gen import write_cases, run_cases
        sets = llm.parallel([(lambda ir=ir: write_cases(ir, st0, inventory=inv0)) for ir in irs])
        sets = [s if isinstance(s, list) else [] for s in sets]
        early["by_ir"] = {id(ir): s for ir, s in zip(irs, sets) if s}
        from sim.mockbank import speaks
        gap = speaks(st0["vocabulary"], [c for s in sets for c in s])
        if gap:
            # the local stand-in bank answers in the practice API's names; with this API's names it would fail a
            # correct read and pass a wrong one, so it may not choose: the read with fewer static problems is kept
            early["bank_gap"] = gap
            tr.log("select: the local test bank does not speak this API (%s): reads chosen by static checks only" % gap[:6])
            return min(range(len(irs)), key=lambda k: (nprobs[k], k))
        scores = []
        for k, ir in enumerate(irs):
            got = tot = 0
            for s in sets:
                if s:
                    res = run_cases(ir, s)
                    got += sum(r["pass"] for r in res); tot += len(res)
            scores.append((got, -nprobs[k], -k))
            tr.log("select: read #%d passes %d/%d test customers (static problems %d)" % (k + 1, got, tot, nprobs[k]))
        return max(range(len(irs)), key=lambda k: scores[k])

    # 1 read (retried once as a whole: a failed read means no agent at all)
    for attempt in (1, 2):
        try:
            ir, st, inv = R.read(briefs, api[0], a.example, a.example_brief, log=lambda m: tr.log("read:", m),
                                 on_compiled=start_cases, select=None if a.no_selftest else select)
            break
        except Exception as e:
            tr.log("read: FAILED attempt %d: %s" % (attempt, str(e)[:300]))
            if attempt == 2:
                raise
    json.dump(ir, open(os.path.join(work, "policy_ir.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(inv, open(os.path.join(work, "inventory.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    tr.log("read: IR rules=%d templates=%d intents=%d phases=%d amendments=%d ambiguities=%d" % (
        len(ir.get("rules", [])), len(ir.get("templates", {})), len(ir.get("intents", [])), len(c2.phases_of(ir)),
        len(inv.get("amendments", [])), len(ir.get("ambiguities", []))))

    # 1b self-test: test customers written from the brief (not from the IR), local runs, referee, repair
    if not a.no_selftest:
        from sim.mockbank import speaks
        gap = early.get("bank_gap") or speaks(st["vocabulary"])
    if not a.no_selftest and gap:
        tr.log("selftest: skipped -- the local test bank does not speak this API (%s); it would steer the read towards "
               "the practice API's names" % gap[:6])
    elif not a.no_selftest:
        from selftest.gen import selftest, interface
        cases = None
        if early.get("cases") and early.get("thread") is None:      # written to choose among the reads
            cases = early["cases"] if interface(ir) == early.get("interface") else None
            if cases is None:
                tr.log("selftest: the read's interface changed in a repair: writing its customers again")
        elif early.get("thread") is not None:
            left = llm.time_left()
            early["thread"].join(timeout=max(0, left) if left is not None else None)
            if early.get("cases") and interface(ir) == early.get("interface"):
                cases = early["cases"]
            else:
                tr.log("selftest: early customers not usable (%s): writing them now" % (
                    early.get("error") or ("interface changed by a repair" if early.get("cases") else "not ready")))
        try:
            ir, rep = selftest(ir, st, log=lambda m: tr.log(m), cases=cases, inventory=inv)
            json.dump(rep, open(os.path.join(work, "selftest.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            json.dump(ir, open(os.path.join(work, "policy_ir.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        except Exception as e:
            tr.log("selftest: FAILED %s" % str(e)[:300])

    # 2 compile
    wf = c2.compile_workflow(ir, st["vocabulary"], name=slot)
    json.dump(wf, open(os.path.join(work, "workflow.json"), "w", encoding="utf-8"), indent=1)
    code_len = len(wf["nodes"]["brain"]["pre_actions"][0]["function"]["parameters"]["properties"]["code"]["default"])
    tr.log("compile: nodes=%d code_node_bytes=%d tools=%s" % (len(wf["nodes"]), code_len, sorted(k[4:] for k in wf["nodes"] if k.startswith("api_"))))

    # 3 check
    probs = [p for p in validate(ir, st["vocabulary"], st["sentences"]) if not p.startswith("WARN")]
    tr.log("check: static validation problems=%d %s" % (len(probs), probs[:5]))
    try:
        from engine.machine import Machine
        call_vars = {"customer_id": "c_probe", "first_name": "Alex", "last_name": "Morgan", "title": "Mr", "now": "2026-10-14T11:00"}
        m = Machine(ir, call_vars)
        outs = m.handle({"type": "start"})
        tr.log("check: start probe ok, first line=%r" % (" ".join(o.get("say", "") for o in outs)[:160],))
    except Exception as e:
        tr.log("check: start probe FAILED %s" % e)
    if code_len > 120000:
        tr.log("check: WARNING code node close to Freya's 131072-byte limit")

    # 4 deploy + export
    ids = {}
    if not a.no_deploy:
        import freya
        ids = _retry(lambda: freya.save_workflow(slot, wf, state_file=os.path.join(HERE, ".freya-agents.json")), "save", tr)
        tr.log("deploy: workflow_id=%s agent_id=%s version=%s" % (ids.get("workflow_id"), ids.get("agent_id"), ids.get("version")))
        path = _retry(lambda: freya.export_workflow(ids["workflow_id"], os.path.join(out_dir, slot + ".workflow.json")), "export", tr)
        tr.log("export: %s" % os.path.relpath(path, ROOT))
        # 5 smoke
        if a.smoke:
            try:
                r = freya.api("POST", "/api/v2/chat/message", {"workflowId": ids["workflow_id"], "message": "Hello?",
                                                              "customerVariables": {"customer_id": "c_probe", "now": "2026-10-14T11:00", "first_name": "Alex", "last_name": "Morgan", "title": "Mr"}})
                r2 = freya.api("POST", "/api/v2/chat/message", {"callId": r["callId"], "message": "Hello?",
                                                               "customerVariables": {"customer_id": "c_probe", "now": "2026-10-14T11:00", "first_name": "Alex", "last_name": "Morgan", "title": "Mr"}})
                freya.api("POST", "/api/v2/chat/end", {"callId": r["callId"]})
                tr.log("smoke: chat ok, agent said %r" % (r2.get("response") or "")[:160])
            except Exception as e:
                tr.log("smoke: FAILED %s" % str(e)[:200])

    tr.log("model calls: %d (each logged when it happened)" % len(llm.TRACE))
    tr.log("END build slot=%s seconds=%.0f" % (slot, time.time() - t0))


if __name__ == "__main__":
    main()
