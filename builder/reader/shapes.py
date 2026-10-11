"""Shape normalisation for every JSON answer of the reader's model calls.

A model gives the same information in slightly different shapes from run to run: a map as a list of pairs, a list as a
single object, a wrapper object around the real answer, a missing key. Trusting one exact shape crashed the builder
(2026-10-11: the gap-fill answer gave `non_normative` as a list -> `dict.update` raised -> no agent at all). Here every
known variation is mapped to the one shape the pipeline uses, keeping the meaning; what cannot be mapped raises
ShapeError so the caller can ask the model again with the error, or fall back to the last good result.
"""


class ShapeError(ValueError):
    pass


def as_list(x):
    if x is None or x == "":
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        # {"a": {...}, "b": {...}} (keyed collection) -> list; a single item -> [item]
        if x and all(isinstance(v, dict) for v in x.values()) and not any(k in x for k in ("id", "sids", "op", "text")):
            return [dict(v, id=v.get("id", k)) for k, v in x.items()]
        return [x]
    return [x]


def as_map(x, key_names=("sid", "sids", "id", "key", "name"), value_names=("reason", "why", "value", "text", "note")):
    """A mapping, from a dict, a list of [key, value, ...] rows, or a list of objects with a key field."""
    if x is None or x == "":
        return {}
    if isinstance(x, dict):
        return x
    if isinstance(x, list):
        out = {}
        for row in x:
            if isinstance(row, (list, tuple)) and row:
                out[str(row[0])] = " ".join(str(v) for v in row[1:]) if len(row) > 1 else ""
            elif isinstance(row, dict):
                k = next((row[n] for n in key_names if n in row), None)
                if k is None:
                    continue
                v = next((row[n] for n in value_names if n in row), "")
                if isinstance(k, list):
                    for kk in k:
                        out[str(kk)] = v
                else:
                    out[str(k)] = v
            elif isinstance(row, str):
                out[row] = ""
        return out
    raise ShapeError("expected a mapping, got %s" % type(x).__name__)


def _unwrap(x, keys):
    """{"inventory": {...}} / {"result": {...}} / [ {...} ] -> the object that has one of `keys`."""
    for _ in range(3):
        if isinstance(x, list) and len(x) == 1 and isinstance(x[0], dict):
            x = x[0]
            continue
        if isinstance(x, dict) and not any(k in x for k in keys) and len(x) == 1:
            only = next(iter(x.values()))
            if isinstance(only, (dict, list)):
                x = only
                continue
        break
    return x


def inventory(x):
    x = _unwrap(x, ("units", "amendments", "non_normative"))
    if isinstance(x, list):
        x = {"units": x}
    if not isinstance(x, dict):
        raise ShapeError("inventory: expected an object with 'units'")
    return {"units": [u for u in as_list(x.get("units")) if isinstance(u, dict)],
            "amendments": [a for a in as_list(x.get("amendments")) if isinstance(a, dict)],
            "non_normative": as_map(x.get("non_normative")),
            "ambiguities": as_list(x.get("ambiguities"))}


def policy_ir(x):
    x = _unwrap(x, ("rules", "templates", "initial_phase"))
    if not isinstance(x, dict):
        raise ShapeError("PolicyIR: expected an object")
    ir = dict(x)
    rules = as_list(ir.get("rules"))
    ir["rules"] = [r for r in rules if isinstance(r, dict)]
    if not ir["rules"]:
        raise ShapeError("PolicyIR: no rules")
    t = ir.get("templates") or {}
    if isinstance(t, list):
        t = {str(e.get("id")): {k: v for k, v in e.items() if k != "id"} for e in t if isinstance(e, dict) and e.get("id")}
    ir["templates"] = t
    ints = ir.get("intents") or []
    if isinstance(ints, dict):
        ints = [dict(v if isinstance(v, dict) else {"description": str(v)}, id=k) for k, v in ints.items()]
    ir["intents"] = [i for i in ints if isinstance(i, dict) and i.get("id")]
    for key in ("slots", "procedures", "functions"):
        v = ir.get(key) or {}
        if isinstance(v, list):
            v = {str(e.get("name") or e.get("id")): {k: w for k, w in e.items() if k not in ("name", "id")} if key != "procedures"
                 else (e.get("do") or e.get("actions") or [])
                 for e in v if isinstance(e, dict) and (e.get("name") or e.get("id"))}
        ir[key] = v
    if not ir.get("initial_phase"):
        raise ShapeError("PolicyIR: no initial_phase")
    return ir
