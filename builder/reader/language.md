# PolicyIR: the rule language you write

You turn a bank's call specification into a **PolicyIR**: a JSON rule machine that a fixed runtime executes
during a phone call with a customer. The runtime knows nothing about banks; everything specific comes from
your IR. The dialogue model on the call only understands the customer and speaks the lines you give it.
**Every decision is yours, in the IR.** If a rule is not in the IR, the agent will not follow it.

## How the runtime works
- The call is in exactly one **phase** at a time (you name the phases). It starts in `initial_phase`.
- Events arrive one by one:
  - `enter`: the call just entered a phase (via `goto`).
  - `user`: the customer spoke. Before your rules run, the language layer has filled **slots** (values such as
    dates, amounts, digits) and **intents** (labels such as `yes`, `hardship`) from what the customer said,
    using the slot and intent definitions you declare.
  - `tool:<name>`: a bank tool the runtime called (because your rule said `call`) returned. Its JSON body is `result`.
- For a `user` event the runtime tries, and the first rule that matches fires and ends the turn:
  1. intent rules (`on: "intent:<id>"`) for each intent present except `yes`/`no`, in descending intent priority;
  2. `yes`/`no` rules whose `if` tests state but no slot (they answer a pending yes/no question, e.g.
     `flag.human_pending`);
  3. if some `on: "user"` rule of this phase tests a slot the customer gave in this turn (e.g.
     `is_set(slot.promise_date)`) and its `if` holds: the `on: "user"` rules, in their normal priority order;
  4. intent rules for `yes`/`no`;
  5. the `on: "user"` rules.
  So "Not today, but Friday" reaches your date rule, not your `no` rule; a bare "no" reaches the `no` rule.
- Within one `on`, rules are tried in descending `priority` (default 0); a rule applies when its `phase` matches
  (a name, a list, or `"*"`), it is not in `not_phase`, and its `if` expression is true. **Only the first
  matching rule fires.**
- A rule's `do` is a list of actions executed in order. `call` pauses: the runtime calls the tool, then fires
  `tool:<name>` rules, then continues with the actions after the call.
- Slots are cleared after every user turn (unless listed in `slots_sticky`). Everything you want to keep, store
  with `set` into `var.*`, `item.*`, `counter.*` or `flag.*`.

## Data you can read in expressions
| Path | Meaning |
|---|---|
| `call.<name>` | call variables given at call start (e.g. `call.customer_id`, `call.now`, names, title) |
| `today` | the call's date as `YYYY-MM-DD`, taken from the "now" call variable (never the real clock) |
| `slot.<name>` | values extracted from the customer's last message (normalised: dates `YYYY-MM-DD`, amounts as numbers, times `HH:MM`, digits as strings) |
| `var.<name>` | your own variables (unset = None) |
| `counter.<name>`, `flag.<name>` | same, by convention for counters and booleans; an unset counter reads as 0 |
| `items` | list of entities (e.g. products) you stored with `set {"items": ...}` |
| `item.<field>` | the current item (`items[cursor]`) |
| `result.<field>` | body of the last tool result. `result.ok` is false when the call failed (transport or `ok:false`) |
| `tool.<name>.<field>` | last result of a named tool |

## Expressions
Python-like: `== != < <= > >= and or not in`, `+ - * /`, `x if cond else y`, string literals in single quotes,
numbers, `None`, `true`, `false`. Missing values are `None`; comparing `None` with `<` is false.
Dates are ISO strings: compare them with `date_lt(a, b)`, `date_le`, `date_ge` or plain `<` on ISO strings.

