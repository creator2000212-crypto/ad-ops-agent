# One round of the 12-hour check, replayed

This demo replays one round of the read-only 12-hour check I ran as a scheduled WorkBuddy job on live Meta and TikTok lead-gen accounts (Sep 22–26, 2026), using fictional data.

[简体中文](README.zh-CN.md) · [Project home](../README.md) · [Technical reference](../docs/operating-loop.md) · [Decision matrix](../docs/decision-matrix.md)

WorkBuddy is Tencent's desktop AI agent; this project is not affiliated with it. Here the round runs offline: the script reads JSON fixtures, makes 0 platform calls, and writes a report plus a local ledger. Accounts, ad sets, creatives and prices are fictional; the rule structure and thresholds are the ones I used.

```bash
python3 demo/run_demo.py                # run the round and print the report (English)
python3 demo/run_demo.py --lang zh-CN   # the same round in Chinese
python3 demo/run_demo.py --steps        # the same round, one step at a time
python3 demo/run_demo.py --check        # compare both languages with demo/expected/
```

## The task

> Review yesterday's delivery across these 4 accounts. Which ad sets can take more budget, which should pause, which need more time? Give me the reasons and the change list first.

The fixture holds **3 Meta accounts and 1 TikTok account, 14 ad sets and ad groups, for September 23, 2026**, plus the settlement export for the same day. Names are shortened to a1, a2 … d2.

## 1. The economics behind every threshold

Each account declares the value of one lead; the methodology declares the lead approval rate and the target ROAS. For account A:

**T = 10.00 value per lead × 0.90 approval / 1.25 target ROAS = 7.20**

T is the highest cost per platform lead the round accepts, and it sits below the value of a lead. The stop-loss line is 3T = **21.60**, and a zero-lead ad set needs at least **300 impressions** before it can be judged. Account B's leads are worth 8.00 (T = 5.76); account D's are worth 12.00 (T = 8.64).

## 2. Check the numbers against the settlement first

Platform numbers drive the decisions, but the settlement decides what is paid. Before anything is promoted, each account's platform totals are joined with the settlement on account and date. Settled leads are compared with platform leads × the declared 0.90 approval rate, because the settlement only pays approved leads.

| Account | Platform → settled | Status | Meaning |
|---|---|---|---|
| **A** | Spend 176.30 → 176.12; leads 21 → 19 (18.9 expected) | `RECON_OK` | Within tolerance; decisions stand |
| **B** | Spend 24.70 → 22.90 | `RECON_TZ` | The account reports in Etc/GMT+5, the settlement in Etc/GMT; the day buckets differ, so the gap cannot be read yet |
| **C** | No settlement row | `RECON_SCOPE` | Outside the settlement's scope; shown as missing, not as zero |
| **D** (TikTok) | Spend 29.40 → 29.40; leads 7 → 3 (6.3 expected) | `RECON_GAP` | The settlement approves 43% of the leads against a declared 90% |
| **E** | Settlement row only | `RECON_SCOPE` | The pull did not return this account; the platform side is missing, not zero |

In an account with `RECON_GAP`, `RECON_TZ` or `RECON_WINDOW`, promotions and over-cost pauses become advisory ("measurement unreconciled") until the numbers agree. This check exists because of a real scope problem: on Sep 20, 2026 the daily sheet, pulled from every connected account, ran about 20% above the settlement export until it was scoped to the accounts the settlement covers (about 0.1% on the checked day).

## 3. What the data says

| Ad set | Observed | Reading | Proposal |
|---|---|---|---|
| **a1** | Spend 19.80; 3 leads; CPA 6.60 | Below T over a full delivery day | Budget **20 → 40** |
| **a2** | Spend 4.60; 210 impressions; 0 leads | Below the 300-impression sample gate | Keep observing; no verdict on the creative |
| **a3** | Spend 22.40; 640 impressions; 0 leads | Past both the sample gate and 3T | Pause and check the destination and conversion tracking |
| **a4** | Spend 40.00; 2 leads; CPA 20.00 | Spend − T × leads = 25.60, past 3T | Pause |
| **a5** | Spend 8.40; 3 leads; CPA 2.80; 42% of budget spent | Cheap but limited delivery; the name says MAX while the ad set runs a 5.00 cost cap below T | Fix delivery before adding budget |
| **a6** | Spend 21.00; 4 leads; CPA 5.25 | Meets the promotion numbers, but creative a6-c1 took 62% of spend at CPA 13.00 (above 1.7T) and a6-c2 is fatigued | **Hold**: fix the creatives first; budget unchanged |
| **b1** | Spend 15.60; 3 leads; CPA 5.20 vs T 5.76 | Meets the numbers, but 9 creatives (cap 8), and account B spent nothing today with a balance below the alert line | **Hold** |
| **b2** | Spend 9.10; 190 impressions; CPC 1.30; CTR 3.7% | Too few impressions to judge, but past the early-stop CPC and CTR lines | Pause and review the hook |
| **d1** | Spend 19.60; 5 leads; CPA 3.92 vs T 8.64 | Would promote on platform numbers, but account D does not reconcile | **Advisory**: no budget change until the settlement agrees |
| **d2** | Spend 9.80; 2 leads | Below the 3-lead minimum | Keep testing |

