"""Reader stage 0: deterministic normalisation of the input documents (no LLM).

Input: brief file paths (markdown / text / e-mail / csv / json) and an OpenAPI file.
Output (dict):
  docs:        [{id, path, kind_guess, title}]
  sentences:   {sid: {"doc": id, "text": ..., "section": ..., "rule_no": ...}}   every normative unit, numbered
  tables:      [{id, doc, header: [...], rows: [[...]], near: sid}]               parsed, never rewritten by an LLM
  numbers:     [{sid, token}]                                                    every number/date/time in the text
  vocabulary:  {tools: {name: {path, summary, args: {..}, required, returns: {..}, write}}, enums: {..}, server}
  amendment_markers: [sid]                                                       sentences with change language
Generic: nothing here knows about banks or any particular brief.
"""
import csv, io, json, os, re

AMEND_RE = re.compile(r"\b(replac\w*|instead of|no longer|from now on|with effect|effective|amend\w*|chang\w* to|now (?:is|are|reads?)|"
                      r"supersed\w*|override\w*|unless replaced|in place of|is withdrawn|revoked?|repeal\w*|update[sd]?|new rule|"
                      r"applies? unless|starting|as of)\b", re.I)
NUM_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b|\$?\b\d+(?:[.,]\d+)*%?|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|"
                    r"eleven|twelve|once|twice|first|second|third|fourth|fifth)\b", re.I)
WRITE_HINT = re.compile(r"\b(record|create|add|schedule|transfer|close|update|delete|set|book|cancel)\b", re.I)


_TITLE_KINDS = [("email", r"\b(e-?mails?|mail|thread|correspondence|forwarded)\b"),
                ("memo", r"\b(memo(randum)?|circular|bulletin|notice of change|amendment)\b"),
                ("code_list", r"\b(code ?list|codes|disposition|outcome table|result codes?|reason codes?)\b"),
                ("policy_extract", r"\b(policy|extract|procedure|manual|handbook|guideline)\b")]


def guess_section_kind(title, text):
    t = (title or "").lower()
    for kind, pat in _TITLE_KINDS:
        if re.search(pat, t):
            return kind
    body = "\n".join(l.lstrip("> ").rstrip() for l in text.splitlines())
    return guess_kind("section", body)


def guess_kind(path, text):
    name = os.path.basename(path).lower()
    head = text[:600].lower()
    if name.endswith((".csv", ".tsv")):
        return "code_list"
    if re.search(r"^(from|to|subject|date):", head, re.M):
        return "email"
    if "memo" in name or re.search(r"\bmemo(randum)?\b", head):
        return "memo"
    if re.search(r"\b(code list|codes?\b.*\|)", head) or ("code" in name and "list" in name):
        return "code_list"
    if "extract" in name or "policy" in name and "brief" not in name:
        return "policy_extract"
    return "spec"


def _delimited_table(block_lines):
    """Rows of a delimited block (csv / semicolon / tab / pipe) with a consistent number of fields, or None."""
    data = [l for l in block_lines if l.strip()]
    if len(data) < 2:
        return None
    best = None
    for delim in (",", ";", "\t", "|"):
        try:
            rows = list(csv.reader(io.StringIO("\n".join(l.strip().strip("|") if delim == "|" else l for l in data)), delimiter=delim))
        except Exception:
            continue
        widths = [len(r) for r in rows]
        if max(widths) < 2:
            continue
        common = max(set(widths), key=widths.count)
        share = widths.count(common) / float(len(widths))
        if share >= 0.6 and (best is None or common > best[0]):
            best = (common, rows)
    if best is None:
        return None
    return [[c.strip() for c in r] for r in best[1] if any(c.strip() for c in r)]


