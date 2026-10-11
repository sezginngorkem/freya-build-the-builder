# Build the Builder: a phone-agent builder for Freya

One command turns a bank's call material (a specification, or raw mails, policies, memos, meeting notes, a service
contract) into a Freya phone agent:

```bash
cd builder
BANK_BASE_URL=<your mock> python build.py <case folder> --slot <name>
```

- **Reader** (`builder/reader/`): reads every sentence of the material into a PolicyIR (phases, rules, intents,
  value slots, templates), each element citing its source sentence ids; later documents amend earlier ones. When
  there is no OpenAPI file, one is written from the service documents.
- **Validation + self-test** (`builder/reader/validate.py`, `builder/selftest/`): static checks, two independent
  reads chosen by tests written from the material, a conversation judge confirmed by a referee, root-cause repair.
- **Compiler** (`builder/compiler/c2.py`): a Freya workflow in which the language model only understands the caller
  and words the replies; every decision (dates, amounts, counters, outcome codes, tool calls) is made by a
  deterministic engine (`builder/engine/`) running the IR in a code step.
- **Trace**: every model call, check and Freya action is written to `traces/<slot>.log`.

Final case: `submission/final.workflow.json` (exported agent), `traces/final.log` (the builder run), `mock/` (the
bank-service mock deployed on Cloudflare Workers).
