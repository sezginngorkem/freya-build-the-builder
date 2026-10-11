"""A small, safe expression language for policy rules.

Rules in the policy IR carry conditions and value formulas as strings, e.g.
    "item.type == 'credit_card'"
    "add_business_days(today(), band.deadline_bd)"
    "counter.wrong_answers >= 3 and not flag.verified"
They are parsed with Python's own grammar (ast) but only a whitelist of node types and the
functions below are allowed: no attribute calls, no imports, no builtins. Names resolve from a
context dict; dotted names walk nested dicts. Standard library only.
"""
import ast
import datetime as _dt

from . import dates as D

_ALLOWED = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
            ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Compare, ast.Eq, ast.NotEq,
            ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.Call,
            ast.Name, ast.Load, ast.Attribute, ast.Constant, ast.List, ast.Tuple, ast.IfExp,
            ast.Subscript, ast.Index if hasattr(ast, "Index") else ast.Constant, ast.Slice)


class ExprError(Exception):
    pass


def make_functions(calendar):
    cal = calendar or D.DEFAULT_CALENDAR

    def _d(x):
        return D.to_date(x) if x not in (None, "") else None

    return {
        "add_business_days": lambda d, n: D.add_business_days(_d(d), n, cal).isoformat(),
        "is_business_day": lambda d: D.is_business_day(_d(d), cal),
        "is_holiday": lambda d: D.is_holiday(_d(d), cal),
        "next_business_day": lambda d, include_same=False: D.next_business_day(_d(d), cal, include_same).isoformat(),
        "prev_business_day": lambda d, include_same=False: D.prev_business_day(_d(d), cal, include_same).isoformat(),
        "last_business_day_of_week": lambda d, offset=0: (lambda r: r.isoformat() if r else None)(D.last_business_day_of_week(_d(d), offset, cal)),
        "weekday_in_week": lambda name, which, ref: D.weekday_in_week(name, which, _d(ref)).isoformat(),
        "add_days": lambda d, n: (_d(d) + _dt.timedelta(days=int(n))).isoformat(),
        "weekday": lambda d: _d(d).strftime("%A"),
        "day_label": lambda d: D.day_label(_d(d)),
        "between": lambda x, lo, hi, inc_lo=True, inc_hi=True: x is not None and D.between(x, lo, hi, (inc_lo, inc_hi)),
        "time_in_window": lambda t, a, b, inc_lo=True, inc_hi=True: t is not None and D.time_in_window(t, a, b, (inc_lo, inc_hi)),
        "min": lambda *a: min(x for x in a if x is not None),
        "max": lambda *a: max(x for x in a if x is not None),
        "round": lambda x, n=2: round(float(x), int(n)),
        "ceil": lambda x, step=1: (__import__("math").ceil(round(float(x) / float(step), 9)) * float(step)),
        "floor_": lambda x, step=1: (__import__("math").floor(round(float(x) / float(step), 9)) * float(step)),
        "pct": lambda x, p: float(x) * float(p) / 100.0,
        "money": lambda x: "%.2f" % float(x),
        "abs": abs,
        "len": lambda x: len(x or []),
        "is_set": lambda x: x not in (None, "", [], {}),
        "lower": lambda s: str(s or "").lower(),
        "str_": lambda x: "" if x is None else str(x),
        "copy_list": lambda xs: [dict(x) if isinstance(x, dict) else x for x in (xs or [])],
        "find_index": lambda items, require=None, exclude=None: next((i for i, x in enumerate(items or [])
                                                                      if all((x or {}).get(k) not in (None, "", False) for k in (require or []))
                                                                      and all((x or {}).get(k) in (None, "", False) for k in (exclude or []))), -1),
        "count_set": lambda items, key: sum(1 for x in (items or []) if (x or {}).get(key) not in (None, "", False)),
        "item_index": _item_index,
        "time_of": lambda dt: D.to_datetime(dt).strftime("%H:%M") if dt else None,
        "date_le": lambda a, b: a is not None and b is not None and _d(a) <= _d(b),
        "date_lt": lambda a, b: a is not None and b is not None and _d(a) < _d(b),
        "date_ge": lambda a, b: a is not None and b is not None and _d(a) >= _d(b),
        "count_where": lambda items, key, value: sum(1 for i in (items or []) if (i or {}).get(key) == value),
        "all_where": lambda items, key, value: bool(items) and all((i or {}).get(key) == value for i in items),
        "first_where_not": lambda items, key, value: next(((i or {}) for i in (items or []) if (i or {}).get(key) != value), None),
    }


def _item_index(items, text):
    """Index of the item a customer refers to ('the loan', 'the card ending 3307', 'the car one'), or -1.
    Matches digit groups against any field, then words against type/label fields. Ambiguous -> -1."""
    import re as _re
    t = str(text or "").lower()
    if not t or not items:
        return -1
    digits = _re.findall(r"\d{3,}", t)
    hits = [i for i, it in enumerate(items) if any(d in " ".join(str(v) for v in (it or {}).values()) for d in digits)] if digits else []
    if len(hits) == 1:
        return hits[0]
    words = set(w for w in _re.findall(r"[a-z]+", t) if len(w) > 2) - {"the", "one", "that", "this", "for", "and", "account", "payment"}
    syn = {"car": "auto", "auto": "car", "vehicle": "car", "mortgage": "home", "house": "home"}
    words |= set(syn[w] for w in list(words) if w in syn)
    scores = []
    for i, it in enumerate(items):
        hay = set(_re.findall(r"[a-z]+", " ".join(str((it or {}).get(k, "")) for k in ("type", "label", "name", "product", "product_type")).lower().replace("_", " ")))
        scores.append(sum(1 for w in words if w in hay))
    best = max(scores) if scores else 0
    if best == 0 or scores.count(best) > 1:
        return -1
    return scores.index(best)


