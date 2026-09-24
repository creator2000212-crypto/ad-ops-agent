# From zero: one operator, 3 live accounts, 10 ad sets

Reading the engine answers *how it computes*. This file answers *how it lands* —
starting from the raw numbers you have in front of you and walking to a report you
can send, with the decisions it made and the decisions it refused to make at each step.

> To follow along in a terminal: `python3 demo/run_demo.py --steps` expands the same
> sequence stage by stage. To read the end state without running anything:
> [`expected/report.md`](expected/report.md).

---

## Step 0 · Starting point: what it costs to do this by hand

It is 11:50. You have:

- 3 live accounts (two spending, one already stalled)
- 10 ad sets across two ladder stages (`T`, `2T`)
- yesterday's settled data
- a written methodology: 85% target ROAS, ladder `T → 2T → 3T`, stop loss at `3T`

One question: **what do I touch today?**

By hand, that is five jobs:

1. work out cost per result, `CTR`, `CVR` and budget utilisation for each ad set;
2. decide what to scale, what to stop, and **what cannot be judged yet**;
3. remember which rows you already edited, so you do not overwrite yourself;
4. confirm the platform actually applied each change;
5. write a one-page report.

Jobs 2, 3 and 4 are the ones you can get wrong without noticing. Each step below
shows what this does at that point.

**What a data feed looks like** — this is the snapshot layer, the API response
turned into something reviewable:

```json
{
  "kind": "operating_snapshot",
  "as_of": "2026-09-24T11:50:00+08:00",
  "observation": {"kind": "settled_day", "date": "2026-09-23", "complete_delivery_day": true},
  "accounts": [{
    "account_key": "fictional-meta-account-a",
    "account_timezone": "Etc/GMT",
    "offer": {"offer_key": "fictional-offer-alpha", "unit_price": "4.000"},
    "adsets": [{
      "adset_key": "fictional-adset-a1",
      "name": "1n1 | A1 | MAX | $10",
      "configured_status": "ACTIVE", "effective_status": "ACTIVE",
      "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
      "daily_budget": "10.00", "ladder_stage": "T",
      "spend": "12.40", "impressions": 3200, "clicks": 210, "results": 3, "frequency": "1.18"
    }]
  }]
}
```

**Why `as_of` and the observation window come first**: without knowing when the data
stops, maturity is meaningless and every later judgement is built on nothing.
"Complete delivery day" decides whether promotion is even allowed — a window that
starts mid-day does not count.

---

## Step 1 · Classify: turn 10 ad sets into "what to touch"

```bash
python3 operating_loop.py diagnose \
    --snapshot examples/operating/snapshot-primary.json \
    --methodology examples/operating/methodology-reference.json \
    --out demo/out/steps/1-diagnose
```

```
{"kind": "operating_findings", "accounts": 3, "proposals": 16, "structure_findings": 3}
→ 16 findings across 12 distinct rules
```

### The real design here: **the order of the checks is itself the judgement**

The engine does not compute everything and then look. It passes **seven gates in a
fixed order, first match wins**:

| # | Gate | If it does not pass |
|---|---|---|
| 1 | Account health (stalled / no spend / low balance) | Account signal reported first, not buried per ad set |
| 2 | Hard faults (rejected? broken link?) | Act immediately, do not wait for the window |
| 3 | **Is the metric computable** | Uncomputable ⇒ missing evidence, **not zero** |
| 4 | **Sample gate** (zero results: enough impressions?) | Too small ⇒ record only, **do not judge the creative** |
| 5 | Loss line (`spend − T × results ≥ 3T`) | Past it ⇒ stop |
| 6 | Budget utilisation (cannot spend / at cap) | Cannot spend ⇒ fix delivery first |
| 7 | **Only now, promotion** | All six above must pass before scaling |

Reverse the order and you would first see "a5 costs $1.60 against a $4.71 target —
obviously scale it". Its utilisation is **32%**. **Its problem is not cost, it is
that it cannot spend.** The order makes you see that first.

### Two rows that look identical get opposite verdicts

| Ad set | Data | Verdict | Reason |
|---|---|---|---|
| `a3` | $15.30 / **420 impressions** / 0 results | `TEST_STOP_NOCONV` (P0 pause) | 420 is **past the 300 gate**, and 15.30 is **past the 14.12 loss line** |
| `a2` | $3.10 / **180 impressions** / 0 results | `TEST_UNDERTESTED` (record only) | 180 is **below the gate** ⇒ not enough evidence to call the creative bad |

