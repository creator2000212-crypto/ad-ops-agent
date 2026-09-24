# Operating loop — a recurring test loop, implemented offline

Everything else in this repository prepares, reviews and connects. This module is
the part an operator actually runs on a schedule: take one settled observation
window, classify every ad set, propose actions with evidence, confirm nothing has
changed underneath you, then record what really happened.

It runs entirely offline. It reads declared JSON, applies declared rules, and
writes reviewable artifacts plus an append-only ledger. It never contacts a
platform.

## Why the loop is longer than "read the numbers"

Three failures account for most of the damage in a recurring test loop, and none
of them is an arithmetic mistake:

| Failure | What it looks like | The guard |
|---|---|---|
| Judging a sample too small to judge | A zero-conversion ad set is killed on $3 of spend | A sample gate that requires both an impression floor and the loss line |
| Treating a failed write as a success | The budget was "raised" but the platform never applied it | Write-back reconciliation against the declared target |
| Overwriting a concurrent human edit | An operator changed the budget while the round was being prepared | A write gate that isolates the conflicting row instead of overwriting it |

The loop therefore has more steps than the arithmetic needs, and each extra step
exists to make one of those failures visible.

## Module map

| File | Responsibility |
|---|---|
| `operating_rules.py` | Pure decision layer. Parses numbers, derives metrics, splits a CPA gap into CPM/CTR/CVR contributions, evaluates creative-level rules, classifies every ad set, and runs the write gate. No file IO except loading a methodology document. |
| `operating_loop.py` | Orchestration and IO. Snapshot validation, account signals, the ledger, the report, and the CLI. |
| `examples/operating/methodology-reference.json` | The thresholds, as data: target ROAS, ladder, sample gate, promotion rule, stop loss, utilisation bands, creative rules, and the action catalogue with each action's acceptance and stop condition. |
| `examples/operating/snapshot-primary.json` | One settled observation window (fictional). |
| `examples/operating/writeback-snapshot.json` | The state read back immediately before writing, including one row a human already changed. |
| `examples/operating/after-snapshot.json` | The state read back after writing, including one write that did not take effect. |
| `examples/operating/settlement-daily.json` | Settlement rows for cross-checking the board against the settlement basis. |
| `tests/test_operating_loop.py` | Executable contracts for every rule and every gate outcome. |
| `scripts/demo_operating_loop.py` | End-to-end demonstration with assertions. |

## The loop, step by step

```
0  re-verify what the previous round proposed        -> open rows in the ledger
1  collect one settled observation window            -> snapshot JSON
2  classify every ad set against the ladder          -> diagnose / decide
3  turn findings into proposals with evidence        -> findings.json
4  pass the write gate before touching anything      -> gate.json
5  record the round in an append-only ledger         -> apply
6  reconcile what was actually written, then report  -> report.md
```

### Target cost and the ladder

`T = unit price x quality factor / target ROAS`. With no deduction the quality
factor is 1, so a 4.00 unit price against an 85% target gives `T = 4.71`. The
ladder is declared as a list; `T`, `2T`, `3T` become multipliers 1, 2 and 3, and
the stop-loss line is declared in multiples of `T` rather than as an absolute
amount. That keeps the thresholds coherent when a unit price changes.

### Metrics

`spend`, `impressions`, `clicks`, `results`, `value` and `frequency` are read from
the snapshot. `CPM`, `CTR`, `CPC`, `CVR`, `CPA`, `ROAS`, `utilisation`, expected
results and the over-cost margin are derived. Every derived value that cannot be
computed is `None` and is reported as missing evidence.

A zero denominator is not a zero metric: nobody clicking out of 1,000 impressions
is a real `CTR` of 0, while `CPC` has no denominator and is therefore `None`. The
engine never substitutes one for the other.

### Cost attribution

`CPA = CPM / (1000 x CTR x CVR)`, so after taking logs the gaps add up:

```
log(CPA / CPA_reference) = dlog(CPM) - dlog(CTR) - dlog(CVR)
```

The three signed terms are reported with their share of the absolute total. That
answers "which stage of the funnel moved the cost" instead of "which number looks
biggest". A non-zero residual means the quoted metrics do not quite satisfy the
identity — usually because they were rounded before publication, which is itself
worth knowing.

### Sample gate

