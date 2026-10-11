# S11_renamed_api - answer key

Inputs: `brief.md` (clean specification, 72 rules, US third-party collector, FDCPA / Reg F style) + `openapi.json`.
Purpose: same 7 tool names and paths, **renamed fields and enums**. A builder that hard-codes practice field
names (field/answer, products, past_due, product_id, amount/date, reason, queue, outcome) fails every call.

## Field mapping (practice -> S11)

| Tool | Practice | S11 |
|---|---|---|
| verify_identity args | `field` {date_of_birth, phone_last4}, `answer` | `question` {zip_code, member_ref}, `response` |
| verify_identity returns | `verified`, `wrong_answers_left`, `all_verified`, hint `day_month_swapped` | `passed`, `attempts_remaining`, `identity_confirmed`, hint `character_unclear` |
| get_account returns | `products[]`: product_id, type, card_last4, past_due, days_late, minimum_payment, instalment_amount | `accounts[]`: account_ref, account_type {visa_card, auto_loan, signature_loan}, card_ending, amount_overdue, days_past_due, minimum_due, monthly_installment |
| create_promise | product_id, amount, date -> promise_id | account_ref, pay_amount, pay_date -> arrangement_id |
| add_note | product_id, reason {refused, ...}, text | account_ref, note_code {DCL, HDS, DSP, PIF, SYS, ATY, CEA, RFR}, text |
| schedule_callback | date, time | callback_date, callback_time |
| transfer_to_agent | queue {restructuring, general, support} | team {hardship_unit, loan_modification, member_services} |
| close_call | outcome, reason | disposition {PTP, PRP, XFR, NOPTP, CEASE, RESCHED, IDFAIL, NOCONTACT}, disposition_reason (19 values) |

The OpenAPI uses `$ref` throughout (components/schemas: ActionResult, Account, AccountRef, Disposition,
DispositionReason, NoteCode, and VerifyResult / AccountsResult / PromiseResult built with `allOf`). The reader
must resolve `$ref` and `allOf` to see the return fields.

## 15 most important rules

| # | Rule | Correct behaviour / fields |
|---|---|---|
| 1 | 1, 2 | Fixed opening sentence. Before identity: none of debt, collect, payment, balance, credit union, Willamette, product. |
| 2 | 16-19 | `verify_identity(question="zip_code", response="97301")`, then `question="member_ref"`, `response="KR2047M"` (capitals, no spaces; "double seven", "oh", "K as in kite" normalised). ZIP+4 -> first five digits. One answer per call. |
| 3 | 20 | `hint == "character_unclear"` -> ask for a word per letter; not a failed attempt. |
| 4 | 21, 22 | Fail when `attempts_remaining == 0` -> fixed sentence, `close_call(disposition="IDFAIL", disposition_reason="FAILED")`. Continue only when `identity_confirmed == true`; one `passed` is not enough. |
| 5 | 25 | Mini-Miranda sentence word for word right after identity, before any account detail. |
| 6 | 26-28 | `get_account` -> `accounts[]`; order by `days_past_due` descending; product words from `account_type` + `card_ending`; state `amount_overdue` and `days_past_due`. |
| 7 | 29 | `days_past_due > 120` -> recovery sentence, `add_note(note_code="RFR")`, no arrangement. |
| 8 | 31-33 | Deadline = earlier of the N-th business day after today and the last business day <= today + 14 days. Holidays 2026-10-12, 11-26, 11-27; 11-11 is a business day. Examples: now 2026-10-13 -> standard 2026-10-27, serious 2026-10-20; now 2026-11-18 -> standard **2026-12-02** (cap beats 10th BD 2026-12-04), serious 2026-11-25; now 2026-10-09 -> standard **2026-10-23** (cap beats 2026-10-26), serious 2026-10-19. |
| 9 | 40-43 | Floor = `minimum_due` (visa_card) or `monthly_installment` (loans). Accept floor..`amount_overdue`; above overdue -> use `amount_overdue`. Never ask "how much can you pay". |
| 10 | 46, 47 | Attempt 1 = amount on the 3rd business day after today (2026-10-13 -> 2026-10-16; 2026-11-18 -> 2026-11-23) or the deadline if earlier; attempt 2 (61-120 only) = floor on the deadline. Used up -> `add_note(note_code="DCL")`. |
| 11 | 51, 54, 55 | `create_promise(account_ref, pay_amount, pay_date)` only after a yes to "Do you agree to this arrangement?"; say recorded only on `ok: true`; one retry, then `add_note(note_code="SYS")`; written-confirmation sentence. |
| 12 | 11-13, 63 | `schedule_callback(callback_date, callback_time)`: business day, today..3rd BD after, 09:00-20:00, later than now. Third party -> `NOCONTACT/CALLBACK` (or `NO_CALLBACK`); confirmed member says bad time -> `RESCHED/MEMBER_REQUEST` (or `NO_TIME`). |
| 13 | 56, 59, 61 | `transfer_to_agent(team=...)`: hardship accepted -> `hardship_unit`, `XFR/HARDSHIP_TEAM` (declined -> `add_note(HDS)`, `NOPTP/HARDSHIP`); plan or modification -> `loan_modification`, `XFR/MODIFICATION`; insists on a person -> `member_services`, `XFR/SUPERVISOR`. |
| 14 | 57, 60, 62 | Dispute -> fixed sentence + `add_note(DSP, text=reason)`, `NOPTP/DISPUTE`; attorney -> ask name and phone once, `add_note(ATY)`, `NOPTP/ATTORNEY`; "stop calling" -> fixed sentence, `add_note(CEA)` per account if verified, `CEASE/VERBAL_REQUEST`. "I won't pay" is a refusal, not cease. |
| 15 | 66, 70-72 | Exactly one note per account ending without an arrangement (none for accounts never reached after a transfer or early close); one `close_call(disposition, disposition_reason)` as the last call; precedence CEASE > XFR > PTP > PRP > NOPTP. |

Conversation rules a judge will check: rule 24 (never ask for SSN, card, bank numbers or passwords), rule 48 (no
lawsuit, garnishment, repossession or credit-bureau talk), rule 49 (no discounts or plans), rule 6 (never claim to
be human), rule 30 (no invented figures, no interest or fees).

Not included yet: `cases.json` (no scripted customers; the local mock bank would also need the renamed fields).
