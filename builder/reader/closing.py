"""Which arguments of the closing tool carry the outcome and the reason.

The tool names stay fixed between briefs but their fields can change (kit README). The engine used to send
{"outcome": ..., "reason": ...} whatever the tool's fields were called; a renamed field would have dropped the outcome
from every call. The names are taken from the tool's own definition (OpenAPI):
  1. the names the reader wrote in the IR (closing.fields), when the tool has them;
  2. a field of exactly that name;
  3. the field whose allowed values contain the values the IR closes with (outcomes, then reasons).
None when nothing fits (the validator reports it)."""
import re

_LIT = re.compile(r"'([^']*)'")


def _close_values(ir):
    outs, reasons = set(), set()

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("close"), dict):
                outs.update(_LIT.findall(str(x["close"].get("outcome") or "")))
                reasons.update(_LIT.findall(str(x["close"].get("reason") or "")))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(ir.get("rules"))
    walk(ir.get("procedures"))
    return outs, reasons


def close_fields(ir, vocabulary):
    closing = ir.get("closing") or {}
    tool = (vocabulary.get("tools") or {}).get(closing.get("tool", "close_call")) or {}
    args = tool.get("args") or {}
    if not args:      # no definition to check against: keep the IR's own names
        f = closing.get("fields") or {}
        return {"outcome": f.get("outcome", "outcome"), "reason": f.get("reason", "reason")}
    outs, reasons = _close_values(ir)
    taken, res = set(), {}
    for role, vals in (("outcome", outs), ("reason", reasons)):
        named = (closing.get("fields") or {}).get(role)
        if named in args and named not in taken:
            res[role] = named
        elif role in args and role not in taken:
            res[role] = role
        else:
            best, score = None, 0
            for name, a in args.items():
                if name in taken or not a.get("enum"):
                    continue
                s = len(vals & set(map(str, a["enum"])))
                if s > score:
                    best, score = name, s
            res[role] = best
        if res[role]:
            taken.add(res[role])
    if res.get("outcome") and not res.get("reason"):
        # a free-text reason has no allowed values to match: the one field left that the IR does not fill otherwise
        left = [n for n in args if n not in taken and n not in (closing.get("extra_args") or {})]
        if len(left) == 1:
            res["reason"] = left[0]
    return res
