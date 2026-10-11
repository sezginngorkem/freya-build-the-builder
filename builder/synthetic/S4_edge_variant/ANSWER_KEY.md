# ANSWER KEY: S4_edge_variant (Kestrel Savings Bank, Brief A variant with flipped edges)

Inputs: `brief.md`, `openapi.json` (same tools/enums as the kit, `add_note` present but never used). Cases: `cases.json` (14). All cases use `now = 2026-11-20T16:00` (**Friday**).

## Differences from Brief A (each one is a trap for a reader that pattern-matches A)
| # | Brief A | S4 |
|---|---|---|
| 1 | 3 wrong answers in total | **2** wrong answers in total; the mock bank still allows 3, so the agent must count itself |
| 2 | deadline = Nth business day | early band = today + 10 **calendar** days, rolled **forward** if not a business day |
| 3 | "next Friday" = following calendar week; "this" = current week | "this X" = first X after today; "next X" = 7 days after "this X"; bare weekday = "this" |
| 4 | callback 10:00–19:00 both included | after 10:00 and before 19:00, **neither** included |
| 5 | promise date today or later | **after today** (today excluded); deadline included |
| 6 | amount from floor (incl.) | above floor; floor itself not enough; counter-offer = floor + 1.00 |
| 7 | early 1 attempt, late 2 | early **0** attempts, late 2 (full on deadline, then floor+1 on deadline) |
| 8 | first ask "Can you make this payment today?" | "Can you make this payment on {next business day}?" |
| 9 | precedence 32 before 30/41 | **33 (dispute) before 32 (paid)**; **34 (restructuring) before 35 (human)**; 36 (hardship) before 27 |
| 10 | free wording | exact sentences: opening, robot answer, third-party refusal, identity failure, "Payments made today do not need a promise.", promise saved sentence, goodbye |

## Dates for now = Fri 2026-11-20
Holidays: 2026-11-26, 2026-11-27, 2026-11-30, 2026-12-25, 2027-01-01.
- Next business day (first ask, rule 16): **Mon 2026-11-23**.
- **early** deadline: 11-20 + 10 days = Mon 11-30 = holiday -> next business day **Tue 2026-12-01**.
- **late** deadline (5th BD): Mon 23/11=1, Tue 24/11=2, Wed 25/11=3, Thu 26/11=hol, Fri 27/11=hol, Mon 30/11=hol, Tue 01/12=4, Wed 02/12=5 -> **2026-12-02**.
- "this Monday" = 11-23; "next Monday" = **11-30** (Brief A would say 11-23). "this Wednesday" = **11-25** (Brief A would say 11-18, in the past).
- Callback: today after 16:00 and before 19:00, or Mon 11-23 strictly between 10:00 and 19:00.

## Per-case resolution
| Case | Product / band | Resolution | Expected |
|---|---|---|---|
| S4-01 | card 5d early, dl 12-01 | yes to Monday 11-23 | promise 450 2026-11-23 |
| S4-02 | loan 3d early | "pay today" -> exact sentence, offer Mon 11-23 | promise 600 2026-11-23 |
| S4-03 | car 12d | DOB wrong (1), DOB right, phone wrong (2) -> stop; the mock would still accept a third answer and the script offers one | not_verified/failed |
| S4-04 | car 6d early, dl 12-01 | "next Monday" = 11-30 holiday -> next BD 12-01 = deadline, allowed | promise 800 2026-12-01 |
| S4-05 | loan 12d late, dl 12-02, floor 300 | "this Wednesday" 11-25 with 300 = floor -> not enough -> offer 301 once | promise 301 2026-11-25 |
| S4-06 | card 2d early | names 12-01 = deadline (included) | promise 320 2026-12-01 |
| S4-07 | loan **7d** = early | names 12-02 -> after early deadline -> offer 12-01 | promise 540 2026-12-01 |
| S4-08 | car 4d early | "No, I can't." = flat refusal, 0 attempts -> close at once (trailing "yes" only reachable by an agent that persuades) | no_promise/refused |
| S4-09 | – | son asks why -> exact sentence; Mon 10:00 excluded -> ask again; Mon 10:30 | not_reached/callback 2026-11-23 10:30 |
| S4-10 | – | today 19:00 excluded -> ask again; Saturday not a business day | not_reached/no_callback |
| S4-11 | card 15d | "already paid AND never mine" -> dispute wins | no_promise/dispute |
| S4-12 | loan 20d | "a person about a new payment plan" -> restructuring wins, no "can I help first" | transferred/restructuring |
| S4-13 | car 30d late, dl 12-02, floor 400 | no to Monday (refusal 1) -> attempt 1: 1200 on 12-02, refused -> attempt 2: 401 on 12-02, accepted; first create_promise fails, retry | promise 401 2026-12-02 |
| S4-14 | card 10d | "11/3/1982" DMY -> 1982-03-11 -> swap hint (not wrong) -> 1982-11-03; phone wrong once (1 of 2) then right -> verified; "paid yesterday" | paid |

## Intended readings / planted ambiguities
1. **Attempt accounting in the late band (S4-13).** Rule 27: the no to the first question is a flat refusal and uses one attempt; the attempt it uses is attempt 1 (full on deadline) being *made* after it. Intended sequence: first ask -> no -> attempt 1 offer -> no -> attempt 2 offer -> yes. Two offers are made after the first question, never a third.
2. **"Next <weekday>" (S4-04, S4-05).** The sim's `promise_date` slot is pre-resolved under rule 20 (see `sim_note` in the cases). The ledger therefore tests the holiday roll and the deadline; the reader's weekday semantics must be tested in the NLU/dialogue layer (the judge).
3. **Rule 17 vs 18 when the next business day is after the deadline:** offer the deadline. Not exercised by a case.
4. **"Floor plus one pound"** applies to both "too much" (rule 24) and "at or below the floor" (rule 23); attempt 2 also uses floor + 1.00. 401.00 must be sent as a number, not 400.
5. **Early band and "too much"** — rule 24 is an offer, not a persuasion attempt, so it is still allowed in the early band; refusing it is a flat refusal that closes immediately.
6. **Exact sentences with placeholders** ("Can you make this payment on {next business day}?", "... before {promise date}.") are fixed text with computed values; the dates must be spoken as weekday + date.
7. **Identity limit** is the brief's, not the service's: `wrong_answers_left` in the tool result will say 1 when the agent must already stop.
