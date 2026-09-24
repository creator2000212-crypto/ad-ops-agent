# How to turn advertising work into an agent

[简体中文](build-from-zero.zh-CN.md) · [See the runnable account-review demo](../demo/README.md)

This agent aims to connect account setup, business context, asset selection, configuration and result checks, leaving media buyers more time for analysis and decisions. A concrete example shows what each step involves.

## Meet the example

**The business, assets, budget and data below are fictional and illustrate the build order.** They are separate from the runnable account-review fixtures in the [demo](../demo/README.md).

Suppose you run an online English-course website for adults in the United States. Ads invite people to book a **15-minute trial lesson**. A visitor reaches the booking page and submits a form; sales staff later confirm whether the booking is valid.

You start with one Meta account and three English-language videos. You choose a **$60 total test budget** and a **review after three days**. These are this fictional user's choices, not recommended defaults.

Build the workflow in this order:

**Connect accounts → Understand the business → Agree on a method → Handle daily work → Retain confirmed experience.**

The conversations and handoffs below describe the intended experience. The final section explains what the repository currently implements.

## 1. Connect accounts: establish what is available

You tell the agent: “Start with Meta using this course account. TikTok and Google can wait. I already have a connection tool.”

The agent first checks account identity, access to ads and data, configuration capabilities and whether changes can be checked afterward. An existing connection remains an option; without one, it helps you choose a route.

**The output should be specific:** “This task uses course account A only. Ad reading is available, but a required configuration permission is missing. Resolve that before continuing.” An installed tool does not prove account access, and a lengthy business questionnaire is not the next step while access remains unresolved.

Put connection checks at the entrance to the workflow. When accounts or platforms change, check the new scope without restarting the entire business interview.

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

**For an experienced buyer:** you can say, “Use my existing method: compare content directions first, keep the booking page fixed and use A as the reference.” The agent organizes an A/C plan and checks the metric and observation window. If your method also requires unsupported actions such as automatic budget increases, those requirements stay visible rather than being silently removed.

The rest of this example follows the user's confirmed A/B choice. **The selection explanation is:** A is your explicit reference, B meets the opening-only condition, and C is excluded because its concept also differs. An A/C choice would follow the same later steps, with selection based on comparing content directions. The basis is your confirmed production notes, not a claim that the program understood the videos.

You confirm adoption of the method. Selection does not mean the assets have been proven to perform well.

## 4. Handle daily work: separate preparation, decisions and checks

First prepare a batch review:

- Use course account A only, target the United States, and use assets A and B with the same booking page.
- Put one asset in each test unit, sharing the account's $60 budget for this round. Do not promise that each receives half the spend.
- Track cost per form submission and retain sales-confirmed booking counts. Review after three days without automatically declaring a winner when the date arrives.

**Your decision is to confirm or revise this concrete plan.** The agent then handles configuration within the permitted scope, checks results and retains incomplete items. Live publishing remains a separate operation requiring integration and authorization.

Suppose a later day's supplied figures look like this. They are still fictional observations:

| Asset | Spend | Form submissions | Cost per submission |
|---|---:|---:|---:|
| A | $18 | 3 | $6 |
| B | $12 | 1 | $12 |

The agent can organize the conclusion: “A had a lower form-submission cost that day. Valid-booking results are incomplete, so these figures do not establish that A deserves more budget.” It brings the data, gaps and recommendation together. You decide whether to observe longer or change direction; “looks promising” does not become an automatic budget increase.

Before a configuration change, a current budget that differs from the previous record should prompt a comparison. If the resulting value differs from the plan, retain the discrepancy instead of marking the work complete based only on a success message.

## 5. Retain experience: reuse what you confirm

During review, you add: “For this course product, always separate form submissions from valid bookings. Do not decide to scale from form-submission cost alone.”

The agent turns that into a proposed working agreement, identifying the course product, why it was raised and which outcomes remain unknown. **It is saved and reused in later tasks after your confirmation.**

If the next round changes from comparing openings to comparing content directions, the agent should explain the difference: A/B becomes A/C, and the constants and test question change with it. You confirm the revised method before a new plan is prepared.

Experience accumulates through observations, candidates, confirmation and later reuse or revision. One result does not automatically become a rule for every product. The program does not learn and promote lessons by itself.

## How the repository fits this workflow

Today, the repository can store business inputs and private records offline, propose limited methods, prepare tests from declared asset differences, and run analysis and reconciliation examples on supplied data. Conversation is handled by a host such as Codex; the components still have separate entry points.

There are no live platform writes, automatic media understanding or automatic learning. This guide illustrates how to assemble the work; its conversations and fictional figures are not evidence of a verified live workflow.

The reusable parts are business context, confirmed methods, preparation and result checks. The user chooses the product, countries, budgets and practices. Keeping connection handling, business methods and execution records separate makes them easier to update without imposing one advertising strategy on everyone.

Read more: [module responsibilities](architecture.md) · [the daily operating loop](operating-loop.md) · [methods and test plans](method-planning.md).

Back to the [project home](../README.md).
