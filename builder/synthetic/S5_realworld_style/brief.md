PINECREST FEDERAL CREDIT UNION
COLLECTIONS DEPARTMENT — OPERATING PROCEDURE

| | |
|---|---|
| Procedure No. | COL-310 |
| Title | Telephone Contact with Delinquent Members (Consumer Loans and Cards) |
| Revision | 4 |
| Effective date | 2026-11-02 |
| Approved | Board of Directors, 2026-10-20 (minute 26-117) |
| Owner | Manager, Member Collections |
| Supersedes | COL-310 Rev. 3 (2025-04-01) |
| Related | COL-300 Collection Policy; COL-330 Repossession (not applicable to telephone contact); 12 CFR part 1006 (Regulation F) |

Pinecrest Federal Credit Union is fictional. Every member, balance and payment in this procedure is synthetic.

---

## 310.1 Purpose

This procedure tells the person or system placing an outbound collection call what to say and do, in what order, and how to record the result. It applies to Collections staff and to the automated voice assistant ("the assistant"). In this procedure "the agent" means whoever places the call.

## 310.2 Scope

(a) Members who are 1 to 89 days delinquent on one or two consumer products: an auto loan, a signature loan or a credit card.

(b) Accounts 90 days or more delinquent, accounts in charge-off and real-estate secured loans are out of scope and are never returned by `get_account`.

## 310.3 Authority and regulatory references

(a) Pinecrest collects its own loans and is not a "debt collector" under 12 CFR 1006.2(i). The Board has nevertheless adopted the Regulation F limits referenced in this procedure as credit union policy. Where this procedure is stricter than the regulation, this procedure applies.

(b) References to a section of Regulation F are for information. The agent follows the text of this procedure.

## 310.4 Definitions

(a) **Call date**: the date part of the call variable `now`. All dates and times in this procedure are the member's local time as given by `now`; the system clock is never used.

(b) **Business day**: Monday to Friday, excluding the credit union holidays in 310.4(c). "The nth business day after the call date" does not count the call date itself.

(c) **Credit union holidays**: 2026-11-11, 2026-11-26, 2026-12-25, 2027-01-01, 2027-01-18. The credit union is open on Friday 2026-11-27.

(d) **Third party**: anyone other than the member, **including the member's spouse**. (Regulation F treats a spouse as the consumer for some purposes, 12 CFR 1006.6(a)(1); Pinecrest policy does not.)

(e) **Tier**: the delinquency tier of a product, from its `days_delinquent` (310.9).

(f) **Floor**: the smallest amount that can be recorded for a product (310.10).

(g) **Disposition code**: the three-letter result code in 310.17. The `close_call` tool takes the outcome and reason that the table maps each code to.

## 310.5 Call variables

`customer_id` (pass to every tool call), `first_name`, `last_name`, `title` (address the member as title plus last name), `now`.

## 310.6 Opening

(a) The first sentence states that the caller is Pinecrest Federal Credit Union's automated assistant and that the call is recorded.

(b) Until the member's identity is verified (310.8), the agent does not say "delinquent", "past due", "debt", "collection", "payment", "loan", "card" or the name of any product, to anyone.

(c) The agent asks "Am I speaking with {title} {last_name}?". Only "yes", "speaking", "this is he/she" or the member's own name confirms. Any other answer is asked once more; if it is still unclear, the result is UNC.

(d) If asked whether it is a robot, the assistant says it is Pinecrest Federal Credit Union's automated assistant and continues.

(e) If asked whether the call is a scam, the agent says the member can call Pinecrest at the number on the back of their card or on their statement, and continues.

## 310.7 When a third party answers

(a) The agent says nothing beyond 310.6(a), does not say why it is calling and discusses no account, even if the person says they pay the member's bills or offers to pay.

(b) The agent asks when the member can be reached. A callback may be booked only:
   (i) on the call date or on one of the next two **calendar** days;
   (ii) Monday to Friday from 08:00 (included) to 21:00 (not included), or Saturday from 09:00 to 17:00 (both included); never on a Sunday or a credit union holiday; and
   (iii) later than `now`.
   Note: Saturday is not a business day, but a Saturday callback is allowed. (12 CFR 1006.6(b)(1)(i) treats calls before 08:00 and after 21:00 as inconvenient.)

(c) A valid time: the agent calls `schedule_callback` with the date and time and closes with TPC.

(d) A time outside (b): the agent asks once for another time. If that is also outside (b), nothing is booked: TPN.

(e) Wrong number: WRN.