Two zero-lead ad sets get different answers (a2, a3), the cheapest leads do not automatically get more money (a5, d1), and a promotion waits when something else in the ad set, the account or the measurement is broken (a6, b1, d1). One change per ad set per round keeps cause and effect readable.

## 4. Why CPA moved

For ad sets that carry a prior window, the report splits the CPA change into CPM, CTR and CVR terms (CPA = CPM ÷ (1000 × CTR × CVR), so the log changes add up exactly):

| Ad set | CPA prior → now | Main driver | Reading |
|---|---|---|---|
| a1 | 7.03 → 6.60 | CTR (60% of the movement) | A stronger hook; the promotion stands |
| a4 | 5.41 → 20.00 | CVR (90%) | After the click: destination, form or lead quality, not the bid |
| d1 | 7.21 → 3.92 | CVR (91%) | More form fills per click while the settlement approves fewer leads: cheaper leads, lower quality |
| a10 | 5.38 → 5.15 | Not decomposed | The prior window has no CVR, and the gap stays visible |

It is an accounting identity, not a cause; it tells you where to look first.

## 5. Check current state before changing anything

Yesterday's data says how things performed; the state read just before writing says whether a change is still needed. Comparing the proposals with that read:

- **a3 is already paused.** Satisfied: nothing to write.
- **a9's budget changed.** The plan was 20 → 40, but the current value is 30. Conflict: isolate the row and find out why before touching it. The values alone do not say who changed it.
- **b2 was not returned by the read.** Unknown: read it again before pausing.
- **d1 never reaches the gate as a write.** It is advisory because account D does not reconcile.

Four rows remain for review:

| Ad set | Proposed change | Evidence |
|---|---|---|
| a1 | Budget **20 → 40** | CPA 6.60 ≤ T 7.20, 3 leads, full delivery day |
| a4 | **Pause** | Over-cost margin 25.60 ≥ 21.60 |
| a8 | **Pause and investigate** | The destination check failed |
| a10 | Budget **20 → 40** | CPA 5.15 ≤ T 7.20, 4 leads, full delivery day |

`ready` means the row passed the state check. It is not approval. The live 12-hour job only read and reported; in live operation I approved launches and budget changes myself. This demo has no approval or submission step.

## 6. Read back, then hand over

To show verification, the fixture supplies the state "after" the change. It is a prepared file, not a platform readback.

**a1, a4 and a8 match their targets. a10's target budget is 40, but it still reads 20.** The write did not take, so a10 stays open in the ledger and must not be treated as running at 40 when the next promotion is considered.

The handoff:

> **Follow up:**
>
> - a10: target budget 40, read back 20. Find out why the change did not land.
> - a9: current budget 30 differs from the plan's baseline 20. Establish the change's context first.
> - b2: re-read its state, then decide on the pause.
> - Account D: reconcile lead approval with the settlement (43% vs 90%) before d1 gets more budget.
>
> Fix the a6 creatives and b1's creative count; account B needs funds, a delivery check and time-zone-aligned settlement data. Keep observing a2 and d2; find out why a5 cannot spend its budget.

## Read the full result

The committed [complete report](expected/report.md) ([中文](expected/report.zh-CN.md)) lists every ad set with its evidence, and [`expected/summary.json`](expected/summary.json) holds the language-neutral counts that `--check` compares; `--check` also fails if the English and Chinese runs reach different decisions. After `python3 demo/run_demo.py`, the generated files are under `demo/out/` (ignored by Git): start with `report.md`, then `findings.json`, `gate.json` and `reconciliation.json` when tracing a decision. Every code in the report is defined in the [decision matrix](../docs/decision-matrix.md).

To start your own task, follow [first use](../docs/first-check.md). For fields, formulas and commands, see the [technical reference](../docs/operating-loop.md).
