# Run an advertising task with an agent

[简体中文](workflow.zh-CN.md) · [Cases from practice](case-studies.md) · [Capability status](capability-status.md)

**For:** users who have loaded the project and checked their connection, and now have a task to delegate. **Outcome:** know the inputs, review decisions and delivery checks for that task. Begin with [first use](first-check.md) if you are new; use [business context and collaboration](first-run.md) to fill relevant gaps.

This is a host-agent workflow: how to take an advertising request through preparation, authorized operations and handoff using an agent tool with the necessary connections. It distils historical work records. A new host must still verify its available tools and permissions.

This route can use the host's MCP, API, SDK or user-authorized platform UI. The repository's Python programs provide a separate offline validation route. They neither make these live calls nor need to become live adapters before a host can use its existing tools. Here, a “write” creates or changes a platform object; “readback” reads that object again afterward to check the actual result.

## Start with the current task

| A user might ask | Establish first | Deliver |
|---|---|---|
| “Prepare the next test from these videos” | Product, destination, account, event, test question and asset fit | Selection reasons, exclusions, batch configuration and budget |
| “Build or update this confirmed batch” | Plan version, objects/actions, budget, dependencies, current state and authorization | Per-operation records, configuration readback, partial failures and open items |
| “Review these accounts for changes” | Time window, account coverage, current method and previous open items | Evidence, recommendations, missing data and follow-ups |
| “Move this campaign to another account” | Source structure, target access, reusable identities/events/media and overlapping spend | Object mapping, differences, authorized operations and checks |
| “This ad is not spending / was rejected / is misconfigured” | Effective and parent state, review/error details and recent changes | Diagnosis, evidence, recovery options and results |
| “Give me a daily report by product or offer” | Date/timezone, channels/accounts, cost/conversion/revenue sources and mapping rules | A readable report, coverage notes and traceable detail |

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

Business type determines which facts matter: IAA means revenue from in-app advertising, IAP means revenue from in-app purchases, and hybrid monetization combines both. Web businesses may track purchases, form submissions or sales-qualified leads. Unknown lifetime revenue stays unknown. The author's historical structures, budget ladders and stop-loss numbers are not universal defaults.

### Experienced buyer example: a daily report using an existing SOP

This fictional read-only task needs no asset selection or ad creation. SOP means the user's existing standard operating procedure.

> ‘Use my existing rules for yesterday's report: cover the two selected accounts and combine spend and form submissions by product; take qualified leads from the sales sheet. Recheck whether the previous recommendations were implemented before suggesting changes. Do not change accounts in this task.’

| Step | What the agent does | What the user can check |
|---|---|---|
| Organize the existing method | Preserve product-level aggregation, the sales-sheet lead definition, prior-action checks and read-only scope | A summary of constants; no substitution with a default creative test |
| Identify variables and missing inputs | Update dates and actual data each round; reuse known timezones, product mapping and prior records; ask only for missing sales dates or matching rules | The reporting window and the gaps that affect conclusions |
| Read facts | Read authorized data, check coverage for both accounts and product mapping, and inspect current state for prior objects | Sources, read times, detail and a distinction between checked and not yet checkable items |
| Hand off and continue | Suppose ad data is complete but the sales sheet and traceable prior-action records are unavailable | Deliver spend and form results; qualified-lead cost and the effects of earlier recommendations remain unresolved; list the required inputs |

The handoff states: ‘Read-only; no account changes. Supply the matching sales sheet and prior execution records before the next review.’ Successful retrieval does not verify lead quality, and missing prior records do not prove a recommendation went unexecuted. Without an agreed threshold, retain observations and gaps rather than inventing a pause or scaling number.

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

Have the agent organize the [task record](../templates/task-record.md) from this conversation and actual tool results, in the private location you allow for this task. You check scope, reasoning and decisions rather than manually filling every field; read-only tasks can skip publishing sections. Keep business facts, native IDs, receipts and assets out of the public repository. Connections and methods can change while preparation, review, execution and verification remain reusable.

In a new host, begin with a read or preparation task, then validate writes and readback within explicit authorization. A historical case from an agent tool does not prove another host is configured or every advertising product on all three platforms is supported.

**Next task:** after a report, ask the agent to collect the missing evidence before another review; for a new batch, reuse confirmed context and prepare the review in step 3. If the business or collaboration changes, update the relevant part of [business context and collaboration](first-run.md).

**For developers:** for public-code checks of planning, recovery and data validation, use the [offline validation entry points](capability-status.md#offline-validation-entry-points). Simulation approvals and fictional accounts never authorize live work.