Functions (the only ones available, plus your own in `functions`):
| Function | Meaning |
|---|---|
| `add_business_days(d, n)` | the n-th business day **after** d (d itself not counted), using `calendar` |
| `is_business_day(d)`, `is_holiday(d)` | |
| `next_business_day(d, include_same=False)`, `prev_business_day(d, include_same=False)` | |
| `last_business_day_of_week(d, offset)` | last business day of d's Mon–Sun week; offset 1 = next week |
| `weekday_in_week(name, 'this'|'next', ref)` | "this Friday" / "next Friday" (next = the following calendar week) |
| `add_days(d, n)`, `weekday(d)`, `day_label(d)` | `day_label` gives "Friday 16 October" for speech |
| `between(x, lo, hi, inc_lo=True, inc_hi=True)` | range test with explicit inclusiveness |
| `time_in_window(t, a, b, inc_lo=True, inc_hi=True)` | `HH:MM` window test |
| `time_of(datetime)` | `HH:MM` of a datetime string, e.g. `time_of(call.now)` |
| `min(...)`, `max(...)`, `round(x, 2)`, `money(x)` (`"637.50"`), `abs`, `len(list)` | |
| `ceil(x, step=1)`, `floor_(x, step=1)`, `pct(x, p)` | round up/down to a step (e.g. `ceil(x, 0.01)` = up to the cent, `ceil(x)` = up to the unit); `pct(x, 25)` = 25 % of x |
| `is_set(x)` | not None / not empty |
| `lower(s)`, `str_(x)` | |
| `copy_list(list)` | copy a list of dicts (use when storing tool results in `items`) |
| `count_where(items, key, value)`, `all_where(items, key, value)`, `first_where_not(items, key, value)` | |
| `find_index(items, require_keys, exclude_keys)` | index of first item with all `require_keys` set and none of `exclude_keys` set; -1 if none |
| `count_set(items, key)` | number of items where `key` is set |

Your own functions: `"functions": {"name": {"params": ["p"], "expr": "...", "src": "..."}}`. Use them for
tables and per-entity derivations (band of a product, its minimum amount, its label for speech).

## Actions
| Action | Effect |
|---|---|
| `{"say": "<template id>"}` | speak a template (fixed text, `{expr}` placeholders filled). Add `"prompt": true` if it asks the customer something (it is repeated after side questions) |
| `{"say_text": "literal {expr}"}` | speak a literal line |
| `{"instruct": "..."}` | let the dialogue model word a short reply following this instruction. Use only where wording must adapt; never for amounts, dates, outcomes or anything the spec fixes |
| `{"reprompt": true}` | repeat the last prompt (after answering a side question) |
| `{"call": "<tool>", "args": {"field": "<expr>"}}` | call a bank tool; arguments are expressions |
| `{"set": {"path": "<expr>"}}` | path root: `var`, `item`, `items`, `counter`, `flag`, `slot` |
| `{"incr": "path", "by": 1}` | add to a number (None counts as 0); `by` is a number or an expression |
| `{"append": {"path": "<expr>"}}` | append to a list |
| `{"goto": "<phase>"}` | enter a phase (fires its `enter` rules); ends the current action list |
| `{"next_item": "<phase>", "done": "<phase>"}` | move the cursor to the next item and enter `next_item`, or enter `done` when no items remain |
| `{"for_each_item": [actions]}` | run actions for every item (cursor moves); do not `call` or `goto` inside |
| `{"set_cursor": "<expr>"}` | select the current item |
| `{"if": "<expr>", "then": [...], "else": [...]}` | branch |
| `{"run": "<procedure>"}` | run a named action list from `procedures` (then continue) |
| `{"refire": "user"}` | re-run `user` rules in the (new) current phase with the same slots/intents (use after `goto` when the same message must be evaluated there) |
| `{"close": {"outcome": "<expr>", "reason": "<expr>"}}` | call the closing tool with outcome/reason and end the call. Say goodbye **before** it |

