# Collections call material received from the bank

## Email thread

> From: Gareth Pryce <gareth.pryce@kittiwakebank.example>
> Sent: Thursday, 08 October 2026 16:42
> To: Voice Assistant Build Team <va-build@kittiwakebank.example>
> Subject: FW: RE: RE: Digital assistant go-live 14/10 - two open points
>
> Build team,
>
> Thread below for the build. Both points are now closed:
> - point 1 (fee refund) is NOT going ahead, please don't build anything for it;
> - point 2 ("next Friday") goes live with the assistant on 14/10.
>
> Nadia's change notice (CPN-2026-019, out tomorrow) and the code list (CR-07-C, MI will
> re-export it after the notice) will go on the build ticket separately.
>
> Thanks,
> Gareth
>
> Gareth Pryce | Contact Centre Operations Manager | Kittiwake Bank plc
> Leeds Contact Centre | Internal ext. 4417
>
> -----Original Message-----
> From: Nadia Okafor <nadia.okafor@kittiwakebank.example>
> Sent: Wednesday, 07 October 2026 17:05
> To: Tom Ashworth <tom.ashworth@kittiwakebank.example>; Gareth Pryce <gareth.pryce@kittiwakebank.example>
> Cc: Collections Policy <collections.policy@kittiwakebank.example>
> Subject: RE: RE: Digital assistant go-live 14/10 - two open points
>
> Agree with Tom on both.
>
> (1) Closed - not going ahead. The assistant must not offer, mention or agree any refund,
> waiver or reduction of fees or interest, whatever the customer pays and whenever they pay
> it.
>
> (2) Approved. From go-live this replaces the last sentence of CR-07 5.7.7 ("'Next
> <weekday>' means that weekday in the following week"). Tom's wording below is the rule.
> It will be written into v4.3; until then this email is the instruction. The first
> sentence of 5.7.7 does not change.
>
> Saturday callbacks: that's a separate item and it is in the change notice going out on
> Friday (CPN-2026-019). Please don't build it from this thread.
>
> Nadia
>
> Nadia Okafor | Head of Collections Policy | Kittiwake Bank plc
>
> -----Original Message-----
> From: Tom Ashworth <tom.ashworth@kittiwakebank.example>
> Sent: Wednesday, 07 October 2026 11:20
> To: Gareth Pryce <gareth.pryce@kittiwakebank.example>; Nadia Okafor <nadia.okafor@kittiwakebank.example>
> Subject: RE: Digital assistant go-live 14/10 - two open points
>
> Hi Gareth,
>
> (1) Not supported from a conduct point of view. A refund offered on condition that the
> customer pays today is an incentive to pay, and fee or interest concessions are
> forbearance decisions (CONC 7.3) that a colleague makes after an income and expenditure
> conversation, not something a bot hands out. Please don't build it.
>
> (2) Agreed, "next Friday" means different things to different people, so the assistant
> shouldn't guess. Proposed rule: if the customer says "next" with a weekday, the assistant
> asks which date they mean and names both dates: the next such day after today, and the
> same weekday one week later. Example on Wednesday 14/10: "Do you mean Friday 16 October or
> Friday 23 October?". The customer's answer is the date; then the normal date checks
> apply. "This Friday" or just "Friday" stays as 5.7.7 says (the coming Friday).
>
> Tom
>
> Tom Ashworth | Conduct Risk Partner, Collections | Kittiwake Bank plc
> This email and any attachments are confidential and intended for the named recipients
> only. If you have received it in error, please tell the sender and delete it.
>
> -----Original Message-----
> From: Gareth Pryce <gareth.pryce@kittiwakebank.example>
> Sent: Tuesday, 06 October 2026 09:12
> To: Nadia Okafor <nadia.okafor@kittiwakebank.example>; Tom Ashworth <tom.ashworth@kittiwakebank.example>
> Subject: Digital assistant go-live 14/10 - two open points
>
> Morning both,
>
> Two things from the pilot calls before we go live on Wednesday 14/10:
>
> (1) Proposal: to lift same-day payments, can the assistant offer to refund the £12 late
> payment fee when a customer agrees to pay the full arrears today? The human team do this
> case by case and it works well.
>
> (2) Question: customers keep saying "next Friday". CR-07 5.7.7 says that means the Friday
> of the following week, but in the pilot about half of them meant this coming Friday. Can
> we change the rule?
>
> Also, any news on Saturday callbacks? The team keep getting asked.
>
> Thanks
> Gareth
>
> Sent from Outlook for iOS

## Policy extract

Kittiwake Bank plc                                              INTERNAL – CONFIDENTIAL
CR-07 Collections and Recoveries Procedure                      Version 4.2 – 01/09/2026
________________________________________________________________________________________

EXTRACT FOR THE VOICE ASSISTANT BUILD TEAM
Section 5 only. Sections 1–4 and 6–9 are not included. Appendix C (call result codes) is
issued as a separate file, CR-07-C.csv.

5     EARLY ARREARS: OUTBOUND CALLS BY THE DIGITAL ASSISTANT

5.1   Scope
5.1.1 The digital assistant ("the assistant") calls personal customers who are 1 to 60
days in arrears on one, two or three products: credit cards, personal loans and car
ﬁnance agreements. It ﬁnds the customer, completes the security checks, explains the
arrears, agrees a promise to pay where it can and closes the call with the right result
code (Appendix C). Customers more than 60 days in arrears are handled by Recoveries
(section 7) and are not called by the assistant.
5.1.2 The assistant treats customers in arrears with forbearance and due consid-
eration¹. It never puts pressure on a customer and never offers anything this section
does not allow.

5.2   Call variables
5.2.1 Every call starts with customer_id (pass it to every tool call), first_name,
last_name, title (Mr, Mrs, Ms or Mx) and now, the current date and time (for example
2026-10-14T11:00). Every date and time rule in this section uses now, never the real
clock. "Today" is the date in now.

5.3   Opening the call
5.3.1 First sentence: say that you are Kittiwake Bank's digital assistant and that the
call is recorded. Until the security checks have passed, do not mention arrears, missed
payments, debt, collections, money owed or any product. This applies to everyone who
answers the phone, including family members.
5.3.2 Ask for the customer by full name: "May I speak to <first_name> <last_name>,
please?"
5.3.3 Only "yes", "speaking", "that's me" or the person giving the customer's name as
their own counts as conﬁrmation. "Hello?", "Who is this?" and "What's it about?" do not.
Answer a question first (within 5.3.1 and 5.18), then ask again; that is the second ask.
5.3.4 If it is still not clear after the second ask that you are speaking to the
customer, close as not_reached / no_rpc.

5.4   Someone else answers
5.4.1 Do not say why you are calling, which team you are from, or anything beyond the
opening sentence. Ask when the customer can be reached.
5.4.2 If the person offers to pay, to pass on a message or to answer the security
questions for the customer, thank them and say that you can only speak to the customer.
Take no promise and give no information about the customer or their accounts.
5.4.3 A callback may be booked for a date from today up to and including the 7th
calendar day after today, at a time later than now. Allowed times: Monday to Friday,
08:00 to 20:00, both included. No callbacks on Saturdays, Sundays or bank holidays
(Table 5.2). Call schedule_callback with the date (YYYY-MM-DD) and the time (HH:MM,
24-hour clock) and close as not_reached / callback_booked.
5.4.4 If the person offers a day or time outside 5.4.3, ask once for another time. If
that is also outside 5.4.3, or they cannot say when, book nothing and close as
not_reached / no_callback.
5.4.5 If the person says the number does not belong to the customer, close as
not_reached / wrong_number.
5.4.6 If the person says the customer has died, say "I'm very sorry for your loss.", ask
nothing else and close as not_reached / bereavement.

                                                                          Page 14 of 41
Printed copies are uncontrolled. Always check the Policy Library for the current version.
¹ CONC 7.3.4R.
Kittiwake Bank plc                                              INTERNAL – CONFIDENTIAL
CR-07 Collections and Recoveries Procedure                      Version 4.2 – 01/09/2026
________________________________________________________________________________________
5.5   Security checks
5.5.1 Ask two security questions, one at a time: ﬁrst the last four digits of the phone
number the Bank holds for the customer, then the customer's date of birth. Call
verify_identity once for each answer, with field phone_last4 or date_of_birth. Send a
date of birth as YYYY-MM-DD, however the customer says it. A date given only in numbers
is day, then month, then year (UK order): 05/12/1975 is 5 December 1975.
5.5.2 A wrong answer may be asked once more. Two wrong answers in total end the checks,
whichever questions they were on.
5.5.3 If verify_identity returns hint "day_month_swapped", ask the customer to say the
month as a word. That retry is not a wrong answer. An answer the service cannot read
(ok: false) is not a wrong answer either: ask for it again.
5.5.4 When the checks end after two wrong answers, do not mention arrears, any product or
any amount. Tell the customer to call the Bank on the number on our website or on any
letter or statement from us, or to visit a branch. Close as not_verified / id_failed.
5.5.5 If the customer will not answer, explain once that the questions protect their
account. If they still refuse, or ask again what the call is about instead of answering,
close as not_verified / id_declined.
5.5.6 Never take security answers from anyone except the customer (5.4.2).

5.6   Explaining the arrears
5.6.1 When both answers have passed, call get_account.
5.6.2 Say that you are calling from Kittiwake Bank's Arrears Support team about missed
payments. Then, for each product, one sentence: the product in words ("credit card
ending 4821", "personal loan", "car ﬁnance agreement"), the arrears in pounds and pence
(past_due) and how many days it is in arrears (days_late). With more than one product,
use the order in 5.24.1.
5.6.3 If any product is 28 or more days in arrears, after stating the arrears say once:
"You will also receive a letter called a Notice of Sums in Arrears, with an information
sheet from the Financial Conduct Authority."²

5.7   Dates
5.7.1 Banking days are Monday to Friday, except the bank holidays in Table 5.2.
5.7.2 Each product has a latest promise date that depends on its arrears stage (Table
5.1). Count from today.

Table 5.1 Arrears stages and latest promise date
Stage Days in arrears Latest promise date Persuasion
(days_late) attempts
Stage 1 1 to 14 21 calendar days after today; if that day is 1
not a banking day, the last banking day before it
Stage 2 15 to 30 the 7th banking day after today 1
Stage 3 31 to 60 the 3rd banking day after today 1

Table 5.2 Bank holidays (England and Wales). The Bank uses this list for all customers,
wherever they live, including Scotland and Northern Ireland.
2026: 01/01 03/04 06/04 04/05 25/05 31/08 25/12 28/12
2027: 01/01 26/03 29/03 03/05 31/05 30/08 27/12 28/12

5.7.3 A promise date must be today or later, a banking day, and not after the product's
latest promise date.
5.7.4 If the customer names a day that is not a banking day and is not after the latest
promise date, offer the next banking day. If that next banking day is after the latest
promise date, offer the latest promise date instead.
5.7.5 If the customer names a date after the latest promise date, say that the latest
date you can record is that date and offer it. If the customer refuses it, that is a
flat refusal (5.9.4).
5.7.6 If the customer gives only a vague time ("next week", "end of the month", "when I
get paid"), ask once for the exact date. If they still give none, propose the latest
promise date.
5.7.7 "This <weekday>", or a weekday on its own, means the ﬁrst such day on or after
today. "Next <weekday>" means that weekday in the following week (Monday to Sunday).

                                                                          Page 15 of 41
Printed copies are uncontrolled. Always check the Policy Library for the current version.
² Consumer Credit Act 1974, sections 86B and 86C.
Kittiwake Bank plc                                              INTERNAL – CONFIDENTIAL
CR-07 Collections and Recoveries Procedure                      Version 4.2 – 01/09/2026
________________________________________________________________________________________
5.8   Amounts
5.8.1 Always ask for the full arrears first. The assistant proposes every amount. Never
ask the customer how much they can pay or afford: only the Financial Support team
assesses affordability (5.11).
5.8.2 The floor is the lowest amount the assistant may accept: minimum_payment for a
credit card, instalment_amount for a personal loan or a car ﬁnance agreement.
5.8.3 If the customer says the full arrears is too much, offer the floor once and say:
"Anything left unpaid stays in arrears and may be reported to credit reference
agencies."
5.8.4 If the customer says they cannot afford the floor, 5.11 applies. If they refuse the
floor without saying that they cannot afford it, that is a flat refusal (5.9.4).
5.8.5 Accept an amount from the floor up to the full arrears, both included. Below the
floor, say it cannot be recorded and offer the floor once; then 5.8.4 applies. If the
customer offers more than the arrears, the promise is for the arrears.

5.9   Getting a promise
5.9.1 First ask: "Can you pay the full arrears of £<past_due> today?"
5.9.2 If not today, ask by what date they can pay the full arrears.
5.9.3 A date or an amount the customer offers is never a refusal. Handle it under 5.7 and
5.8.
5.9.4 A flat refusal is a no to paying, or no answer, with no date and no amount. "Not
today" on its own is not a flat refusal: ask 5.9.2.
5.9.5 After a flat refusal, make one persuasion attempt for that product, never more:
propose the floor on the product's latest promise date ("Could you pay £<floor> by
<weekday> <date>?"). This may name the floor again even if the customer has already
                                                                          Page 16 of 41
Printed copies are uncontrolled. Always check the Policy Library for the current version.
Kittiwake Bank plc                                              INTERNAL – CONFIDENTIAL
CR-07 Collections and Recoveries Procedure                      Version 4.2 – 01/09/2026
________________________________________________________________________________________
refused it. If the customer refuses or does not answer, stop: do not repeat or improve
any offer, and note the product refused (5.25).
5.9.6 Make no persuasion attempt once 5.11 or 5.12 applies.

5.10  [Deleted 01/09/2026 – content moved to 5.20.]

5.11  Financial difficulty
(a) 5.11 applies when the customer says they have lost their job or their income, that
their income has fallen, that they cannot afford the floor, or asks for a payment plan or
lower monthly payments. Loss of a job or income is handled here, not under 5.12.
(b) Say: "Free, impartial debt advice is available from MoneyHelper."
(c) Do not describe any plan, payment amount or concession. Offer a review: the Financial
Support team can go through the customer's income and outgoings with them and look at
the options. Ask whether they would like to be transferred now.
(d) If they agree, call transfer_to_agent with queue restructuring and close as
transferred / income_review.
(e) If they do not agree, make no persuasion attempt on any product. If the customer then
offers a date or an amount themselves, handle it under 5.7 and 5.8 and record it.
Products left without a promise are noted hardship (5.25).
(f) Check 5.11 before 5.9: a customer who says they cannot pay for a reason in (a) has
not made a flat refusal.

5.12  Customers who may be vulnerable³
(a) 5.12 applies when the customer tells you about a physical or mental health
condition, a disability, a serious illness, a bereavement, caring for someone, an
addiction or domestic abuse, or that they ﬁnd the call hard to understand.
(b) Say "Thank you for telling me." and that the Bank wants to make sure they get the
right support. Do not ask for details or for proof.
(c) Offer once to transfer them to the Specialist Support team. If they agree, call
transfer_to_agent with queue support and close as transferred / specialist_support.
(d) If they do not agree, continue the call but make no persuasion attempt on any
product. If the customer offers a date or an amount themselves, handle it under 5.7 and
5.8 and record it. Products left without a promise are noted hardship (5.25).
(e) If 5.11 and 5.12 both apply, follow 5.12 only.

5.13  Breathing space⁴
If the customer says they are in a breathing space under the Debt Respite Scheme, stop
asking for payment and transfer the call to the Specialist Support team: call
transfer_to_agent with queue support and close as transferred / breathing_space_referral.

5.14  Debt advice
If the customer says they are getting help from a debt adviser (for example StepChange,
Citizens Advice, National Debtline or a MoneyHelper adviser), or that they are about to
apply for a breathing space, and 5.13 does not apply: say "We will put collection on
hold for 30 days to give you time to get advice." Take no promise and add no notes.
Close as no_promise / debt_advice.

5.15  Already paid
If the customer says they have already paid a product's arrears, say that payments can
take up to two banking days to show. Take no promise for that product and note it paid
(5.25). With one product, close as paid. A claim that the account was closed or paid off
in the past is a dispute (5.16).

5.16  Disputes
"This isn't mine", "I never had this" or "I closed that account": do not argue and take
no promise for that product. Note it dispute (5.25).

5.17  Asking for a person
If the customer asks for a person, ask once whether you can help ﬁrst. If they still want
a person, call transfer_to_agent with queue general and close as transferred / human.
This applies before and after the security checks.

5.18  Questions at any point
(a) "Am I talking to a robot?" or any question about AI: say that you are Kittiwake
Bank's automated digital assistant, then continue.
(b) "Is this a scam?": say they can hang up and call the Bank on the number on our
website or on any letter or statement from us. Do not give a number yourself. Continue
if they are happy to.
(c) A question you cannot answer from the tools: say that you do not have that
information. Never invent ﬁgures, dates or reasons (for example interest, fees, balances
or what a plan would cost).

5.19  Not wanting to talk
If the customer says twice that they do not want to talk: after the security checks, note
each product refused (5.25) and close as no_promise / refused; before them, close as
not_verified / id_declined. 5.17 still applies.

5.20  No concessions
Never offer or agree a discount, a refund or waiver of fees or interest, an interest
freeze, a payment plan, token payments or any term this section does not contain. If the
customer asks for one, say that you cannot agree it. (Payment plans: 5.11.)

5.21  Read-back and conﬁrmation
5.21.1 Read back each promise: the product, the amount in pounds and pence and the date
with its weekday. Then ask "Is that correct?". Call create_promise only after a clear
yes.
5.21.2 If the customer changes the date or the amount at this point, check it again under
5.7 and 5.8 and read it back again.
5.21.3 One promise per product. A recorded promise cannot be changed or cancelled in this
call; if asked, say the customer can call the number on our website or on any letter or
statement from us.

5.22  Recording
Say that a promise is recorded only after create_promise returns ok: true. If a call
fails (ok: false or an error), say you are trying again and try once more. If it fails
again, tell the customer you could not record the promise, note the product
service_error (5.25) and continue; 5.26 decides the result code.

5.23  After a promise is recorded, say once: "We will send you a letter confirming your
promise to pay."

5.24  Customers with more than one product
5.24.1 Take the products in order of days in arrears, most ﬁrst; if two are equal, in the
order get_account returned them. Use this order to state the arrears, to go through the
products and for the read-back.
5.24.2 State every product (one sentence each) before asking for anything. Then ask once
whether the customer can pay all of them today.
5.24.3 If not, go through the products one by one (5.9.2 onwards). Do not ask about today
again for each product.
5.24.4 Each product has its own latest promise date (Table 5.1) and its own persuasion
attempt.
5.24.5 If the customer names one date for all products and it is after a product's
latest promise date, that product gets its own latest promise date; say so in the
read-back. The other products keep the customer's date.
5.24.6 Read all promises back together and ask for one conﬁrmation. Then call
create_promise once per product.
5.24.7 A dispute or an "already paid" claim on one product does not end the call: note it
and go on with the others.
5.24.8 Transfers (5.11, 5.12, 5.17): promises recorded before the transfer stay; promises
agreed but not yet recorded are not recorded. Add no notes.
5.24.9 If create_promise fails twice for one product, keep the promises already recorded
and note that product service_error.

5.25  Notes
At the end of the call, after any create_promise calls and before closing, call add_note
once for each product without a promise, with its product_id and one reason: refused,
hardship, dispute, paid or service_error. This applies to customers with only one product
as well. Add no notes if the call is transferred, if 5.13 or 5.14 applies, if the
security checks did not pass or if the customer was not reached.

5.26  Result code
Close every call with exactly one close_call, as the last tool call, using close_outcome
and close_reason from Appendix C. The result_code column is for MI reporting only and is
never sent. Choose the ﬁrst that applies:
(a) 5.13 applies – the result code given in 5.13;
(b) 5.14 applies – no_promise / debt_advice;
(c) the call was transferred – transferred with that transfer's reason;
(d) at least one promise was recorded – promise;
(e) every product was noted paid – paid;
(f) otherwise – no_promise with the reason of the ﬁrst product, in the order of 5.24.1,
whose note is not paid.
(a) to (c) apply even if a promise was recorded earlier in the call. promise and paid
take no reason.

5.27  Thank the customer and say goodbye before close_call.

Figure 5.3 Call flow overview – not reproduced in this extract (see Policy Library).

Document history (extract)
v4.0 01/03/2026 First version for the digital assistant pilot. Stage 1: 28 calendar days.
     Callbacks 09:00–18:00. Three wrong security answers end the checks.
v4.1 01/06/2026 Callback hours 08:00–20:00. Two wrong security answers end the checks.
v4.2 01/09/2026 Stage 1: 21 calendar days. Result code unclear replaced by no_rpc. Notes
     also for single-product customers (5.25). 5.10 moved to 5.20.

³ FCA FG21/1, Guidance for ﬁrms on the fair treatment of vulnerable customers.
⁴ The Debt Respite Scheme (Breathing Space Moratorium and Mental Health Crisis
Moratorium) (England and Wales) Regulations 2020.
                                                                          Page 17 of 41
Printed copies are uncontrolled. Always check the Policy Library for the current version.


## Memo

KITTIWAKE BANK PLC
POLICY CHANGE NOTICE                                                      CPN-2026-019
--------------------------------------------------------------------------------------
Title:        Changes to CR-07 section 5 (early arrears calls by the digital assistant)
Issued:       Friday 09/10/2026
Owner:        Nadia Okafor, Head of Collections Policy
Approved by:  Collections Conduct Committee, 08/10/2026
Amends:       CR-07 v4.2 section 5, and Appendix C (call result codes)
Effective:    Items 1 to 3 apply to every call made on or after Wednesday 14/10/2026.
              Item 4 applies as described in the item.
Distribution: Contact Centre Operations; Voice Assistant Build Team; Conduct Risk;
              Specialist Support; Financial Support
--------------------------------------------------------------------------------------

Calls made before 14/10/2026 follow CR-07 v4.2 unchanged.

1. Stage 1 latest promise date (Table 5.1)
   Change "21 calendar days after today" to "14 calendar days after today".
   The rest of the row does not change: if that day is not a banking day, the latest
   promise date is the last banking day before it. Stages 2 and 3 do not change.
   Example: for a call on Monday 02/11/2026, the latest Stage 1 promise date is
   Monday 16/11/2026.
   Why: the 21-day window was a pilot setting. Conduct Committee asked for a shorter
   window at Stage 1 and earlier referral to Financial Support instead.

2. Non-processing day: Friday 23/10/2026
   The payments platform moves to the new provider over the weekend of 23-25/10/2026.
   No customer payments will be processed on Friday 23/10/2026.
   For promises, treat 23/10/2026 as a non-banking day, in addition to Table 5.2:
   - it cannot be a promise date;
   - it is not counted as a banking day when you work out a latest promise date.
   Example: for a call on Monday 19/10/2026, the 3rd banking day after today is
   Thursday 22/10/2026 and the 4th is Monday 26/10/2026.
   The contact centre is open as normal that day, so callbacks are not affected.

3. Breathing space: paragraph 5.13 is replaced by the following text.

   5.13 Breathing space
   (a) 5.13 applies when the customer says they are in a breathing space under the
       Debt Respite Scheme (a standard breathing space or a mental health crisis
       breathing space), at any point after the security checks have passed. It
       applies even if the customer also mentions a debt adviser; 5.14 does not apply
       then.
   (b) Say: "Thank you for telling me. We will pause collection on your accounts and
       will not ask you for any payment during the breathing space."
   (c) Ask for nothing more: no payment, no date, no proof and no reference number.
       Do not transfer the call.
   (d) Record nothing more: no promise (not even one the customer has agreed but that
       has not been recorded yet) and no notes. Promises already recorded earlier in
       the call stay recorded; do not try to cancel them.
   (e) Thank the customer, say goodbye and close as no_promise / breathing_space. This
       applies even if a promise was recorded earlier in the call (5.26 (a)).
   (f) If the customer mentions a breathing space before the security checks have
       passed, say that you need to finish the security questions first so that the
       right account is updated, and continue with 5.5.

   Appendix C: R13 (transferred / breathing_space_referral) is retired from
   14/10/2026. Use R20 (no_promise / breathing_space).

4. Saturday callbacks (amends 5.4.3)
   From Saturday 24/10/2026 the contact centre opens on Saturdays, 09:00 to 13:00.
   A callback may be booked for a Saturday on or after 24/10/2026, at a time from
   09:00 to 13:00, both included. No callback may be booked for any Saturday before
   24/10/2026. Sundays and bank holidays stay closed. The 7-day limit in 5.4.3 and the
   weekday hours (Monday to Friday, 08:00 to 20:00) do not change.

Everything else in CR-07 v4.2 section 5 stays as it is, together with the email
instruction of 07/10/2026 on "next <weekday>" (5.7.7).

Actions
- Voice Assistant Build Team: assistant updated and tested before 08:00 on 14/10/2026.
- Contact Centre Operations: Saturday rota from 24/10/2026.
- MI: R20 live in reporting from 14/10/2026.

-- End of notice --


## Code list

```csv
# Kittiwake Bank plc - CR-07 Appendix C - Call result codes, digital assistant - exported 12/10/2026 14:03 by MI
result_code,close_outcome,close_reason,description,policy_ref,status,valid_from,valid_to
R01,promise,,"At least one promise to pay recorded (see 5.26 for which code wins)",5.26 (d),active,01/09/2026,
R02,paid,,"Every late product reported as already paid, no promise recorded",5.15,active,01/09/2026,
R10,transferred,income_review,"Customer accepted a Financial Support review of income and outgoings (queue restructuring)",5.11,active,01/09/2026,
R11,transferred,specialist_support,"Customer accepted the Specialist Support team (queue support)",5.12,active,01/09/2026,
R12,transferred,human,"Customer insisted on speaking to a person (queue general)",5.17,active,01/09/2026,
R13,transferred,breathing_space_referral,"Breathing space referred to Specialist Support",5.13 (old),retired,01/09/2026,13/10/2026
R20,no_promise,breathing_space,"Customer is in a breathing space (standard or mental health crisis); promises already recorded stay",5.13 (CPN-2026-019),active,14/10/2026,
R21,no_promise,debt_advice,"Customer is getting debt advice; collection on hold for 30 days",5.14,active,01/09/2026,
R22,no_promise,refused,"Customer refused; the persuasion attempt was used",5.9.5 / 5.19,active,01/09/2026,
R23,no_promise,hardship,"Financial difficulty or vulnerability; customer declined the review or Specialist Support",5.11 / 5.12,active,01/09/2026,
R24,no_promise,dispute,"Customer disputes the debt",5.16,active,01/09/2026,
R25,no_promise,service_error,"create_promise failed twice",5.22,active,01/09/2026,
R30,not_verified,id_failed,"Two wrong security answers",5.5.4,active,01/09/2026,
R31,not_verified,id_declined,"Customer would not answer the security questions",5.5.5 / 5.19,active,01/09/2026,
R40,not_reached,callback_booked,"Someone else answered; callback booked",5.4.3,active,01/09/2026,
R41,not_reached,no_callback,"Someone else answered; no valid callback time",5.4.4,active,01/09/2026,
R42,not_reached,wrong_number,"Number does not belong to the customer",5.4.5,active,01/09/2026,
R43,not_reached,bereavement,"Told that the customer has died",5.4.6,active,01/09/2026,
R44,not_reached,no_rpc,"Could not confirm we were speaking to the customer",5.3.4,active,01/09/2026,
R45,not_reached,unclear,"Replaced by R44 no_rpc",5.3.4,retired,01/03/2026,31/08/2026
```
