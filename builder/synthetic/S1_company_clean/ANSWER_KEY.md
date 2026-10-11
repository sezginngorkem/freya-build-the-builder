# ANSWER KEY: S1_company_clean (Northwind Bank, business customers)

Inputs: `brief.md`, `openapi.json`. Cases: `cases.json` (14). All cases use `now = 2026-10-28T10:15` (Wednesday).
Dates verified with `builder/engine/dates.py` (`add_business_days`, holidays from the brief).

## What this suite stresses vs Brief A/B
| Area | Brief A/B | S1 |
|---|---|---|
| Call variables | names, title, now | + `company_name` (used in the opening) |
| Identity | DOB, phone_last4 | `company_number` (8 digits, pad a dropped leading zero) then `postcode`; `founded_year` replaces postcode once if the contact does not know it |
| Bands | 2 | 3 (watch / arrears / recovery), recovery has NO floor |
| Holiday/weekend | roll forward | roll **back** to the previous business day (forward only if that is before today) |
| Attempt 1 date | last business day of the week | 3rd business day after today, or the deadline if earlier |
| Floors | field lookup | overdraft: `min(round(0.15*past_due, 2), 400.00)` |
| Callback window | today/next BD, 10:00–19:00 incl. | today or next **two** BDs, 09:00 incl. – 17:30 **excl.**, today needs >= now+1h |
| Outcome table | `not_reached` | `no_contact`; transfer reasons `insolvency`/`restructuring`/`human`; no `deceased`, no `hardship` |
| Notes | B only | always (also single product), except on transfer |

## Deadlines for now = Wed 2026-10-28
Holiday 2026-11-02 (Mon) falls in the counting window.
- watch (10th BD after today): Thu 29/10=1, Fri 30/10=2, Mon 02/11=holiday, Tue 03/11=3, Wed 04/11=4, Thu 05/11=5, Fri 06/11=6, Mon 09/11=7, Tue 10/11=8, Wed 11/11=9, Thu 12/11=10 -> **2026-11-12**
- arrears (5th BD): 29/10=1, 30/10=2, 02/11 holiday, 03/11=3, 04/11=4, 05/11=5 -> **2026-11-05**
- recovery (2nd BD): 29/10=1, 30/10=2 -> **2026-10-30**
- attempt 1 date (3rd BD): 29/10, 30/10, (02/11 hol), 03/11 -> **2026-11-03**; for recovery the deadline 2026-10-30 is earlier, so attempt 1 = **2026-10-30**.
- callback: valid days are 2026-10-28 (from 11:15, i.e. now+1h), 2026-10-29, 2026-10-30. 2026-11-02 is a holiday and in any case the third business-day slot would be 2026-11-03.

## Floors
- business_loan: `instalment_amount`; business_card: `minimum_payment`.
- overdraft: 15% of past_due rounded to the nearest penny, capped at 400.00. 1833.33 -> 274.9995 -> **275.00** (use decimal half-up; Python float `round` happens to give 275.0 here). 3000.00 -> 450.00 -> **400.00**.
- recovery band: no floor at all (rule 24 overrides 23/25/26 for that band).

## Per-case resolution
| Case | Band / deadline | Resolution | Expected |
|---|---|---|---|
| S1-01 | loan, 6 days, watch, 11-12 | pays today | promise p1 2400.00 2026-10-28 |
| S1-02 | n/a | receptionist = someone else; tomorrow 09:00 is the window start (included) | no_contact/callback 2026-10-29 09:00 |
| S1-03 | n/a | Fri 17:30 = window end (excluded) -> ask once more; Mon 02/11 is a holiday and beyond 2 BDs -> no booking | no_contact/no_callback |
| S1-04 | n/a | company no. wrong (1), right; postcode wrong (2), wrong (3) -> end | not_verified/failed |
| S1-05 | overdraft, 8, watch | "don't know" postcode is not wrong; founded_year 2014 passes; "we paid yesterday" -> note paid; every product paid -> outcome paid | paid, note p1 paid |
| S1-06 | card, 18, arrears, 11-05 | seven digits "7730215" -> send "07730215"; names 11-05 = deadline, accepted | promise 960.00 2026-11-05 |
| S1-07 | loan, 25, arrears, 11-05 | names 11-06 (after deadline) -> offer deadline | promise 1500.00 2026-11-05 |
| S1-08 | card, 3, watch, 11-12 | names Mon 11-02 (holiday, not after deadline) -> previous BD Fri 10-30 (not 11-03 as Brief A would) | promise 640.00 2026-10-30 |
| S1-09 | overdraft 1833.33, 9, watch | "not today + too much" -> floor once on attempt 1 date (no date agreed yet) | promise 275.00 2026-11-03 |
| S1-10 | overdraft 3000, 14, arrears, 11-05 | proposes 300 on Fri 10-30 (below floor 400) -> offer floor once on the same date | promise 400.00 2026-10-30 |
| S1-11 | card 5 watch 11-12; loan 18 arrears 11-05; overdraft 40 recovery 10-30 | one date 11-06 for all -> card keeps 11-06, loan and overdraft go to their own deadlines (rule 30); overdraft must be full amount | promises p1 820 11-06, p2 2100 11-05, p3 1250 10-30 |
| S1-12 | loan, 33, recovery | administration -> rule 38 (before everything in sections 8–11), no notes | transferred/insolvency, queue insolvency |
| S1-13 | card 7 watch; loan 10 watch | "no" to all-today is not a product refusal; card: attempt 1 offer -> "never had a card" = dispute note; loan attempt 1 = 1200 on 11-03 accepted; first create_promise fails, retry ok | promise p2 1200 2026-11-03, note p1 dispute |
| S1-14 | overdraft 980, 45, recovery, 10-30 | attempt 1 = 980 on 10-30 (deadline earlier than 3rd BD); refused; 1 attempt and no floor -> stop. The trailing "yes" turn is only reachable by an agent that wrongly offers a smaller amount | no_promise/refused, note p1 refused |

## Intended readings of tricky rules
- Rule 12 (founded_year): only when the contact says they do not know the postcode; a wrong postcode is a wrong answer, not a trigger for founded_year. In the cases, `identity` lists exactly the fields the bank will accept for that customer (S1-05 has no postcode on file in the mock, so the agent must not call `verify_identity` with `postcode` there).
- Rule 19: "the last business day before it" — for 2026-11-02 that is Friday 2026-10-30 (not today, so no fallback).
- Rule 25: "on the date already agreed or, if no date was agreed, on the attempt 1 date". Saying "too much" is not a flat refusal and does not use an attempt.
- Rule 27: the no to the all-today question does not consume any product's attempt; each product starts at attempt 1 (so attempt 1 is offered next).
- Rule 43 + 41: notes for every product without a promise, even single-product calls, except on transfers.
- Closing `no_promise` reason = first non-`paid` note in get_account order.

## Planted ambiguities (intended reading)
1. "A temporary cash-flow problem is too much, not hardship" — there is no hardship rule; the agent must not invent a support transfer. Intended: treat as too_much.
2. Rule 6 "at least one hour after now" applies only to today's callbacks.
3. Rule 30 with a recovery-band product: the product goes to its own deadline AND must be the full amount (if the customer had said a lower amount, the floor would not exist). Intended: full amount on the recovery deadline.
4. Rule 10 padding: only one leading zero is added, only when exactly seven digits are said.
5. New intents the reader must declare: `dont_know` (S1-05) and `insolvency` (S1-12); give `insolvency` the highest post-verification priority.
