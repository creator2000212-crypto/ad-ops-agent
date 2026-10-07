# 12-hour check · demo-20260924-1150

> OFFLINE ANALYSIS ONLY — no ad platform is contacted, no account is written and no media is uploaded. The action list is a proposal for human review, not an executed instruction.

**Data as of:** 2026-09-24T11:50:00+08:00 · **Method:** reference-1n1-ladder v2026-10-07.2 · **Snapshot hash:** `52ff73b9f09b`

**Observation window:** 2026-09-23 (settled_day; full delivery day: yes) — Calendar-day buckets. Hourly detail is not available through this connection, so the decision window is one calendar day; the approximation is stated here.

## This round

- Diagnosis produced **20 findings** across accounts, ad sets and creatives. One object can trigger several rules, so this is not 20 objects; all 14 ad sets are listed under "Decisions by ad set".
- **4 rows are `ready`**: each change passed the current-state check and is ready for review. `ready` is not approval to act.
- `apply` recorded **4 planned changes / 4 fields** in the local ledger; nothing was sent to a platform.
- Against the supplied `after` snapshot: **3 matched, 1 did not match**.
- Platform vs settlement: RECON_SCOPE 2 · RECON_TZ 1 · RECON_GAP 1 · RECON_OK 1. Cost-based proposals held as advisory until the numbers reconcile: **1**.

## Handle these first

**Gate rows that need a human: 2** (`gate.json`):

- `fictional-adset-a9` · LADDER_PROMOTE · **Conflict (isolated)** — daily_budget: current value 30.00 matches neither baseline 20.00 nor target 40.00 ⇒ isolate the row, hold the change and check where the difference came from.
- `fictional-adset-b2` · TEST_EARLY_STOP · **Unknown** — The pre-write read has no record of 'fictional-adset-b2' ⇒ re-read first; never write blind.

**After-snapshot mismatches: 1** (`reconciliation.json`):

- `fictional-adset-a10` · LADDER_PROMOTE — After snapshot differs from the target ⇒ treat as not in effect; do not move to the next step as if it ran: daily_budget: expected 40.00, read 20.00

**Measurement unreconciled: 1** (`findings.json`, see "Platform vs settlement"):

- `fictional-adgroup-d1` · LADDER_PROMOTE · RECON_GAP — Settlement approved 3 of 7 leads; expected 6.3 at the declared approval rate 0.90 (-52.4%, tolerance ±20.0%). Advisory until platform and settlement agree; no budget or status change this round.

`open` lists only ledger rows that await comparison or failed it. **Gate conflicts and missing state are not in `open`, so it is not the whole to-do list**; hand over every list above.

## Account signals

| Account | Platform | Offer | Value per lead | Configured live | Able to deliver | Ad sets | Today's spend | Balance | Spend cap | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| `fictional-meta-account-a` | meta | fictional-offer-alpha | 10.00 | 10 | 9 | 10 | 28.40 | 820.00 | 6000.00 | 1 ad set(s) configured live but unable to deliver |
| `fictional-meta-account-b` | meta | fictional-offer-beta | 8.00 | 2 | 2 | 2 | 0.00 | 41.20 | — | spend_cap reads back null; the headroom alert is unavailable |
| `fictional-meta-account-c` | meta | fictional-offer-gamma | 10.00 | 0 | 0 | 0 | 0.00 | 300.00 | 2000.00 | — |
| `fictional-tiktok-account-d` | tiktok | fictional-offer-delta | 12.00 | 2 | 2 | 2 | 17.80 | 640.00 | 3000.00 | — |

## Platform vs settlement

Settlement date 2026-09-23 · time zone Etc/GMT · currency USD · tolerance: spend ±2.0%, settled leads ±20.0% of platform leads × approval rate 0.90 · target ROAS 1.25