Both have zero results. **Only an engine with the right order dares say "I don't
know" about one of them.**

---

## Step 2 · From finding to action: every action carries its own acceptance and stop condition

`diagnose` does not emit a sentence of advice. It emits a **reviewable object**. This
is the line between an agent *working* and an agent *suggesting*:

```json
{
  "code": "LADDER_PROMOTE",
  "level": "P1",
  "object_key": "fictional-adset-a1",
  "action": "double the ad set budget (T -> 2T -> 3T)",
  "window": "2-3 complete delivery days",
  "acceptance": "read-back shows daily_budget at the target stage, and the change is visible in the activity feed. A mismatch counts as not executed.",
  "stop_condition": "read-back shows bid_strategy / bid_amount overwritten by a default, or the stage did not cover a complete delivery day -> do not advance.",
  "baseline": {"daily_budget": "10.00"},
  "target":   {"daily_budget": "20.00"},
  "evidence": ["3 results >= 3, complete delivery day = True, CPA 4.13 <= T 4.71."]
}
```

Three fields matter:

- **`acceptance`** — how you know it is done. Without it, an action stays at "I said so".
- **`stop_condition`** — when you are **not allowed** to do it. "Retry with a changed
  hash only once", "never silently swap the optimisation goal to get a create to
  succeed". It is the only thing that keeps an agent inside its lane.
- **`baseline` / `target`** — what was read when the plan was built, and what it should
  become. **The next step's gate runs entirely on these two fields.**

All 16 findings carry these three, with `evidence` holding the why.

---

## Step 3 · Write gate: before touching anything, confirm nothing moved under you

```bash
python3 operating_loop.py gate \
    --findings demo/out/steps/1-diagnose/findings.json \
    --writeback examples/operating/writeback-snapshot.json \
    --out demo/out/steps/2-gate
```

**16 findings → only 4 are writable.** Five outcomes:

| Outcome | Count | Meaning |
|---|---|---|
| `ready` | **4** | matches the baseline ⇒ send only the differing fields |
| `satisfied` | 1 | target already in place ⇒ **write nothing** (it would be a significant edit and reset learning) |
| `conflict` | 1 | **a human changed it ⇒ isolate this row** |
| `unknown` | 1 | pre-write state unreadable ⇒ **re-pull** (absent ≠ equal, never pass it) |
| `advisory` | 9 | creative/account findings with no field change ⇒ nothing to gate |

The two rows that need a human:

```
⚠ fictional-adset-a9 · LADDER_PROMOTE · conflict
   — daily_budget: current 30.00 is neither the baseline 10.00 nor the target 20.00 ⇒ a human changed it; isolate this row.
⚠ fictional-adset-b1 · LADDER_PROMOTE · unknown
   — no record of 'fictional-adset-b1' in the pre-write state ⇒ re-pull first, do not write blind.
```

**Why this stage exists**: minutes — in practice tens of minutes — pass between
collecting and writing, and the operator very likely edited something in Ads Manager
in between.

- Write without comparing ⇒ **you overwrite their edit**.
- Restart the whole batch over one conflict ⇒ the other 15 rows wait a round for nothing.

So the rule is: **isolate only the conflicting row, and let the rest proceed.**

---

## Step 4 · Execute: send only the differing fields, record into an append-only ledger

```bash
python3 operating_loop.py apply \
    --gate demo/out/steps/2-gate/gate.json \
    --ledger demo/out/steps/ledger.jsonl --out demo/out/steps/3-apply
```

```
{"planned_writes": 4, "recorded_events": 7, "not_written": 12}
  → fictional-adset-a1  LADDER_PROMOTE       sends only {'daily_budget': '20.00'}
  → fictional-adset-a4  TEST_STOP_OVERCOST   sends only {'status': 'PAUSED'}
  → fictional-adset-a6  LADDER_PROMOTE       sends only {'daily_budget': '40.00'}
  → fictional-adset-a8  LINK_OR_TRACKING_BAD sends only {'status': 'PAUSED'}
```

Two details:

- **Only the differing fields.** Not the whole object written back, which would
  rewrite fields the plan never intended to touch.
