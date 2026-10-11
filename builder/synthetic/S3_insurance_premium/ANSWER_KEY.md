# ANSWER KEY: S3_insurance_premium (Meridian Insurance, overdue premiums)

Inputs: `brief.md`, `openapi.json`. Cases: `cases.json` (14). All cases use `now = 2026-12-14T09:30` (Monday).

## What this suite stresses
- Domain shift: "products" are insurance policies (`type` motor/home, `premium_overdue`, `days_overdue`, `monthly_premium`, `lapse_date`).
- Identity `date_of_birth` + `postcode` (insured address), with the day/month swap hint.
- Two bands with **different day-counting**: grace = calendar days with roll **back**; final notice = business days.
- A per-policy cap from data (`lapse_date`) that overrides the band deadline (rule 16, "comes before rule 15").
- Motor: no floor, only the full premium. Home: floor = `monthly_premium`.
- Third party: only spouse/partner may give a callback (next business day only, 08:00–20:00 incl.); anyone else -> `not_reached` / `other_party` with no callback even if they volunteer a time.
- Transfer reasons `customer_care`, `policy_change`, `human`; queue `retention` for cancel/change.
- Mandatory sentence: "Your cover stays in place as long as the payment arrives by the date we agreed."

## Deadlines for now = Mon 2026-12-14
Holidays: 2026-12-24, 2026-12-25, 2026-12-28, 2027-01-01.
- **grace** (1–14 days): 14 calendar days -> Mon 2026-12-28 = holiday -> last business day before it: 27 Sun, 26 Sat, 25 hol, 24 hol -> **Wed 2026-12-23**.
- **final notice** (15–30): 5th BD after today: Tue 15/12=1, Wed 16/12=2, Thu 17/12=3, Fri 18/12=4, Mon 21/12=5 -> **2026-12-21**.
- **Lapse cap (rule 16):** if band deadline >= lapse_date, deadline = last BD strictly before lapse_date.
- Attempt 1 date: Friday of this week = **2026-12-18** (business day, not after either deadline).
- Partner callback: next business day only = **2026-12-15**, 08:00–20:00 both included.

## Per-case resolution
| Case | Policy / band / deadline | Resolution | Expected |
|---|---|---|---|
| S3-01 | motor 6d grace, 12-23 (lapse 01-08) | pays today | promise 380 2026-12-14 |
| S3-02 | home 10d grace, 12-23 | "4/7/1985" read DMY -> 1985-07-04 -> hint day_month_swapped (not a wrong answer) -> month as word -> 1985-04-07; "this Friday" = 12-18 | promise 240 2026-12-18 |
| S3-03 | – | husband = spouse; tomorrow 08:00 (start, included) | not_reached/callback 2026-12-15 08:00 |
| S3-04 | – | flatmate volunteers a valid time -> still no booking | not_reached/other_party, no callback |
| S3-05 | – | partner: today 19:00 (never today) -> ask once more; tomorrow 20:30 (> 20:00) -> stop | not_reached/no_callback |
| S3-06 | home 12d grace, 12-23 (lapse 01-12) | names 12-29 -> after deadline -> offer 12-23 | promise 300 2026-12-23 |
| S3-07 | motor 20d final, 12-21 (lapse 12-31) | names 12-21 = deadline (included); first create_promise fails, retry | promise 410 2026-12-21 |
| S3-08 | home 25d final, 12-21 | names 12-22 -> offer 12-21 | promise 520 2026-12-21 |
| S3-09 | motor 4d grace, 12-23 | offers 300 on Fri -> motor: only full premium, offer 600 on 12-18 once -> accepted | promise 600 2026-12-18 |
| S3-10 | home 13d grace, band 12-23, **lapse 12-21** | 12-23 >= 12-21 -> deadline = last BD before 12-21 = Fri 12-18; names 12-22 -> offer 12-18 | promise 260 2026-12-18 |
| S3-11 | motor 8d grace 12-23; home 18d final 12-21 | one date 12-23 -> motor 12-23, home its own deadline 12-21, one read-back | promises p1 390 12-23, p2 450 12-21 |
| S3-12 | home 16d final, 12-21 | Sat 12-19 -> next BD Mon 12-21 (not after deadline) | promise 330 2026-12-21 |
| S3-13 | motor 7d grace | father died -> hardship (before rules 26/35), sympathy, offer customer care, accepted | transferred/customer_care, queue customer_care, no notes |
| S3-14 | motor 22d final | sold the car, wants to cancel -> retention | transferred/policy_change, queue retention, no notes |

## Intended readings of tricky rules
- Rule 15 grace roll is **backward** (last business day before), unlike S4's forward roll and A's "Nth business day" counting.
- Rule 16 "comes before rule 15": the lapse cap is applied after computing the band deadline; "before the lapse_date" is strict (a promise on the lapse date itself is not allowed).
- Rule 18 second sentence (next business day after the deadline -> offer the deadline) is not exercised by a case but must be in the IR.
- Rule 23 motor: an amount below the full premium is offered the full premium **once on the date discussed**; refusing = flat refusal (uses an attempt).
- Rule 5 vs 6: the decisive fact is the relation the person states (spouse/partner vs anyone else), not whether they offer a time.
- Rule 33 includes "a recent accident or burglary" as hardship (insurance-specific trigger list).
- New intent the reader must declare: `policy_change` (S3-14). The "flatmate" / "partner" distinction may be modelled as a slot or two intents (e.g. `third_party` + `partner`); the sim marks both as `third_party` and the relation is in the text, so the reader's NLU must separate them.

## Planted ambiguities
1. "Friday of this week" when today is Monday 12-14 = 12-18 (clear); the rule also covers "if it is after the deadline, use the deadline" — matters only with a lapse cap before Friday.
2. Partner callback "never today" while A allowed today — reader must not inherit A.
3. Rule 21 "this/next weekday" is A-style (calendar week) here, but S4 defines it differently; readers must not hard-code either.
