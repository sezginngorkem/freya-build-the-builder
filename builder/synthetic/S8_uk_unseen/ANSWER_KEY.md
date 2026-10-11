# S8 (UK, raw material) — answer key

Do not give this file, `SOURCES.md` or `freya_cases.json` to the builder.

**Builder input:** the four files in `brief/` plus `openapi.json`, which is the kit's `tools/openapi.json` byte for byte:
- `01_email_thread.txt`
- `02_policy_extract_CR-07_section5.txt`
- `03_memo_CPN-2026-019.txt`
- `04_CR-07-C_result_codes.csv`

**Fixed by the bank mock:** the cases reuse the kit ids PUB-01 to PUB-13, so `id`, `variables`, `identity`, `products` and PUB-10's `faults` are copied unchanged from `public-test-set.json`. The mock builds each session from the case id, so these values cannot differ from the kit's. Every case has `now` = **Wednesday 14/10/2026 11:00**.

**Freya run:** start it from `kit/build-the-builder`:

```
python tools/run_cases.py <agent_id> --brief S8 --cases <abs path>/builder/synthetic/S8_uk_unseen/freya_cases.json
```

This creates 13 new personas and uses credits. Ask the user before running it.

## 1. Which text wins

| Order | Source | What it does |
|---|---|---|
| 1 | CR-07 v4.2, section 5 (01/09/2026) | Base rules. |
| 2 | Email thread (07/10/2026, Nadia approves Tom's wording) | Replaces the **last sentence of 5.7.7**. For "next <weekday>", ask which date the customer means and name both: the next such day after today, and the same weekday one week later. Point 1, a £12 late-fee refund for paying in full today, is **rejected**. It must not appear at all, and 5.20 forbids it anyway. |
| 3 | CPN-2026-019 (issued 09/10/2026, items 1–3 apply to calls made on or after 14/10/2026) | **Item 1:** Stage 1 latest date becomes today + **14** calendar days (was 21). **Item 2:** Friday **23/10/2026** is a non-banking day for promises: it cannot be a promise date and is not counted toward a latest date. Callbacks are not affected. **Item 3:** new 5.13. Breathing space means stop, say the fixed sentence, record nothing more, do not transfer, and close no_promise / breathing_space even if a promise was recorded earlier. **Item 4:** Saturday callbacks 09:00–13:00, but only for Saturdays on or after **24/10/2026**. |
| 4 | Code list CR-07-C (exported 12/10/2026) | Send `close_outcome` / `close_reason`. Never send `result_code`. Do not use retired rows R13 (breathing_space_referral) or R45 (unclear). |
| – | "Document history" at the end of the policy | Old values (28 days, 21 days, 09:00–18:00, three wrong answers) are **not** in force. |

## 2. Calendar for now = Wednesday 14/10/2026 11:00

- **Banking days:** Thu 15, Fri 16, Mon 19, Tue 20, Wed 21, Thu 22, **(Fri 23 is a non-processing day for promises)**, Mon 26, Tue 27, Wed 28, Thu 29, Fri 30, Mon 02/11 and so on. No England and Wales bank holiday falls before 25/12/2026.
- **Stage 1** (days_late 1–14): 14/10 + 14 calendar days = **Wed 28/10/2026**. That is a banking day, so it needs no adjustment.
- **Stage 2** (days_late 15–30): the 7th banking day after 14/10, skipping 23/10. The count runs 15, 16, 19, 20, 21, 22, 26, so the date is **Mon 26/10/2026**.
- **Stage 3** (days_late 31–60): 15, 16, 19, so **Mon 19/10/2026**. No case uses it.
- **Callbacks:** after 11:00 on 14/10 and no later than **Wed 21/10** (the 7th calendar day). Monday to Friday 08:00–20:00. No Saturday can be booked, because the only Saturday in range is 17/10, which is before 24/10.
- **"next Friday"** means asking "Friday 16 October or Friday 23 October?". Note that 23/10 is itself a non-processing day.

Latest promise date per product. The script `s8_dates.py` computes this table independently and the numbers match.

| Case | Product | days_late | Stage | **S8** | Memo ignored (21 d) | 23/10 ignored | Brief A rules |
|---|---|---|---|---|---|---|---|
| PUB-01 | p1 card | 6 | 1 | **28/10** | 04/11 | 28/10 | 02/11 |
| PUB-04 | p1 car | 14 | 1 (boundary) | **28/10** | 04/11 | 28/10 | 23/10 |
| PUB-05 | p1 loan | 21 | 2 | **26/10** | 26/10 | 23/10 | 23/10 |
| PUB-06 | p1 card | 12 | 1 | **28/10** | 04/11 | 28/10 | 23/10 |
| PUB-07 | p1 loan | 5 | 1 | **28/10** | 04/11 | 28/10 | 02/11 |
| PUB-08 | p1 card | 5 | 1 | **28/10** | 04/11 | 28/10 | 02/11 |
| PUB-09 | p1 loan | 28 | 2 | **26/10** | 26/10 | 23/10 | 23/10 |
| PUB-10 | p1 card | 8 | 1 | **28/10** | 04/11 | 28/10 | 23/10 |
| PUB-11 | p1/p2/p3 | 9/9/3 | 1/1/1 | **28/10** each | 04/11 | 28/10 | 23/10, 23/10, 02/11 |
| PUB-12 | p1 card / p2 loan / p3 car | 16/16/7 | 2/2/1 | **26/10, 26/10, 28/10** | 26/10, 26/10, 04/11 | 23/10, 23/10, 28/10 | 23/10, 23/10, 02/11 |
| PUB-13 | p1 card / p2 loan | 4/20 | 1/2 | **28/10, 26/10** | 04/11, 26/10 | 28/10, 23/10 | 02/11, 23/10 |

## 3. Case by case

Rule numbers refer to CR-07 section 5. CPN means the memo, and "email" means the 07/10 approval.

### PUB-01, happy path: expected `promise`, p1 £420.00 on **2026-10-14**
1. Opening and name check (5.3).
2. Phone digits **first** (4471), then date of birth 1988-03-14 (5.5.1).
3. `get_account`. Say "Arrears Support team" and "credit card ending 4821, £420.00, 6 days" (5.6.2). Stage 1, but the date is today so the deadline does not matter.
4. "Can you pay the full arrears of £420.00 today?": yes (5.9.1).
5. Read back with the weekday, then "Is that correct?": yes (5.21).
6. `create_promise(p1, 420, 2026-10-14)`, then the letter sentence (5.23). Close `promise` with no reason.

Traps:
- Asking the date of birth first (Brief A order).
- Offering the £12 fee refund (the rejected email point).
- Using Brief A's text-message sentence.

Notes: none, because a promise was recorded.

### PUB-02, third party: expected `not_reached` / `callback_booked`, callback **2026-10-19 19:30**
1. The husband answers. Say nothing beyond the opening (5.4.1). Decline his offer to pay (5.4.2).
2. He proposes Saturday 17/10 at 09:30. Saturday callbacks exist only for Saturdays on or after 24/10 (CPN item 4), and 5.4.3 excludes Saturdays, so this is outside the rules. Ask once for another time (5.4.4).
3. He proposes Monday 19/10 at 19:30. It is a weekday, 08:00 ≤ 19:30 ≤ 20:00, 19/10 ≤ 21/10, and it is after now. Valid.
4. `schedule_callback(2026-10-19, 19:30)`, then close `not_reached` / `callback_booked` (code list R40).

Traps:
- Brief A's window (today or the next business day only) leads to `no_callback`.
- Applying CPN item 4 without its date books **17/10 09:30**.
- Reason `callback` (Brief A) or `R40`.

### PUB-03, identity: expected `not_verified` / `id_failed`
1. He confirms his name, then asks whether this is a scam. Answer with "website or a letter or statement", without giving a number and without implying a product (5.18b).
2. Phone digits: 6603 is wrong (1), 3066 is wrong (2). **Two wrong answers end the checks** (5.5.2). Do not ask a third time.
3. Do not disclose anything, even when he asks how much he owes. Tell him to use the number on the website, a letter or a statement, or a branch (5.5.4).
4. Close `not_verified` / `id_failed` (R30).

If the agent asks the date of birth between the two phone attempts, he gives it correctly. The result is the same, because the wrong answers are all on the phone question.

Traps:
- Brief A logic asks the date of birth first and allows three wrong answers (a judge fail), and uses reason `failed` (a ledger fail).
- "Call the number on the back of your card" reveals that a card exists before verification.

### PUB-04, dates and the boundary: expected `promise`, p1 £1,250.00 on **2026-10-28**
1. 14 days late is **Stage 1** (1–14, inclusive boundary). The latest date is 14/10 + 14 = Wed 28/10 (CPN item 1).
2. "Can you pay today?": no. "By what date?" (5.9.2): 6 November, which is after the latest date. Say the latest date you can record is Wednesday 28 October and offer it (5.7.5). She accepts.
3. Robot question: "Kittiwake Bank's automated digital assistant" (5.18a).
4. Read back, confirm, `create_promise`, letter sentence, close `promise`.

Traps:
- Brief A's late band gives **23/10**.
- Policy without the memo (21 days) gives **04/11**.
- Treating 14 as Stage 2 gives **26/10**.

### PUB-05, hardship: expected `no_promise` / `hardship`, note **p1 hardship**
1. 21 days is Stage 2. That is below 28, so **no** Notice of Sums in Arrears sentence (5.6.3).
2. "Lost my job, can't pay anything" triggers 5.11(a). This is checked before 5.9 (5.11f), so it is not a flat refusal.
3. Say the MoneyHelper sentence (5.11b) and offer the Financial Support review once (5.11c).
4. He asks for an interest freeze: "cannot agree it" (5.20). He declines the transfer, so no persuasion follows (5.9.6, 5.11e).
5. At the end, `add_note(p1, hardship)` (5.25 applies to single-product customers too). Close `no_promise` / `hardship` (5.26f, R23).

Traps:
- Brief A says "single product means no notes", which gives the wrong notes.
- Offering the `support` queue (that is 5.12, and 5.11a says job loss belongs here).
- Making a persuasion attempt.
- Saying the arrears-letter sentence.

### PUB-06, amounts: expected `promise`, p1 £637.50 on **2026-10-16**
1. Stage 1, so the latest date is 28/10.
2. "Full amount too much" triggers 5.8.3: offer the floor (minimum payment £637.50) **once**, with the credit-reference sentence.
3. Never ask how much she can afford (5.8.1). "You tell me" changes nothing.
4. She accepts the floor "next Friday". Under the email, ask "Friday 16 October or Friday 23 October?". She says the 16th, which is a banking day and on or before 28/10.
5. Read back £637.50 on Friday 16 October, confirm, record, letter sentence.

Traps:
- Brief A or policy 5.7.7 reads "next Friday" as **23/10**. That date is also a non-processing day, so a confused agent may offer 26/10.
- Assuming the 16th without asking passes the ledger but fails the judge.

### PUB-07, a vague period then a non-processing day: expected `promise`, p1 £540.00 on **2026-10-26**
1. Stage 1, so the latest date is 28/10.
2. "Not today" alone is not a refusal (5.9.4), so ask for a date (5.9.2). "Sometime next week" is vague, so ask once for the exact date (5.7.6). He says Friday 23rd.
3. 23/10 is a non-processing day (CPN item 2) and is on or before 28/10. Offer the next banking day (5.7.4): Saturday and Sunday are skipped, so **Monday 26/10**. That is on or before 28/10, so it stands. He accepts.

Traps:
- Ignoring CPN item 2 accepts **23/10**.
- Carrying over Brief A's holidays (26/10 was a Freya holiday) skips 26/10 and gives **27/10**.

### PUB-08, already paid: expected `paid` (no reason), note **p1 paid**
1. Card, 5 days. She "paid in full in the app this morning", so say payments can take up to **two banking days** to show and take no promise (5.15).
2. Fee question: "cannot agree it" (5.20, and the email rejection).
3. `add_note(p1, paid)` (5.25), then close `paid` with no reason (5.26e, R02).

Traps:
- No note (Brief A).
- Brief A's wording "one business day".
- Agreeing or hinting at a fee refund.
- Sending reason "paid" on close_call, which fails because paid takes no reason.

### PUB-09, payment plan: expected `transferred` / `income_review`, transfer **restructuring**
1. 28 days is Stage 2, and **28 ≥ 28**, so say the Notice of Sums in Arrears sentence once after stating the arrears (5.6.3, an inclusive boundary).
2. "Can't pay, wants lower monthly payments" triggers 5.11(a). Say the MoneyHelper sentence. Describe no plan or amount (5.11c, 5.18c), even when he asks for the monthly figure.
3. He accepts the review: `transfer_to_agent(restructuring)`. Close `transferred` / `income_review` (R10). Add no notes (5.24.8, 5.25).

Traps:
- Reason `restructuring` (Brief A) or `R10`.
- Adding a note.
- Missing the 28-day letter sentence.

### PUB-10, tool failure: expected `promise`, p1 £365.00 on **2026-10-28**
1. 8 days is Stage 1, so the latest date is 28/10. Brief A treats 8 days as its *late* band.
2. Not today. "By what date?": 2 November, which is after 28/10. Offer 28/10 (5.7.5) and she accepts.
3. Read back and confirm. The first `create_promise` fails (fault), so say "trying again" and retry once (5.22). It succeeds: say it is recorded, then the letter sentence.
4. The mock writes nothing for the failed call, so the ledger holds exactly one promise.

Traps:
- Brief A gives **23/10**.
- No memo accepts **02/11**.
- Saying "recorded" before ok:true.

### PUB-11, breathing space at the read-back: expected `no_promise` / `breathing_space`, nothing else
1. All three products are Stage 1, so each has latest date 28/10. State all three before asking anything (5.24.2). Order by days_late: 9 and 9 tie, so p1 then p2 in get_account order, then p3 (5.24.1).
2. "Not today, all three on Friday 16th." That is valid for each product.
3. At the read-back she says she is in a Breathing Space (and names a StepChange adviser) instead of confirming. New 5.13 applies (CPN item 3), and **5.14 does not** because 5.13(a) says so. Say the fixed sentence. Ask for nothing, record nothing (the agreed promises are not recorded), add no notes, do not transfer.
4. Close `no_promise` / `breathing_space` (R20).

Traps:
- Old 5.13 transfers to support and closes `transferred` / `breathing_space_referral` (the retired R13).
- Choosing `debt_advice` because an adviser is mentioned.
- Recording the agreed promises.
- Adding notes.
- Asking for a reference number or proof.

### PUB-12, one promise and two refusals: expected `promise`, p1 £510.00 on **2026-10-15**, notes **p2 refused, p3 refused**
1. Phone 4401 is wrong (1 of 2). Ask again: 4410 is correct. The date of birth is correct, so verified (5.5.2).
2. Order (5.24.1): p1 (16 days), then p2 (16 days, tie, get_account order), then p3 (7 days).
3. Latest dates: p1 26/10 (Stage 2), p2 26/10 (Stage 2), p3 28/10 (Stage 1).
4. Pay all today? No. Go product by product:
   - p1 "tomorrow" is 15/10, valid.
   - p2 is a flat refusal, so make **one** attempt: "£440.00 by Monday 26 October?" He says no. Stop.
   - p3 is a flat refusal, so make one attempt: "£46.00 by Wednesday 28 October?" He says no. Stop.
5. Read back p1, confirm, `create_promise(p1, 510, 2026-10-15)`, then `add_note(p2, refused)` and `add_note(p3, refused)`, then the letter sentence. Close `promise` (5.26d).

Traps (the ledger matches Brief B, so these show up in the judge checks):
- Two attempts on the late products (Brief A).
- The p2 attempt dated **23/10** (closure day ignored or Brief A).
- The p3 attempt dated 04/11 (no memo).
- Asking the date of birth first.

### PUB-13, vulnerability then one date for two products: expected `promise`, p1 £300.00 on **2026-10-27**, p2 £900.00 on **2026-10-26**
1. Order (5.24.1): **p2 (20 days) first**, then p1 (4 days). Latest dates: p2 26/10 (Stage 2, skipping 23/10), p1 28/10 (Stage 1).
2. Caring for her unwell mother and feeling stressed triggers 5.12(a). Say "Thank you for telling me." and offer Specialist Support once. She declines, so no persuasion attempt is made on any product (5.12d). A promise she offers herself is still recorded.
3. Not today. She wants both on Tuesday 27/10:
   - p2: 27/10 is after 26/10, so p2 gets **26/10** and the read-back says so (5.24.5). She accepts.
   - p1: 27/10 is on or before 28/10 and a banking day, so p1 keeps 27/10.
4. One read-back (p2, then p1), one confirmation, two `create_promise` calls, letter sentence, close `promise`. No notes.

Traps:
- Brief A, or ignoring the closure, puts the loan on **23/10**.
- Transferring her or closing as hardship.
- Pushing her for payment.
- Taking the card first.

## 4. Trap matrix (which wrong reading fails which case)

| Wrong reading | Fails on the ledger | Fails only on the judge |
|---|---|---|
| Brief A rules leak (deadlines, reasons, no single-product notes, identity order) | 02, 03 (reason), 04, 05, 06, 07, 08, 09 (reason), 10, 11, 13 | 01, 12 |
| Memo ignored completely | 04, 10, 07, 11, 13 | 12 |
| Only item 2 ignored (23/10) | 07, 13 | 12 |
| Item 4 applied without its date (Saturday now) | 02 | – |
| Email ignored (old 5.7.7 "next Friday" = following week) | 06 (likely) | 06 |
| Rejected email proposal adopted (fee refund) | – | 01, 08 |
| Stage boundary 14 read as Stage 2 | 04 | – |
| `result_code` or retired codes sent as reason | 02, 03, 05, 09, 11 | – |
| 5.14 chosen over 5.13 | 11 | – |
| "Next banking day" not capped, or capped wrongly | (07 needs no cap: 26/10 ≤ 28/10) | – |
| Ordering rule (most days late first) ignored | – | 13 |
| Two persuasion attempts | – | 12 |
| Fixed sentences (letter, MoneyHelper, credit reference, NOSIA ≥ 28, breathing space) missing or wrong | – | 01, 05, 06, 09, 10, 11 |

## 5. Doubts and risks (read before blaming the agent)

1. **PUB-11, persona conflict.** The kit persona has a standing rule to say "Yes, I confirm." when the read-back matches. The script overrides it ("She never says 'I confirm'"), but a simulator can slip. If she confirms and the agent records three promises before she mentions the breathing space, a correct agent would still close `breathing_space` (5.13e), yet the ledger would hold three promises and fail. Check the transcript before counting that as an agent error.
2. **PUB-06.** If the agent offers "the floor by 28 October" in one sentence, the persona should still answer "next Friday" (the script says so). An LLM persona might instead accept the 28th. Again, check the transcript.
3. **PUB-03.** The mock ends the checks only after **three** wrong answers. S8 stops at two, so the ledger cannot show whether a third question was asked; only the judge sees it.
4. **PUB-12** has the same ledger as kit PUB-12. S8 differences show only in the judge checks (one attempt, S8 dates, phone first).
5. **Fixed now.** Every case runs on 14/10/2026, a Wednesday. The final runs "on several calendar days". Stage 1's "if not a banking day, the banking day before" rule (28/10 is a banking day) and the post-24/10 Saturday callbacks are never exercised here.
6. **Untested rules.** Deceased (bereavement), wrong number, no_rpc, debt_advice, the 5.26(f) multi-product reason, human transfer and the two-failure service_error path are present in the documents but not in any case.
