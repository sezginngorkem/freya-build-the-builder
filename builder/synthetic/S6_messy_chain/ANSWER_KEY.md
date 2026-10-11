# ANSWER KEY: S6_messy_chain (Brightwater Community Bank, raw material, chained amendments)

Inputs to merge (all five): `policy_extract.txt` (COL-POL-12 v5.1, PDF text layer: page headers mid-text, hyphenated wrap "persua-/sion", flattened Table 5-A, footnote ¹), `memo_M-2026-031.txt` (effective 2026-11-02, item A2 later), `memo_M-2026-034.txt` (effective 2026-11-16; amends 031), `email_thread.txt` (Fwd of a reply chain: newest first, `-----Original Message-----`, `>`/`>>`/`>>>` quoting, inline `[RK]` answers, quoted-printable `=` soft breaks, iPhone one-liner, auto-reply, a wrong TL;DR), `disposition_codes.csv` (semicolon-delimited Excel export: 4 preamble rows, header with odd names incl. trailing space `API reason `, DD/MM/YYYY dates, inactive codes, footer rows), plus `openapi.json` (authoritative wire spelling).
`now = 2026-11-18T10:00` (Wednesday) for all cases except S6-05 (`2026-11-13T10:00`, Friday).

## 1. Final rule set
| Item | Base (v5.1) | Change chain | Final on 18 Nov | Final on 13 Nov |
|---|---|---|---|---|
| Tier 1 (1-29) limit / attempts | 8 BD / 1 | 034 item 5: 6 BD from 1 Dec, NOT in force | 8 BD / 1 | 8 BD / 1 |
| Tier 2 (30-59) limit | 5 BD | 031 A1 -> 4 BD (from 2 Nov); 034 item 1 -> 3 BD (from 16 Nov) | **3 BD** | **4 BD** |
| Tier 2 attempts | 2 | – | 2 | 2 |
| Tier 3 (60-89) limit / attempts | 3 BD / 2 | 031 A3 -> 1 attempt; kept by 034 item 3 | 3 BD / **1** | 3 BD / 1 |
| Holidays | 11-11, 11-26, 12-25, 01-01 | 031 A4 + 2026-11-27 (policy footnote says this is decided by memo); kept by 034 | + **11-27** | + 11-27 |
| 2nd security question | ZIP (`postcode`) | 031 A2 -> phone_last4 from 23 Nov; 034 item 2 withdraws it; email [RK] "Build ZIP" | **postcode** | postcode |
| Confirmation sentence | "You will get a text message confirming your promise." | 031 A5 | "You will receive a text message confirming your promise today." | same |
| Callback window | 09:00-20:00 incl. | email 6 Nov (owner Rachel Kim, Compliance no objection), from Mon 9 Nov | **09:00-19:00, both included** | same |
| Person request (6.4) | ask once to help, then customer_care | email 4 Nov asks for immediate transfer; Compliance 5 Nov: NO; owner 6 Nov accepts | **unchanged: ask once first** | same |
| Stop calling | – | 034 item 4 new 7.6 (effective 16 Nov); code NP-CC/N-CC eff. 16/11/2026 | no_promise/cease_contact + note | (not in force; not tested) |
| Hardship reason | hardship | codes: FH pilot codes inactive; email [RK] "hardship" | `hardship` | same |
| Third-party outcome spelling | "Not reached" | codes + openapi + email [RK] b) | `no_contact` | same |
| Complaints | – | TR-CPL inactive, queue not in API; email [RK] c): no complaints rule, insisting = 6.4 | no special rule | same |

Noise that must NOT become rules: Owen's TL;DR "Tier 2 is four business days per 031" (stale since 034); Rachel's late-fee waiver ("parking that for 2027, don't build"); Hal's Christmas Eve rumour (nothing decided, and outside the case dates); auto-reply; "Distribution of the consolidated v5.2 text will follow"; Appendix C "not reproduced" (the CSV is the list); inactive codes (NP-FH, TR-FH, N-FH, TR-CPL, UR-LM).

