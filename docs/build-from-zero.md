# Building an ad ops agent from zero: architecture, modules, data flow and build order

This document follows the order in which you would actually make the decisions. Each
step states the problem first, then the design it forced, then what that design costs.
The goal is that you could build a comparable thing yourself, not just read this one.

Companions: [the operating loop rules](operating-loop.md) · [what one round looks like](../demo/README.md) · [implementation boundaries](architecture.md)

---

## Step 0 · First draw the line around what it is responsible for

Everything else follows from this. **Skip it and every later technical choice turns
into an argument**, because there is no shared answer to "should the machine do this".

A media buyer's round contains four kinds of labour:

| Labour | Hand it over? | Why |
|---|---|---|
| Prepare assets, assemble configurations | Yes | Repetitive, verifiable, cheap to get wrong |
| Execute an **already approved** batch | Yes | Repetitive, and the result can be read back |
| Explain what actually happened | Yes | Precisely the part most often miscalculated, and the part that most needs a trace |
| Decide direction, judge whether it is worth it, call the stop | No | Expensive to get wrong, and the responsibility has to sit with a person |

Three hard boundaries follow, and they determine every technical choice below:

1. **Offline first.** The prototype contacts no advertising platform, so a logic error
   and a permissions error can never be confused for one another.
2. **A human stays in the path.** The output is a proposal list for review, not an instruction that has run.
3. **Say "unknown" when it is unknown.** Anything that cannot be computed is reported as
   missing evidence. **Never fill the gap with an inference.**

> The cost: this prototype will not change your budgets. The gain: every judgement it
> makes can be inspected and tested on its own.

---

## Step 1 · Layer it, so the volatile parts separate from the stable ones

The obvious first attempt — one script that calls the ad API, computes, and writes — has
one fatal property: **two things with completely different lifetimes are tangled together.**

- Platform interfaces change, and so does the way you connect (official API, SDK, MCP,
  managed connector — each different).
- The team's thresholds change too, but **the structure of "how we decide" should not be
  rewritten every time a number moves.**

So split by rate of change:

```
┌──────────────────────────────────────────────────────┐
│ Presentation  demo/ · the one-page report            │  ← for a human
├──────────────────────────────────────────────────────┤
│ Decision      operating_rules.py  metrics·rules·gate │  ← stable, unit-testable
├──────────────────────────────────────────────────────┤
│ Orchestration operating_loop.py   snapshots·ledger   │  ← stable, owns IO
├──────────────────────────────────────────────────────┤
│ Contract      internal capability names + shapes     │  ← stable, hides the vendor
├──────────────────────────────────────────────────────┤
│ Connection    API / SDK / MCP / managed connector    │  ← most volatile
└──────────────────────────────────────────────────────┘
                   ▲                              ▲
                   │ thresholds are NOT here     │
              methodology.json (one per team)
```

**The key decision: thresholds live in data, not in code.** Target ROAS, ladder, loss
line, sample gate, creative rules, and each action's own acceptance and stop condition
all sit in one methodology document. A new offer, a new unit price, a new team — change
that JSON and nothing else.

> Cost: you need a loader and a validator (`validate_methodology`).
> Gain: the engine never has to change to change a number, and therefore never has to be
> re-tested to change a number.

---

## Step 2 · Technology choices, each with a reason it is not something else

| Choice | Why | Cost |
|---|---|---|
| **Python 3.9+, standard library only** | A demo must run the moment it is cloned. Zero dependencies means zero install failures and zero supply-chain surface | No pandas/numpy; statistics are hand-rolled (the attribution here only needs `math.log`) |
| **`Decimal`, not `float`** | Budget comparison is an equality decision. Under `float`, `10.00` may not equal `10`, and the gate misjudges | Slower and more verbose; the gate only compares a handful of fields |
| **JSON as the stage artifact** | Each stage's output is a **file**, not an in-memory object — so it can be run alone, diffed, committed to the repo as a sample, and resumed after a crash | More files |
| **JSONL ledger, append-only** | State is derived by folding events, so history is never rewritten, and any round's intermediate state is reconstructable | You have to write `fold()` |
| **No LLM** | The decision layer must be deterministic: same input, same output, or it cannot be tested and cannot be reviewed | Natural language is handled by the host; the local program does not attempt it |
| **Offline (no network at all)** | Decouples a logic error from a permissions error, and lets the demo run anywhere | Real integration needs a connector written separately |