def _lookup(ctx, dotted):
    if dotted.startswith("counter.") and dotted.count(".") == 1:   # counters start at 0
        v = (ctx.get("counter") or {}).get(dotted[8:])
        return 0 if v is None else v
    cur = ctx
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
        if cur is None:
            return None
    return cur


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def compile_expr(src):
    try:
        tree = ast.parse(str(src), mode="eval")
    except SyntaxError as e:
        raise ExprError("syntax: %s in %r" % (e.msg, src))
    for n in ast.walk(tree):
        if not isinstance(n, _ALLOWED):
            raise ExprError("not allowed: %s in %r" % (type(n).__name__, src))
        if isinstance(n, ast.Call) and not isinstance(n.func, ast.Name):
            raise ExprError("only plain function calls allowed in %r" % src)
        if isinstance(n, ast.Attribute) and n.attr.startswith("_"):
            raise ExprError("private attribute in %r" % src)
        if isinstance(n, ast.Name) and n.id.startswith("_"):
            raise ExprError("private name in %r" % src)
    return tree


def names_used(src):
    """Dotted variable names and function names an expression refers to (for static checks)."""
    tree = compile_expr(src)
    names, funcs = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            funcs.add(n.func.id)
        elif isinstance(n, ast.Attribute) and not isinstance(getattr(n, "_parent", None), ast.Attribute):
            d = _dotted(n)
            if d:
                names.add(d)
        elif isinstance(n, ast.Name):
            names.add(n.id)
    # keep only maximal dotted names
    out = set(x for x in names if not any(y != x and y.startswith(x + ".") for y in names))
    return out - funcs - {"True", "False", "None", "true", "false", "null"}, funcs


def evaluate(src, ctx, funcs):
    tree = compile_expr(src) if not isinstance(src, ast.AST) else src

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in ("true", "True"):
                return True
            if n.id in ("false", "False"):
                return False
            if n.id in ("null", "None"):
                return None
            return _lookup(ctx, n.id)
        if isinstance(n, ast.Attribute):
            d = _dotted(n)
            if d is None:   # a field of a computed value: first_where_not(items, 'k', 'v').end_reason, items[0].amount
                base = ev(n.value)
                return base.get(n.attr) if isinstance(base, dict) else None
            return _lookup(ctx, d)
        if isinstance(n, ast.Slice):
            return slice(ev(n.lower) if n.lower is not None else None, ev(n.upper) if n.upper is not None else None,
                         ev(n.step) if n.step is not None else None)
        if isinstance(n, ast.Subscript):
            base = ev(n.value)
            key = ev(n.slice) if not hasattr(ast, "Index") or not isinstance(n.slice, ast.Index) else ev(n.slice.value)
            try:
                return base[key]
            except Exception:
                return None
        if isinstance(n, (ast.List, ast.Tuple)):
            return [ev(e) for e in n.elts]
        if isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.And):
                v = True
                for e in n.values:
                    v = ev(e)
                    if not v:
                        return v
                return v
            v = False
            for e in n.values:
                v = ev(e)
                if v:
                    return v
            return v
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            if isinstance(n.op, ast.Not):
                return not v
            if isinstance(n.op, ast.USub):
                return -v
            return +v
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if a is None or b is None:
                return None
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.Div):
                return a / b
            if isinstance(n.op, ast.Mod):
                return a % b
        if isinstance(n, ast.IfExp):
            return ev(n.body) if ev(n.test) else ev(n.orelse)
        if isinstance(n, ast.Compare):
            left = ev(n.left)
            for op, comp in zip(n.ops, n.comparators):
                right = ev(comp)
                ok = _cmp(op, left, right)
                if not ok:
                    return False
                left = right
            return True
        if isinstance(n, ast.Call):
            f = funcs.get(n.func.id)
            if f is None:
                raise ExprError("unknown function %s" % n.func.id)
            args = [ev(a) for a in n.args]
            return f(*args)
        raise ExprError("cannot evaluate %s" % type(n).__name__)

    return ev(tree)


def _num(x):
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return x
    try:
        return float(x)
    except (TypeError, ValueError):
        return x


def _cmp(op, a, b):
    if isinstance(op, (ast.In, ast.NotIn)):
        r = a in (b or [])
        return r if isinstance(op, ast.In) else not r
    if isinstance(op, ast.Is):
        return a is b
    if isinstance(op, ast.IsNot):
        return a is not b
    if isinstance(op, (ast.Eq, ast.NotEq)):
        if a is None or b is None:
            r = a is b
        else:
            na, nb = _num(a), _num(b)
            r = (na == nb) if isinstance(na, (int, float)) and isinstance(nb, (int, float)) else (str(a).lower() == str(b).lower() if isinstance(a, (str, bool)) or isinstance(b, (str, bool)) else a == b)
        return r if isinstance(op, ast.Eq) else not r
    if a is None or b is None:
        return False
    na, nb = _num(a), _num(b)
    if not (isinstance(na, (int, float)) and isinstance(nb, (int, float))):
        na, nb = str(a), str(b)   # ISO dates compare correctly as strings
    if isinstance(op, ast.Lt):
        return na < nb
    if isinstance(op, ast.LtE):
        return na <= nb
    if isinstance(op, ast.Gt):
        return na > nb
    if isinstance(op, ast.GtE):
        return na >= nb
    return False
