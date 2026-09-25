# First use: an agent tool + Pipeboard, one read-only Meta check

[简体中文](first-check.zh-CN.md) · [Project home](../README.md) · [Loading help](use-in-agent.md)

**Complete one task: select one Meta ad account, read its latest complete delivery day, and receive a findings report with sources you can check.** Complete step 1 first; if a working connection already exists, skip step 2. This task creates no ads and changes no budgets or object statuses.

## What has been verified

| Item | Current record |
| --- | --- |
| Selected route | An agent tool that reads project files and supports remote MCP → Pipeboard Ads MCP → one selected Meta account |
| Official setup documentation reviewed | September 25, 2026; service addresses, connection method and read permissions; sources in step 2 |
| Historical use | The author carried out Meta/TikTok work through an agent tool; see the [cases and evidence](case-studies.md) |
| Complete run of this tutorial | No complete acceptance record starting in a new environment using these exact steps yet; historical use does not replace that check |
| Specific host/version and independent users | To be recorded during the first trial; no client version or independent user is currently marked as passed |

“Agent tool” follows the project's generic naming. Confirm the selected client's MCP entry point, authentication support and project-rule loading. Missing remote MCP support or repository access must be resolved before dependent steps. [Other connection routes](platform-connectivity.md) remain available.

## 1. Prepare the project and account

- Get the [complete repository](https://github.com/creator2000212-crypto/ad-ops-agent) and open its root, containing `AGENTS.md` and `docs/`, in the agent tool. Pasting a repository URL does not establish that its instructions loaded.
- Start with one Meta account you can access. Keep its native ID available for identity checks in the private task.
- Reuse existing product information, the target event and your SOP. Without a method, begin with coverage, configuration and missing data rather than inventing a buying strategy.

## 2. Connect Pipeboard

Check an existing connection before configuring or purchasing anything again. If needed, [visit Pipeboard to connect your ad accounts](https://pipeboard.co/#via=tian).

1. Connect Meta on Pipeboard's Connections page and select the account needed for this task.
2. Add `https://ads.mcp.pipeboard.co/` to the agent tool as a **Streamable HTTP** MCP server. Use the authorization flow in clients that support the required OAuth mechanism; otherwise follow the provider's instructions and store credentials in the client's secure configuration. [Ads MCP guide](https://pipeboard.co/guides/ads-mcp)
3. An existing Meta-only connection at `https://meta-ads.mcp.pipeboard.co/` can remain in use. [Meta MCP guide](https://pipeboard.co/guides/meta-ads-mcp)
4. Prefer available read-only credentials or tool restrictions for this task. Permission modes and account restrictions depend on the current service plan; check the dashboard and [permissions guide](https://pipeboard.co/guides/api-token-permissions). A read-only prompt is not a server-enforced permission boundary. Keep credentials out of chat, reports and Git.

**Completion signal:** the host discovers actual account, object and reporting read capabilities. Use the tool definitions visible in that session. A connection indicator alone does not establish that the selected account is readable.

## 3. Load the rules and identify the account

Send this in the task with the repository open:

```text
Read this project's root AGENTS.md and follow docs/workflow.md for this read-only task.
Confirm access to project files, identify the rules used and state any loading uncertainty.
Inspect the connected Pipeboard tools; use only account, object and report reads.
List the authorized Meta accounts for me to select, without reading performance for other accounts.
If I already selected an account, match its native ID and return its name, timezone,
currency and read time.
Do not install services, expand account access, create objects or modify accounts.
```

After selection, expect actual read results and their source. Example JSON, `ready_simulation` or an unsupported claim of connection is insufficient. A host's description of loaded rules helps diagnosis; use session loading records where supported. [Loading and troubleshooting](use-in-agent.md)

## 4. Request the first report

After confirming the account, send the following. Add any existing product context and method; no manual configuration-file editing is needed. The latest complete delivery day means the calendar day that just ended in the account's timezone, not the latest day with spend. A complete day does not establish that attribution updates or backend quality and revenue have matured.

```text
Check the calendar day that just ended in the selected Meta account's timezone;
do not skip days without spend. State the exact date, timezone, currency, reporting level,
attribution definition and data cutoff.
Read account and ad-set performance for that day; check pagination and coverage.
Do not turn missing data into zero.
Reuse known product context, target event, confirmed methods and previous open items;
ask only for missing inputs that affect this assessment.
Without an agreed cost target or method, report facts and data issues without inventing
pause or budget-increase thresholds.
Keep platform-attributed events separate from backend qualified leads, revenue or payback.
State when backend data is missing.
State known limits from attribution updates and backend-result maturity;
do not treat yesterday's outcomes as final.
Read relevant current object states if necessary, separating their read time from the
historical performance window.
Deliver scope and completeness, observations, suggestions with reasons, open decisions,
sources and next steps.
Analyze only. Do not create or modify ads, budgets, statuses or creatives.
```

## 5. Check the deliverable

| Report section | What to expect |
| --- | --- |
| Scope and completeness | One identified account, date, timezone, currency and cutoff; complete, partial or blocked coverage |
| Data and sources | Reporting level, tool/read times, pagination and coverage; defined result event and attribution settings |
| Observations | Objects needing attention, their evidence and limits; unknown, absent and observed zero values distinguished |
| Suggestions | The user's method as a basis, or an explicit missing-method note; suggestions separated from completed actions |
| Open items | Specific missing input, affected judgment and next owner; no writes performed in this task |

Check one ad set in Meta's interface using the **same date, timezone, level, event and attribution definition**. For discrepancies, align read times, filters and definitions, then retain any unresolved difference. Do not add an account total to its detail rows or claim that one day's data proves a method works.

**Complete:** the selected account is actually readable, required coverage is stated, the report and sampled comparison have evidence, and the user understands the limits. Partial data, missing events or unresolved differences can support a partial handoff with open items. An unreadable account warrants a gap report, not invented performance data.

## If a step fails

| Symptom | Next check |
| --- | --- |
| Chat works, but `AGENTS.md` cannot be read | Verify the complete repository and file access in this task |
| MCP appears connected, but no read tools are visible | Check remote MCP support, tool discovery and connection state against actual definitions |
| Accounts are listed, but the selected one is missing | Check platform identity, Pipeboard account selection and current access; retain the gap |
| The account is readable, but the report is empty | Check dates, timezone, filters, pagination and permissions; an empty response is not automatically zero spend |
| Spend exists but conversion or backend quality data is absent | Identify a missing event definition or data source before drawing optimization conclusions |
| A create, upload or budget-change action is requested | Stop that action and return to this task's read scope |

## Test the tutorial with an independent user

A next step is to invite two or three people who did not build the project to follow this page. Use the [first-use section of the task template](../templates/task-record.md#first-use-validation) to record host/version, repository revision, completion stage, blockers, author assistance and the final deliverable. Keep necessary evidence private; anonymize and obtain participant consent before sharing. The blank template is not a completed trial.

After the first report, use [first-run setup](first-run.md) to fill task-relevant business gaps or follow the [workflow](workflow.md) for another task. Publishing and configuration changes require their own concrete plan and applicable authorization.
