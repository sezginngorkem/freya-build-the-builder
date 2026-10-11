# S7_unseen_real - answer key

Inputs given to the builder: `policy_extract.txt`, `memo.txt`, `email_thread.txt`, `codes.csv`, `openapi.json`.
Precedence: memo > policy (memo says so); the compliance e-mail (2026-10-21) adds one agreed rule and rejects one
proposal; codes.csv gives the close_call outcome/reason per code (ACTIVE rows only).

## 1. Final rule set

### Base (policy COL-104 Section 7)
- Opening (7.3.1): virtual assistant of Cobalt Ridge FCU, call recorded; no debt/collections/payment/product words before identity.
- Right party (7.3.2): "May I please speak with <first> <last>?" (full name, NOT title + last name). Unclear twice -> NCU = `not_reached/unclear`.
- Third party (7.4): disclose nothing; nobody but the member may verify or promise. Callback base window: 08:00-21:00 inclusive, business day, no later than the 3rd business day after today, later than now -> CBK `not_reached/callback`. Ask once more if outside; then NCB `not_reached/no_callback`. Wrong number WRN; deceased "I am sorry for your loss." DEC.
- Identity (7.5): DOB then phone_last4; numeric dates are **MONTH/DAY/YEAR**, two-digit year = 19xx; 3 wrong total -> IDF `not_verified/failed`; declines twice -> IDD `not_verified/declined`.
- After verification: get_account, then fixed sentence "This is an attempt to collect a debt, and any information obtained will be used for that purpose.", then product in words ("credit card ending NNNN", "personal loan", "auto loan"), past due, days delinquent.
- Attorney (7.6.4): stop, no note, ATY `no_promise/attorney`.
- Stages (7.7.2): 1-15 days -> limit 10th business day, 1 attempt; 16-59 -> 6th, 2 attempts; 60-120 -> 3rd, 2 attempts.
- Business days: Mon-Fri minus 2026-10-12, 2026-11-11, 2026-11-26, **2026-11-27 (CU closed)**, 2026-12-25, 2027-01-01, 2027-01-18.
- Non-business day <= limit -> next business day (or the limit if that is later). After the limit -> offer the limit. Vague -> ask once, then limit. "Next <weekday>" = following calendar week; bare/"this" weekday = current week if not past.
- Amounts: full first; floor = minimum_payment (card) / instalment_amount (loans); too much -> floor once; below floor -> "cannot be recorded", floor once.
- Attempts (7.9.2): attempt 1 = full (or floor if "too much" already said) on the limit; attempt 2 (stages 2-3) = floor on the limit. Exhausted -> RTP `no_promise/refused` + note refused.
- Hardship (7.9.4): sympathy, no persuasion, offer Member Support -> XFS `transferred/support`; declined -> HDS `no_promise/hardship` + note hardship.
- Paid (7.11.1): "up to two business days to post" -> PAI `paid`. Dispute -> DSP `no_promise/dispute` + note. Plan/lower payments/deferment -> XFW `transferred/restructuring`. Human (insists) -> XFH `transferred/human` queue general.
- Confirm (7.10): read back, "Do you confirm?", create_promise after yes; retry once on failure; second failure -> SVE + note service_error. After success: "You will receive a confirmation by text message within 24 hours."
- Notes (7.12): one add_note per account ending without a promise for refused/hardship/dispute/service_error; none when transferred or not verified. Note text starts with a DLQ_REASON code when a reason was given.
- Multi-account (7.13): in get_account order; any promise -> PTP `promise`; a transfer always wins.

### Amendments (memo COMP-MEMO 26-14, dated 2026-10-19)
1. **Item 1 - callback window** for calls placed **on/after 2026-11-02**: 09:00-20:00 inclusive and no later than the **2nd** business day after today.
2. **Item 2 - credit counselor / DMP** (effective 2026-10-19): no persuasion, **no transfer offer**, say 30-day hold, add_note `hardship` (text "DMP HOLD 30D...") per account, DMP `no_promise/hardship`. Comes before 7.9.2 and 7.9.4.
3. **Item 3 - loans >= 36 days** (effective 2026-10-19): personal/auto loan; on the first flat refusal or "too much", BEFORE any attempt/floor offer, offer the Loan Workout team once. Yes -> XFW `transferred/restructuring` (queue restructuring). No -> continue normally. Not for credit cards.

