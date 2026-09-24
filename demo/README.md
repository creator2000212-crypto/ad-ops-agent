# What the agent does in one ad review

[简体中文](README.zh-CN.md) · [Project home](../README.md)

**You give it a task. The agent turns ad data into recommendations with reasons, then lists the decisions and follow-ups that remain.**

This walkthrough uses the repository's runnable fictional example: **3 Meta accounts and 10 ad sets, reviewing delivery on September 23, 2026.** Ad set names are shortened to a1, a2 and so on. Amounts use the sample account's currency units.

The current demo reads files, generates recommendations and compares values. It does not connect to real accounts. References to your review explain the intended collaboration; they do not record an actual approval or account change.

## 1. You give it a specific task

> Review yesterday's delivery across these 3 accounts. Which ad sets could take more budget, which should pause, and which need more observation? Show me the reasons and proposed changes first.

The example already has a reference method. For account A, the target cost per conversion is **4.71**. The zero-conversion stop-loss rule illustrated by a3 requires both **300 impressions** and **14.12 in spend** before producing that particular pause-and-review recommendation. These numbers belong to this example; users choose a method appropriate to their own business.

## 2. The agent explains what the data means

Start with 4 representative ad sets:

| Ad set | Observed data | Interpretation | Recommendation for you |
|---|---|---|---|
| **a1** | Spend 12.40; 3 conversions; cost per conversion 4.13 | Cost is below the 4.71 target, and this example's conversion-count and full-day requirements are met | Consider increasing daily budget **10 → 20** |
| **a2** | Spend 3.10; 180 impressions; no conversions | It has not reached this method's sample and stop-loss conditions | Keep observing; do not label the creative a failure |
| **a3** | Spend 15.30; 420 impressions; no conversions | Both impression and spend conditions for a pause-and-review recommendation are met | Propose a pause and review the destination and conversion reporting |
| **a5** | Spend 6.40; 4 conversions; cost per conversion 1.60; only 32% budget utilisation | Cost is low, but delivery is not using much of the budget | Investigate limited delivery before deciding whether to increase budget |

This explains why two ad sets with no conversions receive different recommendations, and why the lowest conversion cost does not automatically lead to more budget.

## 3. Check current state before preparing changes

Yesterday's data describes performance. Current state helps determine whether a proposed change is still needed. Comparing the recommendations with a separate current-state file reveals:

- **a3 is already paused.** Keep the diagnosis without scheduling the same pause again.
- **a9's budget differs.** The baseline was 10, the proposal is 20, but the current value is 30. Find out why it changed before overwriting it with 20. The difference does not identify who changed it.
- **b1 has no current-state record.** Obtain that information before deciding whether it can be changed.

The remaining 4 items form a review list:

| Ad set | Proposed change | Evidence to consider during review |
|---|---|---|
| a1 | Daily budget **10 → 20** | Cost per conversion is 4.13 and this example's increase conditions are met |
| a4 | **Pause** | Spend 30; 3 conversions; cost per conversion 10; this example's excess-cost stop condition is met |
| a6 | Daily budget **20 → 40** | Ad set data meets the increase conditions, but there are also warnings about concentrated creative spend, high creative cost and fatigue; review them together |
| a8 | **Pause and investigate** | Input data flags a destination or tracking issue that needs verification and repair |

**You decide whether to adopt the batch.** For example, a6 has both a budget-increase recommendation and creative warnings. You might request a creative review before deciding on its budget. The list must reflect that decision; passing a state check is not your approval.

The intended workflow is to confirm the final batch, let the agent execute within authorization, then read the platform result. This demo only records the review list; it has no real submission or user-approval step.

## 4. Compare results and leave specific follow-ups

To demonstrate verification, the project supplies a preset file representing later state. It is neither produced by execution nor retrieved from a platform.

Against the original 4-item list above, **a1, a4 and a8 match their target values or states. For a6, the target budget is 40 but the file still says 20.** It cannot be marked as successfully changed or treated as being on a budget of 40 when considering another increase.

The handoff could read:

> **Follow up:**
>
> - a9: Current budget 30 differs from the baseline. Establish the change's context.
> - b1: Obtain current state, then check again.
> - a6: Target budget 40, supplied result 20. Investigate the mismatch and retain the creative warnings.
>
> Keep observing a2. Investigate why a5 is not using its budget. The complete report also retains disapproval, account-balance and other creative findings for your judgement.

You receive **ad assessments, proposed changes and follow-ups**. This round provides no evidence that a real ad was changed or that the recommendations improve performance.

## Run it or read the results

Open the [complete report (Chinese)](expected/report.md) for all ad sets and evidence, or run this in the project directory:

```bash
python3 demo/run_demo.py
```

For concrete examples of initial setup, creative testing and retaining experience, read the [building guide](../docs/build-from-zero.md). Refer to the [technical guide](../docs/operating-loop.md) when you need fields, formulas or step-by-step commands.
