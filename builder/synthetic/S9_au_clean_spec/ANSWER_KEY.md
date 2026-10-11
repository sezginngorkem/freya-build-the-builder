# S9_au_clean_spec - answer key

Input given to the builder: `brief.md` (one clean specification) and `openapi.json`.
Kind: clean specification, long and dense, Australian setting (Kestrel Mutual Bank, Melbourne, fictional).
Every expected ledger below was derived rule by rule from `brief.md`; business-day arithmetic was computed
with a script over the rule-17 holiday list (2026-11-03, 2026-12-25, 2026-12-28, 2027-01-01, 2027-01-26).

## 1. What differs from the example briefs A/B (the traps)

| # | Trap | Rule |
|---|---|---|
| 1 | Identity is **postcode then year of birth** (fields `postcode`, `birth_year`), not DOB + phone digits. Leading zero kept ("0870"); two-digit year = 19xx; a full DOB gives only its year. | 12 |
| 2 | Right-party question uses the **first name only**: "Could I please speak with {first_name}?" | 3, 4 |
| 3 | Fixed sentences S-OPEN, S-PURPOSE, S-SCAM, S-FAILED, S-LOSS, S-HOLD, S-CARE, S-SMS must be said word for word. | 3 |
| 4 | Restricted words before verification include "arrears", "repayment", "owe" (not only debt/payment). | 4 |
| 5 | Callback window uses **calendar days** (today, +1, +2), weekday 07:30-21:00, **weekends 09:00-21:00 allowed**, never a Victorian public holiday. | 8 |
| 6 | Calendar: **Melbourne Cup Day 2026-11-03**, Boxing Day substitute **Monday 2026-12-28** (26 Dec is a Saturday). | 17 |
| 7 | **Three stages** (A 1-29 / B 30-59 / C 60-89); limits 10th / 5th / 3rd business day; attempts 1 / 2 / 2. | 18 |
| 8 | **Stage C floor** = max(min/scheduled repayment, 25% of arrears rounded **up** to a whole dollar). | 18 |
| 9 | Offering the limit after a too-late date is **not** an attempt; an attempt that would repeat a refused offer is **skipped but counted**. | 21, 31 |
| 10 | A date without an amount means the full arrears amount. | 26 |
| 11 | **Split payment** for one product is not recordable; ask for one amount and one date. A request for regular smaller payments is a payment plan instead. | 28, 40 |
| 12 | Multi-product: "all today?" first; if yes, one combined read-back; otherwise **per-product read-back and create_promise immediately** (unlike Brief B's single combined read-back). | 30, 32 |
| 13 | **Vulnerability** (family/domestic violence, financial/elder abuse, mental health, cognitive impairment) -> S-CARE + immediate transfer `customer_care`, outcome `transferred/vulnerable`, no consent question. Comes first. | 38 |
| 14 | **Financial counsellor already helping** -> S-HOLD (21-day pause), note `collection_hold`; it overrides the payment-plan transfer even when the counsellor is "putting together a plan". | 41 |
| 15 | Hardship covers **every product without a recorded promise**; transfer queue `hardship_team`. | 39 |
| 16 | Notes are written **at the end**, in get_account order; **no notes on any transferred call**. | 47, 48 |
| 17 | `get_account` failure: retry once (S9-14). `create_promise` failure: retry the same product immediately, once (S9-13). | 15, 35 |
| 18 | Queues renamed: `hardship_team`, `customer_care`, `arrangements`; reasons `vulnerable`, `payment_plan`, `collection_hold` are new. Product fields renamed (`kind`, `arrears_amount`, `days_in_arrears`, `min_repayment`, `scheduled_repayment`); `kind=vehicle_loan` is said "car loan". OpenAPI uses `$ref` + `allOf`. | openapi |

## 2. Per-case derivation

| Case | now | Key derivation | Expected ledger |
|---|---|---|---|
| S9-01 | Tue 2026-10-13 10:00 | Stage A card (12 days). Postcode "oh-eight-seven-oh" -> `0870` (rule 12). Pays full today; today is a business day (rule 19). | promise p1 342.50 on 2026-10-13 |
| S9-02 | Thu 2026-10-29 19:00 | Daughter = third party (rule 7); offer to pay ignored. Sat 08:30 -> weekend window starts 09:00 -> invalid, ask once more (rule 9). Sat 2026-10-31 09:30: within today+2 calendar days, not a holiday, weekend hours OK (rule 8). | not_reached/callback; callback 2026-10-31 09:30 |
| S9-03 | Mon 2026-11-02 12:00 | Tue 2026-11-03 = Melbourne Cup Day -> invalid (rules 8, 17). Wed 2026-11-04 07:45: weekday window starts 07:30 -> valid; 2 days ahead. | not_reached/callback; callback 2026-11-04 07:45 |
| S9-04 | Wed 2026-11-04 14:00 | Two wrong postcodes (3065, 3058) then 3056 -> 2 wrong < 3 (rule 13). "Fifth of May, eighty-four" -> `1984` (rule 12). Redundancy = loss of employment -> rule 39 for both products (no promise recorded); declines -> both noted `hardship` (rule 47). Close: first non-paid note reason = hardship. | no_promise/hardship; notes p1 hardship, p2 hardship |
| S9-05 | Tue 2026-10-20 09:00 | Postcode right; years 1997, 1987, 1978 wrong = 3 wrong in total (rule 13). S-FAILED, nothing disclosed. | not_verified/failed |
| S9-06 | Tue 2026-11-17 11:00 | Card 66 days -> Stage C; limit = 3rd business day = 2026-11-20 (Fri). Floor = max(120, ceil(312.60)=313) = 313 (rule 18). "Too much" + 300 in one turn -> single floor offer (rule 27). Customer: 313 on Friday = 2026-11-20 <= limit. | promise p1 313 on 2026-11-20 |
| S9-07 | Tue 2026-10-27 10:00 | p1 card Stage A, limit 10th BD = 2026-11-11 (11-03 holiday skipped). p2 loan 40 d Stage B. p3 car loan 15 d Stage A. "Not all today" -> one by one. p1: "next Friday" = following calendar week = 2026-11-06 (rule 23), amount given 220 -> read back + record (rule 32). p2: "paid it off back in 2024, should be closed" = dispute (rule 43). p3: "paid this morning" = already paid (rule 42). Notes at end in order (rule 47). Promise recorded -> promise. | promise p1 220 on 2026-11-06; notes p2 dispute, p3 paid |
| S9-08 | Mon 2026-12-21 10:00 | Stage A loan, limit = 2027-01-07 (22,23,24,29,30,31 Dec, 4,5,6,7 Jan). Split offer (247.90 + 247.90) -> rule 28: only one payment per product, ask again. "the twenty-sixth... sorry, Monday the twenty-eighth" -> corrected value 2026-12-28 (rule 24) = Boxing Day substitute holiday (rule 17) -> next business day 2026-12-29 offered (rule 20); accepted. | promise p1 495.80 on 2026-12-29 |
| S9-09 | Mon 2026-11-09 15:00 | Loan 44 d -> Stage B, limit 5th BD = 2026-11-16. "Payday's the twentieth" = date proposal with no amount -> full amount (rule 26); after limit -> offer 1080 on 11-16, not an attempt (rule 21). Refused -> flat refusal -> attempt 1 (1080 on 11-16) repeats the refused offer -> skipped, counted (rule 31) -> attempt 2 = floor 360 on 11-16 -> accepted. | promise p1 360 on 2026-11-16 |
| S9-10 | Thu 2026-11-19 10:30 | p1 card full today (named) -> read back + record (rule 32). p2 loan 62 d (Stage C) would start at attempt 1, but the customer says a financial counsellor (National Debt Helpline) is already helping -> rule 41: S-HOLD, no payment request, note `collection_hold`. "Putting together a plan" is NOT a payment-plan request (rule 41 says rule 40 does not apply). Promise recorded -> promise. | promise p1 180 on 2026-11-19; note p2 collection_hold |
| S9-11 | Wed 2026-12-02 13:00 | p1 car loan 31 d (Stage B, limit 2026-12-09); bare "Friday" = 2026-12-04 (rule 23) -> read back + record. p2 card: customer discloses partner violence -> rule 38: S-CARE, immediate transfer `customer_care`, no consent question, no notes (rule 48), promise stays. | transferred/vulnerable; promise p1 520 on 2026-12-04; transfer customer_care |
| S9-12 | Wed 2026-11-11 16:00 | "Is this a scam?" before confirmation -> S-SCAM, does not count as an ask (rule 6); then confirmation. "Smaller instalments, like fifty a week" = payment plan (rules 28, 40), not a below-floor amount. | transferred/payment_plan; transfer arrangements |
| S9-13 | Mon 2026-11-23 10:00 | "Both in full today" -> combined read-back, one confirmation (rule 30). create_promise p1 fails, retried immediately, fails again -> not recorded, note `service_error` (rule 35). p2 recorded. Fault: create_promise fail_first_n = 2 (calls 1 and 2 are p1). | promise p2 410 on 2026-11-23; note p1 service_error |
| S9-14 | Tue 2026-12-15 09:30 | get_account fails once -> retry (rule 15) succeeds. Asks for a real person -> ask once if the assistant can help (rule 44) -> insists -> transfer `customer_care`. | transferred/human; transfer customer_care |

## 3. New intents / slots used in sim_script
- `split_payment` (S9-08): the customer offers one product's amount as two payments (rule 28). Deliberately no amount/date slot on that turn.
- `financial_counsellor` (S9-10): a financial counsellor is already helping (rule 41).
- `vulnerable` (S9-11): rule 38 disclosure.
- Identity slots: `id_postcode`, `id_birth_year` (field names of the openapi enum).

## 4. Ambiguities deliberately removed or not tested
- "Round up to a whole dollar" defined with an example; S9-06 uses a value with cents (312.60) only.
- Two separate floor offers (too much, then below floor) are not tested: S9-06 puts both in one turn, and rule 27 says a single offer.
- The order of notes vs. transfer is made explicit (rule 48: none on a transferred call); whether notes are written immediately or at the end is fixed to "at the end" (rule 47).
- Hardship mentioned after some products were already recorded is not tested in combination with a prior promise (only S9-04, no promise).
- "Intends to contact a counsellor" (rule 41 last sentence) is stated but not tested.
- Callback when `now` is late in the evening and "today" would be the only valid day: not tested.
- Whether the read-back for a too-late single date must mention the limit is transcript-level only, not in the ledger.
- S9-13 needs two consecutive create_promise failures: it carries only the kit form `faults: [{tool: create_promise, fail_first_n: 2}]` (plus `fail_count: 2`) and deliberately NOT the one-failure shorthand `fail_first`, so a runner that ignores `faults` shows a visible mismatch instead of silently testing a different scenario. S9-14 (one get_account failure) carries both forms, like S7-13.
