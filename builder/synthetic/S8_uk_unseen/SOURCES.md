# S8 sources and likely test design

Quotes are short, at most about 15 words, and everything else is paraphrased. The **Checked** column says how far each source was confirmed in this session:
- **fetched**: the page was opened in this session.
- **by research agent**: a research agent opened it.
- **not fetched**: cited from known references only.

## A. UK collections material behind S8

| S8 rule | Source | What it says | Checked |
|---|---|---|---|
| 5.1.2 forbearance and due consideration | FCA Handbook **CONC 7.3.4R**, https://www.handbook.fca.org.uk/handbook/CONC/7/3.html | Firms must treat customers "in or approaching arrears or in default with forbearance and due consideration". | fetched |
| 5.20 no concessions (the bot may not grant them) | **CONC 7.3.5G**, same page | Examples of forbearance: reducing or waiving interest or charges, deferring arrears, accepting token payments. In S8 only a human after an income and expenditure review decides these (email point 1 is rejected). | fetched |
| 5.9.5 one attempt, no pressure | **CONC 7.3.10R** ("must not pressurise a customer"), same page | Basis for allowing only one persuasion attempt per product. | fetched |
| 5.11(b) MoneyHelper sentence | **CONC 7.3.7AG**, same page | The firm should tell the customer that "free and impartial money guidance and debt advice is available". | fetched |
| 5.14 30-day debt-advice hold | **CONC 7.3.11R** (suspend recovery while a repayment plan is being developed) and **7.3.12G** (reasonable period), same page | The 30 days is S8's own choice. Older UK lending codes also used a 30-day hold. | fetched |
| 5.13 breathing space (CPN item 3) | gov.uk *Debt Respite Scheme (Breathing Space) guidance for creditors*, https://www.gov.uk/government/publications/debt-respite-scheme-breathing-space-guidance/debt-respite-scheme-breathing-space-guidance-for-creditors | Standard breathing space lasts "up to 60 days". A mental health crisis breathing space lasts for the treatment plus 30 days. Creditors must not seek repayment, add interest, fees or charges, or enforce. Protections start from the notified date. | fetched |
| 5.13 legal name | The Debt Respite Scheme (Breathing Space Moratorium and Mental Health Crisis Moratorium) (England and Wales) Regulations 2020, SI 2020/1311, https://www.legislation.gov.uk/uksi/2020/1311/contents/made | The gov.uk page does not give the SI number. | not fetched (SI number from memory) |
| 5.12 vulnerability ("Thank you for telling me", offer Specialist Support, no proof asked) | FCA **FG21/1** (23/02/2021), https://www.fca.org.uk/publications/finalised-guidance/guidance-firms-fair-treatment-vulnerable-customers (PDF: https://www.fca.org.uk/publication/finalised-guidance/fg21-1.pdf) | Definition: "someone who, due to their personal circumstances, is especially susceptible to harm". Four drivers: health, life events (for example new caring duties), resilience (for example sudden job loss), capability. S8 deliberately sends job loss to 5.11, not 5.12. | fetched |
| 5.12(b) wording | Money Advice Trust **TEXAS** protocol (Thank, Explain, eXplicit consent, Ask, Signpost), https://www.moneyadvicetrust.org | Industry practice for handling disclosures of mental health problems. | not fetched |
| 5.6.3 Notice of Sums in Arrears sentence | Consumer Credit Act 1974 **s.86B** (fixed-sum) and **s.86C** (running-account), https://www.legislation.gov.uk/ukpga/1974/39/section/86B | The statutory notice once two payments are missed, sent with the FCA arrears information sheet. S8 uses "28 or more days" as a simple bank proxy. | not fetched |
| Table 5.2 bank holidays | gov.uk, https://www.gov.uk/bank-holidays.json | England and Wales 2026: 01/01, 03/04, 06/04, 04/05, 25/05, 31/08, 25/12, 28/12. 2027: 01/01, 26/03, 29/03, 03/05, 31/05, 30/08, 27/12, 28/12. Scotland adds 30/11/2026 and 04/01/2027; S8 says the England and Wales list applies to everyone. | fetched, matches Table 5.2 exactly |
| 5.4 third parties, 5.4.3 call times, 5.5 security checks, I&E review | General UK practice: right-party contact, data-protection (DPA) checks before any disclosure, third-party authority, income and expenditure via the Standard Financial Statement, referral to specialist teams. Also CONC 7 on contacting customers at unreasonable times. | | not fetched (the regulation research agent was still running at hand-back) |

