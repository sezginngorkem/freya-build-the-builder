# ANSWER KEY: S5_realworld_style (Pinecrest FCU, procedure COL-310 Rev. 4)

Input: `brief.md` only (+ `openapi.json`). Do NOT give this file or `cases.json` to the builder.
Style model: a real credit-union operating procedure (header table, Purpose/Scope/Authority/Definitions, `310.x(a)(i)` numbering, cross-references, "Note:" lines, a regulator citation per rule, a disposition-code table that maps 3-letter codes to API words, revision history). Rule content borrows Regulation F (12 CFR 1006) limits as "credit union policy".
`now = 2026-11-19T15:10` (Thursday) for every case. Holidays: 11-11, 11-26, 12-25, 01-01, 01-18. Pinecrest is OPEN on Fri 2026-11-27.

## 1. Computed values
- Business days after Thu 19 Nov: 20 Nov=1, 23=2, 24=3, 25=4, (26 hol), 27=5, 30=6, 1 Dec=7, 2=8, 3=9, 4=10.
- Courtesy (1-14 dpd): 10th BD = **2026-12-04**, 1 attempt.
- Early (15-44): 5th BD = **2026-11-27**, 2 attempts.
- Pre-charge-off (45-89): 2nd BD = **2026-11-23**, 1 attempt.
- Broken promises >= 2: latest date = min(tier date, 3rd BD **2026-11-24**), no floor.
- Floor = ceil(25% x amount_due) to a whole dollar; card: max(that, minimum_due). Needs a ceiling (the IR has no `ceil` builtin: write a function or `round(x + 0.4999, 0)`-style trick; check the IR).
- Contact hold: held iff call date <= last_conversation_date + 6 days (day 1 = the conversation date).
- Callback: call date or next 2 calendar days (19, 20, 21 Nov); Mon-Fri [08:00, 21:00); Sat [09:00, 17:00]; never Sunday/holiday; later than now (15:10).
- Attempt 1 = full (or floor after "too much") on the latest promise date (NOT last business day of the week, unlike Brief A). Attempt 2 (Early only) = floor on the latest date, skipped if it would repeat a refused offer or no floor.

## 2. Per case
| Case | Key rule | Expected |
|---|---|---|
| S5-01 | happy; disclosure sentence after verification; ssn 0472 | promise 418.60 on 11-19 |
| S5-02 | spouse = third party (stricter than Reg F); Sat 10:00 allowed | no_contact/callback 2026-11-21 10:00 |
| S5-03 | Sunday rejected, 21:00 excluded, one re-ask | no_contact/no_callback |
| S5-04 | executor of estate -> estates (beats "deceased") | transferred/estate, queue estates |
| S5-05 | DOB "04/07/81" = April 7 (US order); 1 wrong SSN; too much -> floor ceil(282.50)=283 on 11-25 | promise 283 on 11-25 |
| S5-06 | broken_promises_12m=2: 27 Nov (open, inside tier) capped to 24 Nov | promise 760 on 11-24 (without 310.13: 11-27) |
| S5-07 | Pre-charge-off, 1 attempt (1290 on 11-23), refused | no_promise/refused, note p1 refused |
| S5-08 | Early, attempt 2 floor = max(ceil(160.60)=161, 95) on 11-27 | promise 161 on 11-27 |
| S5-09 | attorney -> fixed sentence, note | no_promise/attorney, note p1 attorney |
| S5-10 | bankruptcy beats an offered amount | no_promise/bankruptcy, note p1 bankruptcy |
| S5-11 | card last conv 11-12 (day 8, not held) / loan 11-13 (day 7, held) | promise p1 300 on 11-19; note p2 contact_hold |
| S5-12 | "stop calling" once is enough | no_promise/cease, note p1 cease |
| S5-13 | skip-a-pay = restructuring | transferred/restructuring, queue loan_servicing |
| S5-14 | scam question before confirming (then 2nd ask); person: ask once, insists | transferred/human, queue member_services |

## 3. Intended readings / ambiguities
1. Disposition codes (PTP, ATY...) are NOT sent; `close_call` takes the outcome/reason columns.
2. "Third party" includes the spouse (310.4(d)); the Reg F remark is information only (310.3(b)).
3. A Saturday callback is allowed although Saturday is not a business day ("Note:" under 310.7(b)).
4. 310.11(b): a held product is not stated, not offered, but noted `contact_hold`; it is ignored for the outcome (310.17(c)).
5. 310.15(j) precedence: attorney/bankruptcy > hardship > rest.
6. New intents a reader must declare: `estate_executor`, `attorney`, `bankruptcy`, `stop_calling`.
7. "Revision history" is informational; it does not change any rule.