## Top-level IR keys
```json
{
  "version": 0, "name": "...",
  "calendar": {"workdays": ["Mon","Tue","Wed","Thu","Fri"], "holidays": ["YYYY-MM-DD", ...],
               "weekday_words": {"this": "calendar_week|upcoming", "next": "following_calendar_week|this_plus_7", "bare": "upcoming|this"},
               "src": "<sentence ids>"},
  "time": {"now_var": "<call variable holding the current date-time>"},
  "vocabulary": {"tools": {"<tool>": {"write": true|false}, ...}},
  "closing": {"tool": "<closing tool>", "extra_args": {"customer_id": "call.customer_id"},
              "fields": {"outcome": "<the closing tool's argument for the outcome>", "reason": "<its argument for the reason>"}},
  "initial_phase": "<phase>",
  "slots": {"<name>": {"kind": "birth_date|date|amount|digits|time|text|enum", "phases": [...], "length": 4, "min_length": 7, "max_length": 8, "numeric_order": "DMY", "values": [...], "description": "...", "src": "..."}},
  "slots_sticky": [],
  "intents": [{"id": "...", "description": "<in the spec's words>", "priority": 0, "src": "..."}],
  "templates": {"<id>": {"text": "...", "exact": false, "src": "..."}},
  "functions": {...}, "procedures": {"<name>": [actions]},
  "rules": [{"id": "...", "phase": "...", "on": "...", "if": "...", "do": [...], "priority": 0, "src": "..."}],
  "restricted_words": [{"words": ["<word>", ...], "until": "<expr: true once the word may be said>", "src": "..."}],
  "coverage": {"<sentence id>": "non-normative: <why>"},
  "ambiguities": [{"src": "...", "question": "...", "decision": "...", "why": "..."}]
}
```

## Conventions (follow them; the language layer and tests rely on them)
- **Identity answer slots** are named `id_<field>` where `<field>` is the value the identity tool expects for
  which question (e.g. the tool's `field` enum). Kind: `birth_date` for full dates of birth, `digits` (with
  `length`) for digit strings, `text` otherwise.
- **Standard intents** (reuse these ids when the meaning matches; add new ones when the spec needs them):
  `confirm_identity`, `third_party`, `wrong_number`, `deceased`, `ask_bot`, `ask_scam`, `ask_reason`,
  `other_question`, `not_want_talk`, `human`, `decline`, `yes`, `no`, `hardship`, `restructure`, `paid`,
  `dispute`, `too_much`, `vague_date`. Give every intent a description in the spec's own words. Keep the standard
  intents apart where they are easily confused: `ask_bot` = asks whether the agent is a robot, an AI or a real person
  ("You're a real person, aren't you?"); `human` = asks to be put through to a human (not: asking whether the agent is
  one); `ask_reason` = asks what the call is about; `decline` = refuses to answer the question asked; `not_want_talk` =
  does not want this call at all (not: declining one offer); `no` = says no to what the agent just asked or offered.
- **Standard slots**: `promise_date` (date), `promise_amount` (amount), `callback_date` (date), `callback_time` (time),
  `product_ref` (text: which of several products/policies/accounts the customer is talking about, as said, e.g.
  "the car loan", "the card ending 3307"). Declare `product_ref` in every phase where several items are discussed.
- **Referring to another item.** With several items, a customer may speak about a different item than the current one
  ("the loan was paid off", "I already paid the line of credit"). Resolve it with `item_index(items, slot.product_ref)`
  (index or -1). When it points to another item, record the fact on THAT item (e.g. set its end reason with
  `set_cursor`, `set`, then set the cursor back), acknowledge it, and continue with the current item; when that item's
  turn comes, skip it if it already has an outcome. Never attach the claim to the current item by default.
- Phase names are free (snake_case).
- Every rule, template, intent, slot and function carries `src`: the sentence ids (e.g. `"D1.s024,D1.s025"`)
  it implements. **Every sentence id of the documents must appear in some `src`, or in `coverage` with the
  reason it is not a rule** (introductions, examples already covered, notes for humans).
- Use only tools, argument names and enum values from the TOOLS vocabulary given to you. Argument values that are
  constants are quoted string expressions: `"'date_of_birth'"`.

## How to write good rules (these are what the scorer checks)
1. **Fixed wording where the spec fixes it.** If the spec quotes a sentence, put it verbatim in a template with
   `"exact": true`. Every mandatory statement (disclosures, what to say on a failure, the closing goodbye) is a
   template, not an `instruct`.
