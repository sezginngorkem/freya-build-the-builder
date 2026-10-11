"""Gold PolicyIR for Brief B: Brief A plus the multi-product rules (B1-B11), written as a patch on A.
Every rule of A applies unless a rule below replaces it. The patch is explicit so it doubles as a
worked example of applying an amending document.
Run: python ir/brief_b.py  -> writes ir/brief_b.json
"""
import copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brief_a import IR as A, T, BYE

IR = copy.deepcopy(A)
IR["name"] = "brief_b"

IR["templates"].update({
    "state_intro_multi": T("Thank you. I am calling from the collections team about late payments.", "A17,B2"),
    "state_item": T("Your {item.label} has {money(item.past_due)} dollars past due, and it is {item.days_late} days late.", "A17,B2"),
    "ask_all_today": T("Can you pay all of them today?", "B4"),
    "item_start": T("Let's look at your {item.label}.", "B4"),
    "item_paid_ack": T("Thank you for letting me know. Payments can take one business day to appear.", "A39,B9"),
    "item_dispute_ack": T("I understand, thank you for letting me know.", "A40,B9"),
    "readback_intro": T("To confirm:", "B7"),
    "readback_item": T("your {item.label}, {money(item.pa_amount)} dollars on {day_label(item.pa_date)}.", "B7"),
    "readback_item_capped": T("your {item.label}, {money(item.pa_amount)} dollars on {day_label(item.pa_date)}, which is the latest date I can record for it.", "B6,B7"),
    "readback_ask": T("Do you confirm?", "A34,B7", exact=True),
    "item_record_failed": T("I'm sorry, I could not record the promise for your {item.label} because of a technical problem.", "A37,B11"),
    "recorded_multi": T("{'Your promises are' if count_set(items, 'recorded') > 1 else 'Your promise is'} recorded. You will receive a text message confirming this promise.", "A38", exact=False),
    "item_accepted": T("Thank you, noted.", "B4"),
    "closing_bye": T("Thank you, goodbye.", "A47"),
})

# ---------------------------------------------------------------- replaced rules
def replace_rule(rid, new):
    for i, r in enumerate(IR["rules"]):
        if r["id"] == rid:
            IR["rules"][i] = new
            return
    raise KeyError(rid)

for r in IR["rules"]:
    if r["id"] == "A_res":                                   # B1-B3: state every product first
        r["do"][-1] = {"goto": "state_all"}
        r["src"] = "A16,B1-B3"
    if r["id"] in ("N_hard", "N_restr", "N_human", "N_nowant") and isinstance(r["phase"], list):
        r["phase"] = r["phase"] + ["negotiate_all", "confirm_all"]
    if r["id"] == "N_restr":                                  # B10: transfer; nothing more is recorded; no notes
        r["src"] = "A41,B10"

