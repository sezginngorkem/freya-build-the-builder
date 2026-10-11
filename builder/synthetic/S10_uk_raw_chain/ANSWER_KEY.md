# S10_uk_raw_chain - answer key

Inputs given to the builder: `policy_extract.txt` (CRP-07 Part 5, Rev. 4), `memo_CR-MEMO-2026-11.txt`
(05/10/2026), `memo_CR-MEMO-2026-14.txt` (09/11/2026), `email_thread.txt` (07/10 - 12/11/2026),
`appendix_C_result_codes.csv` (Appendix C), `openapi.json`.
Kind: raw bank material with a chain of amendments. UK setting (Pennine & Wharfe Bank plc, fictional).

Precedence: memo 14 > memo 11 > policy (each memo says so), **per item and per effective date of the call
(`now`)**. The Compliance answers in the e-mail ([RP]) are binding where marked "agreed"/"not approved";
Gareth's own proposals and his 02/11 reminder are not. Appendix C gives close outcome / reason / note reason /
queue per code; only codes valid on the call date may be used (status, valid_from, valid_to; dates are
DD/MM/YYYY).

## 1. Final rule set by call date

| Topic | Before 12/10/2026 | 12/10 - 08/11/2026 | 09/11 - 15/11/2026 | From 16/11/2026 |
|---|---|---|---|---|
| Band 2 limit | 5th BD (policy) | **6th BD** (memo 11 item 1) | 6th BD | **5th BD** (memo 14 item 2) |
| Band 3 attempts | 2 | 2 | **1** (memo 14 item 4) | 1 |
| Closure day (not a business day) | none | **Fri 20/11/2026** (memo 11 item 2) | **Fri 27/11/2026**; 20/11 open (memo 14 item 1) | 27/11/2026 |
| Saturday callbacks | 09:00-13:00 (policy) | **none** (memo 11 item 4; e-mail [RP] 3) | none (e-mail 12/11) | none |
| Payment plan request | queue `collections_team`, XPP | same | same | queue **`financial_support`, XFS** (memo 14 item 3; csv XPP valid_to 15/11) |
| Debt advice (StepChange etc. working on a plan) | not covered | **DAH**: hold sentence, note `debt_advice`, no transfer (memo 11 item 3) | same | same |
| Breathing Space (standard or mental health crisis) | BRS, no note (policy 5.10.3) | from 09/10: **BSP**, fixed sentence, note `breathing_space`, before 5.10.2 (e-mail [RP] 4; csv BRS retired 08/10) | same | same |

Unchanged throughout: identity = DOB (numeric = DAY/MONTH/YEAR, 2-digit year 19xx) then outward postcode
(capitals, no space), 3 wrong in total; Band 1 = 1-30 d, 7th BD, 1 attempt; Band 3 = 61-90 d, 3rd BD;
floors; England & Wales bank holidays 25/12/2026, 28/12/2026, 01/01/2027 (St Andrew's Day 30/11 and 04/01/2027
ARE business days, 5.7.1 note); callbacks today + 3 calendar days, Mon-Fri 09:00-20:00; one combined read-back
at the end (5.12.1); notes for every account without a promise, none on a transferred call (5.13.2).

Rejected in the e-mail (must NOT be built): fee waiver for same-day payment (code FWV "DRAFT - NOT APPROVED");
verifying / taking a promise from a Lasting Power of Attorney holder.

Final close_call table (Appendix C, valid codes only):

| Code | outcome | reason | note reason | queue |
|---|---|---|---|---|
| PTP | promise | - | - | - |
| PAI | paid | - | paid | - |
| RTP | no_promise | refused | refused | - |
| HRD | no_promise | hardship | hardship | - |
| DSP | no_promise | dispute | dispute | - |
| SVE | no_promise | service_error | service_error | - |
| DAH | no_promise | debt_advice | debt_advice | - |
| BSP | no_promise | breathing_space | breathing_space | - |
| XSU / XSV | transferred | support / vulnerable | - | support |
| XPP (to 15/11) / XFS (from 16/11) | transferred | payment_plan / financial_support | - | collections_team / financial_support |
| XHU | transferred | human | - | general |
| IDF / IDD | not_verified | failed / declined | - | - |
| CBK / NCB / WNO / DEC / NCU | not_reached | callback / no_callback / wrong_number / deceased / unclear | - | - |

Never valid: PTS, BRS (`moratorium`), FWV, TPP, LMS. The openapi `add_note` enum still lists `moratorium`
("historic records only") - a trap.

## 2. Per-case derivation

Business-day arithmetic was computed with a script that applies the closure day valid on the call date.