2. **Never reveal what must stay hidden before it is allowed.** Do not put such information in any template or
   instruction reachable before the condition holds (e.g. before identity is verified, or to a third party).
3. **Counts are exact.** "Ask once more", "offer once", "two attempts", "three wrong answers in total" → a counter
   in `var`/`item` and an `if` that stops at the limit. The agent must never ask or offer more than allowed.
4. **Facts come from tools, not from the customer.** A flag like verified/recorded is set only from `result`.
   Say "recorded" only on the branch where the tool returned `ok`.
5. **Compute, do not ask the model.** Deadlines, business days, windows, minimum amounts, product order,
   outcome codes: expressions and functions.
6. **Precedence.** When the spec says a rule comes before others, give its intent a higher `priority` (intent
   rules are tried by intent priority) or its rule a higher rule `priority`.
7. **Every path ends** with a goodbye template then `close`, with the outcome/reason the spec's table requires.
   The closing tool is called exactly once, last. **As soon as the outcome is decided, say the goodbye and close in
   the same action list.** Do not ask open questions the spec does not ask for ("anything else?", "how was your
   experience?"): every extra question is a new chance to fail.
8. **Side questions** (are you a robot, is this a scam, a question you cannot answer) are answered with their
   template and followed by `{"reprompt": true}` unless the spec says otherwise, **in every phase that listens to
   the customer** (simplest: rules with `"phase": "*"`). A side question is never a "no" and never moves the call on.
9. **Don't invent rules.** If the spec is silent, do nothing special. If a sentence is genuinely ambiguous, pick
   the reading the spec's own examples support, else the narrowest reading, and record it in `ambiguities`.
10. **Amending documents** (memos, "unless replaced", newer instructions): apply the change to the rule it
    targets and keep only the final version in the IR; record each change under `ambiguities` with
    `"question": "amendment"` and the old and new values.
11. **A restricted word is restricted everywhere.** The scorer reads words literally. If the spec limits when a
    word may be said (e.g. "say the promise is recorded only after `create_promise` returns ok"), no sentence that
    can be said earlier may contain that word, even in another sense: write "we record this call", not "this call
    is recorded". Same for words forbidden before identity is verified. **List every such word in
    `restricted_words`** with the state expression that makes it allowed (e.g. `{"words": ["recorded"], "until":
    "flag.promise_recorded"}`, `{"words": ["debt", "collections"], "until": "flag.verified"}`; a word never allowed:
    `"until": "false"`). The build checks every sentence the agent says against this list and fails on a word said
    before its condition holds.
12. **Intents are precise.** An intent's `description` is what the language layer matches. Use the spec's words,
    and write an exclusion as what does not count ON ITS OWN ("not: only saying the full amount is too much"): a
    message can carry both, and then the intent is true;
    and when the spec handles a neighbouring request differently, name it as an exclusion so it is not matched by
    similarity: e.g. restructure = "asks for a new payment plan or lower instalments (not: a discount, a waiver or
    a fee refund, which the spec handles separately)".
