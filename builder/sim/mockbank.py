"""Local stand-in for the bank's tool API (tools/openapi.json), built from a practice case.
Behaviour follows the openapi descriptions; the ledger has the shape tools/score.py reads."""
import re, datetime as _dt


# The names this stand-in reads and answers with (the practice API's). A brief's API may name them otherwise (the tool
# names stay, fields may change); then this bank cannot judge the agent and must not steer the build (see speaks()).
SPEAKS = {"verify_identity": {"args": ["field", "answer"], "returns": ["verified"]},
          "get_account": {"returns": ["products"], "items": ["product_id"]},
          "create_promise": {"args": ["product_id", "amount", "date"]},
          "add_note": {"args": ["product_id", "reason"]},
          "schedule_callback": {"args": ["date", "time"]},
          "transfer_to_agent": {"args": ["queue"]},
          "close_call": {"args": ["outcome", "reason"]}}


def speaks(vocabulary, cases=()):
    """What this stand-in bank would get wrong about the brief's own API: [] when it speaks it. Also the product fields
    the test customers carry that the API's account listing does not have (they would be answered under wrong names)."""
    tools = (vocabulary or {}).get("tools") or {}
    miss = []
    if not any(t in tools for t in SPEAKS):     # a different set of services altogether: this stand-in knows none of them
        return ["none of the stand-in bank's tools exist in this API"]
    for tool, need in SPEAKS.items():
        t = tools.get(tool)
        if not t:
            continue
        for part in ("args", "returns"):
            have = set((t.get(part) or {}).keys())
            miss += ["%s.%s %s" % (tool, part, n) for n in need.get(part, []) if n not in have]
        if need.get("items"):
            items = set()
            for v in (t.get("returns") or {}).values():
                if isinstance(v, dict) and isinstance(v.get("items"), dict):
                    items |= set(v["items"].keys())
            miss += ["%s item %s" % (tool, n) for n in need["items"] if n not in items]
    return miss