| Account | Spend: platform → settled | Leads: platform → settled (expected) | CPA: platform / settled | T / settled target | Settled ROAS | Status |
|---|---|---|---|---|---|---|
| `fictional-meta-account-a` | 176.30 → 176.12 (-0.1%) | 21 → 19 (18.9, +0.5%) | 8.40 / 9.27 | 7.20 / 8.00 | 1.0788 | **RECON_OK** |
| `fictional-meta-account-b` | 24.70 → 22.90 (-7.3%) | 3 → 3 (2.7, +11.1%) | 8.23 / 7.63 | 5.76 / 6.40 | 1.0480 | **RECON_TZ** |
| `fictional-meta-account-c` | — → — | — → — | — / — | 7.20 / 8.00 | — | **RECON_SCOPE** |
| `fictional-tiktok-account-d` | 29.40 → 29.40 (+0.0%) | 7 → 3 (6.3, -52.4%) | 4.20 / 9.80 | 8.64 / 9.60 | 1.2245 | **RECON_GAP** |
| `fictional-meta-account-e` | — → 12.50 | — → 1 | — / 12.50 | — / — | — | **RECON_SCOPE** |

- `fictional-meta-account-b` · RECON_TZ — Account time zone Etc/GMT+5 differs from settlement time zone Etc/GMT; the day buckets differ, so the gap cannot be read. Align time zones first.
- `fictional-meta-account-c` · RECON_SCOPE — In the snapshot but not in the settlement export: outside the settlement's scope; reported as missing, not as zero.
- `fictional-tiktok-account-d` · RECON_GAP — Settlement approved 3 of 7 leads; expected 6.3 at the declared approval rate 0.90 (-52.4%, tolerance ±20.0%).
- `fictional-meta-account-e` · RECON_SCOPE — In the settlement export but not returned by the platform pull: the platform side is missing, not zero; re-pull before reading totals.

Settled CPA is spend per approved lead, so it is compared with the settled target, T ÷ approval rate (value per lead ÷ target ROAS), not with T. A row that exists on one side only is shown as missing, never as zero. In accounts with RECON_GAP or RECON_TZ or RECON_WINDOW, LADDER_PROMOTE or TEST_STOP_OVERCOST become advisory ("measurement unreconciled").

## Decisions by ad set

| Ad set | Stage | Spend | Impr. | Leads | CPA | T | Stop line | Utilisation | Rules fired |
|---|---|---|---|---|---|---|---|---|---|
| `fictional-adset-a1` | T | 19.80 | 4600 | 3 | 6.60 | 7.20 | 21.60 | 99.0% | LADDER_PROMOTE(P1) |
| `fictional-adset-a2` | T | 4.60 | 210 | 0 | — | 7.20 | 21.60 | 46.0% | TEST_UNDERTESTED(P2) |
| `fictional-adset-a3` | T | 22.40 | 640 | 0 | — | 7.20 | 21.60 | 112.0% | TEST_STOP_NOCONV(P0) |
| `fictional-adset-a4` | 2T | 40.00 | 9300 | 2 | 20.00 | 7.20 | 21.60 | 100.0% | TEST_STOP_OVERCOST(P0) |
| `fictional-adset-a5` | T | 8.40 | 1900 | 3 | 2.80 | 7.20 | 21.60 | 42.0% | TEST_UNDERTESTED(P2) |
| `fictional-adset-a6` | T | 21.00 | 4900 | 4 | 5.25 | 7.20 | 21.60 | 105.0% | CREATIVE_BREAKER(P1); CREATIVE_FATIGUE(P2); LADDER_HOLD(P2) |
| `fictional-adset-a7` | T | 6.10 | 1100 | 0 | — | 7.20 | 21.60 | 30.5% | AD_STATUS(P0) |
| `fictional-adset-a8` | T | 14.20 | 2700 | 2 | 7.10 | 7.20 | 21.60 | 71.0% | LINK_OR_TRACKING_BAD(P0) |
| `fictional-adset-a9` | T | 19.20 | 4300 | 3 | 6.40 | 7.20 | 21.60 | 96.0% | LADDER_PROMOTE(P1) |
| `fictional-adset-a10` | T | 20.60 | 4800 | 4 | 5.15 | 7.20 | 21.60 | 103.0% | LADDER_PROMOTE(P1) |
| `fictional-adset-b1` | T | 15.60 | 3700 | 3 | 5.20 | 5.76 | 17.28 | 78.0% | CREATIVE_OVERFLOW(P2); LADDER_HOLD(P2) |
| `fictional-adset-b2` | T | 9.10 | 190 | 0 | — | 5.76 | 17.28 | 45.5% | TEST_EARLY_STOP(P1) |
| `fictional-adgroup-d1` | T | 19.60 | 5800 | 5 | 3.92 | 8.64 | 25.92 | 98.0% | LADDER_PROMOTE(P1, advisory: measurement unreconciled) |
| `fictional-adgroup-d2` | T | 9.80 | 2600 | 2 | 4.90 | 8.64 | 25.92 | 49.0% | TEST_UNDERTESTED(P2) |

