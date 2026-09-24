# One operating round, end to end

This folder exists for one reason: to show, in a few minutes and without an
account connection, what this actually decides inside a real operating loop —
and what it refuses to decide.

**Start here: [`expected/report.md`](expected/report.md)** — the output of a real run.

---

## What you would otherwise do by hand

It is 11:50. You have 3 live accounts and 10 ad sets. You:

1. read spend, impressions, clicks and results for each one, and work out cost per
   result, `CTR`, `CVR` and budget utilisation by hand;
2. decide what to scale, what to stop, and what **cannot be judged yet**;
3. remember which rows you already edited, so you do not overwrite yourself;
4. confirm the platform actually applied each change rather than assuming it did;
5. write a one-page report.

The loop does all five, and leaves a readable trace for every step.

## What one run returns

Numbers from [`expected/summary.json`](expected/summary.json), a real run:

| Result | Count | Meaning |
|---|---|---|
| Findings | **16** | across **12 distinct rules** |
| Writable now | **4** | and only the differing fields, never a whole-object rewrite |
| Already satisfied | **1** | the target is in place — writing again is a significant edit that resets learning |
| Conflict, isolated | **1** | a human edited that row while the round was being prepared |
| Unknown, re-pull first | **1** | the pre-write state was not readable; **absent is not equal** |
| Advisory only | **9** | creative and account-level findings that declare no field change |
| Simulated writes | **4** | field-level patches to `daily_budget` and `status` |
| Write-back check | 4 checked → **3 effective / 1 not effective** | catches a write that silently did not land |
| Platform calls | **0** | offline throughout |

### The twelve rules that fired

```
LADDER_PROMOTE       4   healthy stage, promote (budget x2)
TEST_UNDERTESTED     2   sample too small, or cannot spend — record only, do not judge
TEST_STOP_NOCONV     1   zero results past the sample gate and the loss line — pause
TEST_STOP_OVERCOST   1   above the acceptable cost — pause
CREATIVE_BREAKER     1   one creative took ~half the spend at an excessive cost — cut it, not the group
CREATIVE_FATIGUE     1   frequency, CTR and CVR all deteriorated — declare fatigue
CREATIVE_OVERFLOW    1   nine creatives against a cap of eight — trim before scaling
AD_STATUS            1   effective_status is DISAPPROVED — recover the asset, do not toggle status
LINK_OR_TRACKING_BAD 1   declared link validity failed — pause immediately
ACC_STOPPED          1   nothing is configured to run
ACC_NO_DELIVERY      1   configured to run, but no spend today
ACC_BALANCE_LOW      1   balance below the alert line
```

## The three places a real loop actually loses money

Each one is visible in [`expected/report.md`](expected/report.md).

### 1. It refuses to judge a sample too small to judge

`fictional-adset-a2`: $3.10 spent, 180 impressions, zero results.
`fictional-adset-a3`: $15.30 spent, 420 impressions, zero results.

On the numbers alone a2 looks no better. The engine returns:

| Ad set | Verdict | Reason given |
|---|---|---|
| a3 | `TEST_STOP_NOCONV` (P0) | 420 impressions is **past the 300 gate**, and 15.30 is **past the 14.12 loss line** |
| a2 | `TEST_UNDERTESTED` (record only) | 180 impressions is **below the gate** — not enough evidence to call the creative bad |

And `fictional-adset-a5` has a cost per result of $1.60 against a $4.71 target, yet
32% budget utilisation, so the verdict is **"cannot spend — fix delivery first"**
rather than "excellent, scale it".

### 2. It does not believe a write happened

`fictional-adset-a6` was proposed for promotion, budget 20 → 40. The state read
back afterwards still shows **20.00**, so it records:

> **not effective** — the read-back does not match the target: `daily_budget`
> expected 40.00, read 20.00. Treat as not applied; do not advance the stage.

That row **stays open** (`open_rows: 1`) instead of quietly counting as done.

### 3. It does not overwrite you

`fictional-adset-a9` was planned as 10 → 20, but the state read just before
writing shows **30.00** — someone changed it while the round was being prepared.
The engine does not overwrite it and does not restart the batch:

> **conflict** — `daily_budget`: current 30.00 is neither the baseline 10.00 nor
> the target 20.00 ⇒ a human changed it; isolate this row.

The other 15 findings are unaffected. Exactly **2 rows** need a human.

## Run it

```bash
python3 demo/run_demo.py            # run one round and print the report
python3 demo/run_demo.py --check    # verify expected/ still matches a fresh run
python3 demo/run_demo.py --refresh  # regenerate expected/ from a real run
```

Artifacts land in `demo/out/` (gitignored): `findings.json`, `gate.json`,
`application.json`, `reconciliation.json`, a growing `ledger.jsonl`, `report.md`
and `round-summary.json`.

## What is in this folder

| Path | Purpose |
|---|---|
| `README.md` | This file |
| `README.zh-CN.md` | The same walkthrough in Chinese |
| `run_demo.py` | One command, plus generating and drift-checking `expected/` |
| `expected/report.md` | **The report from a real run** — readable without running anything |
| `expected/summary.json` | Deterministic summary of the same run |

The engine itself stays where the repository conventions put it (`operating_rules.py`
and `operating_loop.py` at the root, fixtures under `examples/operating/`). This
folder is a **presentation layer** and duplicates no logic. Its only job is to make
"what can this do" self-evident, and to keep the committed sample honest:
a sample that claims more than the code does is worse than no sample, so CI runs
`--check` and fails on drift.

## What it deliberately does not do

- **No platform connection, no credentials, no account writes.** The output is a
  proposal list for a human, not an executed instruction.
- **No media understanding.** Assets are referenced by declared identity only.
- **No automatic decision.** Every rule emits evidence; the gate and the human stay in the path.
- **No claim that a result generalises.** A rule firing is not proof of a cause, and
  a repaired row is not proof that the repair worked.

Next: the [full operating loop guide](../docs/operating-loop.md) — thresholds, the
five gate outcomes, the attribution identity, and how to swap in your own numbers.

Back to the [project home](../README.md).
