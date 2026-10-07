# Operating loop — the 12-hour check, implemented offline

This page is the technical reference for the rules, data dependencies and CLI.
Start with the [worked example](../demo/README.md) for sample results;
[building from zero](build-from-zero.md) explains the architecture and build order,
and the [decision matrix](decision-matrix.md) lists every code with its trigger,
action, response window, acceptance and stop condition.

The rules are ported from the read-only 12-hour check I ran as a scheduled
WorkBuddy (Tencent's desktop AI agent; not affiliated) job on live Meta and TikTok
lead-gen accounts (Sep 22–26, 2026). Builds ran interactively: create paused →
field-by-field readback → activate. This repo is the offline, tested version.

**Scope:** the module is offline by design. It reads JSON files, makes 0 platform
calls, and writes proposals, a report and an append-only ledger. `ready` means a
difference passed the state check, not that anyone approved it; a matching after
snapshot is a file comparison, not proof of a live change.

## What each guard prevents

| Failure | What it looks like | The guard |
|---|---|---|
| Judging a sample too small to judge | A zero-lead ad set is killed after a few dollars | Sample gate: an impression floor **and** the stop-loss line must both be met |
| Scaling while something else is broken | Budget doubles on an ad set whose creative just tripped the breaker | Rule precedence: `LADDER_HOLD` replaces the promotion; one change per ad set per round |
| Acting on numbers the settlement does not confirm | Platform CPA looks cheap, but the settlement approves half the leads | Platform vs settlement: `RECON_GAP` / `RECON_TZ` / `RECON_WINDOW` make promotions and over-cost pauses advisory |
| Filling a missing side with zero | An account absent from the settlement is reported as 0 spend | `RECON_SCOPE`: the missing side is shown as missing |
| Writing a field the plan should never touch | A proposal targets a field outside its object type | `WRITABLE_FIELDS`: the gate raises `RuleError` and the round stops |
| Overwriting someone's change | The current budget matches neither baseline nor target | `conflict`: the row is isolated; the values alone do not identify who changed it |
| Treating a target as the actual state | The plan sets a budget of 40, the after snapshot still says 20 | Readback comparison: the row stays open as `verified_not_effective` |
| Reading "no ledger" as "nothing open" | A typo in the ledger path reports `open: 0` | A missing ledger raises `LoopError` (exit code 2) |

## Module map

| File | Responsibility |
|---|---|
| `operating_rules.py` | Pure decision layer. Parses numbers as `Decimal`, derives metrics, decomposes CPA changes into CPM/CTR/CVR terms, evaluates creative rules, classifies every ad set, applies rule precedence, reconciles platform totals with the settlement and runs the write gate. Holds the English and Chinese message tables. No file IO except loading a methodology document. |
| `operating_loop.py` | Orchestration and IO: snapshot validation, account signals, the ledger, the report and the CLI. |
| `examples/operating/methodology-reference.json` | Thresholds and economics as data: target ROAS, lead approval rate, ladder, sample gate, promotion rule, stop loss, utilisation bands, creative rules, balance alert, creative cap, reconciliation tolerances, and the action catalogue with each action's English text, trigger, acceptance and stop condition. |
| `examples/operating/snapshot-primary.json` | One settled observation window: 3 fictional Meta accounts and 1 TikTok account, 14 ad sets and ad groups, prior windows on a1, a4, a10 and d1. |
| `examples/operating/writeback-snapshot.json` | The supplied pre-write state: a9's budget was hand-edited to 30, and b2 is missing. |
| `examples/operating/after-snapshot.json` | The supplied after state: a10 still reads its old budget. It is not produced by `apply`. |
| `examples/operating/settlement-daily.json` | Settlement rows for the same day: A reconciles, B is in another time zone, C is deliberately outside the settlement, D's leads are mostly rejected, E exists only in the settlement. |
| `scripts/render_decision_matrix.py` | Renders [decision-matrix.md](decision-matrix.md) from the methodology and the engine's own code table; `--check` fails when the page is stale. |
| `tests/test_operating_loop.py` | Executable contracts for every rule, every gate state, both languages and every fix. |
| `tests/test_reconciliation.py` | Contracts for the five settlement statuses and the downgrade. |
| `scripts/demo_operating_loop.py` | End-to-end run with assertions (two rounds on one ledger, plus the same round in Chinese). |

## The five steps and their data

```
1  diagnose: snapshot + methodology (+ settlement)  -> findings.json
2  gate: findings + pre-write state                 -> gate.json / difference plan
3  apply: gate                                      -> application.json / ledger events
4  verify: gate + after state + ledger              -> reconciliation.json / ledger events
5  open: read the ledger                            -> unresolved rows; round also writes report.md
```

`diagnose` classifies every ad set and, when a settlement file is supplied, checks
each account against it before anything reaches the gate. `apply` records proposed
field changes; `verify` compares them with the supplied after snapshot. `round`
runs all steps in sequence and writes the report; it does not re-check the
previous round at startup or retry rows from `open`.

The fixture produces 20 account, ad-set and creative findings. Four enter the
difference plan (a1, a4, a8, a10); three match the after snapshot and a10 does not.
d1 would be a fifth, but account D does not reconcile with the settlement, so it
stays advisory.

### Language

Every command takes `--lang en|zh-CN` (default `en`). It changes the report,
gate labels, evidence sentences, ledger reasons and the action texts taken from
the methodology (`en` object per action; the base fields otherwise). Evidence is
generated per code from the numbers in either language. Codes, gate states and
write plans do not depend on the language: `demo/run_demo.py --check` fails if
the two languages reach different decisions. Error messages are in English.

### Target cost and the ladder

`T = value per lead x lead approval rate / target ROAS`. In the methodology these
are `offer.unit_price` (per account), `quality_factor` and `target_roas`. The
reference uses a 10.00 lead, a 0.90 approval rate and a 1.25 target, so
`T = 10.00 x 0.90 / 1.25 = 7.20`; account B's 8.00 lead gives `T = 5.76` and
account D's 12.00 lead `T = 8.64`. T must stay below the value of a lead,
otherwise every lead at target cost loses money. All prices are fictional; the
structure and thresholds are the ones I used.

The ladder is declared as a list; `T`, `2T`, `3T` become multipliers 1, 2 and 3,
and the stop-loss line is declared in multiples of `T` (3T = 21.60 for account A).
A changed price or approval rate therefore recalculates T and every threshold
derived from it.

### Metrics

`spend`, `impressions`, `clicks`, `results`, `value` and `frequency` are read from
the snapshot. `CPM`, `CTR`, `CPC`, `CVR`, `CPA`, `ROAS`, utilisation, expected
results and the over-cost margin are derived. A value that cannot be computed is
`None` and is reported as missing evidence.

A zero denominator is not a zero metric: nobody clicking out of 1,000 impressions
is a real `CTR` of 0, while `CPC` has no denominator and is therefore `None`.

### Platform vs settlement

`reconcile_settlement(snapshot, settlement, methodology)` joins each account's
platform totals (the sum of its ad-set rows) with the settlement row for the same
account and date. Settled leads are compared with platform leads × `quality_factor`,
because the settlement only pays approved leads; settled CPA is compared with the
settled target `T / quality_factor` (value per lead / target ROAS), not with T.

Each account gets the first status that applies:

| Status | When | Effect (reference policy) |
|---|---|---|
| `RECON_SCOPE` | The account is on one side only | Reported; the missing side stays missing, never zero |
| `RECON_WINDOW` | The settlement has the account, but not for the observation date | Promotions and over-cost pauses become advisory |
| `RECON_TZ` | Account and settlement time zones differ, or one is not declared | Same |
| `RECON_GAP` | Spend or settled leads outside tolerance, a different unit price, or incomplete totals | Same |
| `RECON_OK` | Within tolerance | Decisions stand |

Tolerances (`spend_tolerance_pct`, `results_tolerance_pct`), the statuses that
downgrade (`downgrade_on`) and the codes they downgrade (`downgrade_codes`) live in
the methodology's `reconciliation` block; there is no code default. A downgraded
proposal keeps its code and evidence, loses its write intent and carries
`downgraded: {status, detail}`, so the gate reports it as advisory. The report's
"Platform vs settlement" table shows spend, leads, CPA and target on both sides.

In the fixture: A reconciles (spend −0.1%, 19 settled leads against 18.9
expected), B is `RECON_TZ` (Etc/GMT+5 against Etc/GMT), C is outside the
settlement, D is `RECON_GAP` (3 of 7 leads approved against 6.3 expected) and E
appears only in the settlement. The block exists because of a real scope problem:
on Sep 20, 2026 the daily sheet, pulled from every connected account, ran about
20% above the settlement export until it was scoped to the accounts the
settlement covers (about 0.1% on the checked day).

### Why CPA moved

`CPA = CPM / (1000 x CTR x CVR)`, so after taking logs the changes add up:

```
log(CPA / CPA_prior) = dlog(CPM) - dlog(CTR) - dlog(CVR)
```

`cpa_driver_decomposition(reference, observed)` (still importable as
`attribution`) returns each term's signed contribution, its share of the absolute
total, the main driver and the residual. An ad set opts in with a `prior_window`
object (`date`, `cpm`, `ctr`, `cvr`, `cpa`); the current values are derived from
the snapshot. The report's "Why CPA moved" section shows the terms in log-points
(100 × change in the natural log). A missing or non-positive input leaves the row
visibly "not decomposed" (a10 in the fixture). It is an accounting identity, not a
causal claim; a non-zero residual means the quoted prior CPA does not exactly
satisfy the identity (rounding, different windows or definitions).

### Classification order

Account signals come first: no configured ad set (`ACC_STOPPED`), zero spend today
with configured ad sets (`ACC_NO_DELIVERY`) and a balance at or below
`balance_alert_below` (`ACC_BALANCE_LOW`). Then, per ad set:

1. Creative findings (breaker, fatigue, overflow).
2. Disapproval (`AD_STATUS`) and link/tracking failure (`LINK_OR_TRACKING_BAD`) end the ad set's evaluation.
3. Missing spend, impressions or results block the ad set; nothing is guessed.
4. Zero leads: `TEST_STOP_NOCONV` only when the impression floor **and** the stop-loss line are met; otherwise the declared CPC/CTR early-stop thresholds (`TEST_EARLY_STOP`, pause and review the hook); otherwise `TEST_UNDERTESTED`.
5. With leads: over-cost stop loss, then the minimum lead count, then utilisation (limited delivery), then promotion.

Then the account's settlement status may downgrade promotions and over-cost
pauses. See `decide_account`, `_classify_adset` and `downgrade_unreconciled`.

### Rule precedence: hold before promote

A promotion that met its numbers is replaced by advisory `LADDER_HOLD` when the
same ad set has `CREATIVE_BREAKER`, `CREATIVE_OVERFLOW` or a `name_mismatch`
structure finding, or when its account has any P0 `ACC_*` finding. The evidence
names every blocker. Fix the creative, structure or account problem first; the
budget stays unchanged this round, and the next round re-evaluates from scratch.
One change per ad set per round keeps cause and effect readable. Fatigue alone
does not block a promotion. In the fixture, a6 is held by its creative breaker and
b1 by its creative count and account B's two P0 findings.

### Creative rules

* **Circuit breaker** (`CREATIVE_BREAKER`, object type `creative`) — spend share
  above the declared limit *and* CPA above the declared multiple of T, with at
  least two creatives in the ad set.
* **Fatigue** (`CREATIVE_FATIGUE`, object type `creative`) — frequency, CTR decline
  and CVR decline must all meet their thresholds together.
* **Overflow** (`CREATIVE_OVERFLOW`, object type `adset`) — more creatives than
  `max_creatives_per_adset`.

Creative findings carry the creative as `object_key` and the ad set as
`parent_key`, so the report keeps them on their ad set's row.

### Write gate: five states

**Only `ready` rows enter the difference plan.**

| State | Meaning | Action |
|---|---|---|
| `ready` | Each differing field still holds its baseline value | Add only those fields to the plan for review |
| `satisfied` | The current state already equals the target | Write nothing; a repeated write only adds risk and noise |
| `conflict` | A current field matches neither baseline nor target | Isolate the row and find the source of the change |
| `unknown` | The object or a target field is missing from the read, or a differing field has no concrete baseline | Re-read state or recover the plan's baseline; absence never means equality |
| `advisory` | The finding declares no field change, or was downgraded as measurement unreconciled | Nothing to gate; counted separately |

Before any comparison, every target field must be allowed for the proposal's
`object_type` by `WRITABLE_FIELDS`: `adset` may change `daily_budget`, `status`,
`bid_strategy` and `bid_amount`; `creative` may change `status`; `account` may
change nothing. A field outside the table raises `RuleError` and stops the round;
it is a malformed plan, not a sixth state.

A field already at its target needs no baseline because it will not be changed.
Every other field needs a concrete baseline; a missing field and an explicit
`null` both produce `unknown`. Numeric `0` is a concrete value. Values are compared
as `Decimal` (`10`, `10.0` and `'10.00'` match); a boolean never equals a number.
One unknown field holds the whole proposal; other proposals are checked
independently. Recover a missing baseline from the original plan rather than
filling it with a fresh current value.

### After-snapshot comparison

`verify` compares the targets of `ready` rows with the `--after` file. An object
present in that file counts as `checked`; all target fields matching means
`effective`, anything else a mismatch. An absent object is not counted as checked.
In the fixture, a10 targets a budget of 40 and the after snapshot still reads 20.

### Ledger

Append-only JSONL keeps proposals, skips and reconciliation events; the current
state of each row is folded from the stream. `open` lists `pending_write` and
`verified_not_effective` rows. `conflict` and `unknown` are recorded as `skipped`
and are not in `open`, so hand over both lists: in the fixture, the one open row
is a10, and the two rows needing a human are the a9 conflict and the missing b2
state.

`apply` creates the ledger even when it records no event. `read_events`, `open`
and `verify` raise `LoopError` on a missing ledger path instead of reporting an
empty history. A damaged JSON line becomes a `corrupt` record rather than
disappearing.

## Running it

```bash
# The demo: English report by default, --lang zh-CN for Chinese
python3 demo/run_demo.py
python3 demo/run_demo.py --check          # both languages against demo/expected/, with a diff on change

# End-to-end run with assertions
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
python3 operating_loop.py diagnose --snapshot <snapshot> --methodology <methodology> [--settlement <settlement>] --out <dir>
python3 operating_loop.py gate     --findings <dir>/findings.json --writeback <writeback> --out <dir>
python3 operating_loop.py apply    --gate <dir>/gate.json --ledger <ledger.jsonl> --out <dir>
python3 operating_loop.py verify   --gate <dir>/gate.json --after <after> --ledger <ledger.jsonl> --out <dir>
python3 operating_loop.py open     --ledger <ledger.jsonl>

# The decision matrix
python3 scripts/render_decision_matrix.py           # rewrite docs/decision-matrix.md
python3 scripts/render_decision_matrix.py --check   # fail with a diff if it is stale

# Tests
python3 -m unittest tests.test_operating_loop tests.test_reconciliation -v
```

`round`, `apply` and `verify` accept `--at` to pin event timestamps (default: now);
it does not change the observation date in the snapshot. `round` also accepts
`--settlement` and `--ledger`; without `--ledger` it uses `ledger.jsonl` in the
output directory. Every command accepts `--lang`. Blocked input exits with code 2
and a JSON error on stderr.

## Bringing your own thresholds

Copy `examples/operating/methodology-reference.json`, change the numbers and pass
it with `--methodology`. Thresholds come only from that document:
`balance_alert_below` and `max_creatives_per_adset` are required, and a missing
one is rejected rather than replaced by a code default. The `reconciliation` block
is required once you pass `--settlement`. The one optional value is
`quality_factor`, which means "no deduction" (1) when omitted and must lie in
(0, 1] when present.

The action catalogue must declare every code the engine emits. An action's
`implemented` flag must agree with the engine (`true` for the codes in
`ENGINE_CODES`, `false` for playbook actions the engine never evaluates), and an
optional `en` object holds the English `action`, `window`, `acceptance`,
`stop_condition` and the `trigger` template used by the decision matrix. Keys the
engine does not read are marked `"implemented": false`. Configuration changes
parameters, not the branch order or the set of writable fields.

## Boundaries

* No platform connection, credentials or account writes; the output is a list for
  a human to review.
* No media understanding; creatives are referenced by declared identity.
* A rule firing is evidence for a decision, not proof of a cause.

Live use needs its own reads, object mapping, permissions, approval, submission
and readback; in my live runs those went through WorkBuddy's connectors under my
approval. `knowledge/catalog.json` stays the advisory layer, and `contracts/` stays
a design reference that is not loaded at runtime.

Return to the [documentation index](index.md).