> One discipline runs through all of it: **only the ledger timestamps are impure.** Everything
> else is deterministic — and even that is pinned with `--at`, or a committed sample would
> drift on every run.

---

## Step 3 · Reduce one round until nothing can be removed — the data flow grows out of that

**The data flow is not designed. It appears once you cut a round down so that each step
needs only the previous step's output.**

Ask: how many things actually happen in one round?

| Stage | On hand | Produces | Layer |
|---|---|---|---|
| 0 Re-verify | last round's ledger | the rows still open | orchestration |
| 1 Collect | platform connection | `snapshot.json` | connection |
| 2 Classify | snapshot + methodology | `findings.json` (actions included) | decision |
| 3 Propose | findings | (action objects inside findings) | decision |
| 4 Gate | findings + a fresh read | `gate.json` (+ write plan) | decision |
| 5 Execute | gate.json | `application.json` + `ledger.jsonl` | connection (offline = record) |
| 6 Reconcile | gate.json + a second read | `reconciliation.json` | decision |
| 7 Report | all of the above | `report.md` | presentation |

The flow itself:

```
 platform/connector ──▶ snapshot.json ──┐
                                        ├─▶ findings.json ──┐
 methodology.json ──────────────────────┘                   │
                                                           ▼
 fresh read ──▶ writeback.json ──▶ gate.json ──▶ write plan (differing fields only)
                                      │                       │
                                      ▼                       ▼
                            (non-writable rows isolated) application.json + ledger.jsonl
                                      │                       │
 second read ──▶ after.json ──────────┴──▶ reconciliation.json ──▶ report.md
                                                          │
                                        ledger.jsonl ─────┴──▶ next round's "re-verify"
```

**Two consequences that are not obvious and matter a lot:**

1. **Every stage's output is a file ⇒ a real run's output can be committed as a sample.**
   This is what solves "how does a newcomer understand this quickly": the result is
   readable without installing anything.
2. **The gate sits between "classify" and "execute", not after execution.**
   Checking after the fact only lets you roll back; checking before means the conflicting
   row is never written at all.

---

## Step 4 · The decision layer: one pure-function module

`operating_rules.py` — **no IO, no state, no network**. Internally it always runs in this order:

```
parse numbers → derive metrics → cost attribution → creative rules → classify each ad set → write gate
```

Four implementation decisions, each answering a real failure:

### 1. Uncomputable is `None`, not `0`

`CPC = spend ÷ clicks`. With zero clicks, `CPC` has **no value** — it is not zero.
But `CTR = clicks ÷ impressions`: 1000 impressions and zero clicks is a **genuine zero**.

Conflate them and downstream reads "no data" as "the value is zero", turning missing
evidence into "performed badly". So **missing and zero are kept apart**, and the report
labels which field is missing evidence.

### 2. The order of the checks is fixed, first match wins

It does not compute everything and then look. It passes seven gates:

```
1 account health → 2 hard faults → 3 is the metric computable → 4 sample gate → 5 loss line → 6 utilisation → 7 only now, promotion
```

**The order is itself the judgement.** An ad set costing $1.60 against a $4.71 target looks
excellent — until you see 32% budget utilisation, at which point the verdict is
"**cannot spend**, fix delivery first" rather than "scale it". The order makes you see
utilisation before cost.

### 3. Every action carries its own acceptance and stop condition

This is the line between an agent *working* and an agent *suggesting*:

```json
{
  "code": "LADDER_PROMOTE",
  "acceptance": "read-back shows daily_budget at the target stage and the change in the activity feed. A mismatch counts as not executed.",
  "stop_condition": "read-back shows bid_strategy overwritten by a default, or the stage did not cover a complete delivery day -> do not advance.",
  "baseline": {"daily_budget": "10.00"},
  "target":   {"daily_budget": "20.00"}
}
```