## 2. Dates
now Wed 18 Nov (holidays incl. 26 + 27 Nov): BD after: 19=1, 20=2, 23=3, 24=4, 25=5, 30=6, 1 Dec=7, 2 Dec=8.
- Tier 1 limit **2026-12-02** (base calendar without 27 Nov: 12-01). Tier 2 limit **2026-11-23** (031 only: 11-24; base: 11-25). Tier 3 limit **2026-11-23**.
- Attempt 1 date = last BD of this week = **Fri 2026-11-20** (before every limit here).
now Fri 13 Nov: Tier 2 (031 A1) 4th BD: 16, 17, 18, 19 -> **2026-11-19** (034 applied too early: 11-18).

## 3. Per case
| Case | Trap | Expected | Wrong reading gives |
|---|---|---|---|
| S6-01 | ZIP 07302 leading zero; new confirmation sentence | promise 455 on 11-18 | – |
| S6-02 | email callback window: 19:30 out, 19:00 in | no_contact/callback 11-18 19:00 | policy only: 19:30 booked |
| S6-03 | asks postcode, never phone_last4; 2 wrong still pass | promise 600 on 11-18 | phone_last4 -> "unknown field" |
| S6-04 | chained: 034 replaces 031 A1 | promise 820 on **11-23** | 031 only 11-24; base 11-25->asked 11-24 accepted |
| S6-05 | effective dates: on 13 Nov 034 not yet in force | promise 1040 on **11-19** | 034 early: 11-18 |
| S6-06 | Tier 3 one attempt (990 on Fri 11-20) | no_promise/refused, note p1 refused | base: attempt 2 99 on 11-23 -> promise |
| S6-07 | 27 Nov holiday -> next BD | promise 380 on 11-30 | base: 11-27 |
| S6-08 | person request: ask once first (early quoted request was rejected) | promise 260 on 11-18 | reading only Rachel's 4 Nov ask: transferred/human |
| S6-09 | new 7.6 stop calling | no_promise/cease_contact, note p1 cease_contact | – |
| S6-10 | one date for both, loan capped at its own limit | p1 310 on 11-25, p2 900 on 11-23 | 031 only: p2 on 11-24 |
| S6-11 | paid this morning vs paid off last year (= dispute) | no_promise/dispute; notes p1 paid, p2 dispute | – |
| S6-12 | hardship spelling `hardship` | transferred/hardship, queue hardship_desk | financial_hardship (retired pilot code) |
| S6-13 | floor = installment; create_promise fails once | promise 210 on 11-18 | – |

Cases carry partial-override fields (`memo031_only_expected`, `memo034_applied_too_early_expected`, `base_policy_expected`, `without_email_expected`, `early_quote_reader_expected`) that the scorer ignores.

## 4. Ambiguities and intended reading
1. **Chained amendment.** 034 item 1 replaces 031 A1, so the Tier 2 value depends on the call date: 5 (before 2 Nov), 4 (2-15 Nov), 3 (from 16 Nov). The IR should store the final value for the deployment date; if the IR can branch on `today`, branching on the memo effective dates is best (S6-05 tests it).
2. **Item with its own later effective date inside a memo** (031 A2 from 23 Nov) that a later memo withdraws before it takes effect -> never applies.
3. **"Not yet in force" items** (034 item 5) are ignored.
4. **Email authority**: owner + Compliance agreement = binding (callback window). A request inside the chain that Compliance rejected (immediate transfer) is not a rule, even though it is quoted lower in the same file and stated more clearly than the answer.
5. **Forwarder's summary** is not authoritative ("the memo text is what counts"); it contains one stale fact.
6. **CSV parsing**: separator `;`, quoted fields with `""` escapes, trailing spaces in `UR-CB ` and `API reason `, DD/MM/YYYY dates, footer rows, inactive rows.
7. New intent: `stop_calling`.