def _split_markdown_tables(lines):
    """Yield ('table', header, rows, line_no) or ('text', line, line_no) or ('line', line, line_no) (a line that must
    stay a sentence of its own, e.g. inside a code block)."""
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            block = lines[i + 1:j]
            rows = _delimited_table(block)
            if rows and len(rows) >= 2:
                yield ("table", rows[0], rows[1:], i)
            else:
                for k, bl in enumerate(block):
                    if bl.strip():
                        yield ("line", bl, i + 1 + k)
            i = j + 1
            continue
        if ln.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            header = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            yield ("table", header, rows, i)
            i = j
            continue
        yield ("text", ln, i)
        i += 1


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=(?:[A-Z\"'(]|\d+\.\s))")


def split_sentences(text):
    out = []
    for part in _SENT_SPLIT.split(text.strip()):
        p = part.strip()
        if p:
            out.append(p)
    return out


def parse_doc(doc_id, path, text, state):
    m = re.search(r"\[(email|memo|code_list|policy_extract|spec)\]$", path)
    kind = m.group(1) if m else guess_kind(path, text)
    doc = {"id": doc_id, "path": os.path.basename(path), "kind_guess": kind, "title": ""}
    state["docs"].append(doc)
    if kind == "code_list" and (path.lower().endswith((".csv", ".tsv")) or text.count(",") > text.count("|")):
        dialect = "excel-tab" if path.lower().endswith(".tsv") else "excel"
        rows = list(csv.reader(io.StringIO(text), dialect=dialect))
        rows = [r for r in rows if any(c.strip() for c in r)]
        if rows:
            state["tables"].append({"id": "%s.t1" % doc_id, "doc": doc_id, "header": [c.strip() for c in rows[0]],
                                    "rows": [[c.strip() for c in r] for r in rows[1:]], "near": None})
        return
    section, rule_no = "", None
    lines = text.splitlines()
    n_tab = 0
    para = []

    def flush():
        if not para:
            return
        block = " ".join(x.strip() for x in para)
        para.clear()
        rn = None
        m = re.match(r"^\s*(\d+)\.\s+(.*)$", block)
        if m:
            rn, block = m.group(1), m.group(2)
        for s in split_sentences(block):
            sid = "%s.s%03d" % (doc_id, len([k for k in state["sentences"] if k.startswith(doc_id + ".")]) + 1)
            state["sentences"][sid] = {"doc": doc_id, "text": s, "section": section, "rule_no": rn}
            for tok in NUM_RE.findall(s):
                state["numbers"].append({"sid": sid, "token": tok})
            if AMEND_RE.search(s):
                state["amendment_markers"].append(sid)

    for item in _split_markdown_tables(lines):
        if item[0] == "table":
            flush()
            n_tab += 1
            _, header, rows, ln = item
            last_sid = sorted(k for k in state["sentences"] if k.startswith(doc_id + "."))[-1:] or [None]
            state["tables"].append({"id": "%s.t%d" % (doc_id, n_tab), "doc": doc_id, "header": header, "rows": rows,
                                    "near": last_sid[0], "section": section})
            continue
        ln = item[1]
        if item[0] == "line":
            flush()
            para.append(ln)
            flush()
            continue
        if ln.lstrip().startswith(">"):        # quoted mail text: the quote marks are not part of the sentence
            ln = re.sub(r"^\s*(>\s?)+", "", ln)
        st = ln.strip()
        if st.startswith("#"):
            flush()
            section = st.lstrip("#").strip()
            if not doc["title"]:
                doc["title"] = section
            continue
        if not st:
            flush()
            continue
        if re.match(r"^\s*(\d+\.|[-*])\s+", ln) and para:
            flush()
        para.append(ln)
    flush()


def _resolve(spec, x, depth=0):
    """A schema with $ref followed and allOf/oneOf/anyOf merged into one object schema (fields can be written either
    way in an OpenAPI file; the practice file uses neither, a hidden one may)."""
    if not isinstance(x, dict) or depth > 20:
        return x if isinstance(x, dict) else {}
    if "$ref" in x:
        node = spec
        for part in str(x["$ref"]).lstrip("#/").split("/"):
            node = (node or {}).get(part.replace("~1", "/").replace("~0", "~")) if isinstance(node, dict) else None
        merged = dict(_resolve(spec, node or {}, depth + 1))
        merged.update({k: v for k, v in x.items() if k != "$ref"})
        return merged
    parts = [p for k in ("allOf", "oneOf", "anyOf") for p in (x.get(k) or [])]
    if parts:
        out = {k: v for k, v in x.items() if k not in ("allOf", "oneOf", "anyOf")}
        props, req = dict(out.get("properties") or {}), list(out.get("required") or [])
        for p in parts:
            r = _resolve(spec, p, depth + 1)
            props.update(r.get("properties") or {})
            if "allOf" in x:
                req += [q for q in (r.get("required") or []) if q not in req]
            for k in ("type", "description"):
                out.setdefault(k, r.get(k))
        out["properties"], out["required"] = props, req
        return out
    return x


def _content_schema(spec, holder):
    holder = _resolve(spec, holder or {})
    content = holder.get("content") or {}
    body = content.get("application/json") or next(iter(content.values()), {}) if content else {}
    return _resolve(spec, (body or {}).get("schema") or {})


def _ok_response(op):
    rs = op.get("responses") or {}
    for code in ["200", "201", "202"] + sorted(k for k in rs if str(k).startswith("2")) + ["2XX", "default"]:
        if code in rs:
            return rs[code]
    return {}


def parse_openapi(path):
    spec = json.load(open(path, encoding="utf-8"))
    server = ((spec.get("servers") or [{}])[0]).get("url", "")
    server = os.environ.get("BANK_BASE_URL") or server     # the address the agent's tools really call (e.g. a team's own mock)
    tools, enums = {}, {}
    for p, item in (spec.get("paths") or {}).items():
        for method, op in item.items():
            if method.lower() not in ("post", "get", "put", "patch", "delete"):
                continue
            name = op.get("operationId") or p.strip("/").split("/")[-1]
            schema = _content_schema(spec, op.get("requestBody"))
            props = schema.get("properties") or {}
            wire = {}
            # an envelope ({"data": {...fields...}, "call": {...metadata...}} in, {"data": {...}, "result": {...}} out):
            # the tool's arguments and answer fields are the ones INSIDE "data"; the wrapper is only transport.
            dres = _resolve(spec, props["data"]) if "data" in props else {}
            if dres.get("properties"):
                extra = {}
                for k, v in props.items():
                    if k == "data":
                        continue
                    sub = {}
                    for kk, vv in (_resolve(spec, v).get("properties") or {}).items():
                        d = _resolve(spec, vv).get("default")
                        if d is not None:
                            sub[kk] = d
                    if sub:
                        extra[k] = sub
                wire["req_wrap"] = {"key": "data", "extra": extra}
                schema = dict(schema, required=dres.get("required") or [])
                props = dres["properties"]
            args = {}
            for k, v in props.items():
                v = _resolve(spec, v)
                a = {"type": v.get("type"), "description": v.get("description", "")}
                if v.get("enum"):
                    a["enum"] = v["enum"]
                    enums["%s.%s" % (name, k)] = v["enum"]
                if v.get("format"):
                    a["format"] = v["format"]
                args[k] = a
            resp = _content_schema(spec, _ok_response(op))
            resp_props = resp.get("properties") or {}
            rd = _resolve(spec, resp_props["data"]) if "data" in resp_props else {}
            if rd.get("properties"):
                wire["resp_wrap"] = "data"
                resp_props = rd["properties"]
            returns = {}
            for k, v in resp_props.items():
                v = _resolve(spec, v)
                r = {"type": v.get("type")}
                if v.get("enum"):
                    r["enum"] = v["enum"]
                    enums["%s.returns.%s" % (name, k)] = v["enum"]
                if v.get("type") == "array" and isinstance(v.get("items"), dict):
                    sub = {}
                    for kk, vv in (_resolve(spec, v["items"]).get("properties") or {}).items():
                        vv = _resolve(spec, vv)
                        sub[kk] = {"type": vv.get("type"), "description": vv.get("description", "")}
                        if vv.get("enum"):
                            sub[kk]["enum"] = vv["enum"]
                            enums["%s.returns.%s[].%s" % (name, k, kk)] = vv["enum"]
                    r["items"] = sub
                if v.get("type") == "object" and v.get("properties"):     # one level of nested fields, for the reader
                    r["fields"] = {kk: (_resolve(spec, vv).get("type")) for kk, vv in v["properties"].items()}
                returns[k] = r
            summary = (op.get("summary") or "") + (" " + op.get("description") if op.get("description") else "")
            if wire.get("resp_wrap"):
                summary += (" [On a failed call there are no answer fields: result.ok is false and result.code / result.message "
                            "carry the bank's error code and text, e.g. result.code == 'SOME_CODE'.]")
            tools[name] = {"wire": wire, "path": p, "method": method.upper(), "url": server.rstrip("/") + p, "summary": summary.strip(),
                           "args": args, "required": schema.get("required") or [], "returns": returns,
                           "write": bool(WRITE_HINT.search(name)) and not name.startswith(("get", "verify", "list"))}
    return {"server": server, "title": (spec.get("info") or {}).get("title", ""),
            "description": (spec.get("info") or {}).get("description", ""), "tools": tools, "enums": enums}


def split_composite(path, text):
    """[(virtual_path, text)]: one entry per top-level section when a Markdown file bundles different material (a mail,
    a policy extract, a memo, a code list); else the whole file. A clean specification is never split."""
    if not path.lower().endswith((".md", ".markdown", ".txt")):
        return [(path, text)]
    lines = text.splitlines()
    heads = [i for i, l in enumerate(lines) if re.match(r"^#{1,2}\s+\S", l)]
    if len(heads) < 2:
        return [(path, text)]
    lv = [len(re.match(r"^(#+)", lines[i]).group(1)) for i in heads]
    level = min((x for x in set(lv) if lv.count(x) >= 2), default=None)   # the shallowest level with 2+ sections
    if level is None:
        return [(path, text)]
    heads = [i for i, x in zip(heads, lv) if x == level]
    parts = []
    for k, i in enumerate(heads):
        j = heads[k + 1] if k + 1 < len(heads) else len(lines)
        title = lines[i].lstrip("#").strip()
        parts.append((title, "\n".join(lines[i:j])))
    kinds = [guess_section_kind(t, b) for t, b in parts]
    material = set(k for k in kinds if k in ("email", "memo", "code_list", "policy_extract"))
    if len(material) < 2:
        return [(path, text)]
    pre = "\n".join(lines[:heads[0]]).strip()
    out = []
    for (title, body), kind in zip(parts, kinds):
        out.append(("%s#%s [%s]" % (os.path.basename(path), title[:60], kind), (pre + "\n\n" if pre and not out else "") + body))
    return out


def run(brief_paths, openapi_path):
    state = {"docs": [], "sentences": {}, "tables": [], "numbers": [], "amendment_markers": []}
    n = 0
    for p in brief_paths:
        text = open(p, encoding="utf-8", errors="replace").read()
        for vpath, vtext in split_composite(p, text):
            n += 1
            parse_doc("D%d" % n, vpath, vtext, state)
    state["vocabulary"] = parse_openapi(openapi_path) if openapi_path else {"tools": {}, "enums": {}}
    return state


def render_for_llm(state, doc_ids=None):
    """The documents as numbered lines the LLM must cite by id."""
    out = []
    for d in state["docs"]:
        if doc_ids and d["id"] not in doc_ids:
            continue
        out.append("=== DOCUMENT %s (%s, %s) ===" % (d["id"], d["path"], d["kind_guess"]))
        last_section = None
        for sid, s in state["sentences"].items():
            if s["doc"] != d["id"]:
                continue
            if s["section"] != last_section:
                out.append("## " + s["section"])
                last_section = s["section"]
            rn = ("[rule %s] " % s["rule_no"]) if s["rule_no"] else ""
            out.append("%s %s%s" % (sid, rn, s["text"]))
            for t in state["tables"]:
                if t["near"] == sid:
                    out.append("%s TABLE header=%s rows=%s" % (t["id"], json.dumps(t["header"]), json.dumps(t["rows"])))
        for t in state["tables"]:
            if t["doc"] == d["id"] and t["near"] is None:
                out.append("%s TABLE header=%s rows=%s" % (t["id"], json.dumps(t["header"]), json.dumps(t["rows"])))
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    api = [a for a in args if a.endswith(".json")]
    briefs = [a for a in args if not a.endswith(".json")]
    st = run(briefs, api[0] if api else None)
    print(render_for_llm(st))
    print("\n# %d sentences, %d tables, %d numbers, %d amendment markers, %d tools" % (
        len(st["sentences"]), len(st["tables"]), len(st["numbers"]), len(st["amendment_markers"]), len(st["vocabulary"]["tools"])))