- **`acceptance`** — how you know it is done. Without it, an action stays at "I said so".
- **`stop_condition`** — when you are **not allowed** to do it. The only thing that keeps an agent in its lane.
- **`baseline` / `target`** — what was read when the plan was built and what it should become.
  **The next stage's gate runs entirely on these two fields.**

### 4. Attribute cost with log differences, not by "which number looks biggest"

`CPA = CPM ÷ (1000 × CTR × CVR)`, so after taking logs the gaps add up:

```
log(CPA / CPA_reference) = dlog(CPM) − dlog(CTR) − dlog(CVR)
```

The three signed terms are reported with their share of the absolute total. It answers
"which stage of the funnel moved the cost". A non-zero residual means the quoted metrics
were rounded — itself worth knowing.

---

## Step 5 · The orchestration layer: IO, ledger, report

`operating_loop.py` does four things and **contains not one line of judgement**:

1. Validate the snapshot (no `unit_price` ⇒ refuse: without `T` the cost rules are
   meaningless, and guessing is worse than failing).
2. Call the decision layer and write the results as files.
3. Maintain the append-only ledger and fold it into current state.
4. Render the report and expose the CLI.

**Why two modules**: the decision layer must be unit-testable purely (dict in, verdict
asserted) without dragging in files, directories and a CLI. That is why 40 of the 49
contract tests call the decision layer directly.

---

## Step 6 · Fixtures that force every branch

This is **part of the design, not a by-product of testing**.

Fixtures containing only "normal data" leave half the engine never executed, so a
misclassification never surfaces. The fictional data is therefore built **backwards from
the branches**: healthy, below the sample gate, past the loss line, over cost, cannot
spend, one ad set with three simultaneous findings, a disapproved ad, a broken link, a
name that disagrees with reality, plus three account-level signals.

Then build **two "second moment" snapshots** — the step most often forgotten:

| Snapshot | Purpose | Deliberately planted |
|---|---|---|
| `writeback-snapshot.json` | read just before writing | one row **a human already edited** (current is neither baseline nor target) |
| `after-snapshot.json` | read after writing | one **write that did not take effect** (expected 40, read 20) |

> Without these two, the gate and the reconciliation are paper features — normal data
> never lights them up.

---

## Step 7 · Three guardrails — the line between this and "a script that does arithmetic"

By now the engine can compute. These three are where the value actually is, and **each has
a corresponding row in the fixtures**:

| Guardrail | Without it | How it is designed |
|---|---|---|
| **Sample gate** | A zero-result ad set is killed on $3 of spend when it was only ever under-observed | Being dead requires **both** the impression floor and the loss line. Below the floor it is recorded as under-tested. An expensive click triggers an early stop that halts new spend **without** concluding the creative is bad |
| **Write-back reconciliation** | A successful API response is treated as a changed field | Read again after writing and compare against `target`; a mismatch is recorded as not effective and **the row stays open** |
| **Write gate** | Someone edits during the round ⇒ you overwrite them, or you restart the whole batch | Read once more, compare baseline against current against target, five outcomes: **only "ready" rows are written, and only their differing fields**; a conflict **isolates that row alone** |

**The five gate outcomes** — the piece most worth borrowing:

| Outcome | Meaning | Action |
|---|---|---|
| `ready` | current = baseline | send only the differing fields |
| `satisfied` | current = target | **write nothing** (writing is a significant edit and resets learning) |
| `conflict` | current ∉ {baseline, target} | isolate the row; do not overwrite, do not restart the batch |
| `unknown` | not read, or the field is absent from the read | **re-pull first**. Absent ≠ equal, never pass it |
| `advisory` | the finding declares no field change | nothing to gate; counted separately |

> The last one was added later: folding "findings that are not writes" into `unknown`
> inflates the number of rows needing attention by more than double (measured here: 11 → 2).

---

## Step 8 · Make the review artifact itself reviewable

The report is the final human-facing output. That alone is not enough — why should a new
reader trust it? So add one more layer:

1. **Commit the output of a real run into the repository** (`demo/expected/`) ⇒ readable
   without installing anything.
2. **Add a drift check** (`--check` re-runs and compares byte for byte, wired into CI).

Why the second is mandatory: **a sample that claims more than the code does is worse than
no sample.** The moment it diverges it stops being evidence and becomes a misleading claim.

---

## Step 9 · Framework and strategy are two different lines

This is the most commonly confused point. The **framework** is the unchanging skeleton
(layers, contracts, the gate, the ledger). The **strategy** is the content that evolves with
live results (thresholds, rules, ordering). They are built in completely different ways.

### The framework: designed once, then barely touched

Layering, the stage split, the five gate outcomes, the append-only ledger — all decided
when the first line was written, and only added to since.

### The strategy: not designed, grown out of each failure

```
① Start from the financial basis: unit price x quality / target ROAS = T
   ⇒ gives the loss line 3T and the ladder T -> 2T -> 3T

② Run a live round -> "zero-result ad sets are being killed unfairly"
   ⇒ add the sample gate: below the impression floor, record, do not judge

③ Run a live round -> "the budget was 'changed' but never took effect, and we counted it"
   ⇒ add write-back reconciliation: compare the read-back against target

④ Run a live round -> "the buyer edited a row during the round and the plan overwrote it"
   ⇒ add the write gate: three-way comparison, isolate only the conflicting row

⑤ Every new finding -> distilled into "rule + acceptance + stop condition" in the methodology
```

**This is why thresholds must live in data.** The strategy will be contradicted by live
results over and over; with thresholds hard-coded, each contradiction means changing code,
re-running tests and re-releasing. Externalised, each contradiction is one JSON field.

> Conversely: **a threshold table that never changes means it is not running against live traffic.**

### Deciding whether a new finding belongs to the framework or the strategy

| Question | Framework | Strategy |
|---|---|---|
| Would it still hold after changing offer or unit price? | Yes | No |
| Is it a **mechanism** or a **number**? | mechanism | number |
| Example | "always read back after writing" | "stop loss = 3T" |

---

## Step 10 · Port it to your own accounts

```bash
# 1. Shape your collected data like the reference snapshot
#    follow examples/operating/snapshot-primary.json
# 2. Copy the methodology and change the numbers (the only "strategy" file you edit)
cp examples/operating/methodology-reference.json my-methodology.json
# 3. Run
python3 operating_loop.py diagnose --snapshot my-snapshot.json \
    --methodology my-methodology.json --out runs/my-round
```

**No unit price, target ROAS or budget multiple is hard-coded.** The action catalogue
travels with the thresholds, so every action always carries its own acceptance and stop
condition.

---

## Appendix · Module inventory

| Module | Layer | One-line responsibility |
|---|---|---|
| `operating_rules.py` | decision | metrics, attribution, sample gate, creative rules, classification, write gate (pure) |
| `operating_loop.py` | orchestration | snapshot validation, stage artifacts, append-only ledger + fold, report, CLI |
| `onboarding.py` | orchestration | connection gate, collaboration guidance, business readiness |
| `guidance.py` | orchestration | first-run connection routing |
| `knowledge.py` + `knowledge/catalog.json` | knowledge | runtime catalog retrieval and advisory assessment |
| `memory_store.py` / `personalization.py` | knowledge | private methods and observations (local SQLite, versioned, revocable, product-scoped) |
| `methodology.py` / `planning.py` | decision | method candidates and adoption / asset identity into test units |
| `adops.py` / `task.py` | orchestration | plan, authorize, simulate, recover / unified task flow |
| `demo/` | presentation | one command, a committed sample of real output, and a drift check |
| `contracts/` | contract | provider-neutral design contracts (**not loaded at runtime**) |

Supporting: `tests/` (208) · `examples/` (fictional inputs) · `docs/` · `.github/workflows/` (offline CI)

---

## In one sentence

> **Cut a round down until each step needs only the previous step's output, externalise every
> threshold into data, then put a gate before the write and a read-back after it — and make
> every stage's output openable on its own.**

Back to the [documentation index](index.md) · [project home](../README.md)
