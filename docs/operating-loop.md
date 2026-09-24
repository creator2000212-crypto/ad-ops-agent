# Operating loop — a recurring test loop, implemented offline

This page is the technical reference for rules, data dependencies and the CLI.
Start with the [five-step demo](../demo/README.md) for the operator/agent division
of work and sample results; [building from zero](build-from-zero.md) explains the
architecture and build order.

This module reads a window declared as settled and a set of method parameters,
produces proposals with evidence, compares fields in supplied files, and writes
a report and an append-only ledger. It is entirely offline: it does not collect
platform data, submit ad changes, check user authorization or schedule background
runs. Every result depends on the JSON supplied by the caller.

## Why the loop is longer than "read the numbers"

The example demonstrates checks for three types of problem:

| Failure | What it looks like | The guard |
|---|---|---|
| Judging a sample too small to judge | A zero-conversion ad set is killed on $3 of spend | A sample gate that requires both an impression floor and the loss line |
| Treating a target as the actual state | The plan targets a budget of 40, but the supplied after snapshot says 20 | Compare the after snapshot with the target; no write occurs in this example |
| Missing a change in current state | The current field matches neither baseline nor target | Isolate the conflicting row; the difference alone does not identify who changed it |

These checks preserve proposals, state differences and unresolved work
separately for review.

## Module map

| File | Responsibility |
|---|---|
| `operating_rules.py` | Pure decision layer. Parses numbers, derives metrics, splits a CPA gap into CPM/CTR/CVR contributions, evaluates creative-level rules, classifies every ad set, and runs the write gate. No file IO except loading a methodology document. |
| `operating_loop.py` | Orchestration and IO. Snapshot validation, account signals, the ledger, the report, and the CLI. |
| `examples/operating/methodology-reference.json` | The thresholds, as data: target ROAS, ladder, sample gate, promotion rule, stop loss, utilisation bands, creative rules, and the action catalogue with each action's acceptance and stop condition. |
| `examples/operating/snapshot-primary.json` | One settled observation window (fictional). |
| `examples/operating/writeback-snapshot.json` | A separately supplied example of pre-write state, including one row different from its baseline. The program does not fetch it from an account. |
| `examples/operating/after-snapshot.json` | A separately supplied after-state example in which one planned object does not match its target; it is not produced by `apply`. |
| `examples/operating/settlement-daily.json` | Settlement rows for cross-checking the board against the settlement basis. |
| `tests/test_operating_loop.py` | Executable contracts for every rule and every gate outcome. |
| `scripts/demo_operating_loop.py` | End-to-end demonstration with assertions. |

## The demo's five steps and their data dependencies

```
1  diagnose: observation snapshot + method         -> findings.json
2  gate: findings + supplied pre-write state       -> gate.json / difference plan
3  apply: gate                                    -> application.json / ledger events
4  verify: gate + supplied after state + ledger    -> reconciliation.json / ledger events
5  open: read the ledger                          -> unresolved rows; round also produces report.md
```

`apply` only records proposed field changes. `verify` compares the supplied after
snapshot without fetching platform data. `round` runs the computations and
recording stages in sequence, then produces the report and open-row count; it
does not recheck the previous round at startup or automatically retry rows from
`open`. The optional settlement file supplies settlement figures and basis notes
for the report; it does not automatically explain data discrepancies.

The fixture contains three Meta accounts and ten ad sets, producing sixteen
account/ad-set/creative findings. Four enter the difference plan; three match
the after snapshot and one does not. `ready` is not authorization, and a matching
snapshot is not proof of a successful live change.

### Target cost and the ladder

`T = unit price x quality factor / target ROAS`. With no deduction the quality
factor is 1, so a 4.00 unit price against an 85% target gives `T = 4.71`. The
ladder is declared as a list; `T`, `2T`, `3T` become multipliers 1, 2 and 3, and
the stop-loss line is declared in multiples of `T` rather than as an absolute
amount. A changed unit price therefore recalculates target cost and its related
stop-loss thresholds.

### Metrics

`spend`, `impressions`, `clicks`, `results`, `value` and `frequency` are read from
the snapshot. `CPM`, `CTR`, `CPC`, `CVR`, `CPA`, `ROAS`, `utilisation`, expected
results and the over-cost margin are derived. Every derived value that cannot be
computed is `None` and is reported as missing evidence.

A zero denominator is not a zero metric: nobody clicking out of 1,000 impressions
is a real `CTR` of 0, while `CPC` has no denominator and is therefore `None`. The
engine never substitutes one for the other.

### Cost-gap decomposition

`CPA = CPM / (1000 x CTR x CVR)`, so after taking logs the gaps add up:

```
log(CPA / CPA_reference) = dlog(CPM) - dlog(CTR) - dlog(CVR)
```

For positive metrics with comparable definitions, the three signed terms
describe the mathematical relationship between the CPA gap and changes in CPM,
CTR and CVR. Each term's share of the absolute total is also reported. **This is
not causal attribution or proof that changing a metric will improve results.**
A non-zero residual means the inputs do not exactly satisfy the identity; check
precision, observation windows and metric definitions. The program does not
establish the cause of the discrepancy.