**Invented for S8 and not real rules:** the 14-day Stage 1 limit, the 7th-banking-day Stage 2 limit, the 23/10/2026 non-processing day, Saturday callbacks from 24/10/2026, the result codes, and the bank itself. Kittiwake Bank plc and its people are fictional, and its domain uses the reserved `.example` TLD.

## B. Evidence on how the organisers test

### Kit (primary evidence)

- **README, "How you are scored":**
  - The ledger must match exactly: outcome, every promise, note, callback and transfer.
  - A judge reads the transcript against each customer's checks for policy and honesty.
  - There is no partial credit, and the README warns that one green run is "a hint, not proof".
- **README, "The final":**
  - The final briefs are unseen and use other numbers, limits, identity questions, outcome table and calendar.
  - One brief is raw material: a mail, a policy extract, a memo that changes it, and a code list.
  - Each brief has its own tool API: the same 7 tool names, but fields and allowed values may change.
  - Customers are tested "on several calendar days", three runs each, and all three must pass.
  - Customers have up to 3 products.
  - Customers talk in pieces, correct themselves, go off-topic, ask back, or say numbers in words.
- **`public-test-set.json`:**
  - 13 cases in 10 families (Happy path, Third party, Identity, Dates ×2, Hardship, Amounts, Already paid, Restructuring, Tool failure, Multi-product ×3).
  - Levels: 1 easy, 7 medium, 5 hard.
  - Each case is a 1–3 sentence conditional script plus an expected ledger plus 2–4 checks.
  - The checks test order of steps, counters, forbidden words, fixed sentences and honesty.
- **`tools/run_cases.py`:**
  - `STYLES`: pieces, corrects, talkative (with a distractor date, "wedding on the 30th"), asks_back, in_words.
  - `persona_for` already knows how to voice `postcode`, `birth_year`, `company_number` and `founded_year`. That points to other identity fields in the finals, including possibly a **business customer**.
  - `case.get("third_party")` and `case.get("style")` let third-party twists appear outside the family and fix a style per case.
  - The comment "organisers: a run made while the model was slow is thrown away and repeated".
- **`tools/score.py`:**
  - Treats `not_reached`, `no_contact` and `unreached` as equivalent, which means **renamed outcomes** are expected.
  - Checks from the ledger that `get_account` and `create_promise` are never called before verification, and that no identity tools run when the customer was not reached.
- **`tools/openapi.json`:**
  - "The service does not enforce the brief", so wrong dates and amounts are recorded silently.
  - Faults are injected per case (for example `fail_first_n`).

### Research on user simulators (summary from the research agent; arXiv abstracts fetched where marked)

- **τ-bench**, https://arxiv.org/abs/2406.12045.
  - Each task is a hidden user instruction revealed step by step, scored on database end state plus required outputs.
  - **pass^k**: gpt-4o retail drops from about 61% at pass^1 to under 25% at pass^8.
  - Common failures: rule-ignoring decisions and partially handled multi-part requests.
- **τ²-bench**, https://arxiv.org/abs/2506.07982.
  - Tasks are composed in code from atomic subtasks, and difficulty is the number of subtasks.
  - Persona levels; natural-language assertions, including negative ones.
  - pass^1 to pass^4 drops (retail 0.74 → 0.53).
  - About 12% of conversations had simulator errors that broke the task.
- **IntellAgent**, https://arxiv.org/abs/2501.11067.
  - Builds a policy graph and samples combinations of policies by complexity.
  - Success falls as complexity rises, and all models are weak on consent policies.
