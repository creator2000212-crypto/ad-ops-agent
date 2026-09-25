# Follow a course product through the advertising workflow

[简体中文](build-from-zero.zh-CN.md) · [See the runnable account-review demo](../demo/README.md)

**For:** newcomers and media buyers who want to understand a complete task without running code. **Outcome:** see concrete business context, method selection, a review draft and follow-up handoff. To begin your own task, use [first use](first-check.md).

This agent connects account setup, business context, asset selection, configuration and result checks, leaving media buyers more time for analysis and decisions. It comes from advertising workflows already used in an agent tool. Others can load the instructions in their own host and work with tools they have connected and authorized. A fictional example shows how to assemble the work and hand it over.

## Meet the example

**The business, assets, budget and data below are fictional and illustrate the build order.** They are separate from the runnable account-review fixtures in the [demo](../demo/README.md).

Suppose you run an online English-course website for adults in the United States. Ads invite people to book a **15-minute trial lesson**. A visitor reaches the booking page and submits a form; sales staff later confirm whether the booking is valid.

You start with one Meta account and three English-language videos. You choose a **$60 total test budget** and a **review after three days**. These are this fictional user's choices, not recommended defaults.

Build the workflow in this order:

**Connect accounts → Understand the business → Agree on a method → Handle daily work → Retain confirmed experience.**

The example explains how a host organizes a task. Actual reading, media inspection and publishing depend on that host's tools, accounts and authorization, which the deployer must verify. The final section separately describes the Python offline programs. These conversations and figures are not evidence of a live deployment.

## 1. Connect accounts: establish what is available

You tell the agent: “Start with Meta using this course account. TikTok and Google can wait. I already have a connection tool.”

The agent first checks account identity, access to ads and data, configuration capabilities and whether changes can be checked afterward. An existing connection remains an option; without one, it helps you choose a route.

**The output should be specific:** “This task uses course account A only. Ad reading is available, but a required configuration permission is missing. Resolve that before continuing.” An installed tool does not prove account access, and a lengthy business questionnaire is not the next step while access remains unresolved.

Put connection checks at the entrance when setting up a complete advertising workflow. When accounts or platforms change, check the new scope without restarting the entire business interview. If the current task only needs a daily report, sufficient read access is enough; publishing permission is not a prerequisite.

## 2. Understand the business: make ‘I want leads’ precise

Once the required connection capabilities are verified as available, the agent organizes your existing description and asks questions that affect the plan:

> “Does a conversion mean a submitted form or a booking confirmed by sales? How do you charge after the trial? Is $60 the whole test budget or a daily budget?”

You confirm that this round will track cost per submitted form and separately record valid bookings. The business sells courses after the trial, and $60 covers the whole test. Lifetime revenue per learner is still unknown, so it stays unknown.

**The agent produces a business summary you can correct:** United States, English, course website, adult learners, trial bookings, two separate measures for submissions and valid bookings, a $60 total budget and a review after three days.

Reuse that context in later tasks. For an app or ecommerce business, establish the relevant install, purchase and revenue definitions rather than retaining the course-booking assumptions.

## 3. Agree on a method: the same assets, different guidance

You supply the videos and production notes:

| Asset | Content | Differences confirmed in the production notes |
|---|---|---|
| A | Opens with “Nervous about speaking English in meetings?”, then introduces the trial | The reference asset for this round |
| B | Opens with “Practise a work conversation in 15 minutes” | Same concept as A; only the opening differs. Body, call to action and booking page are unchanged |
| C | A teacher demonstrates how to answer a workplace question | A different concept from A, linking to the same booking page |

**For a newcomer:** the agent offers two concrete candidates: compare A with B to examine different openings, or compare A with C to explore two content directions. It explains what stays fixed and what each comparison can address, then asks you to choose.

**For an experienced buyer:** you can say, “Use my existing method: compare content directions first, keep the booking page fixed and use A as the reference.” The agent organizes an A/C plan and checks the metric and observation window. If you also require a budget increase under certain conditions, specify its trigger, limit and authorization scope, then check whether this host can carry it out. Keep any capability gap visible; do not silently remove the requirement to fit a template.

The rest of this example follows the user's confirmed A/B choice. **The selection explanation is:** A is your explicit reference, B meets the opening-only condition, and C is excluded because its concept also differs. An A/C choice would follow the same later steps, with selection based on comparing content directions. This example relies on your confirmed production notes. If the host actually inspected frames or videos, record what it inspected and found separately. Notes alone do not support a claim that the media was viewed.

You confirm adoption of the method. Selection does not mean the assets have been proven to perform well. These comparisons are options for this example; the host workflow does not restrict users to them. The Python compiler currently supports only these two structured templates, so other requirements remain visible for the host to handle according to its capabilities.

## 4. Handle daily work: separate preparation, decisions and checks

### 4.1 Start with a filled review draft

**Fictional plan `course-test-v1`: draft; writes cannot proceed.** The user has agreed on the test question and $60 total boundary. The native budget owner, budget type and exact dates remain unresolved; the agent must not choose them silently.

| Review item | Current content | What remains |
|---|---|---|
| Scope | Meta, course account A (an example alias), United States, English, adult courses | Read and verify the actual account and timezone |
| Question and assets | Compare A/B openings; keep body, call to action and booking page fixed; exclude C | Verify real asset references, destination and tracking event |
| Proposed creation | Two test units with one asset each; leave existing ads unchanged | Map the units to specific native advertising objects |
| Budget boundary | USD; at most $60 for this entire new test, counted across both units | Verify owner, daily versus total budget, sharing and enforcement capability; not $60 per asset or $60 per day |
| Timing and judgement | Review after three days; track form cost and qualified bookings separately | Set start/end times in the account timezone; no automatic pause or scaling threshold is agreed |
| Current status | Method and draft preparation only | No batch configuration or publishing authorization; no creation, review or delivery receipts |