| Case | now | Key derivation | Expected ledger |
|---|---|---|---|
| S10-01 | Wed 2026-10-14 10:00 | DOB "zero four, zero seven, eighty-two" -> DAY/MONTH -> 1982-07-04 (5.5.1). "L S six" -> `LS6`. Band 1 card pays full today. | promise p1 186.40 on 2026-10-14 |
| S10-02 | Fri 2026-10-16 12:00 | Daughter with LPA = third party (e-mail [RP] 2 rejected the proposal; 5.4.1). "Tomorrow at ten" = Sat 17/10 -> no Saturday callbacks after 12/10 (memo 11 item 4) -> ask once more (5.4.3). Mon 19/10 19:30: 3 calendar days ahead, Mon-Fri 09:00-20:00. | not_reached/callback; callback 2026-10-19 19:30 |
| S10-03 | Wed 2026-11-11 14:00 | DOB "three, eleven, seventy-nine" -> 1979-11-03. Outward codes M1, M41 wrong, M14 right (2 wrong < 3). Loan 75 d = Band 3, limit 3rd BD = 16/11. "No" -> attempt 1 = 1140 on 16/11; "No" -> memo 14 item 4 (from 09/11): Band 3 has one attempt -> RTP, note refused. (Base policy: attempt 2 = 380 on 16/11, accepted in the last script turn.) | no_promise/refused; note p1 refused |
| S10-04 | Thu 2026-11-12 10:00 | p1 card 40 d = Band 2: memo 11 item 1 still in force (memo 14 item 2 starts 16/11) -> 6th BD; memo 14 item 1 already in force -> 20/11 open -> limit = 13, 16, 17, 18, 19, **20** = 2026-11-20. p2 loan 10 d Band 1: 7th BD = 2026-11-23. Customer: both in full on Mon 23/11 -> p1 after its limit -> recorded on 20/11 and said in the read-back (5.7.8); p2 keeps 23/11. One read-back, then create_promise p1, p2. | promise p1 520 on 2026-11-20, p2 300 on 2026-11-23 |
| S10-05 | Mon 2026-11-23 11:00 | Loan 45 d Band 2, from 16/11 back to 5th BD: 24, 25, 26, (27 closed), 30, 1 Dec -> limit 2026-12-01. "Friday" = 27/11 = closure (memo 14 item 1) -> next business day 30/11 (St Andrew's Day is a business day, 5.7.1). Date without amount = full (5.8.1). | promise p1 660 on 2026-11-30 |
| S10-06 | Mon 2026-11-16 10:00 | Robot question answered, not an ask (5.3.3). "The hundred and twelve pounds and the fifty pence" = 112.50. Friday 20/11 is a business day (memo 14 item 1; e-mail 12/11; the 02/11 reminder is superseded). Band 1 limit 2026-11-25. | promise p1 112.50 on 2026-11-20 |
| S10-07 | Wed 2026-10-21 14:00 | "No" -> one by one; p1 attempt 1 (590 on 30/10). Customer: StepChange is putting a debt management plan together -> memo 11 item 3 (5.10.5): hold sentence, no transfer offer, every account without an agreed promise -> DAH; it comes before 5.11.3 (not a payment-plan transfer). | no_promise/debt_advice; notes p1 debt_advice, p2 debt_advice |
| S10-08 | Wed 2026-11-04 10:00 | Mental Health Crisis Breathing Space -> e-mail [RP] 4: 5.10.3 applies and comes before 5.10.2 (no vulnerability transfer); fixed sentence; note `breathing_space` (not `moratorium`); code BSP (BRS retired 08/10). | no_promise/breathing_space; note p1 breathing_space |
| S10-09 | Wed 2026-10-28 11:00 | "Card today, not the loan" -> card agreed (full 240 today). Loan 70 d Band 3 (2 attempts before 09/11), limit 2026-11-02: attempt 1 = 1350 on 02/11 -> separation = relationship breakdown -> 5.10.1: sympathy, offer CSU, declined -> HRD for the loan; the earlier agreed card promise is kept. Combined read-back at the end -> card recorded. Promise recorded -> PTP. | promise p1 240 on 2026-10-28; note p2 hardship |
| S10-10 | Tue 2026-11-17 15:00 | "Too much" + "payment plan, forty a month" -> 5.11.3 applies even with "too much"/a monthly amount; call on/after 16/11 -> memo 14 item 3: queue `financial_support`, XFS. | transferred/financial_support; transfer financial_support |
| S10-11 | Mon 2026-10-26 10:00 | p1 card "already paid on Friday" -> PAI for p1, call continues. p2 loan: payment plan request before 16/11 -> queue `collections_team`, XPP. Transferred call -> NO note at all (not even `paid` for p1, 5.13.2). | transferred/payment_plan; transfer collections_team |
| S10-12 | Mon 2026-12-21 10:00 | p1 card 20 d Band 1 limit 2027-01-04 (25/12, 28/12, 01/01 skipped). "No, not today" -> one by one. Card: "one-twenty... no, sorry, the full one-forty-five, on the twenty-eighth" -> corrected 145 (120 would also be valid, so the correction matters); 28/12 = Boxing Day substitute bank holiday -> 29/12 offered and accepted. p2 loan: "not mine, never took a loan" -> DSP. p3 car finance 5 d Band 1: attempt 1 = 310 on 04/01 refused -> one attempt -> RTP. Combined read-back -> card recorded. | promise p1 145 on 2026-12-29; notes p2 dispute, p3 refused |
| S10-13 | Wed 2026-11-25 15:00 | Car finance 65 d Band 3, limit: 26, (27 closed), 30, 1 Dec -> 2026-12-01. "Too much" -> floor 245 once (5.8.3); fee-waiver question -> no waiver (5.11.7, e-mail [RP] 1). "245 on Monday" = 30/11, valid. create_promise fails once -> retry (5.12.3). | promise p1 245 on 2026-11-30 (exactly one) |
| S10-14 | Tue 2026-10-13 16:00 | Bipolar disorder, bad week = mental health condition -> 5.10.2 (before 5.10.1): fixed sentence, transfer queue `support` without asking, XSV. | transferred/vulnerable; transfer support |

## 3. Traps
1. **Effective dates per item**: memo 14 items 1 and 4 start 09/11, items 2 and 3 start 16/11. S10-04 (12/11) needs memo 11 item 1 AND memo 14 item 1 together. Three wrong readings give 19/11 (base), 23/11 (memo 11 only) for p1.
2. **Closure moved**: 20/11 closed only for calls 12/10-08/11; 27/11 closed from 09/11. Gareth's 02/11 reminder is stale (S10-06).
3. **St Andrew's Day 30/11** is listed but is a business day for collections (S10-05, S10-13).
4. **Day-first numeric dates** (S10-01, S10-03); a US reader sends 1982-04-07 / 1979-03-11.
5. **Outward postcode** spelled letter by letter ("Y O ten" = YO10, "L S twenty-eight" = LS28).
6. **Rejected proposals**: LPA holder verification (S10-02), fee waiver / FWV (S10-13).
7. **Agreed e-mail rule** (Breathing Space incl. mental health crisis, note `breathing_space`, BSP) lives only in the e-mail and the csv (S10-08); openapi still offers `moratorium`.
8. **Code validity by date**: XPP until 15/11 (S10-11), XFS from 16/11 (S10-10); BRS retired.
9. **Debt management plan via StepChange** is debt advice (DAH), not a payment-plan transfer (S10-07).
10. **Mental health**: a crisis breathing space -> BSP (S10-08); a mental health condition without breathing space -> XSV transfer (S10-14).
11. **No notes on a transferred call** even for an account already found paid (S10-11).
12. Combined read-back at the end (unlike S9's per-product read-back), with 5.7.8 per-account capping (S10-04).

## 4. New intents / slots used in sim_script
- `debt_counselling` (S10-07), `breathing_space` (S10-08), `vulnerable` (S10-14), `restructure` (S10-10, S10-11), `ask_bot` (S10-06), `other_question` (S10-13, fee-waiver question).
- Identity slots: `id_date_of_birth`, `id_postcode_outward`.
- New close reasons: `debt_advice`, `breathing_space`, `vulnerable`, `financial_support`, `payment_plan` (all from the csv; the openapi `reason` is a free string).

## 5. Ambiguities deliberately removed or not tested
- Memo effective dates refer to the date the call is placed (`now`), stated in every memo item.
- Base-policy behaviour for a debt management plan or a mental-health-crisis breathing space is not given as an alternative expectation (it would be a guess); only S10-02/03/04 (and S10-06/S10-10 alternatives) carry `base_policy_expected` / `memo11_only_expected` / `pre_memo_expected` for diagnosis.
- The DLQ-style note text is not checked (ledger compares product_id + reason only).
- Hardship after a promise was already recorded (vs. only agreed) is not tested; S10-09 has an agreed, not yet recorded, card promise, which 5.10.1 explicitly keeps.
- Whether the read-back in S10-04 must mention the cap is a transcript check only.
- A Saturday callback between 12/10 and memo 14 is the only callback-window variation tested; the Saturday 09:00-13:00 base window itself is never valid in any case date.
- S10-11: the agent may either make attempt 1 for the loan or ask about it; the customer's next line is a payment-plan request either way, so the ledger does not depend on it.
