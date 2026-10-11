"""Gold PolicyIR for Brief A, written by hand. It is the reference the reader is measured against
and the worked example of the rule language. Every element names the brief rule it comes from (src).
Run: python ir/brief_a.py  -> writes ir/brief_a.json
"""
import json, os

def T(text, src, exact=False):
    return {"text": text, "src": src, "exact": exact}

BYE = " Thank you, goodbye."

templates = {
    "opening": T("Hello, this is Freya Bank's digital assistant, and we record this call. Am I speaking with {call.title} {call.last_name}?", "A1,A2"),
    "ask_identity_again": T("Am I speaking with {call.title} {call.last_name}?", "A3"),
    "i_am_assistant": T("I am Freya Bank's digital assistant.", "A4"),
    "scam_answer": T("You can verify this call by phoning Freya Bank's customer service number.", "A43"),
    "no_info": T("I'm sorry, I don't have that information.", "A44"),
    "unclear_bye": T("I'm sorry, I could not confirm who I am speaking with." + BYE, "A3,A47"),
    "tp_ask": T("When would be a good time to reach {call.title} {call.last_name}?", "A5"),
    "tp_only_customer": T("I'm sorry, I can only speak about this with {call.title} {call.last_name}. When would be a good time to reach them?", "A5,A10"),
    "tp_ask_time": T("At what time would be good?", "A6"),
    "tp_other_time": T("I'm sorry, I can only arrange a call back for today or the next business day, between 10:00 and 19:00. Is there another time that works?", "A7"),
    "tp_callback_done": T("Thank you, we will call back on {day_label(var.cb_date)} at {var.cb_time}." + BYE, "A6,A47"),
    "tp_no_callback_bye": T("I understand, thank you for your time. Goodbye.", "A7,A47"),
    "wrong_number_bye": T("I'm sorry for the inconvenience." + BYE, "A8,A47"),
    "sorry_loss": T("I am sorry for your loss. Goodbye.", "A9", exact=False),
    "ask_dob": T("For your security, could you please tell me your date of birth?", "A11"),
    "ask_dob_again": T("That does not match our records. Could you please tell me your date of birth again?", "A12"),
    "ask_dob_repeat": T("Could you please tell me your date of birth, with the day, the month and the year?", "A11"),
    "ask_month_word": T("Could you please say your date of birth again, with the month as a word?", "A13"),
    "ask_phone": T("Thank you. Could you tell me the last four digits of the phone number we have on file for you?", "A11"),
    "ask_phone_again": T("That does not match our records. Could you please tell me the last four digits of your phone number again?", "A12"),
    "ask_phone_repeat": T("Could you please tell me the last four digits of your phone number?", "A11"),
    "protect": T("These questions protect your account.", "A15"),
    "fail_identity": T("I'm sorry, I could not verify your identity. Please use the Freya Bank mobile app or visit a branch." + BYE, "A14,A47"),
    "declined_bye": T("I understand." + BYE, "A15,A47"),
    "state_debt": T("Thank you. I am calling from the collections team about a late payment. Your {item.label} has {money(item.past_due)} dollars past due, and it is {item.days_late} days late.", "A16,A17"),
    "ask_today": T("Can you make this payment today?", "A28", exact=True),
    "offer": T("Could you pay {money(var.offer_amount)} dollars on {day_label(var.offer_date)}?", "A30"),
    "offer_floor": T("I understand. The minimum you can pay is {money(item.floor)} dollars, and the rest stays overdue. Could you pay {money(item.floor)} dollars on {day_label(var.offer_date)}?", "A26"),
    "below_floor": T("I'm sorry, I can't record an amount below {money(item.floor)} dollars. The minimum is {money(item.floor)} dollars, and the rest stays overdue. Could you pay {money(item.floor)} dollars on {day_label(var.offer_date)}?", "A27"),
    "after_deadline": T("The latest date I can record is {day_label(item.deadline)}. Could you pay {money(var.offer_amount)} dollars on {day_label(item.deadline)}?", "A23"),
    "not_business_day": T("{day_label(var.cust_date)} is not a business day. Could you pay {money(var.offer_amount)} dollars on {day_label(var.offer_date)}?", "A20"),
    "past_date": T("I can only record a date from today onwards. Which day could you pay?", "A19"),
    "ask_exact_day": T("Which exact day could you pay?", "A21"),
    "ask_day_for_amount": T("On which day could you pay {money(var.offer_amount)} dollars?", "A24"),
    "readback": T("To confirm: your {item.label}, {money(var.pa_amount)} dollars on {day_label(var.pa_date)}. Do you confirm?", "A34", exact=False),
    "recorded": T("Your promise is recorded. You will receive a text message confirming this promise." + BYE, "A37,A38,A47"),
    "record_failed": T("I'm sorry, I could not record your promise because of a technical problem." + BYE, "A37,A47"),
    "cannot_change": T("A recorded promise can't be changed in this call. You can change it in the mobile app.", "A36"),
    "paid_bye": T("Thank you for letting me know. Payments can take one business day to appear." + BYE, "A39,A47"),
    "dispute_bye": T("I understand, thank you for letting me know." + BYE, "A40,A47"),
    "sympathy_offer": T("I'm sorry to hear that. Would you like me to connect you with our customer support team?", "A32"),
    "transfer_support": T("I will connect you with our customer support team now." + BYE, "A32,A47"),
    "transfer_restructuring": T("I will transfer you to a colleague who can help you with that." + BYE, "A41,A47"),
    "human_first": T("I can help you with this. Is there anything I can help you with first?", "A42"),
    "transfer_human": T("I will transfer you to a colleague now." + BYE, "A42,A47"),
    "refused_bye": T("I understand." + BYE, "A31,A47"),
    "hardship_bye": T("I understand." + BYE, "A32,A47"),
    "not_want_once": T("I understand. It will only take a moment.", "A45"),
}

