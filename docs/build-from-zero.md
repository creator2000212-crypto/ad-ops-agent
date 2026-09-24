# How to turn advertising work into an agent

[简体中文](build-from-zero.zh-CN.md) · [See the runnable account-review demo](../demo/README.md)

This agent connects account setup, business context, asset selection, configuration and result checks, leaving media buyers more time for analysis and decisions. It comes from advertising workflows already used in WorkBuddy. Others can load the instructions in their own host and work with tools they have connected and authorized. A fictional example shows how to assemble the work and hand it over.

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

First prepare a batch review:

- Use course account A only, target the United States, and use assets A and B with the same booking page.
- Put one asset in each test unit and keep the round within the user's $60 total. Explain which native object owns the budget, whether it is daily or lifetime, and whether it is shared. Do not promise that each asset receives half the spend.
- Track cost per form submission and retain sales-confirmed booking counts. Review after three days without automatically declaring a winner when the date arrives.

**Your decision is to confirm or revise this concrete plan.** After checking account and tool capabilities and recording the batch authorization, the host carries out the permitted configuration and publishing steps. Creating paused objects is also a write and must be covered. Unchanged mechanical steps already authorized do not need repeated approval. If a required capability is missing, deliver the preparation and state the gap; do not treat a local simulation as publishing.

A handoff such as “A and B were created and their configuration checked; A has passed review, while B is still pending review” needs the corresponding objects, check times and read results. Record enabled configuration, review approval and observed delivery separately instead of assigning one success label to the whole batch.

Suppose a later day's supplied figures look like this. They are still fictional observations:

| Asset | Spend | Form submissions | Cost per submission |
|---|---:|---:|---:|
| A | $18 | 3 | $6 |
| B | $12 | 1 | $12 |

The agent can organize the conclusion: “A had a lower form-submission cost that day. Valid-booking results are incomplete, so these figures do not establish that A deserves more budget.” It brings the data, gaps and recommendation together. You decide whether to observe longer or change direction; “looks promising” does not become an automatic budget increase.

Before a configuration change, a current budget that differs from the previous record should prompt a comparison. If the resulting value differs from the plan, retain the discrepancy instead of marking the work complete based only on a success message. Observed receipt status must come from a read result, never from the target value or a hardcoded `ACTIVE`.

Later, when you ask for yesterday's course report, the agent reuses the agreed definitions and checks the date, time zone, accounts and data coverage. It does not repeat the A/B planning interview. At the start of a new account review, it first rechecks relevant outstanding items from the previous round.

## 5. Retain experience: reuse what you confirm

During review, you add: “For this course product, always separate form submissions from valid bookings. Do not decide to scale from form-submission cost alone.”

The agent turns that into a proposed working agreement, identifying the course product, why it was raised and which outcomes remain unknown. **It is saved and reused in later tasks after your confirmation.**

If the next round changes from comparing openings to comparing content directions, the agent should explain the difference: A/B becomes A/C, and the constants and test question change with it. You confirm the revised method before a new plan is prepared.

Experience accumulates through observations, candidates, confirmation and later reuse or revision. Adopting an agreement and proving its effectiveness are separate. One result does not automatically become a rule for every product or expand the agent's execution authority. The Python program does not learn and promote lessons by itself.

## How the repository fits this workflow

| Layer | How it relates to this example |
|---|---|
| Historical WorkBuddy business practice | Saved records cover media inspection, campaign building, reporting and account reviews; see the [case studies](case-studies.md). This course example remains fictional |
| Reusable host workflow | The host handles conversation and uses connected, authorized tools to read, inspect media, configure and verify. The deployer validates the specific environment |
| Public Python programs | They store business inputs/private records offline, propose two method types, prepare tests from declared differences, analyze snapshots and simulate recovery. They do not call platforms, understand media or learn automatically |

Start with the [host workflow](workflow.md) and [task template](../templates/task-record.md) for your own task. Use Python when you want to validate supported structured plans; reports, troubleshooting and migrations do not all need to become creative tests in `task.py`. See the [capability boundaries](capability-status.md) for limits and acceptance criteria.

The reusable parts are business context, confirmed methods, preparation and result checks. The user chooses the product, countries, budgets and practices. Keeping connection handling, business methods and execution records separate makes them easier to update without imposing one advertising strategy on everyone.

Read more: [module responsibilities](architecture.md) · [offline review fields and commands](operating-loop.md) · [Python methods and test plans](method-planning.md).

Back to the [project home](../README.md).