**You can confirm the method and draft direction at this point, not a publishable final batch.** The agent reads native structure and supported fields, completes budget, dates, object mapping and tracking, and explains how the $60 boundary will be enforced. If the tools cannot enforce it, the plan stays unresolved. A completed revision then presents the concrete actions for your review.

Only after the final plan and authorization are complete may the host configure and publish within scope. Creating paused objects is a write; mechanical steps already covered need no repeated approval. After execution, the handoff needs object references, read times, actual configuration, review states and remaining work. This example supplies no real execution receipt and does not establish creation or delivery.

### 4.2 Day 1: deliver an interim observation

This separate section demonstrates **how to report supplied data**; it does not establish that the unresolved draft above was published. Suppose the user supplies these fictional Day 1 figures:

| Asset | Spend | Form submissions | Cost per submission |
|---|---:|---:|---:|
| A | $18 | 3 | $6 |
| B | $12 | 1 | $12 |
| Total | $30 | 4 | $7.50 |

An interim handoff could say:

> **Scope:** user-supplied Day 1 A/B figures, totaling $30 and four submissions. This example supplies no native platform receipt or specific date/timezone; a real report needs the matching window and source for account reconciliation.
>
> **Observation:** A had the lower submission cost that day.
>
> **Still unknown:** qualified-booking results are incomplete and the three-day observation period has not ended. This does not establish that A deserves more budget.
>
> **Next:** check later data against the agreed budget and schedule, and obtain sales-qualified bookings. This task only analyzes data; no ad changes or budget increase occurred.

Subtracting this day's known $30 from the $60 boundary does not verify remaining allowance. Complete cumulative spend, current configuration and other periods still need checking. The review date, data maturity and permission to continue spending are separate conditions.

### 4.3 Day 3: the review is due, but missing evidence stays visible

Suppose the agreed review date arrives, but the user has supplied only Day 1 data, with Days 2–3 and qualified bookings still unavailable. The agent does not invent cumulative results or present Day 1 costs as the final outcome.

| Handoff item | What can be delivered on Day 3 |
|---|---|
| Known | The agreement was three days with a $60 total boundary; only Day 1 observations are available |
| To verify | Full three-day account data, cumulative spend, actual schedule state, sales-qualified bookings and matching rules |
| Conclusion status | Due review remains incomplete; total-budget compliance and a winning asset are unverified |
| Next steps and responsibilities | Agent obtains account data through authorized reads; user supplies or authorizes access to sales results; compare agreed measures once coverage is complete |
| Action boundary | Do not automatically extend the schedule or increase budget; if delivery is still running, flag it promptly and check existing authorization and stop conditions; read back any action taken within scope, and present changes outside that scope for the user's decision |

If a proposed change reveals a current value different from the prior record, reconcile the difference. An actual result that differs from the plan remains open despite a success message. “Readback” means reading an object again after an operation to check its result; actual values come from the read, not from copied targets.

Later, “Give me yesterday's course report” reuses the agreed definitions and checks dates, timezone, account scope and coverage, without another A/B interview. A new review starts by rechecking relevant open items from the previous round.

## 5. Retain experience: reuse what you confirm

During review, you add: “For this course product, always separate form submissions from valid bookings. Do not decide to scale from form-submission cost alone.”

The agent turns that into a proposed working agreement, identifying the course product, why it was raised and which outcomes remain unknown. **It is saved and reused in later tasks after your confirmation.**

If the next round changes from comparing openings to comparing content directions, the agent should explain the difference: A/B becomes A/C, and the constants and test question change with it. You confirm the revised method before a new plan is prepared.

Experience accumulates through observations, candidates, confirmation and later reuse or revision. Adopting an agreement and proving its effectiveness are separate. One result does not automatically become a rule for every product or expand the agent's execution authority. The Python program does not learn and promote lessons by itself.

## How the repository fits this workflow

| Layer | How it relates to this example |
|---|---|
| Historical business practice in an agent tool | Saved records cover media inspection, campaign building, reporting and account reviews; see the [case studies](case-studies.md). This course example remains fictional |
| Reusable host workflow | The host handles conversation and uses connected, authorized tools to read, inspect media, configure and verify. The deployer validates the specific environment |
| Public Python programs | They store business inputs/private records offline, propose two method types, prepare tests from declared differences, analyze snapshots and simulate recovery. They do not call platforms, understand media or learn automatically |

**Next:** begin your own task with [first use](first-check.md); if connected but business details are missing, use [business context and collaboration](first-run.md); with context and a method ready, use the [daily task workflow](workflow.md) and have the agent prepare the [task record](../templates/task-record.md). Use Python when you want to validate supported structured plans; reports, troubleshooting and migrations do not all need to become creative tests in `task.py`. See the [capability boundaries](capability-status.md) for limits and acceptance criteria.

The reusable parts are business context, confirmed methods, preparation and result checks. The user chooses the product, countries, budgets and practices. Keeping connection handling, business methods and execution records separate makes them easier to update without imposing one advertising strategy on everyone.

**For developers:** [module responsibilities](architecture.md) · [offline review fields and commands](operating-loop.md) · [Python methods and test plans](method-planning.md).

Back to the [project home](../README.md).
