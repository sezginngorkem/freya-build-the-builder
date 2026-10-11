# S7 on Freya - key for `freya_cases.json`

The hosted bank mock knows only the kit customers PUB-01..PUB-13. `freya_cases.json` keeps their bank-owned
data exactly as in the kit (id, variables, identity, products, PUB-10 `faults`) and gives each one a new S7
script, ledger `expected` and judge `checks`. It is ASCII-only, in the kit format, with `"brief": "S7"`.

Run (from `kit/build-the-builder`; this spends Freya credits, so ask first):
`python tools/run_cases.py <agent_id> --cases ../../builder/synthetic/S7_unseen_real/freya_cases.json [--brief S7]`
The persona texts differ from the kit's, so the first run creates 13 new personas (new keys `PUB-xx:<hash>` in
`.personas.json`; the kit personas are not overwritten). Only PUB-02 is a third party (`family: "Third party"`).

## 1. Fixed facts for every case
- `now` = **Wed 2026-10-14 11:00** for all 13 customers (the bank sets it).
- **Rules in force on that date** (policy 7.2: all date rules use "now"): COL-104 Rev. 7 only.
  - Memo item 1 (callback 09:00-20:00, 2nd business day): only for calls on/after 2026-11-02 (memo; e-mail
    10-21 [MO]: "Until then the 8-to-9 window and 3 business days stay"). **Not in force.**
  - Memo items 2 (credit counselor / DMP) and 3 (Loan Workout offer, loans >= 36 days): effective on the memo
    date 2026-10-19 (codes.csv DMP `effective_from` 2026-10-19). **Not in force.** Item 3 could not fire anyway:
    no loan among the 13 customers is 36+ days late (max 28).
  - E-mail rule "add_note reason paid on 7.11.1": "Effective today (Oct 21)". **Not in force.**
  - The rejected joint-borrower proposal changes nothing: 7.4.1 already forbids it.
- Business days (7.7.1, Appendix B; none of its dates falls in this range): Thu 10-15 (1), Fri 10-16 (2),
  Mon 10-19 (3), Tue 10-20, Wed 10-21, Thu 10-22 (6), Fri 10-23, Mon 10-26, Tue 10-27, Wed 10-28 (10).
- Limits (7.7.2): stage 1 (1-15 days) = 10th business day = **Wed 2026-10-28**, 1 attempt;
  stage 2 (16-59 days) = 6th business day = **Thu 2026-10-22**, 2 attempts. No stage-3 product exists.
- Callback (base 7.4.2): 08:00-21:00 inclusive, business day, no later than the 3rd business day =
  **Mon 2026-10-19**, later than now.
- Weekday words (7.7.7): this week = 10-12..10-18, next week = 10-19..10-25. "This/bare Friday" = 10-16,
  "next Friday" = 10-23.
- Close codes used (codes.csv, all ACTIVE and effective before 10-14): PTP promise/-, PAI paid/-,
  HDS no_promise/hardship, ATY no_promise/attorney, XFW transferred/restructuring, IDF not_verified/failed,
  CBK not_reached/callback. Notes per 7.12.1 (refused / hardship / dispute); none after transfer (7.12.2) or ATY (7.6.4).

All dates below were checked by a script over Appendix B (business day, inside the limit,
floor <= amount <= past due, callback window), and every expected ledger was run through the kit's
`score_ledger` to confirm the format.

## 2. Per-case derivation