## Why CPA moved

CPA = CPM ÷ (1000 × CTR × CVR), so the change in log CPA splits exactly into a CPM, a CTR and a CVR term. Each cell is that term in log-points (100 × change in the natural log; negative pushed CPA down) and its share of the total movement. The residual is what the quoted prior CPA leaves unexplained (rounding). It is an accounting identity, not a cause.

| Ad set | Prior window | CPA: prior → now | Δ log CPA | CPM | CTR | CVR | Residual | Main driver |
|---|---|---|---|---|---|---|---|---|
| `fictional-adset-a1` | 2026-09-22 | 7.03 → 6.60 | -6.3 | +2.5 (22%) | -6.7 (60%) | -2.0 (18%) | -0.1 | **CTR** |
| `fictional-adset-a4` | 2026-09-22 | 5.41 → 20.00 | +130.8 | +9.8 (7%) | +3.2 (2%) | +117.7 (90%) | +0.1 | **CVR** |
| `fictional-adset-a10` | 2026-09-22 | 5.38 → 5.15 | — | — | — | — | — | not decomposed: prior CVR missing |
| `fictional-adgroup-d1` | 2026-09-22 | 7.21 → 3.92 | -60.9 | +3.9 (5%) | +2.5 (3%) | -67.3 (91%) | -0.1 | **CVR** |

Read the largest share first: CVR points after the click (destination, form, lead quality), CTR to the hook, CPM to the auction.

## Gate results and recorded difference plan

| Result | Rows | Meaning |
|---|---|---|
| Ready for review (`ready`) | 4 | Current value equals the baseline; only differing fields are listed; not yet approved |
| Satisfied | 1 | Target already in place; skipped |
| Conflict (isolated) | 1 | State matches neither baseline nor target; the values do not say who changed it; isolate and confirm |
| Unknown | 1 | Pre-write state not read, a field missing or no usable baseline; re-read first |
| Advisory | 13 | No field change declared, or downgraded; nothing to gate |

Fields `apply` recorded. They are planned, not submitted:

| Object | Rule | Planned fields |
|---|---|---|
| `fictional-adset-a1` | LADDER_PROMOTE | `daily_budget` → 40.00 |
| `fictional-adset-a4` | TEST_STOP_OVERCOST | `status` → PAUSED |
| `fictional-adset-a8` | LINK_OR_TRACKING_BAD | `status` → PAUSED |
| `fictional-adset-a10` | LADDER_PROMOTE | `daily_budget` → 40.00 |