IR["rules"] += [
    {"id": "B_S0", "phase": "state_all", "on": "enter", "do": [
        {"say": "state_intro_multi"}, {"for_each_item": [{"say": "state_item"}]},
        {"say": "ask_all_today", "prompt": True}, {"goto": "negotiate_all"}], "src": "B2,B4"},
    {"id": "B_allyes", "phase": "negotiate_all", "on": "intent:yes", "if": "not is_set(slot.promise_date) and not is_set(slot.promise_amount)", "do": [
        {"for_each_item": [{"set": {"item.pa_amount": "item.past_due", "item.pa_date": "today"}}]}, {"goto": "confirm_all"}], "src": "B4,B7"},
    {"id": "B_onedate", "phase": "negotiate_all", "on": "user", "if": "is_set(slot.promise_date) and not is_set(slot.promise_amount)", "do": [
        {"set": {"var.cust_date": "slot.promise_date"}},
        {"if": "date_lt(var.cust_date, today)", "then": [{"say": "past_date", "prompt": True}],
         "else": [{"for_each_item": [{"set": {
                      "item.pa_amount": "item.past_due",
                      "item.capped": "date_lt(item.deadline, var.cust_date)",
                      "item.pa_date": "item.deadline if date_lt(item.deadline, var.cust_date) else (var.cust_date if is_business_day(var.cust_date) else min_date(next_business_day(var.cust_date), item.deadline))"}}]},
                  {"goto": "confirm_all"}]}], "priority": 10, "src": "B6"},
    {"id": "B_toitems", "phase": "negotiate_all", "on": "user", "do": [{"set_cursor": "0"}, {"goto": "negotiate_item"}], "priority": -5, "src": "B4"},
    {"id": "B_item0", "phase": "negotiate_item", "on": "enter", "do": [
        {"say": "item_start"}, {"run": "refusal"}, {"goto": "negotiate_wait"}], "src": "B4,B5"},
    {"id": "B_wrap", "phase": "wrap_up", "on": "enter", "do": [
        {"if": "count_set(items, 'pa_date') > 0", "then": [{"goto": "confirm_all"}], "else": [{"goto": "record_notes"}]}], "src": "B7,B8"},
    {"id": "B_c0", "phase": "confirm_all", "on": "enter", "do": [
        {"say": "readback_intro"},
        {"for_each_item": [{"if": "is_set(item.pa_date)", "then": [{"if": "item.capped", "then": [{"say": "readback_item_capped"}], "else": [{"say": "readback_item"}]}]}]},
        {"say": "readback_ask", "prompt": True}], "src": "B6,B7"},
    {"id": "B_cyes", "phase": "confirm_all", "on": "intent:yes", "if": "not is_set(slot.promise_date) and not is_set(slot.promise_amount)", "do": [{"goto": "recording"}], "src": "B7"},
    {"id": "B_cno", "phase": "confirm_all", "on": "user", "do": [
        {"for_each_item": [{"if": "is_set(item.pa_date)", "then": [{"set": {"item.pa_date": "None", "item.end_reason": "'refused'"}}]}]},
        {"goto": "record_notes"}], "priority": -5, "src": "A35"},
    {"id": "B_rec0", "phase": "recording", "on": "enter", "do": [{"run": "record_next"}], "src": "B7"},
    {"id": "B_rec_res", "phase": "recording", "on": "tool:create_promise", "do": [
        {"if": "result.ok", "then": [{"set": {"item.recorded": "true"}}, {"run": "record_next"}],
         "else": [{"incr": "item.fail"},
                  {"if": "item.fail < 2", "then": [{"run": "record_current"}],
                   "else": [{"set": {"item.failed": "true", "item.end_reason": "'service_error'"}}, {"say": "item_record_failed"}, {"run": "record_next"}]}]}],
        "src": "A37,B11"},
    {"id": "B_n0", "phase": "record_notes", "on": "enter", "do": [{"run": "note_next"}], "src": "B8"},
    {"id": "B_n_res", "phase": "record_notes", "on": "tool:add_note", "do": [{"set": {"item.noted": "true"}}, {"run": "note_next"}], "src": "B8"},
    {"id": "B_close", "phase": "closing", "on": "enter", "do": [
        {"if": "count_set(items, 'recorded') > 0", "then": [{"say": "recorded_multi"}]},
        {"say": "closing_bye"},
        {"close": {"outcome": "'promise' if count_set(items, 'recorded') > 0 else ('paid' if all_where(items, 'end_reason', 'paid') else 'no_promise')",
                   "reason": "None if count_set(items, 'recorded') > 0 or all_where(items, 'end_reason', 'paid') else first_where_not(items, 'end_reason', 'paid').end_reason"}}],
        "src": "A46,B-closing"},
]

NEXT = {"next_item": "negotiate_item", "done": "wrap_up"}
IR["procedures"].update({
    "accept": [{"set": {"item.pa_amount": "var.pa_amount", "item.pa_date": "var.pa_date", "item.capped": "false"}},
               {"if": "var_cursor_has_next()", "then": [{"say": "item_accepted"}]}, NEXT],
    "end_refused": [{"set": {"item.end_reason": "'refused'"}}, NEXT],
    "end_hardship": [{"set": {"item.end_reason": "'hardship'"}}, NEXT],
    "end_paid": [{"say": "item_paid_ack"}, {"set": {"item.end_reason": "'paid'"}}, NEXT],
    "end_dispute": [{"say": "item_dispute_ack"}, {"set": {"item.end_reason": "'dispute'"}}, NEXT],
    "record_next": [
        {"set": {"var.ri": "find_index(items, ['pa_date'], ['recorded', 'failed'])"}},
        {"if": "var.ri < 0", "then": [{"goto": "record_notes"}],
         "else": [{"set_cursor": "var.ri"}, {"run": "record_current"}]}],
    "record_current": [{"call": "create_promise", "args": {"customer_id": "call.customer_id", "product_id": "item.product_id", "amount": "item.pa_amount", "date": "item.pa_date"}}],
    "note_next": [
        {"set": {"var.ni": "find_index(items, [], ['recorded', 'noted'])"}},
        {"if": "var.ni < 0", "then": [{"goto": "closing"}],
         "else": [{"set_cursor": "var.ni"}, {"set": {"item.end_reason": "item.end_reason if is_set(item.end_reason) else 'refused'"}},
                  {"call": "add_note", "args": {"customer_id": "call.customer_id", "product_id": "item.product_id", "reason": "item.end_reason"}}]}],
})
IR["functions"]["var_cursor_has_next"] = {"params": [], "expr": "find_index(items, [], ['pa_date', 'end_reason']) >= 0 and len(items) > 1", "src": "B4"}
IR["slots"]["promise_date"]["phases"] += ["negotiate_all", "confirm_all"]
IR["slots"]["promise_amount"]["phases"] += ["negotiate_all", "confirm_all"]

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brief_b.json")
    json.dump(IR, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", out, len(IR["rules"]), "rules")
