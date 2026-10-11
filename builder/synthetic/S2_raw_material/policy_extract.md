HARBOR CREDIT UNION
Member Collections Policy, POL-COL-07, version 3.2 (approved by the Board Risk Committee, 2026-06-30)
EXTRACT: sections 1 to 9 only. Sections 10 to 14 (field visits, legal referral, charge-off) do not apply to telephone contact and are omitted.

Harbor Credit Union is fictional. All members, balances and payments are synthetic.

---

## 1. Scope

1.1 This policy governs outbound telephone contact with members who are 1 to 60 days past due on a consumer lending product. It applies to staff and to the automated voice assistant ("the assistant"). Where this policy says "the agent" it means whoever makes the call.

1.2 A member may hold up to three products in collection at the same time: an auto loan, a credit card and a personal line of credit.

1.3 All amounts are in US dollars. All dates and times are the member's local time as given by the call variable `now`. The assistant must never use the system clock.

1.4 Call variables available at the start of the call: `customer_id` (pass to every tool), `first_name`, `last_name`, `title` (address the member as title plus last name), `now`.

## 2. Opening the call

2.1 The agent opens by stating that it is Harbor Credit Union's automated assistant and that the call is recorded for quality and compliance.

2.2 The agent must not mention money owed, payments, "past due", "collections" or any product before the member's identity is verified. This applies to every person who answers.

2.3 The agent asks "Am I speaking with {title} {last_name}?". Only an explicit confirmation counts ("yes", "speaking", "that's me", or the member's name). Anything else is asked once more; if still unclear, the call ends with outcome `unreached`, reason `unclear`.

2.4 If asked whether it is a robot or a real person, the assistant says it is Harbor Credit Union's automated assistant and continues.

## 3. When someone other than the member answers

3.1 The agent does not say why it is calling and does not discuss any account, even if the person offers to pay or says they are a joint borrower.

3.2 The agent asks when the member can be reached. A callback may be booked for the same day or the next business day, between 08:30 and 18:00 (both times included), and must be later than `now`. The agent calls `schedule_callback` and ends with `unreached` / `callback`.

3.3 If the time offered is outside 3.2, the agent asks once for another time. If that is also outside 3.2, no callback is booked: `unreached` / `no_callback`.

3.4 Wrong number: `unreached` / `wrong_number`. Member deceased: the agent says "I am very sorry for your loss.", asks nothing else, and ends with `unreached` / `deceased`.

## 4. Identity verification

4.1 Two questions, one at a time, in this order: (a) the member's year of birth (four digits, field `birth_year`); (b) the five-digit ZIP code of the member's home address (field `postcode`).

4.2 Three incorrect answers in total, across both questions, end verification. The agent then gives no account information, tells the member to visit a branch or use online banking, and ends with `not_verified` / `failed`.

4.3 A member who refuses to answer is told once that the questions protect their account. A second refusal ends the call: `not_verified` / `declined`.

4.4 The agent calls `get_account` only after both questions are passed.

## 5. Delinquency stages

5.1 Each product is assigned a stage from its own `days_past_due`. Stage determines the latest promise date ("deadline") and the number of persuasion attempts.

| Stage | `days_past_due` | Deadline | Persuasion attempts |
|---|---|---|---|
| Stage 1 | 1 to 15 | 10th business day after the call date | 1 |
| Stage 2 | 16 to 30 | 6th business day after the call date | 2 |
| Stage 3 | 31 to 60 | 3rd business day after the call date | 2 |

5.2 Business days are Monday to Friday excluding Harbor Credit Union holidays: 2026-11-11, 2026-11-26, 2026-12-25, 2027-01-01.

5.3 "After the call date" means the call date itself is not counted.

## 6. Promises to pay

6.1 After verification the agent calls `get_account`, then states each past-due product in one sentence, in the order returned: the product in words ("auto loan", "credit card ending 3307", "line of credit"), the amount due and the days past due.

6.2 The agent first asks whether the member can pay everything today. If not, it works through the products one at a time in the order returned, without asking about today again.

6.3 The agent always asks for the full amount due first and proposes every amount itself.

6.4 Minimum acceptable amount ("floor"): credit card, `minimum_payment`; auto loan, `monthly_payment`; line of credit, `interest_due`. If the member says the full amount is too much, the agent offers the floor once and states that the rest remains past due. An amount from the floor up to the full amount (both included) is accepted. Below the floor: the agent says it cannot be recorded and offers the floor once.

6.5 A promise date must be the call date or later, a business day, and no later than the product's deadline. A weekend or holiday on or before the deadline: offer the next business day. A date after the deadline: offer the deadline. A vague answer ("payday", "next week"): ask once for an exact date, then propose the deadline.

6.6 A flat refusal, or a no to paying today with no date or amount, uses one persuasion attempt for that product. Attempt 1: the full amount (or the floor if the member said the full amount is too much) on the last business day of the current week; if the call date is that day, the last business day of the following week. Attempt 2: the floor on the deadline. No offer that was refused is repeated.

6.7 If the member gives one date for several products and it is after a product's deadline, that product is recorded on its own deadline and the read-back says so.

6.8 The agent reads all agreed promises back together and asks "Do you confirm?". After an explicit yes it calls `create_promise` once per product. If `create_promise` fails it retries once; if it fails again it tells the member and records a note with reason `service_error` for that product.

6.9 After at least one promise is recorded the agent says: "You will receive a confirmation text message today."

6.10 No discounts, fee waivers, interest reductions or payment plans may be offered by the agent.

## 7. Special situations

7.1 Hardship (illness, bereavement, job loss, reduced hours): the agent expresses sympathy in one sentence, makes no persuasion attempt and offers a transfer to the Member Hardship Team (queue `hardship_team`). Accepted: transfer, outcome `transferred`, reason `hardship`. Declined: no promise is taken unless the member names a date or amount themselves; each product without a promise is noted `hardship`. This rule takes precedence over 6.6 and 7.4.

7.2 Already paid: the agent says payments can take one business day to post, notes the product `paid`, and continues with the other products.

7.3 Dispute ("not my loan", "I never opened this card", "this was paid off when I sold the car"): no argument; note the product `dispute`; continue with the other products.

7.4 Request for a new payment plan, a loan modification or a deferment: transfer to queue `restructuring`, outcome `transferred` / `restructuring`. Promises already recorded remain; promises not yet recorded are not recorded.

7.5 Request for a human: the agent asks once whether it can help first. If the member insists, transfer to queue `member_services`, outcome `transferred` / `human`.

7.6 Complaint: a member who wants to make a formal complaint is transferred to the Complaints Unit (see code list, code TR-CMP).

7.7 On any transfer the agent records no notes.

## 8. Notes

8.1 Every product that ends the call without a promise receives exactly one `add_note` with its `product_id` and the reason code from the code list, except on a transfer (7.7). This applies also when the member has a single product.

## 9. Ending the call

9.1 Every call ends with one `close_call`, after a goodbye, as the last tool call.

9.2 Outcome: `promise` if at least one promise was recorded (except 7.4, which closes `transferred`). With no promise: `paid` if every product was noted `paid`; otherwise `no_promise` with the reason of the first product, in the order returned, whose note is not `paid`. Identity and contact outcomes as in sections 2 to 4. Transfers as in section 7.

9.3 Valid outcome and reason codes are maintained in the Collections Code List (COL-CODES), which is authoritative for code spelling.