class MockBank(object):
    def __init__(self, case, fail_first_promise=False):
        """Faults come from the case, in the kit's format: "faults": [{"tool": "create_promise", "fail_first_n": 1}]
        (the first n calls of that tool fail with a 500). Older cases say "fail_first": "<tool>" (= n 1). One place
        decides this, so every harness (local runner, emulator, fuzz, builder self-test) injects the same faults."""
        self.case = case
        self.faults = {}
        self.lost = {}
        for f in case.get("faults") or []:
            if f.get("tool") and f.get("kind") == "lost":   # the request never reaches the bank (gateway error page)
                self.lost[f["tool"]] = int(f.get("fail_first_n") or 1)
            elif f.get("tool"):
                self.faults[f["tool"]] = int(f.get("fail_first_n") or 1)
        if case.get("fail_first") and case["fail_first"] not in self.faults:
            self.faults[case["fail_first"]] = 1
        if fail_first_promise and "create_promise" not in self.faults:
            self.faults["create_promise"] = 1
        self.fault_calls = {}
        ident = case.get("identity", {})
        self.answers = dict(ident)
        # how many correct answers verify the customer: the case may say; otherwise two (or all, if fewer)
        self.required = int(case.get("identity_required") or min(2, len(self.answers)))
        self.passed = set()
        self.wrong_left = 3
        self.products = []
        for i, p in enumerate(case.get("products", [])):
            q = dict(p)
            q["product_id"] = "p%d" % (i + 1)
            self.products.append(q)
        self.fail_first_promise = fail_first_promise
        self.promise_calls = 0
        self.ledger = {"outcome": None, "reason": None, "promises": [], "notes": [], "callbacks": [], "transfers": [], "calls": []}
        self.closed = False

    def _log(self, tool, args, result):
        self.ledger["calls"].append({"tool": tool, "args": args, "result": result})

    def __call__(self, tool, args):
        """Returns (transport_ok, data)."""
        if self.closed:
            data = {"ok": False, "error": "call closed"}
            self._log(tool, args, data)
            return True, data
        n = self.fault_calls.get("lost:" + tool, 0)
        if n < self.lost.get(tool, 0):
            self.fault_calls["lost:" + tool] = n + 1
            return False, None                      # nothing logged: the bank never saw it
        n = self.fault_calls.get(tool, 0)
        if n < self.faults.get(tool, 0):
            self.fault_calls[tool] = n + 1
            self._log(tool, args, {"ok": False, "error": "500"})
            return False, {"ok": False, "error": "500"}
        fn = getattr(self, "t_" + tool, None)
        if fn is None:
            data = {"ok": False, "error": "unknown tool"}
            self._log(tool, args, data)
            return True, data
        transport_ok, data = fn(args or {})
        self._log(tool, args, data if transport_ok else {"ok": False, "error": "500"})
        return transport_ok, data

    def t_verify_identity(self, a):
        field, ans = a.get("field"), str(a.get("answer") or "").strip()
        if self.wrong_left <= 0:
            return True, {"ok": False, "error": "check ended", "wrong_answers_left": 0}
        if field not in self.answers:
            return True, {"ok": False, "error": "unknown field"}
        expected = str(self.answers[field])
        # the kind of answer comes from the expected value, not from the field's name (fields differ between briefs:
        # date_of_birth, birth_date, dob; postcode, postcode_outward, company_number ...)
        if re.match(r"^\d{4}-\d{2}-\d{2}$", expected):
            try:
                d = _dt.date.fromisoformat(ans)
            except ValueError:
                return True, {"ok": False, "error": "unreadable date"}
            e = _dt.date.fromisoformat(expected)
            if d == e:
                self.passed.add(field)
            elif d.year == e.year and d.month == e.day and d.day == e.month:
                return True, {"ok": True, "verified": False, "hint": "day_month_swapped", "wrong_answers_left": self.wrong_left,
                              "all_verified": False}
            else:
                self.wrong_left -= 1
                return True, {"ok": True, "verified": False, "wrong_answers_left": self.wrong_left, "all_verified": False}
        else:
            if expected.isdigit():
                if not (ans.isdigit() and len(ans) == len(expected)):
                    return True, {"ok": False, "error": "unreadable answer"}
            else:      # letters and digits (a postcode, a company number): case, spaces and punctuation do not matter
                ans, expected = re.sub(r"[^0-9A-Za-z]", "", ans).upper(), re.sub(r"[^0-9A-Za-z]", "", expected).upper()
                if not ans:
                    return True, {"ok": False, "error": "unreadable answer"}
            if ans == expected:
                self.passed.add(field)
            else:
                self.wrong_left -= 1
                return True, {"ok": True, "verified": False, "wrong_answers_left": self.wrong_left, "all_verified": False}
        return True, {"ok": True, "verified": True, "wrong_answers_left": self.wrong_left,
                      "all_verified": self._verified()}

    def _verified(self):
        return len(self.passed) >= self.required

    def t_get_account(self, a):
        if not self._verified():
            return True, {"ok": False, "error": "identity not verified"}
        return True, {"ok": True, "products": [dict(p) for p in self.products]}

    def t_create_promise(self, a):
        if not self._verified():
            return True, {"ok": False, "error": "identity not verified"}
        self.promise_calls += 1
        pid = a.get("product_id")
        try:
            amount = float(a.get("amount"))
            _dt.date.fromisoformat(str(a.get("date"))[:10])
        except (TypeError, ValueError):
            return True, {"ok": False, "error": "invalid amount or date"}
        if amount <= 0:
            return True, {"ok": False, "error": "invalid amount or date"}
        if pid not in [p["product_id"] for p in self.products]:
            return True, {"ok": False, "error": "unknown product_id"}
        if any(p["product_id"] == pid for p in self.ledger["promises"]):
            return True, {"ok": False, "error": "promise already recorded for this product"}
        self.ledger["promises"].append({"product_id": pid, "amount": float(a.get("amount")), "date": str(a.get("date"))})
        return True, {"ok": True, "promise_id": "pr_%d" % len(self.ledger["promises"])}

    def t_add_note(self, a):
        self.ledger["notes"].append({"product_id": a.get("product_id"), "reason": a.get("reason")})
        return True, {"ok": True}

    def t_schedule_callback(self, a):
        self.ledger["callbacks"].append({"date": a.get("date"), "time": a.get("time")})
        return True, {"ok": True}

    def t_transfer_to_agent(self, a):
        self.ledger["transfers"].append({"queue": a.get("queue")})
        return True, {"ok": True}

    def t_close_call(self, a):
        self.ledger["outcome"] = a.get("outcome")
        self.ledger["reason"] = a.get("reason")
        self.closed = True
        return True, {"ok": True}