(f) The person says the member has died:
   (i) If the person says they are the **executor or administrator of the member's estate**, the agent says nothing about any account and transfers the call to queue `estates` (result TRE). (Regulation F treats the estate's representative as the consumer, 12 CFR 1006.6(a)(4); account matters are handled by the Estates Unit, not by telephone collection.)
   (ii) Anyone else: the agent says "Please accept our sympathy.", asks nothing else and closes with DEC.

## 310.8 Identity verification

(a) Two questions, one at a time, in this order:
   (i) date of birth (field `date_of_birth`, sent as `YYYY-MM-DD`). A date said only in numbers is read **month, then day, then year** (US order);
   (ii) the last four digits of the member's Social Security number (field `ssn_last4`).

(b) Three wrong answers in total, across both questions, end verification. The agent gives no account information, tells the member to call Member Services or visit a branch, and closes with NVF.

(c) A member who will not answer is told once that the questions protect their account. A second refusal, or asking again what the call is about instead of answering, closes with NVD.

(d) **Required disclosure.** As soon as both questions are passed, and before anything about the account is said, the agent says exactly: "This is an attempt to collect a debt, and any information obtained will be used for that purpose." (Pinecrest policy, modelled on 12 CFR 1006.18(e)(1).)

(e) Then the agent calls `get_account`.

## 310.9 Delinquency tiers

| Tier | `days_delinquent` | Latest promise date | Persuasion attempts |
|---|---|---|---|
| Courtesy | 1 to 14 | 10th business day after the call date | 1 |
| Early | 15 to 44 | 5th business day after the call date | 2 |
| Pre-charge-off | 45 to 89 | 2nd business day after the call date | 1 |

Each product has its own tier. Two products of the same member can have different latest promise dates.

## 310.10 Floor

(a) The floor is 25% of the product's `amount_due`, **rounded up to the next whole dollar** (example: 25% of 1,130.00 is 282.50; the floor is 283.00).

(b) For a credit card, if `minimum_due` is higher than the amount in (a), the floor is `minimum_due`.

(c) See 310.13 for members with broken promises, who have no floor.

## 310.11 Stating the debt

(a) The agent states each product in one sentence, in the order `get_account` returns them: the product in words ("auto loan", "signature loan", "credit card ending 4417"), the amount due and the number of days delinquent.

(b) **Contact hold (Regulation F 7-day rule, 12 CFR 1006.14(b)(2)(i)(B)).** A product whose `last_conversation_date` is within the last seven days is on contact hold. The seven-day period starts on `last_conversation_date` itself (that date is day 1), so a product is on hold when the call date is no later than `last_conversation_date` plus 6 days. The agent does not state a product on hold, does not ask about it and records no promise for it, even if the member raises it. It receives one `add_note` with reason `contact_hold`. `get_account` never returns only products on hold.

## 310.12 Asking for payment

(a) The agent first asks whether the member can pay the full amount due (of every product stated) today.

(b) If not, the agent works through the stated products one at a time in the order returned, without asking about today again.

(c) The agent always asks for the full amount due first and proposes every amount itself. It never asks "how much can you pay?".

(d) If the member says the full amount is too much, the agent offers the floor, once, and says that the rest stays delinquent. An amount from the floor up to the full amount, both included, is accepted. Below the floor, the agent says it cannot be recorded and offers the floor once.

(e) A promise date must be the call date or later, a business day and not after the product's latest promise date. A weekend day or holiday on or before the latest promise date: offer the next business day. A date after the latest promise date: offer the latest promise date. A vague answer ("payday", "next week"): ask once for an exact date, then propose the latest promise date.

(f) A flat refusal, or a no to paying today with no date and no amount, uses one persuasion attempt for that product:
   (i) Attempt 1: the full amount due on the latest promise date; if the member already said the full amount is too much, the floor on the latest promise date.
   (ii) Attempt 2 (Early tier only): the floor on the latest promise date. If that would repeat an offer the member already refused, or the product has no floor (310.13), there is no attempt 2.
   When the attempts are used up the product ends without a promise (note `refused`).

(g) No discount, waiver, fee reversal, skip-a-pay, extension or payment plan is offered by the agent.

## 310.13 Members with broken promises

If a product's `broken_promises_12m` is 2 or more:
   (a) the product has no floor: only the full `amount_due` can be recorded, and a "too much" answer is treated as a flat refusal (310.12(f));
   (b) its latest promise date is the earlier of the tier date (310.9) and the 3rd business day after the call date.

## 310.14 Confirming and recording

(a) The agent reads all agreed promises back together (product, amount, date) and asks "Do you confirm?". After a clear yes it calls `create_promise` once per product.

(b) If `create_promise` fails, the agent tries once more. If it fails again, it tells the member and adds a note with reason `service_error` for that product.

(c) After at least one promise is recorded, the agent says: "You will receive a confirmation letter by mail within five business days."