- **τ-Voice**, https://arxiv.org/abs/2603.13686 (fetched).
  - Voice agents reach 31–51% in clean audio and 26–38% with noise, against 85% for text.
  - Most failures come from the agent: missed identifiers, actions claimed without the tool call, dropped steps.
- **Lost in Simulation**, https://arxiv.org/abs/2601.17087 (fetched).
  - Simulated users are unreliable proxies: up to 9 points of swing depending on which model plays the user.
- **Non-Collaborative User Simulators**, https://arxiv.org/abs/2509.23124 (fetched).
  - Adds unavailable requests, tangents, impatience and incomplete input. Agents degrade sharply.
- **LLMs Get Lost in Multi-Turn Conversation**, https://arxiv.org/abs/2505.06120.
  - Spreading a task across turns cuts performance by about 39%.
- **UserLM**, https://arxiv.org/abs/2510.06552.
  - Cooperative assistant models make weak user simulators.
- **Voice-testing vendors:**
  - Coval (https://docs.coval.ai/concepts/personas/overview) keeps personas separate from scenarios and controls noise, speed and interruptions.
  - Hamming (https://hamming.ai/resources/voice-agent-test-personas-support-calls-template) uses typed checks on outcome, tool calls and side effects.
  - Vapi (https://docs.vapi.ai/observability/simulations-overview) and Retell (https://docs.retellai.com/test/llm-simulation-testing) run N fresh calls per scenario and judge by pass rate.

## C. Likely test design for the hidden customers (prediction)

**Families.** The same 10 families as the kit, recombined, with about 10–15 customers per brief. Hard cases stack 2–4 rules, in the IntellAgent and τ² style. Each case is pinned to a `now`, and the `now` values are spread over several weekdays and calendar positions.

**Difficulty knobs.**
1. **Where `now` falls:**
   - Friday versus mid-week, which changes "this" and "next" weekday.
   - A deadline that lands on a weekend or holiday.
   - A holiday inside the window.
   - **`now` before versus after the memo's effective date**, which is the raw brief's natural trap.
2. **Boundaries:**
   - days_late exactly at a band edge.
   - Amount equal to the floor, just below it, or above the arrears.
   - Callback time exactly at the window edge.
   - A promise date exactly on the deadline.
3. **Number of rules and products:**
   - 1–3 products with different bands and floors.
   - Mixed per-product results (promise, refusal, dispute, paid).
   - Notes and closing-code logic.
4. **Speech:** pieces, corrections, words, asks back, and talkative turns with a distractor date. Rules are revealed only when asked.
5. **Tool faults:** `fail_first_n=1` means a retry is needed. `fail_first_n=2` probably exercises the service-error path.
6. **Messy brief:**
   - Rejected email proposals.
   - Superseded values in history or old versions.
   - Retired or renamed codes, for example `no_contact` or `unreached`.
   - New identity fields (postcode, birth year, company number, founded year).
   - A different calendar and holiday list.

**Traps they are likely to use.**
- Disclosing something before verification, or doing so to a third party who offers to pay.
- Side questions (bot, scam, "who is this?", wanting a human) between the security questions, which interact with the ask counters.
- A vague period followed by a non-business day, or a date after the deadline.
- Mid-call disclosures (hardship, vulnerability, a legal hold) that change which outcome wins.
- Restructuring after a promise has already been recorded.
- Honesty when a tool fails ("recorded" said before ok).
- Banned concessions (discount, waiver, plan).
- Fixed sentences and exact counters.
- pass^3: a case that passes 90% of the time survives all three runs only about 73% of the time.

**What this means for testing our builder.**
- Run every suite on at least 2–3 `now` values, at least one on each side of a memo's effective date.
- Treat effective dates, retired codes and rejected proposals as data the builder must reason about.
- Keep dates, counters and outcome selection deterministic in code.
- Measure pass^3, not pass^1.
