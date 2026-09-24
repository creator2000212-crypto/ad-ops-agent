# Run an advertising task with an agent

[简体中文](workflow.zh-CN.md) · [Cases from practice](case-studies.md) · [Capability status](capability-status.md)

This is a host-agent workflow: how to use tools already connected in WorkBuddy, Codex or another environment to take an advertising request through preparation, authorized operations and handoff. It distils historical work records. A new host must still verify its available tools and permissions.

This route can use the host's MCP, API, SDK or user-authorized platform UI. The repository's Python programs provide a separate offline validation route. They neither make these live calls nor need to become live adapters before a host can use its existing tools.

## Start with the current task

| A user might ask | Establish first | Deliver |
|---|---|---|
| “Prepare the next test from these videos” | Product, destination, account, event, test question and asset fit | Selection reasons, exclusions, batch configuration and budget |
| “Build or update this confirmed batch” | Plan version, objects/actions, budget, dependencies, current state and authorization | Per-operation records, configuration readback, partial failures and open items |
| “Review these accounts for changes” | Time window, account coverage, current method and previous open items | Evidence, recommendations, missing data and follow-ups |
| “Move this campaign to another account” | Source structure, target access, reusable identities/events/media and overlapping spend | Object mapping, differences, authorized operations and checks |
| “This ad is not spending / was rejected / is misconfigured” | Effective and parent state, review/error details and recent changes | Diagnosis, evidence, recovery options and results |
| “Give me an Offer-level daily report” | Date/timezone, channels/accounts, cost/conversion/revenue sources and mapping rules | A readable report, coverage notes and traceable detail |

Choose the task before collecting its inputs. A report request does not require another creative-testing interview.

## 1. Establish the available scope

Record the platform, accounts and tools needed for this task. Use authorized reads to verify identity, account scope, currency/timezone and required objects and fields. For writes, also verify the corresponding create/update and readback capabilities. Do not create ads just to test access.

- **First setup for a complete operating workflow:** resolve connectivity before the business and methodology interview.
- **Existing connection:** check the capabilities needed now and reuse known context, without reinstalling tools or repeating provider recommendations.
- **Read-only analysis:** proceed with sufficient read access; reporting does not require publishing permission.
- **Missing connection:** list the specific gaps. User-supplied material can remain task input; never fabricate a connection snapshot.

Tool availability, account access and user authorization are separate. An available write operation is not permission to use it.

## 2. Understand the business and the user's method

Read relevant material and confirmed agreements. Summarize the product, market, Web or App journey, conversion and monetization, budget boundary, data sources and the question for this round.

**Newcomer example:** “I have a course website but do not know how to test creative.” Propose a choice between comparing openings and comparing content directions. Explain variables, constants, metrics and unknowns; let the user choose.

**Experienced buyer example:** “Keep my original campaign and test in a separate group. Leave existing delivery alone.” Record the original objects as excluded from changes, identify the new test and budget, and resolve missing conditions. Show conflicts with older methods instead of silently substituting a previous approach.

IAA, IAP, hybrid monetization, purchases, forms and qualified leads determine which facts matter. Unknown lifetime revenue stays unknown. The author's historical campaign structures, budget ladders and stop-loss numbers are not defaults for everyone.

## 3. Prepare a concrete batch for review

Use supplied material and current state for reversible preparation: check the destination and event, establish asset identities and specifications, find duplicates, explain inclusion and exclusion, prepare native configuration and total the budget.

Asset judgements need a stated basis. If tools actually inspected frames or video, record the inspected scope. If only names or production notes were available, say so. Do not present an inference as observed content or proven performance.

The batch review should contain:

- Product, platform, account, event, market, language and destination.
- Selected assets and copy, exclusions, test variables and constants.
- Exact objects to create, change, pause or activate, plus existing objects to leave alone.
- Currency, budget owner, daily or total period, schedule and overlapping spend.
- Differences from current state, dependencies, open issues and partial-completion handling.
- Plan version, requested confirmation scope and how results will be checked.

For example: “Keep the original campaign; create two test groups with one asset each, within the user's total test allowance; create paused objects and verify them before activation within the approved batch.” Creating paused objects is itself an external write and must be authorized.

## 4. Confirm the batch, then complete authorized steps

Record the confirmed version, accounts, objects, actions, budget and restrictions. Mechanical steps within that scope can continue without asking again for every upload. A new account, added spend, a changed method or more affected objects requires a concrete revised review.

Read relevant state again before changing it:

- Already at the target: verify and skip the duplicate change.
- Different from the plan's baseline: retain the discrepancy and establish context; do not infer who changed it.
- Unknown state, missing fields or a timeout: query existing objects and the prior request before deciding whether to retry.

Respect dependencies between media processing, object creation and configuration. Preserve each platform's object relationships rather than forcing Google's products into Meta's hierarchy. Record requests and returned object identities in the user's private task directory.

## 5. Build the receipt from actual readback

**Actual values in a receipt must come from tool results after the corresponding operation.** Never populate them from planned targets, hard-coded script constants or the model's completion statement.

| Question | Required evidence | What can be stated |
|---|---|---|
| Was the request sent and accepted? | Request receipt or platform operation record | Submitted; object check still needed |
| Does configuration match the plan? | Timestamped field readback of the same object | Configuration verified, with any differing fields |
| What is the review state? | Actual review state | Pending / rejected / approved / unknown |
| Is delivery eligible? | Effective object and parent state, restrictions | Eligible / restricted; not proof of impressions |
| Has delivery started? | Impressions or spend in a stated window | Observed impressions / spend as of a given time |
| Did performance improve? | Comparable, sufficiently mature later data | Observations and uncertainty, not inferred from activation |

Record only available fields. Platforms differ; missing evidence stays unknown. If eight items match, one remains in review and another cannot be read, hand them off separately.

## 6. Recheck previous work before proposing the next round

When relevant prior open items exist, establish whether recommendations were adopted, changes took effect and data matured. An unexecuted recommendation cannot be judged as an ineffective intervention. Configuration success and performance improvement are separate. Without related history, do not load unrelated product records.

Hand off **confirmed results, open items, next steps and user decisions**. A daily report may include a short shareable summary alongside sources, account coverage, detailed rows and differences in definitions. Failed retrieval is not zero, and an old file is not fresh data.

A user correction first fixes the current conclusion. When the user explicitly requests persistence, save a scoped private agreement with product, conditions, source and version. New observations remain candidates; method revisions require corresponding plan updates. Learning does not expand budgets, publishing rights or platform permissions.

## Reuse the workflow

Copy the [task record template](../templates/task-record.md) to a private directory and have the host follow this guide. Business facts, native object IDs, receipts and assets stay private. Connections and methods can change while preparation, review, execution and verification remain reusable.

In a new host, begin with a read or preparation task, then validate writes and readback within explicit authorization. A historical WorkBuddy case does not prove another host is configured or every advertising product on all three platforms is supported.

For public-code checks of planning, recovery and data validation, use the [offline validation entry points](capability-status.md#offline-validation-entry-points). Simulation approvals and fictional accounts never authorize live work.