intents = [
    {"id": "deceased", "description": "the person says the customer has died", "priority": 99, "src": "A9"},
    {"id": "wrong_number", "description": "the person says this number does not belong to the customer", "priority": 98, "src": "A8"},
    {"id": "third_party", "description": "the person who answered is not the customer (a relative, partner, colleague or someone else)", "priority": 97, "src": "A4-A5"},
    {"id": "hardship", "description": "the customer mentions illness, a death in the family or job loss", "priority": 90, "src": "A32"},
    {"id": "restructure", "description": "the customer asks for a new payment plan or lower instalments (not: a discount or a waiver, rule 33)", "priority": 80, "src": "A41"},
    {"id": "paid", "description": "the customer says they already paid this past-due amount", "priority": 76, "src": "A39"},
    {"id": "dispute", "description": "the customer says the debt is not theirs, they never had the product, or it was closed or paid off in the past", "priority": 77, "src": "A40"},
    {"id": "human", "description": "the customer asks to speak to a human or a person", "priority": 70, "src": "A42"},
    {"id": "not_want_talk", "description": "the customer says they do not want to talk", "priority": 60, "src": "A45"},
    {"id": "ask_bot", "description": "the customer asks whether they are talking to a robot, a bot or an AI", "priority": 55, "src": "A4"},
    {"id": "ask_scam", "description": "the customer asks whether this is a scam or doubts the call is real", "priority": 54, "src": "A43"},
    {"id": "ask_reason", "description": "the customer asks who is calling or what the call is about instead of answering", "priority": 50, "src": "A3,A15"},
    {"id": "other_question", "description": "the customer asks a question the agent has no information for", "priority": 40, "src": "A44"},
    {"id": "confirm_identity", "description": "the person confirms they are the customer: yes, that's me, speaking, or says the customer's own name", "priority": 30, "src": "A3"},
    {"id": "decline", "description": "the customer refuses to answer the security question", "priority": 30, "src": "A15"},
    {"id": "too_much", "description": "the customer says the full amount is too much", "priority": 25, "src": "A26"},
    {"id": "vague_date", "description": "the customer gives a vague period instead of a day (next week, end of the month, when my salary comes)", "priority": 24, "src": "A21"},
    {"id": "yes", "description": "the customer agrees or confirms", "priority": 20, "src": "A34"},
    {"id": "no", "description": "the customer says no, refuses or does not answer the question", "priority": 19, "src": "A30"},
]

