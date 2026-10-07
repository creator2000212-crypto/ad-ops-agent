# One round of the 12-hour check, replayed

This demo replays one round of the read-only 12-hour check I ran as a scheduled WorkBuddy job on live Meta and TikTok lead-gen accounts (Sep 22–26, 2026), using fictional data.

[简体中文](README.zh-CN.md) · [Project home](../README.md) · [Technical reference](../docs/operating-loop.md)

WorkBuddy is Tencent's desktop AI agent; this project is not affiliated with it. Here the round runs offline: the script reads JSON fixtures, makes 0 platform calls, and writes a report plus a local ledger. Accounts, ad sets, creatives and prices are fictional; the rule structure and thresholds are the ones I used.

```bash
python3 demo/run_demo.py           # run the round and print the report
python3 demo/run_demo.py --steps   # the same round, one step at a time
python3 demo/run_demo.py --check   # compare with the committed sample in demo/expected/
```

## The task

> Review yesterday's delivery across these 3 accounts. Which ad sets can take more budget, which should pause, which need more time? Give me the reasons and the change list first.

The fixture holds **3 Meta accounts and 12 ad sets for September 23, 2026**. Ad set names are shortened to a1, a2 and so on.

## 1. The economics behind every threshold

Each account declares the value of one lead; the methodology declares the lead approval rate and the target ROAS. For account A:

**T = 10.00 value per lead × 0.90 approval / 1.25 target ROAS = 7.20**

T is the highest cost per lead the round accepts, and it sits below the value of a lead. The stop-loss line is 3T = **21.60**, and a zero-lead ad set needs at least **300 impressions** before it can be judged. Account B's leads are worth 8.00, so its T is 5.76.

## 2. What the data says

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

Two zero-lead ad sets get different answers (a2, a3), the cheapest leads do not automatically get more money (a5), and a promotion waits when something else in the ad set or account is broken (a6, b1). One change per ad set per round keeps cause and effect readable.

## 3. Check current state before changing anything

Yesterday's data says how things performed; the state read just before writing says whether a change is still needed. Comparing the proposals with that read:

- **a3 is already paused.** Satisfied: nothing to write.
- **a9's budget changed.** The plan was 20 → 40, but the current value is 30. Conflict: isolate the row and find out why before touching it. The values alone do not say who changed it.
- **b2 was not returned by the read.** Unknown: read it again before pausing.

Four rows remain for review:

| Ad set | Proposed change | Evidence |
|---|---|---|
| a1 | Budget **20 → 40** | CPA 6.60 ≤ T 7.20, 3 leads, full delivery day |
| a4 | **Pause** | Over-cost margin 25.60 ≥ 21.60 |
| a8 | **Pause and investigate** | The destination check failed |
| a10 | Budget **20 → 40** | CPA 5.15 ≤ T 7.20, 4 leads, full delivery day |

`ready` means the row passed the state check. It is not approval. The live 12-hour job only read and reported; in live operation I approved launches and budget changes myself. This demo has no approval or submission step.

## 4. Read back, then hand over

To show verification, the fixture supplies the state "after" the change. It is a prepared file, not a platform readback.

**a1, a4 and a8 match their targets. a10's target budget is 40, but it still reads 20.** The write did not take, so a10 stays open in the ledger and must not be treated as running at 40 when the next promotion is considered.

The handoff:

> **Follow up:**
>
> - a10: target budget 40, read back 20. Find out why the change did not land.
> - a9: current budget 30 differs from the plan's baseline 20. Establish the change's context first.
> - b2: re-read its state, then decide on the pause.
>
> Fix the a6 creatives and b1's creative count; account B needs funds and a delivery check. Keep observing a2; find out why a5 cannot spend its budget.

## Read the full result

The committed [complete report (Chinese)](expected/report.md) lists every ad set with its evidence, and [`expected/summary.json`](expected/summary.json) holds the counts that `--check` compares. After `python3 demo/run_demo.py`, the generated files are under `demo/out/` (ignored by Git): start with `report.md`, then `gate.json` and `reconciliation.json` when tracing a decision.

To start your own task, follow [first use](../docs/first-check.md). For fields, formulas and commands, see the [technical reference](../docs/operating-loop.md).