## 310.15 Special situations

(a) **Hardship** (illness, death in the family, job loss, reduced income): one sentence of sympathy, no persuasion attempt, and an offer to transfer to the Financial Counseling team (queue `financial_counseling`). Accepted: TRF. Declined: no promise is taken unless the member names a date or amount themselves; every stated product without a promise is noted `hardship`. This rule comes before 310.12(f) and 310.15(f).

(b) **Already paid**: the agent says payments can take one business day to post, notes that product `paid` and continues with the other products.

(c) **Dispute** ("not my loan", "I never had this card", "that was settled when I refinanced"): no argument; note the product `dispute`; continue with the other products. A claim that a product was paid off or settled in the past is a dispute, not 310.15(b).

(d) **Attorney.** If the member says an attorney represents them for this debt, the agent says "Thank you. We will contact your attorney.", asks nothing else, notes every stated product without a promise `attorney` and closes with ATY. (12 CFR 1006.6(b)(2).)

(e) **Bankruptcy.** If the member says they have filed for bankruptcy, the agent says "Thank you for letting us know.", takes no promise even if the member offers to pay, notes every stated product without a promise `bankruptcy` and closes with BKR.

(f) **Payment plan, skip-a-pay, extension or loan modification**: the agent does not describe any option and transfers to queue `loan_servicing` (TRS). Promises already recorded remain.

(g) **Stop calling.** If the member asks Pinecrest to stop calling, the agent says "I have noted your request.", makes no further offer, notes every stated product without a promise `cease` and closes with CNC. One request is enough.

(h) **Request for a person**: the agent asks once whether it can help first. If the member insists, transfer to queue `member_services` (TRH).

(i) On any transfer (TRF, TRS, TRH, TRE) the agent adds no notes.

(j) Precedence when a member says several of these things: 310.15(d) and (e) before everything else; then (a); then the rest in the order said.

## 310.16 Notes

(a) Every stated product that ends the call without a promise receives exactly one `add_note` with its `product_id` and reason. A product on contact hold receives one note with reason `contact_hold` (310.11(b)).

(b) Exception: on a transfer (310.15(i)) no note at all is added, not even `contact_hold`.

(c) Notes are added only for products returned by `get_account`, so a call that ends before `get_account` has no notes.

## 310.17 Closing and disposition codes

(a) Every call ends with exactly one `close_call`, after a goodbye, as the last tool call.

(b) Disposition codes:

| Code | Situation | `outcome` | `reason` |
|---|---|---|---|
| PTP | at least one promise recorded | `promise` | – |
| PIF | no promise; every stated product noted `paid` | `paid` | – |
| RTP | refused, attempts used up | `no_promise` | `refused` |
| DSP | disputed | `no_promise` | `dispute` |
| HRD | hardship, transfer declined | `no_promise` | `hardship` |
| ATY | attorney represents the member | `no_promise` | `attorney` |
| BKR | bankruptcy | `no_promise` | `bankruptcy` |
| CNC | member asked us to stop calling | `no_promise` | `cease` |
| SVC | promise could not be recorded | `no_promise` | `service_error` |
| TRF | hardship, transfer accepted | `transferred` | `hardship` |
| TRS | plan / skip-a-pay / extension | `transferred` | `restructuring` |
| TRH | member insisted on a person | `transferred` | `human` |
| TRE | estate executor or administrator | `transferred` | `estate` |
| NVF | three wrong answers | `not_verified` | `failed` |
| NVD | declined verification | `not_verified` | `declined` |
| TPC | third party, callback booked | `no_contact` | `callback` |
| TPN | third party, no valid time | `no_contact` | `no_callback` |
| WRN | wrong number | `no_contact` | `wrong_number` |
| DEC | member deceased (not the executor) | `no_contact` | `deceased` |
| UNC | could not confirm who answered | `no_contact` | `unclear` |

(c) With no promise recorded and no ATY, BKR, CNC or transfer: PIF if every stated product is noted `paid`; otherwise the code of the first stated product, in the order returned, whose note is not `paid`. A product on contact hold is not a stated product.

(d) The assistant never leaves a voicemail. (A limited-content message under 12 CFR 1006.2(j) may be left by staff only; out of scope for the assistant.)

---

## Revision history

| Rev | Date | Summary |
|---|---|---|
| 1 | 2022-03-14 | First issue. |
| 2 | 2023-09-01 | Added Saturday callbacks. |
| 3 | 2025-04-01 | Pre-charge-off tier; broken-promise rule (310.13). |
| 4 | 2026-11-02 | Contact hold (310.11(b)); estate executor transfer (310.7(f)(i)); disposition codes renamed to three letters. |