Advisory (13 rows, no field change, not gated): `fictional-adset-a2`·TEST_UNDERTESTED, `fictional-adset-a5`·TEST_UNDERTESTED, `a6-c1`·CREATIVE_BREAKER, `a6-c2`·CREATIVE_FATIGUE, `fictional-adset-a6`·LADDER_HOLD, `fictional-adset-a7`·AD_STATUS, `fictional-meta-account-b`·ACC_NO_DELIVERY, `fictional-meta-account-b`·ACC_BALANCE_LOW, `fictional-adset-b1`·CREATIVE_OVERFLOW, `fictional-adset-b1`·LADDER_HOLD, `fictional-meta-account-c`·ACC_STOPPED, `fictional-adgroup-d1`·LADDER_PROMOTE, `fictional-adgroup-d2`·TEST_UNDERTESTED

## After-snapshot comparison

Targets compared with the supplied after file; no platform write happens here.

| Object | Rule | Matches | Detail |
|---|---|---|---|
| `fictional-adset-a1` | LADDER_PROMOTE | Yes | After snapshot matches the target. |
| `fictional-adset-a4` | TEST_STOP_OVERCOST | Yes | After snapshot matches the target. |
| `fictional-adset-a8` | LINK_OR_TRACKING_BAD | Yes | After snapshot matches the target. |
| `fictional-adset-a10` | LADDER_PROMOTE | **No** | After snapshot differs from the target ⇒ treat as not in effect; do not move to the next step as if it ran: daily_budget: expected 40.00, read 20.00 |

**Not compared this round: 16 rows, listed in full:**

- `fictional-adset-a2` · TEST_UNDERTESTED — Gate is Advisory; not written this round.
- `fictional-adset-a3` · TEST_STOP_NOCONV — Gate is Satisfied; not written this round.
- `fictional-adset-a5` · TEST_UNDERTESTED — Gate is Advisory; not written this round.
- `a6-c1` · CREATIVE_BREAKER — Gate is Advisory; not written this round.
- `a6-c2` · CREATIVE_FATIGUE — Gate is Advisory; not written this round.
- `fictional-adset-a6` · LADDER_HOLD — Gate is Advisory; not written this round.
- `fictional-adset-a7` · AD_STATUS — Gate is Advisory; not written this round.
- `fictional-adset-a9` · LADDER_PROMOTE — Gate is Conflict (isolated); not written this round.
- `fictional-meta-account-b` · ACC_NO_DELIVERY — Gate is Advisory; not written this round.
- `fictional-meta-account-b` · ACC_BALANCE_LOW — Gate is Advisory; not written this round.
- `fictional-adset-b1` · CREATIVE_OVERFLOW — Gate is Advisory; not written this round.
- `fictional-adset-b1` · LADDER_HOLD — Gate is Advisory; not written this round.
- `fictional-adset-b2` · TEST_EARLY_STOP — Gate is Unknown; not written this round.
- `fictional-meta-account-c` · ACC_STOPPED — Gate is Advisory; not written this round.
- `fictional-adgroup-d1` · LADDER_PROMOTE — Gate is Advisory; not written this round.
- `fictional-adgroup-d2` · TEST_UNDERTESTED — Gate is Advisory; not written this round.

## Structure warnings (no action, but they limit how far a verdict can be trusted)

- `fictional-adset-a5` — Name says MAX but bid_strategy = LOWEST_COST_WITH_COST_CAP (5.00) ⇒ the name does not match the setup; read structure from bid_strategy, not from the name.
- `fictional-adset-a7` — configured_status=ACTIVE but effective_status=DISAPPROVED ⇒ judge whether it can deliver by effective_status.
- `fictional-meta-account-b` — spend_cap reads back null ⇒ the headroom alert cannot be computed; reported as a gap, never inferred from the balance.

## Handoff rules

- `satisfied` produces no change. A `conflict` is isolated and its cause confirmed; the values alone do not say who changed it.
- An insufficient sample (impressions below the floor) is recorded, not judged.
- Capability gaps are stated (for example a spend cap that reads back null), never filled by inference.
- Platform numbers that do not reconcile with the settlement do not drive budget or pause changes until they do.
- Approval, submission and live readback are outside this offline round.