- **Append-only ledger.** State is derived by folding the event stream, so history is
  never rewritten. A damaged line surfaces as a `corrupt` event instead of vanishing.

> In a live setup, `apply` is where the connector call goes and **nothing else changes**.
> In the offline version it only records the decision.

---

## Step 5 · Reconcile: confirm "sent" became "happened"

```bash
python3 operating_loop.py verify \
    --gate demo/out/steps/2-gate/gate.json \
    --after examples/operating/after-snapshot.json \
    --ledger demo/out/steps/ledger.jsonl --out demo/out/steps/4-verify
```

```
{"checked": 4, "effective": 3, "ineffective": 1}
  ✗ fictional-adset-a6 not effective — read-back does not match the target:
    daily_budget: expected 40.00, read 20.00
```

**This is the step most often skipped and most expensive to skip.** A successful API
response is not a changed field. Read once more and compare; a mismatch is recorded
as **not effective**, and **the row stays open** instead of counting as done and
advancing the stage.

---

## Step 6 · Report: one page, for a human

Steps 1 to 5 assembled → [`expected/report.md`](expected/report.md).

It contains: the one-line conclusion → account signals (including capability gaps) →
per-ad-set judgement detail → the five gate outcomes → the rows needing a human →
write-back reconciliation → settlement reconciliation → structure warnings → the rules.

A report you can send without reformatting it.

---

## Step 7 · Close the loop: back to step 0

```bash
python3 operating_loop.py open --ledger demo/out/steps/ledger.jsonl
```

```
{"open": 1, "rows": [{"object_key": "fictional-adset-a6",
                      "status": "verified_not_effective",
                      "patch": {"daily_budget": "40.00"}}]}
```

The next round **starts by re-verifying what this round did not finish**, then
proposes new actions.

**Without this, actions hang forever** — this is the line between a system and
scattered optimisation: a round says "change the budget", the next round nobody
confirms whether it was changed or whether it helped, so the same list gets rewritten
every time.

The loop closes: **step 0 → … → step 7 → step 0**.

---

## Run it

```bash
python3 demo/run_demo.py            # one pass, prints the report
python3 demo/run_demo.py --steps    # expands the seven steps above (start here)
python3 demo/run_demo.py --check    # verify the committed sample still matches a real run
python3 demo/run_demo.py --refresh  # regenerate demo/expected/ from a real run
```

`--steps` still assembles the full report at the end, so walking through and jumping
to the result give you the same artifact.

### Bring your own accounts and thresholds

```bash
# 1. Shape your collected data like examples/operating/snapshot-primary.json
# 2. Copy the methodology and change the numbers
cp examples/operating/methodology-reference.json my-methodology.json
# 3. Run
python3 operating_loop.py diagnose --snapshot my-snapshot.json \
    --methodology my-methodology.json --out runs/my-round
```

**No unit price, target ROAS or budget multiple is hard-coded.** The action catalogue
travels with the thresholds, so every action always carries its own acceptance and
stop condition.

---

## What is in this folder

| Path | Purpose |
|---|---|
| `README.md` | This file |
| `README.zh-CN.md` | The same walkthrough in Chinese |
| `run_demo.py` | One command; `--steps` expands it; owns generating and drift-checking `expected/` |
| `expected/report.md` | **The report from a real run** — readable without running anything |
| `expected/summary.json` | Deterministic summary of the same run |

The engine stays where the repository conventions put it (`operating_rules.py` and
`operating_loop.py` at the root, fixtures under `examples/operating/`). This folder is
a **presentation layer** and duplicates no logic.

> **Why `expected/` is drift-checked**: a sample that claims more than the code does is
> worse than no sample. CI runs `--check` and fails the moment the two diverge.

---

## What it deliberately does not do

- **No platform connection, no credentials, no account writes.** The output is a
  proposal list for a human, not an executed instruction.
- **No media understanding.** Assets are referenced by declared identity only.
- **No automatic decision.** Every rule emits evidence; the gate and the human stay in the path.
- **No claim that a result generalises.** A rule firing is not proof of a cause, and a
  repaired row is not proof that the repair worked.

Next: the [full operating loop guide](../docs/operating-loop.md) — thresholds, the
complete rules behind the five gate outcomes, the attribution identity, and how to
swap in your own numbers.

Back to the [project home](../README.md).
