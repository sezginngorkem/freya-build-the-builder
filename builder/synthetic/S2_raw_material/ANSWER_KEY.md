# ANSWER KEY: S2_raw_material (Harbor Credit Union, raw material)

Inputs (all four must be merged): `policy_extract.md` (base, POL-COL-07 v3.2), `memo.md` (CO-26-14, effective 2026-11-02), `email.txt` (VP Member Collections, 2026-10-30), `codes.csv` (COL-CODES), plus `openapi.json` (wire format, authoritative for spelling).
Cases: `cases.json` (14). `now = 2026-11-04T10:30` (Wednesday) except S2-07 (`2026-11-23T14:00`, Monday). Both are on/after the memo's effective date, so the memo is in force in every case.

## 1. Merge result (the final rule set)
| Item | Policy | Change | Source | Final |
|---|---|---|---|---|
| Stage 1 (1–15 dpd) deadline / attempts | 10 BD / 1 | none ("for information only" 8 BD proposal is not approved and would start 2027-01-04) | memo | **10 BD / 1** |
| Stage 2 (16–30) deadline | 6 BD | 6 -> 4, Stage 2 only | memo A1 | **4 BD** |
| Stage 2 attempts | 2 | none | – | **2** |
| Stage 3 (31–60) deadline | 3 BD | none | – | **3 BD** |
| Stage 3 attempts | 2 | 2 -> 1 | memo A2 | **1** |
| Holidays | 11-11, 11-26, 12-25, 01-01 | + 2026-11-27 | memo A3 | **11-11, 11-26, 11-27, 12-25, 01-01** |
| Hardship reason | `hardship` | renamed `financial_hardship` (close no_promise, close transferred, note) | memo A4 + codes.csv + openapi enum | **financial_hardship** |
| Request for a person (7.5) | ask once first, then member_services | transfer at once | email item 1 (author owns s.7, Compliance signed off, "effective immediately") | **transfer at once, transferred/human** |
| Complaint (7.6) | Complaints Unit, TR-CMP | TR-CMP has queue `complaints` and reason `complaint`, neither exists in openapi; email: route to member_services as transferred/human | codes.csv vs openapi, email item 2 | **queue member_services, transferred/human** |
| Contact outcome | `unreached` | – | policy + openapi | `unreached` (not `not_reached`) |
| Identity | birth_year then postcode (ZIP, keep leading zero), 3 wrong total | – | policy 4 | same |
| Floors | card minimum_payment; auto monthly_payment; LOC interest_due | – | policy 6.4 + openapi field names | same |
| Product fields | – | openapi uses `product_type`, `amount_due`, `days_past_due` | openapi | read these names |

Non-binding / ignored content (must NOT become rules):
- email "5% goodwill reduction ... we might do this in Q1" -> no discount (policy 6.10 stands). Tested in S2-14 (transcript check).
- email "might move confirmation to email" -> 6.9 sentence stays "You will receive a confirmation text message today."
- email "ten business days is too generous", "three security questions would be better" -> opinions, no change.
- email paraphrase "the memo cuts **the deadline** to four business days" is over-general; the memo itself limits it to Stage 2. The memo text prevails over the email summary (the email even says "read the memo itself").
- memo "for information only" Stage 1 -> 8 BD from 2027-01-04: not approved, not in force.
- codes.csv retired codes `hardship` (NP-HS, TR-HS, NT-HS) and `left_message` (UR-LM, retired 2025, and the assistant never leaves voicemail): never sent.
- codes.csv header has two preamble rows before the column header and a trailing blank line; descriptions contain commas inside quotes.

## 2. Deadlines
now = Wed 2026-11-04 (memo calendar):
- Stage 1, 10th BD: Thu 05/11=1, Fri 06/11=2, Mon 09/11=3, Tue 10/11=4, Wed 11/11=holiday, Thu 12/11=5, Fri 13/11=6, Mon 16/11=7, Tue 17/11=8, Wed 18/11=9, Thu 19/11=10 -> **2026-11-19**
- Stage 2, 4th BD (memo): 05/11=1, 06/11=2, 09/11=3, 10/11=4 -> **2026-11-10** (pre-memo 6th BD: ... 12/11=5, 13/11=6 -> 2026-11-13)
- Stage 3, 3rd BD: 05/11, 06/11, 09/11 -> **2026-11-09**
- Attempt 1 date (last BD of this week): **Fri 2026-11-06**.

now = Mon 2026-11-23 (S2-07):
- Stage 1, memo calendar: Tue 24/11=1, Wed 25/11=2, Thu 26/11=hol, Fri 27/11=hol, Mon 30/11=3, Tue 01/12=4, Wed 02/12=5, Thu 03/12=6, Fri 04/12=7, Mon 07/12=8, Tue 08/12=9, Wed 09/12=10 -> **2026-12-09** (pre-memo: 27/11 counts -> 2026-12-08)
- Attempt 1 date: last BD of this week = **Wed 2026-11-25** (26 and 27 are holidays; pre-memo it would be Fri 27).