A zero-conversion ad set is only judged dead when **both** the impression floor
and the loss line are crossed. Below the floor it is recorded as under-tested. An
expensive click or an unusually low `CTR` produces an early stop that halts new
spend **without** concluding that the creative is bad — a high `CPC` usually has a
low `CTR` upstream, so the thing to fix is the hook, not the bid.

### Creative rules

* **Circuit breaker** — requires a spend share above the declared limit *and* a
  cost above the declared multiple, and at least two creatives. With a single
  creative "it consumed all the spend" is trivially true and says nothing.
* **Fatigue** — requires frequency, `CTR` decline and `CVR` decline to hold
  together. One or two of them is noise.
* **Overflow** — more creatives than the declared cap, checked before any scale-up.

### Write gate

Five outcomes per proposal. Only `ready` rows may be written, and only for the
fields that actually differ:

| Outcome | Meaning | Action |
|---|---|---|
| `ready` | The field still holds its baseline value | Send only the differing fields |
| `satisfied` | The target value is already in place | Write nothing — writing again is a significant edit that resets learning |
| `conflict` | The field holds neither the baseline nor the target | Isolate this row; do not overwrite, and do not restart the batch |
| `unknown` | The state was not read, or the field is absent from the read | Re-pull first. Absent is not the same as equal |
| `advisory` | The finding declares no field change | Nothing to gate; counted separately so it does not inflate the rows needing attention |

An absent field is deliberately `unknown` rather than writable. A ladder stage
that has no bid amount today is exactly the situation where writing a bid blindly
would be worst.

### Reconciliation

After writing, the state is read again and compared with the declared target. A
mismatch is recorded as **not effective**, and the row stays open. A write that
was sent is not a write that happened.

### Ledger

Append-only JSONL. Proposals, skips and reconciliation events accumulate; state is
derived by folding the stream, so history is never rewritten. A damaged line is
surfaced as a `corrupt` event instead of disappearing, because a silently missing
action is worse than a visibly broken one.

## Running it

```bash
# End-to-end demonstration with assertions
python3 scripts/demo_operating_loop.py

# One round, producing findings / gate / reconciliation / report
python3 operating_loop.py round \
    --snapshot examples/operating/snapshot-primary.json \
    --writeback examples/operating/writeback-snapshot.json \
    --after examples/operating/after-snapshot.json \
    --methodology examples/operating/methodology-reference.json \
    --settlement examples/operating/settlement-daily.json \
    --out runs/operating-demo

# Steps individually
python3 operating_loop.py diagnose --snapshot <snapshot> --methodology <methodology> --out <dir>
python3 operating_loop.py gate     --findings <dir>/findings.json --writeback <writeback> --out <dir>
python3 operating_loop.py apply    --gate <dir>/gate.json --ledger <ledger.jsonl> --out <dir>
python3 operating_loop.py verify   --gate <dir>/gate.json --after <after> --ledger <ledger.jsonl> --out <dir>
python3 operating_loop.py open     --ledger <ledger.jsonl>

# Tests
python3 -m unittest tests.test_operating_loop -v
```

`round` and the sub-commands accept `--at` so a run can be stamped with a fixed
time; without it the wall clock is used and only the ledger timestamps differ.

## Bringing your own thresholds

Copy `examples/operating/methodology-reference.json`, change the numbers, and pass
it with `--methodology`. The action catalogue travels with the thresholds, so an
action always carries its own acceptance and stop condition. Nothing about a unit
price, a target ROAS or a budget multiple is hard-coded in the engine.

## What this module deliberately does not do

* No platform connection, no credentials, no account writes. The output is a
  proposal list for a human, not an executed instruction.
* No media understanding. Assets are referenced by declared identity only.
* No automatic decision. Every rule emits a proposal with evidence; the gate and
  the human remain in the path.
* No claim that one account's result generalises. A rule firing is not proof of a
  cause, and a repaired row is not proof that the repair worked.

## Relationship to the rest of the repository

`knowledge/catalog.json` remains the contextual advisory layer, and the files
under `contracts/` remain design references that are not loaded at runtime. This
module is executable and self-contained: it does not read the contracts and it
does not write to any platform. If a real connector is added later, it replaces
the snapshot files at the edges — the classification, gate and reconciliation
logic does not change.

Return to the [documentation index](index.md).
