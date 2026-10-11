"""A repair as a PATCH of the PolicyIR instead of the whole IR written again.

A repair of one problem used to make the model write the complete IR again (S8: 31 000 output tokens, 205 s, for one
problem). The patch names only what changes; this module applies it. The result goes through the same validator and the
same tests as before, so a wrong patch is caught exactly as a wrong full rewrite was.

Patch format (every part optional):
  {"rules":     {"<rule id>": <full rule object> | null},      list items with an "id": replaced in place, added, removed
   "intents":   {"<intent id>": <full intent object> | null},
   "templates": {"<name>": <value> | null},                    dict entries: set or removed (also slots, procedures, ...)
   "replace":   {"<top-level key>": <new value>}}              anything else, replaced whole
A reply that is a complete IR (it has "rules" as a list) is taken as a complete IR, as before.
"""
import copy

PATCH_FORMAT = """Return ONLY what changes, as one JSON object (a patch), not the whole IR:
{"rules": {"<rule id>": <the complete corrected or new rule object, with its "id"> or null to remove it},
 "intents": {"<intent id>": <complete intent object> or null},
 "templates": {"<name>": <value> or null}, "slots": {...}, "procedures": {...}, "functions": {...},
 "replace": {"<any other top-level key>": <its complete new value>}}
Leave out every part that does not change. Write each changed object complete (not a fragment of it)."""


def is_full_ir(obj):
    return isinstance(obj, dict) and isinstance(obj.get("rules"), list)


def apply_patch(ir, patch):
    """A new IR with the patch applied. Raises ValueError on a patch that does not fit the IR."""
    if not isinstance(patch, dict):
        raise ValueError("patch is not an object")
    out = copy.deepcopy(ir)
    for key, change in patch.items():
        if key == "replace":
            if not isinstance(change, dict):
                raise ValueError("'replace' must be an object")
            for k, v in change.items():
                out[k] = v
            continue
        if not isinstance(change, dict):
            raise ValueError("patch part %r must be an object keyed by id or name" % key)
        cur = out.get(key)
        if isinstance(cur, list) or (cur is None and key in ("rules", "intents")):
            items = list(cur or [])
            pos = {it.get("id"): i for i, it in enumerate(items) if isinstance(it, dict)}
            removed = set()
            for iid, obj in change.items():
                if obj is None:
                    removed.add(iid)
                    continue
                if not isinstance(obj, dict):
                    raise ValueError("%s %r: not an object" % (key, iid))
                obj = dict(obj)
                obj.setdefault("id", iid)
                if iid in pos:
                    items[pos[iid]] = obj
                else:
                    pos[iid] = len(items)
                    items.append(obj)
            out[key] = [it for it in items if not (isinstance(it, dict) and it.get("id") in removed)]
        elif isinstance(cur, dict) or cur is None:
            d = dict(cur or {})
            for name, v in change.items():
                if v is None:
                    d.pop(name, None)
                else:
                    d[name] = v
            out[key] = d
        else:
            raise ValueError("patch part %r: the IR's %r is neither a list nor an object" % (key, key))
    return out


def patched(ir, reply):
    """The repaired IR from a model reply: a patch (applied) or a complete IR (taken as it is)."""
    return copy.deepcopy(reply) if is_full_ir(reply) else apply_patch(ir, reply)
