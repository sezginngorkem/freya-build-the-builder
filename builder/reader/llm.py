"""Model calls for the builder, with a trace entry per call.

Backends, in order:
  1. ANTHROPIC_API_KEY set  -> Anthropic Messages API (pip install anthropic)
  2. otherwise              -> the `claude` CLI in print mode (uses the local Claude login)
Model: BUILDER_MODEL env var, default claude-opus-5-5.
"""
import json, os, re, subprocess, tempfile, threading, time

MODEL = os.environ.get("BUILDER_MODEL", "claude-opus-5-5")
TRACE = []                 # appended by every call; the builder writes it to the trace file
_lock = threading.Lock()


ON_RECORD = None           # set by the builder: called for every model call as it happens (trace written live)
DEADLINE = None            # set by the builder: wall-clock time by which every model call must be over (30-minute rule)


def time_left():
    """Seconds left before the builder's deadline (None: no deadline)."""
    return None if DEADLINE is None else DEADLINE - time.time()


def _record(entry):
    with _lock:
        TRACE.append(entry)
    if ON_RECORD is not None:
        try:
            ON_RECORD(entry)
        except Exception:
            pass


def _api_call(system, prompt, model, max_tokens):
    import anthropic
    client = anthropic.Anthropic()
    out = []
    with client.messages.stream(model=model, max_tokens=max_tokens, system=system,
                                messages=[{"role": "user", "content": prompt}]) as s:
        for text in s.text_stream:
            out.append(text)
        final = s.get_final_message()
    u = final.usage
    return "".join(out), {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens}


# The CLI runs isolated: inside an empty folder of this project, no tools (cannot read or run anything),
# no MCP servers, no user/project settings or memory, no saved session, no access to other conversations.
SANDBOX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".llm-sandbox")
CLI_FLAGS = ["--max-turns", "1", "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
             "--setting-sources", "", "--no-session-persistence", "--exclude-dynamic-system-prompt-sections"]


class Transient(RuntimeError):
    """The machine, not the model, failed the call (no memory, no process slot): worth waiting and trying again."""


# Every model call is a separate `claude` process of a few hundred MB. Callers run several groups in parallel at once
# (two compiles + case writing + judging), so the cap is here, per builder process, not per group: on 2026-10-11 a
# rehearsal with too many processes ran Windows out of virtual memory (WinError 1455) and every call failed in 0 s.
_PROCS = threading.Semaphore(int(os.environ.get("BUILDER_MAX_PROCS", "6")))


def _transient(e):
    return isinstance(e, (Transient, MemoryError)) or (isinstance(e, OSError) and getattr(e, "winerror", None) in (1455, 1450, 8))


def _cli_call(system, prompt, model, timeout):
    os.makedirs(SANDBOX, exist_ok=True)
    sys_path = os.path.join(SANDBOX, "system-%d-%d.txt" % (os.getpid(), threading.get_ident()))
    with open(sys_path, "w", encoding="utf-8") as f:
        f.write(system)
    cmd = ["claude", "-p", "--output-format", "json", "--model", model, "--system-prompt-file", sys_path] + CLI_FLAGS
    try:
        with _PROCS:
            p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=timeout, cwd=SANDBOX)
    finally:
        try:
            os.unlink(sys_path)
        except OSError:
            pass
    try:
        j = json.loads(p.stdout)
    except ValueError:
        if not p.stdout.strip():   # the process died before it answered (out of memory / processes): not the model
            raise Transient("claude CLI produced no output (exit %s): %s" % (p.returncode, p.stderr[-300:]))
        raise RuntimeError("claude CLI failed: %s %s" % (p.stdout[-500:], p.stderr[-500:]))
    if j.get("is_error"):
        raise RuntimeError("claude CLI error: %s" % str(j.get("result"))[:500])
    u = j.get("usage") or {}
    return j.get("result") or "", {"input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
                                   "cost_usd": j.get("total_cost_usd")}


def call(system, prompt, purpose, model=None, max_tokens=32000, timeout=1800, retries=1):
    """One model call. Its time limit is the builder's time left, not a guess of how long the call takes: a slow but
    healthy call is never killed early (a killed 14-minute compile started over would break the 30-minute rule), and
    no call runs past the deadline."""
    model = model or MODEL
    backend = "api" if os.environ.get("ANTHROPIC_API_KEY") else "cli"
    last = None
    attempt, wait, waited = 0, 10, 0
    while attempt <= retries:
        left = time_left()
        if left is not None:
            if left <= 5:
                raise TimeoutError("no time left for '%s'" % purpose)
            timeout = min(timeout, left)
        t0 = time.time()
        try:
            if backend == "api":
                text, usage = _api_call(system, prompt, model, max_tokens)
            else:
                text, usage = _cli_call(system, prompt, model, timeout)
            _record({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "backend": backend, "purpose": purpose,
                     "seconds": round(time.time() - t0, 1), "usage": usage, "ok": True})
            return text
        except Exception as e:
            last = e
            _record({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "backend": backend, "purpose": purpose,
                     "seconds": round(time.time() - t0, 1), "ok": False, "error": str(e)[:300]})
            if _transient(e):
                # the machine was short of resources: wait for it to recover instead of spending the retry in 0 s;
                # the deadline (time_left above) still bounds how long this can go on
                left = time_left()
                if left is None:   # no builder deadline (tools, experiments): a bounded wait instead
                    left = 600 - waited
                if left <= wait + 5:
                    raise
                waited += wait
                time.sleep(wait)
                wait = min(wait * 2, 60)
                continue
            attempt += 1
    raise last


def extract_json(text):
    """The first complete JSON object or array in a model reply (fenced or bare)."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except ValueError:
            pass
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0] or [-1])
    if start < 0:
        raise ValueError("no JSON in reply")
    dec = json.JSONDecoder()
    obj, _ = dec.raw_decode(text[start:])
    return obj


def parallel(jobs, limit=8):
    """jobs: list of zero-arg callables. Runs them in threads, at most `limit` at a time (each one is a model process;
    too many at once ran the machine out of resources: "fork: Resource temporarily unavailable"), returns results in
    order (exceptions returned)."""
    res = [None] * len(jobs)
    gate = threading.Semaphore(limit)

    def run(i, f):
        with gate:
            try:
                res[i] = f()
            except Exception as e:  # returned, not raised, so one failure does not kill the others
                res[i] = e
    ts = [threading.Thread(target=run, args=(i, f)) for i, f in enumerate(jobs)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return res