### Sample gate

The zero-conversion branch produces `TEST_STOP_NOCONV` only when **both** the
impression floor and the loss line are met. Otherwise, it checks the declared
CPC/CTR early-stop thresholds and proposes a pause if they trigger, without
concluding that a creative is invalid; otherwise it returns `TEST_UNDERTESTED`.
None of these proposals stops account spending by itself.

The sample gate is not the first step for every rule. Account signals are
independent. Per ad set, creative findings come first, followed by disapproval,
link/tracking problems and missing required metrics. For ad sets with results,
the classifier checks excess-cost stop loss, the minimum result count,
utilisation and then promotion conditions. See `decide_account` and
`_classify_adset`; insufficient samples do not stop all other rules from running.

### Creative rules

* **Circuit-breaker finding** — requires a spend share above the declared limit
  *and* a cost above the declared multiple, with at least two creatives. A
  single-creative group does not trigger this rule but still has ad-set checks.
* **Fatigue finding** — requires frequency, `CTR` decline and `CVR` decline to
  meet their conditions together. Not triggering it does not prove that a
  creative has no problem.
* **Overflow finding** — records a proposal when creative count exceeds the
  declared cap.

Creative and ad-set proposals are generated separately. Creative findings do not
automatically block promotion; fixture a6 has both creative findings and a
promotion candidate.

### Write gate

There are five outcomes per proposal. **Only `ready` rows enter the difference
plan; this is neither user authorization nor an execution receipt.**

| Outcome | Meaning | Action |
|---|---|---|
| `ready` | The implemented field comparison passes and differences remain | Add those fields to the review plan; this module does not submit them |
| `satisfied` | Supplied current state already matches the target | Do not propose a duplicate change; the program does not determine learning-phase effects |
| `conflict` | The current field matches neither baseline nor target | Isolate the row and investigate the difference without inferring its author |
| `unknown` | The supplied state lacks the object or a target field | Obtain current state before proceeding; absence does not mean equality |
| `advisory` | The finding declares no field change | Nothing to gate; counted separately so it does not inflate the rows needing attention |

In the fixture, the `ready` rows match their declared baselines. The general
function can also return `ready` when the baseline is `None`, so this label does
not replace complete baseline, authorization or platform-capability checks.

### After-snapshot comparison

`verify` compares targets from `ready` rows with the `--after` file. An object
present in that file counts as `checked`; all target fields matching means
`effective`, while differences mean a mismatch. An absent object is not counted
as checked. Here `effective` is a snapshot comparison, not proof of a submitted
request, live delivery or business impact. Fixture a6 targets a budget of 40,
while its after-state value is 20.

### Ledger

Append-only JSONL preserves proposals, skips and reconciliation events; current
state is obtained by folding the stream. `open` lists only `pending_write` and
`verified_not_effective`. It does not recheck, retry or schedule another round.
`conflict` and `unknown` are recorded as `skipped` and are not included in `open`;
`advisory` produces no action event. The fixture's one open row is a6. The two
separate rows needing human review are the a9 conflict and missing b1 snapshot.

`read_events` returns a `corrupt` record for a damaged JSON line, but `open` is
not a complete event list or corruption report.

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

Only `round`, `apply` and `verify` accept optional `--at`, which sets timestamps
in events and application/reconciliation artifacts; omission uses the current
time. `diagnose`, `gate` and `open` do not accept it. It does not change the
observation date inside the input snapshot. `round` also accepts optional
`--settlement` and `--ledger`; without `--ledger`, it uses `ledger.jsonl` in the
output directory.

## Bringing your own thresholds

Copy `examples/operating/methodology-reference.json`, change the numbers, and pass
it with `--methodology`. The action catalogue supplies acceptance and stop
descriptions; those descriptions are not separate authorization checks.
Configuration changes cover implemented parameters, not Python branch order or
new platform actions. Defaults still exist, such as a `quality_factor` of 1
when omitted; not every behavior is defined by the supplied configuration.

## What this module deliberately does not do

* No platform connection, no credentials, no account writes. The output is a
  proposal list for a human, not an executed instruction.
* No media understanding. Assets are referenced by declared identity only.
* No automatic account operations. Rules classify inputs and generate proposals,
  but this module has no user-approval, publishing or background scheduler implementation.
* No claim that one account's result generalises. A rule firing is not proof of a
  cause, and a repaired row is not proof that the repair worked.

## Relationship to the rest of the repository

`knowledge/catalog.json` remains the contextual advisory layer, and the files
under `contracts/` remain design references that are not loaded at runtime. This
module is executable and self-contained: it does not read the contracts and it
does not write to any platform. Live integration needs a separately designed
process for metric definitions, object mapping, permissions, authorization,
submission and readback, followed by validation of the applicable rules.
Replacing file inputs with a connector does not complete a live deployment.

Return to the [documentation index](index.md).