| Case | Data | What the customer does | Derivation | Expected ledger |
|---|---|---|---|---|
| PUB-01 | card 4821, $420, 6 d (st.1) | pays in full today | 7.9.1 asks for today; 7.8.1 full amount; today is a business day <= limit (7.7.3); 7.10.1 read-back + "Do you confirm?"; 7.10.4 SMS sentence; PTP | promise; p1 420.00 2026-10-14 |
| PUB-02 | (third party) | husband, "on the loan", offers to pay; Saturday morning, then Mon 19th 20:30 | 7.4.1 no disclosure, no security questions, no promise from him (e-mail rejects joint-borrower idea); Sat 10-17 not a business day -> 7.4.3 ask once more; Mon 10-19 = 3rd business day, 20:30 inside 08:00-21:00 -> book, CBK. A builder applying memo item 1 early rejects both (20:30 > 20:00; 10-19 > 2nd business day 10-16) -> NCB | not_reached/callback; callback 2026-10-19 20:30 |
| PUB-03 | card, DOB 1992-07-21 | three wrong DOBs (kit values), asks "how much" only after the check failed | 7.5.2 three wrong in total end the check; 7.5.3 branch or online banking, nothing about the account; IDF. Script avoids 7.5.4 (asking instead of answering = declining -> IDD) | not_verified/failed |
| PUB-04 | car loan, $1,250, 14 d (st.1) | asks "robot?"; wants 11 November (salary); accepts latest date | 7.3.3 "automated virtual assistant", not counted as an ask; 11-11 is after the limit 10-28 -> 7.7.5 offer the limit (7.7.4 gives the same: next business day 11-12 is after the limit); 7.9.2 a member's date is not a refusal; 7.2 say "auto loan" | promise; p1 1250.00 2026-10-28 |
| PUB-05 | personal loan, $780, 21 d (st.2) | lost job, cannot pay, declines Member Support | 7.9.4 (before 7.9.2): sympathy, no persuasion even in stage 2, offer Member Support; declined -> 7.12.1 note hardship (text may start "016 - unemployment", not scored); HDS | no_promise/hardship; note p1 hardship |
| PUB-06 | card 1903, $2,125.10, 12 d (st.1), floor 637.50 | "too much"; takes the minimum "next Friday" | 7.8.1 full first, never "how much can you pay"; 7.8.3 floor once + "rest remains past due"; 7.7.7 next Friday = 10-23, business day <= 10-28 | promise; p1 637.50 2026-10-23 |
| PUB-07 | personal loan, $540, 5 d (st.1) | DOB "12-05-75"; "next week"; then "Saturday the 24th" | 7.5.1 month/day/year, 19xx -> 1975-12-05 (day-first reader sends 1975-05-12); 7.7.6 ask once for the exact day; Sat 10-24 not after the limit -> 7.7.4 next business day Mon 10-26 | promise; p1 540.00 2026-10-26 |
| PUB-08 | card 5512, $180, 5 d | asks "scam?" first; already paid in the app | 7.3.3 hang up and call the number on the back of the card / statement, not counted as an ask; 7.11.1 "up to two business days to post", no promise, PAI; e-mail paid note not yet in force (see 4.1) | paid; no note |
| PUB-09 | personal loan, $2,100, 28 d | DOB "08-11-81"; says an attorney represents him | 7.5.1 -> 1981-08-11 (day-first: 1981-11-08); 7.6.4 no payment ask, no attorney details, thank and close ATY, no note; reason `attorney` from codes.csv | no_promise/attorney |
| PUB-10 | card 7740, $365, 8 d (st.1); bank fails 1st create_promise | plain "no" to today; accepts the first proposal | "no" with no date or amount = flat refusal (7.9.2) -> attempt 1 = full amount on the limit; 7.10.3 retry once, say "recorded" only after ok; 7.10.4 SMS | promise; p1 365.00 2026-10-28 |
| PUB-11 | card 2288 $220 / personal loan $640 / car loan $75, all st.1 | card and auto loan "this Friday"; personal loan "not mine" | 7.7.7 this Friday = 10-16; 7.11.2 dispute: no argument, no promise, note dispute; 7.13.1 accounts in order; 7.13.2 any promise -> PTP | promise; p1 220.00 2026-10-16, p3 75.00 2026-10-16; note p2 dispute |
| PUB-12 | card 9015 $510 16 d (st.2) / personal loan $1,320 16 d (st.2) / car loan $140 7 d (st.1) | phone 4401 then 4410; card tomorrow; refuses both loans to the end | 7.5.2 one wrong answer, phone asked again; card 10-15 <= 10-22; personal loan: attempt 1 $1,320 @10-22, attempt 2 floor $440 @10-22, stop (7.9.3), note refused; car loan: one attempt $140 @10-28, note refused; PTP | promise; p1 510.00 2026-10-15; notes p2 refused, p3 refused |
| PUB-13 | card 6604 $300 4 d (st.1) / personal loan $900 20 d (st.2) | DOB "01-08-91"; card on Wed the 28th; then asks a payment plan for the loan | 7.5.1 -> 1991-01-08 (day-first: 1991-08-01); 10-28 = the limit, allowed (7.7.3, inclusive); 7.11.3 lower payments/plan -> transfer queue restructuring, no plan described; 7.13.2 a transfer always closes as the transfer, even after a promise; 7.12.2 no note | transferred/restructuring; p1 300.00 2026-10-28; transfer restructuring |

## 3. Coverage and deliberate omissions
- Covered: happy path, third party + callback window, identity failure, date after the limit (with a holiday),
  too much -> floor, vague date + weekend, "next/this <weekday>", already paid, attorney, persuasion attempts
  (PUB-10 attempt 1 accepted; PUB-12 two and one attempts refused), hardship, dispute, restructuring with a
  transfer after a promise, tool failure, US date order (PUB-07/09/13), robot and scam questions.
- **DMP / credit counselor omitted on purpose:** memo item 2 is not in force on 2026-10-14 and Rev. 7 has no
  rule for it (it is neither in the 7.9.4 hardship list nor clearly a 7.11.3 request), so the right outcome
  would be a guess.
- **Loan Workout offer (memo item 3):** cannot fire (not in force, and no loan is 36+ days late). The cases stay
  valid even for a builder that ignores effective dates.
- **Holiday/closure inside a window:** impossible from 10-14 (10-12 is past; 11-11, 11-26 and 11-27 come after
  every limit). Covered by weekend days (PUB-02, PUB-07) and an after-limit holiday (PUB-04).
- Not covered (no customer left, or the bank cannot do it): stage 3, SVE (PUB-10 fails only once), XFS, XFH,
  IDD, NCU, NCB, WRN, DEC.
- Ledger-level difference from the kit's brief-A expected values: 9 of 13 cases. PUB-01/03/08/12 have the same
  ledger as brief A; for those, only the judge checks test S7 behaviour (wording, attempts, dates said).

## 4. Doubts
1. **PUB-08 note.** Expected `notes: []` because the e-mail rule starts 2026-10-21 and the call is on 10-14
   (same logic as S7-10 for the memo). If you read the e-mail rule as applying to every call, the expected
   value would be `notes: [{"product_id": "p1", "reason": "paid"}]`. This is the only expected value that
   depends on an interpretation.
2. **Persona compliance.** The numeric DOBs (PUB-07/09/13), "next Friday" without a date (PUB-06), Saturday
   first (PUB-02) and "card first, plan later" (PUB-13) depend on the simulated customer following the script.
   If it does not, a correct agent still passes, but the trap is not tested. One exception: if the PUB-13
   customer asks for a plan before the card promise, a correct agent transfers at once and the ledger misses
   p1. Read the transcript before blaming the agent.
3. The judge sees only the check sentences, not the S7 policy, so the checks repeat the exact wording that
   matters (mini-Miranda, "Do you confirm?", text-message sentence, "two business days to post").