ANSWERS = [   # side questions answered anywhere, then the pending question is repeated
    {"id": "G_bot", "phase": "*", "on": "intent:ask_bot", "do": [{"say": "i_am_assistant"}, {"reprompt": True}], "priority": 5, "src": "A4"},
    {"id": "G_scam", "phase": "*", "on": "intent:ask_scam", "do": [{"say": "scam_answer"}, {"reprompt": True}], "priority": 5, "src": "A43"},
    {"id": "G_other", "phase": "*", "not_phase": ["identify", "verify_dob", "verify_phone"], "on": "intent:other_question", "do": [{"say": "no_info"}, {"reprompt": True}], "priority": 5, "src": "A44"},
]

POST = ["state_debt", "negotiate", "confirm", "hardship_offer", "human_offer"]

rules = ANSWERS + [
    # ---------------------------------------------------------------- who is on the line (A1-A3, A8, A9)
    {"id": "I0", "phase": "identify", "on": "enter", "do": [{"say": "opening", "prompt": True}], "src": "A1,A2"},
    {"id": "I_conf", "phase": "identify", "on": "intent:confirm_identity", "do": [{"goto": "verify_dob"}], "src": "A3"},
    {"id": "I_tp", "phase": "identify", "on": "intent:third_party", "do": [{"goto": "third_party"}], "src": "A5"},
    {"id": "I_wrong", "phase": ["identify", "third_party"], "on": "intent:wrong_number", "do": [{"say": "wrong_number_bye"}, {"close": {"outcome": "'not_reached'", "reason": "'wrong_number'"}}], "src": "A8"},
    {"id": "I_dead", "phase": ["identify", "third_party"], "on": "intent:deceased", "do": [{"say": "sorry_loss"}, {"close": {"outcome": "'not_reached'", "reason": "'deceased'"}}], "src": "A9"},
    {"id": "I_nowant", "phase": ["identify", "verify_dob", "verify_phone"], "on": "intent:not_want_talk", "do": [
        {"incr": "var.nowant"},
        {"if": "var.nowant >= 2", "then": [{"say": "declined_bye"}, {"close": {"outcome": "'not_verified'", "reason": "'declined'"}}],
         "else": [{"say": "not_want_once"}, {"reprompt": True}]}], "src": "A45"},
    {"id": "I_q", "phase": "identify", "on": "intent:ask_reason", "do": [{"say": "i_am_assistant"}, {"run": "identify_ask_again"}], "src": "A3"},
    {"id": "I_bot", "phase": "identify", "on": "intent:ask_bot", "do": [{"say": "i_am_assistant"}, {"run": "identify_ask_again"}], "priority": 6, "src": "A3,A4"},
    {"id": "I_scam", "phase": "identify", "on": "intent:ask_scam", "do": [{"say": "scam_answer"}, {"run": "identify_ask_again"}], "priority": 6, "src": "A3,A43"},
    {"id": "I_other", "phase": "identify", "on": "user", "do": [{"run": "identify_ask_again"}], "src": "A3"},

    # ---------------------------------------------------------------- third party (A5-A10)
    {"id": "T0", "phase": "third_party", "on": "enter", "do": [{"say": "tp_ask", "prompt": True}], "src": "A5"},
    {"id": "T_q", "phase": "third_party", "on": "intent:ask_reason", "do": [{"say": "tp_only_customer", "prompt": True}], "src": "A5,A10"},
    {"id": "T_cb", "phase": "third_party", "on": "user", "if": "is_set(slot.callback_date) or is_set(slot.callback_time)", "do": [
        {"set": {"var.cb_date": "slot.callback_date if is_set(slot.callback_date) else var.cb_date",
                 "var.cb_time": "slot.callback_time if is_set(slot.callback_time) else var.cb_time"}},
        {"if": "not is_set(var.cb_date) or not is_set(var.cb_time)", "then": [{"say": "tp_ask_time", "prompt": True}], "else": [{"run": "check_callback"}]}], "src": "A6"},
    {"id": "T_refuse", "phase": "third_party", "on": "intent:no", "do": [{"say": "tp_no_callback_bye"}, {"close": {"outcome": "'not_reached'", "reason": "'no_callback'"}}], "src": "A7"},
    {"id": "T_other", "phase": "third_party", "on": "user", "do": [{"say": "tp_only_customer", "prompt": True}], "priority": -1, "src": "A5,A10"},

    # ---------------------------------------------------------------- identity (A11-A15)
    {"id": "V0", "phase": "verify_dob", "on": "enter", "do": [{"say": "ask_dob", "prompt": True}], "src": "A11"},
    {"id": "V_dob", "phase": "verify_dob", "on": "user", "if": "is_set(slot.id_date_of_birth)", "do": [
        {"call": "verify_identity", "args": {"customer_id": "call.customer_id", "field": "'date_of_birth'", "answer": "slot.id_date_of_birth"}}], "src": "A11"},
    {"id": "V_dob_res", "phase": "verify_dob", "on": "tool:verify_identity", "do": [{"run": "after_verify_dob"}], "src": "A12-A14"},
    {"id": "W0", "phase": "verify_phone", "on": "enter", "do": [{"say": "ask_phone", "prompt": True}], "src": "A11"},
    {"id": "W_ph", "phase": "verify_phone", "on": "user", "if": "is_set(slot.id_phone_last4)", "do": [
        {"call": "verify_identity", "args": {"customer_id": "call.customer_id", "field": "'phone_last4'", "answer": "slot.id_phone_last4"}}], "src": "A11"},
    {"id": "W_res", "phase": "verify_phone", "on": "tool:verify_identity", "do": [{"run": "after_verify_phone"}], "src": "A12-A14"},
    {"id": "V_decl", "phase": ["verify_dob", "verify_phone"], "on": "intent:decline", "do": [{"run": "declined"}], "src": "A15"},
    {"id": "V_reason", "phase": ["verify_dob", "verify_phone"], "on": "intent:ask_reason", "do": [{"run": "declined"}], "src": "A15"},
    {"id": "V_other", "phase": ["verify_dob", "verify_phone"], "on": "user", "do": [{"reprompt": True}], "priority": -1, "src": "A11"},

    # ---------------------------------------------------------------- account and debt (A16, A17, A28)
    {"id": "A0", "phase": "account", "on": "enter", "do": [{"call": "get_account", "args": {"customer_id": "call.customer_id"}}], "src": "A16"},
    {"id": "A_res", "phase": "account", "on": "tool:get_account", "if": "result.ok and len(result.products) > 0", "do": [
        {"set": {"items": "copy_list(result.products)"}},
        {"for_each_item": [{"set": {"item.label": "product_label(item)", "item.floor": "product_floor(item)",
                                     "item.band": "band_name(item.days_late)", "item.attempts_limit": "band_attempts(item.days_late)",
                                     "item.deadline": "add_business_days(today, band_deadline(item.days_late))", "item.attempts": "0"}}]},
        {"set_cursor": "0"}, {"goto": "state_debt"}], "src": "A16-A18,A25"},
    {"id": "A_fail", "phase": "account", "on": "tool:get_account", "do": [{"say": "record_failed"}, {"close": {"outcome": "'no_promise'", "reason": "'service_error'"}}], "priority": -1, "src": "A44"},
    {"id": "S0", "phase": "state_debt", "on": "enter", "do": [
        {"say": "state_debt"}, {"set": {"var.offer_amount": "item.past_due", "var.offer_date": "today", "var.offer_kind": "'today'"}},
        {"say": "ask_today", "prompt": True}, {"goto": "negotiate_wait"}], "src": "A17,A24,A28"},

    # ---------------------------------------------------------------- negotiation (A19-A33)
    {"id": "N_hard", "phase": ["negotiate_wait", "confirm"], "on": "intent:hardship", "do": [{"set": {"var.hardship": "true"}}, {"say": "sympathy_offer", "prompt": True}, {"goto": "hardship_offer"}], "src": "A32"},
    {"id": "N_restr", "phase": ["negotiate_wait", "confirm", "hardship_offer"], "on": "intent:restructure", "do": [
        {"say": "transfer_restructuring"}, {"call": "transfer_to_agent", "args": {"customer_id": "call.customer_id", "queue": "'restructuring'"}},
        {"close": {"outcome": "'transferred'", "reason": "'restructuring'"}}], "src": "A41"},
    {"id": "N_paid", "phase": ["negotiate_wait", "confirm"], "on": "intent:paid", "do": [{"run": "end_paid"}], "src": "A39"},
    {"id": "N_disp", "phase": ["negotiate_wait", "confirm"], "on": "intent:dispute", "do": [{"run": "end_dispute"}], "src": "A40"},
    {"id": "N_human", "phase": ["negotiate_wait", "confirm", "hardship_offer"], "on": "intent:human", "do": [
        {"incr": "var.human_asks"},
        {"if": "var.human_asks >= 2", "then": [{"say": "transfer_human"}, {"call": "transfer_to_agent", "args": {"customer_id": "call.customer_id", "queue": "'general'"}},
                                                {"close": {"outcome": "'transferred'", "reason": "'human'"}}],
         "else": [{"say": "human_first", "prompt": True}]}], "src": "A42"},
    {"id": "N_nowant", "phase": ["negotiate_wait", "confirm"], "on": "intent:not_want_talk", "do": [
        {"incr": "var.nowant"},
        {"if": "var.nowant >= 2", "then": [{"say": "refused_bye"}, {"close": {"outcome": "'no_promise'", "reason": "'refused'"}}],
         "else": [{"say": "not_want_once"}, {"reprompt": True}]}], "src": "A45"},
    {"id": "N_vague", "phase": "negotiate_wait", "on": "intent:vague_date", "if": "not is_set(slot.promise_date)", "do": [
        {"if": "not item.asked_exact", "then": [{"set": {"item.asked_exact": "true"}}, {"say": "ask_exact_day", "prompt": True}],
         "else": [{"set": {"var.offer_date": "item.deadline", "var.offer_kind": "'deadline'"}}, {"say": "offer", "prompt": True}]}], "src": "A21"},
    {"id": "N_eval", "phase": "negotiate_wait", "on": "user", "if": "is_set(slot.promise_date) or is_set(slot.promise_amount)", "do": [{"run": "evaluate_proposal"}], "priority": 10, "src": "A19-A27,A29"},
    {"id": "N_yes", "phase": "negotiate_wait", "on": "intent:yes", "if": "not is_set(slot.promise_date) and not is_set(slot.promise_amount)", "do": [
        {"set": {"var.pa_amount": "var.offer_amount", "var.pa_date": "var.offer_date"}}, {"run": "accept"}], "src": "A34"},
    {"id": "N_toomuch", "phase": "negotiate_wait", "on": "intent:too_much", "if": "not item.floor_offered and not var.hardship and not is_set(slot.promise_amount)", "do": [
        {"set": {"item.too_much": "true", "item.floor_offered": "true", "var.offer_amount": "item.floor"}}, {"say": "offer_floor", "prompt": True}], "src": "A26"},
    {"id": "N_refuse", "phase": "negotiate_wait", "on": "user", "do": [{"run": "refusal"}], "priority": -5, "src": "A30,A31"},

    # ---------------------------------------------------------------- hardship and human (A32, A42)
    {"id": "H_yes", "phase": "hardship_offer", "on": "intent:yes", "do": [
        {"say": "transfer_support"}, {"call": "transfer_to_agent", "args": {"customer_id": "call.customer_id", "queue": "'support'"}},
        {"close": {"outcome": "'transferred'", "reason": "'support'"}}], "src": "A32"},
    {"id": "H_prop", "phase": "hardship_offer", "on": "user", "if": "is_set(slot.promise_date) or is_set(slot.promise_amount)", "do": [{"goto": "negotiate_wait"}, {"refire": "user"}], "priority": 10, "src": "A32"},
    {"id": "H_no", "phase": "hardship_offer", "on": "user", "do": [{"run": "end_hardship"}], "priority": -5, "src": "A32"},

    # ---------------------------------------------------------------- confirm and record (A34-A38)
    {"id": "C0", "phase": "confirm", "on": "enter", "do": [{"say": "readback", "prompt": True}], "src": "A34"},
    {"id": "C_change", "phase": "confirm", "on": "user", "if": "(is_set(slot.promise_date) and slot.promise_date != var.pa_date) or (is_set(slot.promise_amount) and slot.promise_amount != var.pa_amount)", "do": [{"goto": "negotiate_wait"}, {"refire": "user"}], "priority": 10, "src": "A35"},
    {"id": "C_yes", "phase": "confirm", "on": "intent:yes", "if": "not is_set(slot.promise_date) and not is_set(slot.promise_amount)", "do": [
        {"call": "create_promise", "args": {"customer_id": "call.customer_id", "product_id": "item.product_id", "amount": "var.pa_amount", "date": "var.pa_date"}}], "src": "A34"},
    {"id": "C_ok", "phase": "confirm", "on": "tool:create_promise", "if": "result.ok", "do": [
        {"set": {"var.promises": "(var.promises or 0) + 1"}}, {"say": "recorded"}, {"close": {"outcome": "'promise'"}}], "src": "A37,A38"},
    {"id": "C_fail", "phase": "confirm", "on": "tool:create_promise", "do": [
        {"incr": "var.promise_fail"},
        {"if": "var.promise_fail < 2", "then": [{"call": "create_promise", "args": {"customer_id": "call.customer_id", "product_id": "item.product_id", "amount": "var.pa_amount", "date": "var.pa_date"}}],
         "else": [{"say": "record_failed"}, {"close": {"outcome": "'no_promise'", "reason": "'service_error'"}}]}], "priority": -1, "src": "A37"},
    {"id": "C_no", "phase": "confirm", "on": "user", "do": [{"goto": "negotiate_wait"}, {"run": "refusal"}], "priority": -5, "src": "A35"},
]

