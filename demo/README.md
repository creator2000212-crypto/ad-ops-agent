# Understand the agent through one example

[简体中文](README.zh-CN.md) · [Project home](../README.md)

**You set the goal and choose the method. The agent checks ads, organizes recommendations and shows you what needs a decision.**

This example uses fictional data. It does not change real ad accounts.

## You give it a task

> Check yesterday's ads and tell me what needs attention.

## The agent does three things

**1. Find ads worth reviewing.**

For example, an ad set with no conversions but few impressions may need more observation. Another has reached your chosen stop-loss conditions and becomes a pause recommendation. You choose the criteria.

**2. List specific changes and check whether they are still needed.**

For example, propose raising a1's budget from 10 to 20. An already paused ad does not need another pause. Changed budgets and missing information are listed separately for your judgement.

**3. Explain the result and what remains unresolved.**

This example ends with three follow-ups:

- **a9:** Its budget changed. Find out why before proceeding.
- **b1:** Its current state is missing. Obtain that information first.
- **a6:** The target budget is 40, but the supplied result still says 20. Check the difference.

You get the proposed changes, their reasons and unresolved questions, then decide what to do next.

## Does it act after confirmation?

The intended workflow is: **the agent prepares a plan → you confirm → it acts within your authorization → it checks the result.**

The current demo uses files to demonstrate recommendations and comparisons. It does not connect to accounts or carry out the changes.

## Try it

Open the [complete example report (Chinese)](expected/report.md), or run this in the project directory:

```bash
python3 demo/run_demo.py
```

To understand how the agent is built and how experience can improve it, read the [building guide](../docs/build-from-zero.md). Developers can refer to [rules and commands](../docs/operating-loop.md).
