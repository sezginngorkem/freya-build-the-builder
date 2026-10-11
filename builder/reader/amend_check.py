"""Was each amendment of the brief (a memo that changes a value) really applied in the IR?

The inventory lists every amendment with its old and new text and the sentences it comes from / changes. Applying an
amendment is where LLM readers fail most (about 63% success in the NLLP 2024 measurements). A value that the memo
replaced must not survive in the IR parts that cite the amended sentences, and the new value must be there. Checked in
code, numbers and dates only (no wording judgement). Returns a list of findings (strings)."""
import json, re

_NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w.])")
_DATE = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b|\b(\d{4})-(\d{2})-(\d{2})\b")


def _nums(text):
    return set(float(x) for x in _NUM.findall(str(text or "")))


def _dates(text):
    out = set()
    for m in _DATE.finditer(str(text or "")):
        if m.group(3):
            out.add("%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1))))
        else:
            out.add("%s-%s-%s" % (m.group(4), m.group(5), m.group(6)))
    return out


def _citing(ir, sids):
    """IR parts (rules, templates, procedures, functions, calendar, ...) whose source cites one of the sentences."""
    parts = []

    def cites(x):
        return isinstance(x, dict) and any(s in str(x.get("src") or "") for s in sids)

    def body(x):
        return json.dumps({k: v for k, v in x.items() if k != "src"}, ensure_ascii=False)
    for r in ir.get("rules") or []:
        if cites(r):
            parts.append(("rule " + str(r.get("id")), body(r)))
    for key in ("templates", "procedures", "functions", "slots"):
        for name, v in (ir.get(key) or {}).items():
            if cites(v):
                parts.append(("%s %s" % (key[:-1], name), body(v)))
    return parts


def check(ir, inventory):
    findings = []
    cal = json.dumps(ir.get("calendar") or {})
    for a in (inventory or {}).get("amendments") or []:
        sids = list(a.get("sids") or []) + list(a.get("target_sids") or [])
        parts = _citing(ir, sids)
        old, new = _nums(a.get("old")), _nums(a.get("new"))
        gone = old - new
        for name, text in parts:
            left = gone & _nums(text)
            if left and not (new & _nums(text)):
                findings.append("amendment %s: %s still uses %s, which the memo replaced (%r -> %r)" % (
                    ",".join(a.get("sids") or []), name, sorted(left), str(a.get("old"))[:80], str(a.get("new"))[:80]))
        added = new - old
        if added and parts and not any(added & _nums(t) for _, t in parts) and not (added & _nums(cal)):
            findings.append("amendment %s: its new value %s is in no IR part citing it (%r)" % (
                ",".join(a.get("sids") or []), sorted(added), str(a.get("new"))[:100]))
        for d in _dates(a.get("new")) - _dates(a.get("old")):
            if d not in json.dumps(ir, ensure_ascii=False):
                findings.append("amendment %s: its date %s is nowhere in the IR (%r)" % (
                    ",".join(a.get("sids") or []), d, str(a.get("new"))[:100]))
    return findings