procedures = {
    "identify_ask_again": [
        {"incr": "var.identify_asks"},
        {"if": "var.identify_asks >= 2", "then": [{"say": "unclear_bye"}, {"close": {"outcome": "'not_reached'", "reason": "'unclear'"}}],
         "else": [{"say": "ask_identity_again", "prompt": True}]}],
    "check_callback": [
        {"if": "(var.cb_date == today or var.cb_date == next_business_day(today)) and time_in_window(var.cb_time, '10:00', '19:00') and (var.cb_date > today or var.cb_time > now_time())",
         "then": [{"call": "schedule_callback", "args": {"customer_id": "call.customer_id", "date": "var.cb_date", "time": "var.cb_time"}},
                  {"say": "tp_callback_done"}, {"close": {"outcome": "'not_reached'", "reason": "'callback'"}}],
         "else": [{"incr": "var.cb_bad"},
                  {"if": "var.cb_bad >= 2", "then": [{"say": "tp_no_callback_bye"}, {"close": {"outcome": "'not_reached'", "reason": "'no_callback'"}}],
                   "else": [{"set": {"var.cb_date": "None", "var.cb_time": "None"}}, {"say": "tp_other_time", "prompt": True}]}]}],
    "after_verify_dob": [
        {"if": "result.verified", "then": [{"goto": "verify_phone"}],
         "else": [{"if": "result.hint == 'day_month_swapped'", "then": [{"say": "ask_month_word", "prompt": True}],
                   "else": [{"if": "result.ok == false and not is_set(result.wrong_answers_left)", "then": [{"say": "ask_dob_repeat", "prompt": True}],
                             "else": [{"incr": "var.wrong"}, {"run": "wrong_answer", "_": "dob"}]}]}]}],
    "after_verify_phone": [
        {"if": "result.verified or result.all_verified", "then": [{"set": {"flag.verified": "true"}}, {"goto": "account"}],
         "else": [{"if": "result.ok == false and not is_set(result.wrong_answers_left)", "then": [{"say": "ask_phone_repeat", "prompt": True}],
                   "else": [{"incr": "var.wrong"}, {"run": "wrong_answer_phone"}]}]}],
    "wrong_answer": [
        {"if": "var.wrong >= 3 or result.wrong_answers_left == 0", "then": [{"say": "fail_identity"}, {"close": {"outcome": "'not_verified'", "reason": "'failed'"}}],
         "else": [{"say": "ask_dob_again", "prompt": True}]}],
    "wrong_answer_phone": [
        {"if": "var.wrong >= 3 or result.wrong_answers_left == 0", "then": [{"say": "fail_identity"}, {"close": {"outcome": "'not_verified'", "reason": "'failed'"}}],
         "else": [{"say": "ask_phone_again", "prompt": True}]}],
    "declined": [
        {"incr": "var.declines"},
        {"if": "var.declines >= 2", "then": [{"say": "declined_bye"}, {"close": {"outcome": "'not_verified'", "reason": "'declined'"}}],
         "else": [{"say": "protect"}, {"reprompt": True}]}],
    "evaluate_proposal": [
        {"set": {"var.cust_amount": "slot.promise_amount if is_set(slot.promise_amount) else None",
                 "var.cust_date": "slot.promise_date if is_set(slot.promise_date) else None"}},
        {"if": "is_set(var.cust_amount) and var.cust_amount < item.floor", "then": [
            {"if": "not item.floor_offered", "then": [
                {"set": {"item.floor_offered": "true", "var.offer_amount": "item.floor",
                         "var.offer_date": "var.cust_date if is_set(var.cust_date) and is_business_day(var.cust_date) and date_ge(var.cust_date, today) and date_le(var.cust_date, item.deadline) else var.offer_date"}},
                {"say": "below_floor", "prompt": True}],
             "else": [{"run": "refusal"}]}],
         "else": [
            {"set": {"var.offer_amount": "min(var.cust_amount, item.past_due) if is_set(var.cust_amount) else var.offer_amount"}},
            {"if": "not is_set(var.cust_date)", "then": [
                {"if": "is_set(var.cust_amount) and var.offer_kind == 'today'", "then": [{"say": "ask_day_for_amount", "prompt": True}],
                 "else": [{"set": {"var.pa_amount": "var.offer_amount", "var.pa_date": "var.offer_date"}}, {"run": "accept"}]}],
             "else": [
                {"if": "date_lt(var.cust_date, today)", "then": [{"say": "past_date", "prompt": True}],
                 "else": [{"if": "date_lt(item.deadline, var.cust_date)", "then": [
                              {"set": {"var.offer_date": "item.deadline", "var.offer_kind": "'deadline'"}}, {"say": "after_deadline", "prompt": True}],
                          "else": [{"if": "not is_business_day(var.cust_date)", "then": [
                                       {"set": {"var.offer_date": "min_date(next_business_day(var.cust_date), item.deadline)", "var.offer_kind": "'next_business_day'"}},
                                       {"say": "not_business_day", "prompt": True}],
                                   "else": [{"set": {"var.pa_amount": "var.offer_amount", "var.pa_date": "var.cust_date"}}, {"run": "accept"}]}]}]}]}]}],
    "refusal": [
        {"if": "var.hardship", "then": [{"run": "end_hardship"}],
         "else": [{"if": "item.attempts < item.attempts_limit", "then": [
                      {"incr": "item.attempts"},
                      {"if": "item.attempts == 1", "then": [
                          {"set": {"var.offer_amount": "item.floor if item.too_much else item.past_due",
                                   "var.offer_date": "last_business_day_of_week(today, 1) if last_business_day_of_week(today, 0) == today else last_business_day_of_week(today, 0)",
                                   "var.offer_kind": "'attempt1'"}}],
                       "else": [{"set": {"var.offer_amount": "item.floor", "var.offer_date": "item.deadline", "var.offer_kind": "'attempt2'"}}]},
                      {"say": "offer", "prompt": True}],
                  "else": [{"run": "end_refused"}]}]}],
    "accept": [{"goto": "confirm"}],
    "end_refused": [{"say": "refused_bye"}, {"close": {"outcome": "'no_promise'", "reason": "'refused'"}}],
    "end_hardship": [{"say": "hardship_bye"}, {"close": {"outcome": "'no_promise'", "reason": "'hardship'"}}],
    "end_paid": [{"say": "paid_bye"}, {"close": {"outcome": "'paid'"}}],
    "end_dispute": [{"say": "dispute_bye"}, {"close": {"outcome": "'no_promise'", "reason": "'dispute'"}}],
}