## 3. Per-case resolution
| Case | Product / stage | Resolution | Expected | Pre-memo / pre-email result |
|---|---|---|---|---|
| S2-01 | card 9 dpd, S1 | pays today; ZIP "02134" keeps leading zero | promise 610 2026-11-04 | same |
| S2-02 | – | wife; today 18:00 = window end (included), later than now | unreached/callback 11-04 18:00 | same |
| S2-03 | – | 1987 wrong(1), 1978 ok, 60614 wrong(2), 60661 wrong(3) | not_verified/failed | same |
| S2-04 | auto 22 dpd, S2 | names 11-12, after memo deadline 11-10 -> offer 11-10; create_promise fails once, retry | promise 1150 2026-11-10 | 11-12 accepted |
| S2-05 | card 28 dpd, S2 | names 11-11: holiday AND after deadline 11-10 -> "after the deadline" rule -> 11-10 | promise 880 2026-11-10 | holiday before deadline 11-13 -> next BD 11-12 |
| S2-06 | LOC 40 dpd, S3 | attempt 1 = 720 on Fri 11-06, refused -> attempts used (memo: 1) -> note refused. Trailing "yes" only reachable by a pre-memo agent making attempt 2 | no_promise/refused, note p1 refused | attempt 2 = 96.00 on 11-09 accepted -> promise |
| S2-07 | card 5 dpd, S1, now 11-23 | names Fri 11-27 = memo holiday, not after deadline 12-09 -> next BD Mon 11-30 | promise 430 2026-11-30 | 11-27 accepted |
| S2-08 | auto 19 dpd, S2 | hours cut = hardship; sympathy, offer hardship_team, declined -> note | no_promise/financial_hardship, note p1 financial_hardship | reason/note `hardship` |
| S2-09 | card 11 dpd | asks for a person -> transfer at once (email). Trailing turns only reachable by an agent that asks "can I help first?" | transferred/human, queue member_services | policy-only agent asks first, member then pays today -> promise 515 11-04 |
| S2-10 | auto 12 dpd | formal complaint -> member_services, transferred/human (TR-CMP unusable) | transferred/human | – |
| S2-11 | card 6 S1, auto 24 S2, LOC 35 S3 | no to all today; card attempt 1 (540 on 11-06) accepted; auto "paid off when I sold the car" = dispute (7.3, not 7.2); LOC "paid this morning" = paid; one read-back at the end | promise p1 540 11-06; notes p2 dispute, p3 paid | same |
| S2-12 | auto 15 dpd -> **Stage 1** (15 included) | names 11-19 = Stage 1 deadline (unchanged) | promise 700 2026-11-19 | same (regression: memo must not touch Stage 1) |
| S2-13 | LOC 3 dpd, S1 | too much -> floor = interest_due 140 on attempt 1 date (Fri 11-06) | promise 140 2026-11-06 | same |
| S2-14 | card 10 dpd, S1 | asks for discount -> none offered, then pays today | promise 350 2026-11-04 | same |

Cases carry `pre_memo_expected` / `without_email_expected` fields (partial overrides of `expected`) to document how the result would differ without the amendment; the scorer ignores them.

## 4. Known ambiguities and intended reading
1. **Email authority.** The email overrides policy 7.5 because its author owns section 7, Compliance is copied and signed off, and it is an explicit "effective immediately ... replacing" instruction. Her opinions in the same email are not instructions. A reader that applies "email < policy" blindly will fail S2-09.
2. **Email paraphrase vs memo scope.** "cuts the deadline to four business days" — the memo limits A1 to Stage 2. Scope-limited reading is intended (Stage 1 = 10 BD, Stage 3 = 3 BD).
3. **Code present in code list but not in API.** TR-CMP (`complaint` / `complaints`). Intended: never send it; follow the email's interim routing. Without the email, the conservative choice would also be a person transfer (member_services).
4. **Holiday that is also after the deadline (S2-05).** Policy 6.5 has both "weekend/holiday on or before the deadline -> next business day" and "after the deadline -> deadline". 11-11 is after 11-10, so the second applies.
5. **"Paid off when I sold the car"** is a dispute by the policy's own example (7.3), not "already paid".
6. **Rename scope.** A4 renames hardship everywhere (close no_promise, close transferred, note). The openapi `close_call.reason` enum and `add_note.reason` enum only contain `financial_hardship`.
7. **Effective date.** Memo effective 2026-11-02; all case `now`s are later, so it applies. The email's "effective immediately" is 2026-10-30, also in force.
8. New intent the reader must declare: `complaint` (S2-10).