17. **The right person can come to the phone.** If someone else answered and the customer then takes the phone ("he just
    walked in", "Daniel Reyes speaking"), the call continues with the customer: the identity confirmation and checks
    as for any call. The phase for someone else must listen to `confirm_identity` and go back to the opening check.
18. **An effectful intent covers exactly the situation the spec names.** For intents that close, transfer or record
    (paid, dispute, restructure, ...), put the spec's limits into the description and exclude the near cases the spec
    treats otherwise or does not cover: e.g. paid = "already paid THIS past-due amount in full (not: a part of it; not:
    a product paid off in the past, which is a dispute)"; restructure = "asks for a new payment plan or lower instalments
    (not: asking what the minimum payment is, or asking to pay the minimum / the floor -- the spec's floor rules handle that)".
19. **Do not widen the spec's words; keep an intent on its own dimension.** Describe an intent with the spec's own
    condition, not a looser paraphrase. When the agent's question carries two things (an amount AND a day: "Can you pay
    540.00 today?"), an intent about one of them excludes the other: too_much = "says the full AMOUNT is too much (not:
    cannot pay today or on that day, which is about the day; not: naming a smaller amount)". A paraphrase such as "cannot
    pay all of it" also matches "I can't pay that today" and sends a customer who only needs another day to the floor.
20. **One offer, even when two rules describe it.** When one rule says WHAT to offer ("offer the floor, once") and
    another says WHEN or in which step ("attempt 1 is for the floor if the customer said the full amount is too much;
    attempt 1 proposes the last business day of this week"), they describe the same single offer: make it once, with
    the amount from the one and the day from the other. Do not chain them into two offers of the same amount.
16. **Name what you offer.** A sentence that offers a policy amount says what it is, in the words the spec uses with
    customers ("the minimum payment of 637.50", "the full past-due amount of 2125.10", "the instalment"), never a bare
    number. Customers (and the scorer) decide by what the amount IS: a bare "Could you pay 637.50?" is not recognisable as
    the minimum, is refused, and the next offer then repeats it.
15. **Relative day words go in `calendar.weekday_words`, not in a description.** If the spec defines "this <weekday>" /
    "next <weekday>" / a bare weekday name, encode it: this = `calendar_week` (the one in today's Monday-Sunday week) or
    `upcoming` (the first such day after today); next = `following_calendar_week` or `this_plus_7` (seven days after
    "this"); bare = `upcoming` or `this`. Omit what the spec does not define (defaults: calendar_week,
    following_calendar_week, upcoming). The runtime resolves dates with this; the language layer cannot (it does not
    know today's date).
14. **A slot `description` says what the value MEANS, never its format.** The runtime asks the language layer for the
    customer's own words and resolves them itself (calendar, amounts); do not write "as YYYY-MM-DD" or "resolved against
    now" in a description.
13. **Every `digits` slot states its length**: `length` when fixed, else `min_length` (and `max_length`) from the
    spec ("seven or eight digits" → 7 and 8). Callers say long numbers in pieces; without a length the runtime
    cannot tell that a number is unfinished and sends half of it to the bank.

## Language of the call, spoken fallback lines, a call that ends without a closing tool
21. **The call's language.** If the spec's customers speak a language other than English, write `"language": "<its
    English name>"` at the top level (the dialogue model is told to speak it) and write EVERY template and `instruct`
    in that language, using the spec's own sample sentences word for word where it gives them. Also write
    `"engine_text": {"continuer": "<short line inviting the customer to go on when their message was cut off>",
    "fallback": "<short line asking the customer to say that again>", "fault": "<apology for a technical problem, then goodbye>"}`
    in that language (the runtime speaks these itself). Intent and slot `description`s stay in English.
22. **No closing tool.** If the spec's services have no closing/note tool (hanging up, or handing the call back to a menu
    or to a person, is only something the assistant SAYS and then the call ends), write `"closing": {"tool": null}` and end
    the call with `{"close": {}}` after the spoken line (no outcome, no reason). Say the spec's exact hand-over sentence
    before it. Never invent a tool.
23. **A service answer with a failure.** A failed call has `result.ok == false` and `result.code` / `result.message` hold
    the bank's code and text (when the OpenAPI describes an envelope with `result`). Branch on `result.code` for the
    errors the spec distinguishes (a 'warning' meaning "nothing to work with" is not a technical fault); never read the
    service's `message` text to the customer unless the spec says so. Dates that services return in a fixed written form
    (a written pattern such as day.month.year) are text: turn them into speech with your own `functions` (a table of month names in the
    call's language) instead of reading digits.
24. **Values the caller says that pick out a record** (an identifier fragment, a choice among options) are slots; the argument sent to
    a service that identifies a record must be the value the service itself returned earlier, never rebuilt from what
    the caller said. Never say more of an identifier than the spec allows, whatever a service returns.