functions = {
    "product_label": {"params": ["p"], "expr": "('credit card ending ' + str_(p.card_last4)) if p.type == 'credit_card' else ('personal loan' if p.type == 'personal_loan' else ('car loan' if p.type == 'car_loan' else p.type))", "src": "A17"},
    "product_floor": {"params": ["p"], "expr": "p.minimum_payment if p.type == 'credit_card' else p.instalment_amount", "src": "A25"},
    "band_name": {"params": ["d"], "expr": "'early' if between(d, 1, 7) else ('late' if between(d, 8, 45) else None)", "src": "A18"},
    "band_deadline": {"params": ["d"], "expr": "12 if between(d, 1, 7) else 7", "src": "A18"},
    "band_attempts": {"params": ["d"], "expr": "1 if between(d, 1, 7) else 2", "src": "A18"},
    "min_date": {"params": ["a", "b"], "expr": "a if date_le(a, b) else b", "src": ""},
    "now_time": {"params": [], "expr": "time_of(call.now)", "src": "A6"},
}

IR = {
    "version": 0, "name": "brief_a",
    "calendar": {"workdays": ["Mon", "Tue", "Wed", "Thu", "Fri"], "holidays": ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"], "src": "A7"},
    "time": {"now_var": "now"},
    "vocabulary": {"tools": {"verify_identity": {}, "get_account": {}, "create_promise": {"write": True}, "add_note": {"write": True},
                             "schedule_callback": {"write": True}, "transfer_to_agent": {"write": True}, "close_call": {"write": True}}},
    "closing": {"tool": "close_call", "extra_args": {"customer_id": "call.customer_id"}},
    "initial_phase": "identify",
    "slots": {"id_date_of_birth": {"kind": "birth_date", "numeric_order": "DMY", "phases": ["verify_dob"], "src": "A11"},
              "id_phone_last4": {"kind": "digits", "length": 4, "phases": ["verify_phone"], "src": "A11"},
              "promise_date": {"kind": "date", "phases": ["negotiate_wait", "confirm", "hardship_offer"], "src": "A19"},
              "promise_amount": {"kind": "amount", "phases": ["negotiate_wait", "confirm", "hardship_offer"], "src": "A24"},
              "callback_date": {"kind": "date", "phases": ["third_party"], "src": "A6"},
              "callback_time": {"kind": "time", "phases": ["third_party"], "src": "A6"}},
    "templates": templates, "intents": intents, "rules": rules, "procedures": procedures, "functions": functions,
}

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brief_a.json")
    json.dump(IR, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", out, len(rules), "rules", len(templates), "templates")