### E-mail thread (2026-10-20/21)
- REJECTED: joint borrower/spouse answering may be verified and give a promise. -> stays a third party (7.4).
- AGREED (effective 2026-10-21): "already paid" -> add_note reason `paid` on that account before close_call (codes.csv PAI row updated).
- Clarified: memo item 1 starts 2026-11-02, not "Monday the 26th" (Priya's wrong assumption, corrected by Marcus).

### Final close_call table (from codes.csv, ACTIVE only)
| Code | outcome | reason | note |
|---|---|---|---|
| PTP | promise | - | - |
| PAI | paid | - | paid |
| RTP | no_promise | refused | refused |
| HDS | no_promise | hardship | hardship |
| DMP | no_promise | hardship | hardship |
| DSP | no_promise | dispute | dispute |
| SVE | no_promise | service_error | service_error |
| ATY | no_promise | attorney | - |
| XFS / XFW / XFH | transferred | support / restructuring / human | - |
| IDF / IDD | not_verified | failed / declined | - |
| CBK / NCB / WRN / DEC / NCU | not_reached | callback / no_callback / wrong_number / deceased / unclear | - |
INACTIVE, must never be used: TPM (`not_reached/third_party`), LVM (`voicemail`), PTP-P (`promise/partial`).

## 2. New intents (not in the standard id list)
- `debt_counselling` - member says they work with a credit counseling / debt-management agency on a plan (S7-08, memo item 2).
- `attorney_represented` - member says an attorney represents them for this debt (S7-14, policy 7.6.4).
New close reason string: `attorney` (allowed: openapi `reason` is a free string; from codes.csv ATY).

## 3. Per-case derivation

Business-day arithmetic was computed with a script over the Appendix B list (including 2026-11-27).

| Case | now | Key derivation | Expected |
|---|---|---|---|
| S7-01 | Tue 2026-10-20 10:30 | Card 7 days -> stage 1. "eleven, oh-three, ninety" -> 7.5.1 MM/DD/YY -> 1990-11-03. Pays full today (7.9.1, today is a business day). | promise p1 312.40 on 2026-10-20 |
| S7-02 | Wed 2026-10-28 18:00 | Husband = third party even as co-borrower (e-mail: REJECTED). Call before 2026-11-02 -> base window 08:00-21:00, limit 3rd business day = 2026-11-02. Fri 2026-10-30 20:30 valid (7.4.2). | not_reached/callback, callback 2026-10-30 20:30 |
| S7-03 | Tue 2026-11-03 12:00 | Memo item 1 in force: 09:00-20:00, limit 2nd business day = 2026-11-05. Thu 11-05 20:30 -> time after 20:00 -> ask once more (7.4.3). Fri 11-06 09:30 -> date after limit. No booking. (Under the base rule both would be valid -> catches a builder ignoring the memo.) | not_reached/no_callback |
| S7-04 | Wed 2026-10-21 14:00 | DOB "04/07/84" -> 1984-04-07 (MM/DD) passes. Phone 5521, 5512, 2155 = 3 wrong -> 7.5.3. | not_verified/failed, no tools after verify |
| S7-05 | Mon 2026-11-09 11:00 | Card 22 days -> stage 2, limit 6th business day: 11-10, (11-11 holiday), 11-12, 11-13, 11-16, 11-17, 11-18 -> 2026-11-18. "Wednesday" (bare, current week) = 2026-11-11 Veterans Day -> 7.7.4 next business day 2026-11-12. | promise p1 450 on 2026-11-12 |
| S7-06 | Mon 2026-11-23 15:00 | Card 75 days -> stage 3, limit 3rd business day: 11-24, 11-25, (11-26 hol, 11-27 closed), 11-30 -> 2026-11-30. $60 < floor 95 -> 7.8.4 offer 95 once. "Friday" = 2026-11-27 closed -> next business day 2026-11-30 (= limit). Card -> memo item 3 not applicable. | promise p1 95 on 2026-11-30 |
| S7-07 | Thu 2026-10-22 09:15 | Job loss -> 7.9.4; accepts Member Support. No note (7.12.2). | transferred/support, transfer queue support |
| S7-08 | Mon 2026-10-26 13:00 | After memo date -> item 2: no persuasion, no transfer offer; note hardship on p1. Loan 20 days < 36, item 3 irrelevant. | no_promise/hardship, note p1 hardship |
| S7-09 | Tue 2026-10-27 16:00 | Personal loan 40 >= 36, flat "no" -> memo item 3 workout offer before attempts; accepts. | transferred/restructuring, transfer queue restructuring |
| S7-10 | Thu 2026-10-15 10:00 | BEFORE memo (2026-10-19) -> no item 3 offer. Auto loan 45 days -> stage 2, limit = 10-16, 10-19, 10-20, 10-21, 10-22, 10-23 -> 2026-10-23. "No, not today" = flat refusal -> attempt 1: 930 on 10-23 (refused) -> attempt 2: 310 on 10-23 (accepted). | promise p1 310 on 2026-10-23 |
| S7-11 | Thu 2026-10-29 11:00 | p1 card 9 days -> stage 1, limit 10th business day = 2026-11-13 (11-11 holiday skipped). "next Friday" on a Thursday -> 7.7.7 following calendar week -> 2026-11-06. p2 loan: "not mine" -> 7.11.2 note dispute. Any promise -> PTP (7.13.2). | promise p1 240 on 2026-11-06; note p2 dispute |
| S7-12 | Wed 2026-11-04 17:30 | "Already paid" -> 7.11.1 PAI + e-mail (agreed 2026-10-21) note `paid`. | paid; note p1 paid |
| S7-13 | Mon 2026-11-16 10:00 | Card 5 days -> stage 1, limit: 11-17, 18, 19, 20, 23, 24, 25, (26 hol, 27 closed), 30, 12-01, 12-02 -> 2026-12-02. Dec 4 after limit -> 7.7.5 offer 12-02, accepted. create_promise fails once -> retry (7.10.3). | promise p1 510 on 2026-12-02 (exactly one) |
| S7-14 | Fri 2026-10-30 14:00 | Attorney -> 7.6.4, no note. | no_promise/attorney |

## 4. Traps
1. **US date order** (7.5.1) - the example brief A reads numeric dates day-first; this one is month-first (S7-01, S7-04, S7-10). For 1990-11-03 a DMY reader sends 1990-03-11 (mock may answer `day_month_swapped`, so the call can still recover, but it costs a retry).
2. **Full name**, not title + last name, in the right-party question.
3. **Credit-union closure 2026-11-27** is listed under Appendix B with a side remark "not a Fed holiday" - must still be excluded (S7-06, S7-13).
4. **Memo effective dates differ**: item 1 from 2026-11-02 (calls placed), items 2-3 from 2026-10-19. S7-02 vs S7-03 (item 1) and S7-10 vs S7-09 (item 3).
5. **Priya's wrong date** in the e-mail ("Monday the 26th") is corrected by Compliance - do not use it.
6. **Rejected e-mail proposal** (joint borrower verification/promise) - must not be applied (S7-02).
7. **Agreed e-mail rule** (paid note) lives only in the e-mail and in a codes.csv comment column (S7-12).
8. **Inactive codes** TPM/LVM/PTP-P look usable (TPM has a plausible reason `third_party`).
9. **New reason `attorney`** is outside the familiar reason set; it comes only from codes.csv.
10. **Memo item 2 overrides 7.9.4**: no Member Support offer for a DMP member (S7-08).
11. **Memo item 3 is loans-only** (S7-06 card at 75 days must not get the offer).
12. **Core codes VISA/SIG/AUTO** must not be spoken; "car_loan" is said "auto loan".
13. PDF noise in the policy: broken hyphenation ("delin-quent", "at-tempt"), ligature "ﬁ", spaced "O ff er", page headers/footers, missing pages 14-15 and missing section 7.14.

## 5. Ambiguities and intended reading
- **7.4.2(b) "no later than the 3rd business day after today"**: count business days strictly after today; today itself allowed if time > now. Intended: S7-02 limit 2026-11-02, S7-03 (memo) limit 2026-11-05.
- **Memo item 1 "calls placed on or after 2 November"**: the date of `now` decides, not the callback date.
- **Second callback answer in S7-03** must be checked against the memo window too (7.4.3 unchanged).
- **S7-06 "too much" + $60 in one turn**: 7.8.3 and 7.8.4 both lead to one floor offer; intended single offer of 95. Customer then names a closed Friday; 7.7.4 gives Monday 11-30, which equals the limit, so no conflict.
- **S7-10**: the case is ledger-identical whether or not an erroneous workout offer is declined; the sim script deliberately has the member say "no" to the next question, so a wrong agent that offers the transfer will read that "no" as a decline and may still reach the same ledger. The check ("no workout offer") is transcript-level. The prose `script` says he WOULD accept a transfer, so with an LLM-simulated customer a wrong agent ends `transferred/restructuring` and fails.
- **Mini-Miranda** comes after get_account but before the amount; whether it is said once per call (intended) or once per account: once per call.
- **7.12.1 note text** (DLQ_REASON prefix) is not checked in the ledger (`notes` only compare product_id and reason).
- **S7-08**: memo says "for each account discussed" - only one account, so one note.
- **fail_first**: each case with a tool fault carries both the kit format (`faults: [{tool, fail_first_n}]`) and the shorthand `fail_first: "create_promise"`.
