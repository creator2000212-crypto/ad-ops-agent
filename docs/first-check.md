# First use: get your first useful result

[简体中文](first-check.zh-CN.md) · [Project home](../README.md) · [Documentation](index.en.md)

**For:** product owners and media buyers using this project for the first time. **Outcome:** a launch-preparation checklist, an account findings report, or a review of your existing method. Supply context through conversation; no coding or JSON editing is required.

Follow **open the project → verify the connection and account → explain the current need → choose one task → check the result**. Skip steps already completed and still valid for this task.

This page illustrates **an agent tool + Pipeboard + one Meta (Facebook / Instagram) account**. Keep an existing connection and verify the same necessary reading capabilities. See [connection options](platform-connectivity.md) for TikTok / Google. All first tasks here read and prepare only: no ad creation, budget changes or status changes. Later publishing requires the necessary capabilities, a concrete plan and covered authorization.

> Validation: setup sources were checked on 2026-09-25. There is no recorded end-to-end fresh-environment run or independent-user pass for this tutorial yet. [Validation scope](#validation).

## What to bring

- An agent tool that can read project files and use the relevant advertising connection, plus an account you are authorized to access. Choose a connection in step 2 if needed.
- Any existing product description, destination page, assets or SOP (your established working method). The agent asks for missing details that affect this task.
- To see the output without connecting an account, read the [course-business example](build-from-zero.md) or [offline walkthrough](../demo/README.md). No Python installation is needed to read them.

<details>
<summary><strong>What do these terms mean?</strong></summary>

| Term | What you need to know now |
| --- | --- |
| Agent tool / host | The software where you talk to AI and let it read files and use tools |
| This project | Working instructions, workflows and reference material opened in your agent tool |
| MCP / connector | A way for the agent to use external advertising tools; APIs / SDKs are other technical connection routes |
| `AGENTS.md` | This project's instructions for the agent; opening a folder alone does not prove they loaded |
| Read-only | View data and configuration without changing accounts |
| Readback | Read an object again after an operation to check it against the plan; used in later writing tasks |

</details>

<a id="open-project"></a>

## 1. Download and open the project

**You:** open the [repository](https://github.com/creator2000212-crypto/ad-ops-agent), select **Code → Download ZIP**, and extract the download. In your agent tool, open the extracted project folder, normally named `ad-ops-agent-main`. The exact menu depends on the client. [GitHub download instructions](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives)

Select the folder containing these files, rather than its enclosing downloads folder or one Markdown file:

```text
ad-ops-agent-main/
├── AGENTS.md
├── README.md
└── docs/
```

**Ask the agent to check:** send this in the project conversation:

```text
Read the current project's root AGENTS.md and docs/workflow.md.
Identify the instruction files you actually read. If any are inaccessible, name the missing file or access capability.
Reuse known context and ask only about gaps affecting this task. Do not operate on ad accounts yet.
```

**Done when:** file tools can read these files, and the response identifies the rules used and uncertain loading details. Check instruction logs if the host exposes them. If files are inaccessible, use [project loading and troubleshooting](use-in-agent.md), then return here. Pasting a GitHub URL alone does not establish that the complete project loaded.

<details>
<summary>Git users can clone instead</summary>

```bash
git clone https://github.com/creator2000212-crypto/ad-ops-agent.git
cd ad-ops-agent
```

Open that directory in your agent tool. A ZIP is a snapshot at download time; later updates require a new download or a Git update. Keep your business materials in a private directory outside the repository.

</details>

<a id="connect"></a>

## 2. Prepare the account connection

**Already connected:** go to step 3 to verify this account; no repeat purchase or setup is needed. **No route selected:** consider Pipeboard first to reduce connection maintenance; [visit Pipeboard to connect your ad accounts](https://pipeboard.co/#via=tian). Check current plans and account access. Other routes remain available in the [connection reference](platform-connectivity.md).

**You:** connect Meta on Pipeboard's Connections page and select the permitted accounts. Then configure a remote MCP connection in a compatible agent tool:

| Setting | Value or action |
| --- | --- |
| Name | A recognizable name, such as `Pipeboard Ads` |
| Connection type | Streamable HTTP, a transport for remote MCP |
| Server URL | `https://ads.mcp.pipeboard.co/` |
| Sign-in / authorization | Use the consent flow in a client supporting the required OAuth process; otherwise follow the official instructions using the client's secure configuration |

These fields follow the [official Pipeboard setup guide](https://pipeboard.co/guides/ads-mcp). Menus vary by client; if no setting is available, check whether the client supports this connection. An existing Meta-specific connection can remain in use.

Prefer available read-only credentials or tool restrictions for this task; see the [permission guide](https://pipeboard.co/guides/api-token-permissions) for availability. A read-only chat instruction is not a server-side permission restriction. Keep tokens out of conversations and the repository.

**Done when:** the client discovers account, object and report reading tools. The next step verifies the account through an actual read; a connection-success message alone is insufficient.

<a id="verify-account"></a>

## 3. Verify one account

Send this request and select the account from the actual returned list:

```text
Inspect the current advertising connection using reading tools only.
List the authorized Meta accounts for me to select, without reading other accounts' performance.
If I already selected an account, verify it by its native account ID.
Read its name, time zone and currency; identify the source, read time and missing fields.
Do not install services, expand authorization, create objects or modify accounts.
```

**The agent delivers:** the selected platform/account, available basic information, sources, timestamps and gaps. Use native account IDs for verification in the private conversation; redact them for public sharing.

**Done when:** the selected account is actually readable. Explain the effect of unavailable fields and resolve prerequisites for dependent tasks. Example JSON, `ready_simulation` or an unsupported claim of connection is not a real read. Resolve missing access through [troubleshooting](#troubleshooting), retaining information already supplied.

<a id="choose-task"></a>

## 4. Explain the need and choose one task

After connection verification, the agent reuses known information and asks at most three initial questions: **Are ads already running? What do you want to accomplish now? Do you have a method or want guidance?** Experience changes explanation depth, not permissions. [Business and working preferences](first-run.md) explains the context needed; you need not read it all or complete a full questionnaire first.

| Your situation | First task | Deliverable |
| --- | --- | --- |
| Product ready, no advertising history | A: prepare to launch | Business brief, gaps, asset checklist and candidate test directions |
| Already advertising, need a clear picture | B: inspect one complete day | Sourced report, observations, data problems and next steps |
| Existing SOP, seeking efficiency | C: review and retain the method | Original terms, support status, missing conditions and a proposal for review |

<details>
<summary><strong>A · Product ready, no campaigns yet: copy this task</strong></summary>

```text
The account has been verified. I have a product but have not started advertising, and want guidance preparing my first test.
Read the product description, destination page and existing assets I provide; identify anything inaccessible.
Establish the target countries, Web or App, conversion journey, what counts as a useful result, and my budget boundary.
Reuse information already provided. Ask only about gaps affecting preparation, without inventing answers.
Deliver a business brief, asset checklist and candidate test directions with applicability conditions. I will confirm budget and method.
Prepare only; do not create or publish ads.
```

**Done when:** the user can correct the brief and knows what is missing, who supplies it and what will be reviewed next. Record an absence of advertising history explicitly; do not invent results or promise performance.

</details>

<details>
<summary><strong>B · Already advertising: copy this account check</strong></summary>

```text
For the selected Meta account, inspect the calendar day that just ended in its time zone. Do not skip a no-spend day.
State the exact date, time zone, currency, reporting level, result event, attribution definition and data cutoff.
Read account and ad-set performance, checking pagination and coverage. Do not replace missing data with zero.
Reuse known business context, confirmed methods and prior open items; ask only about gaps affecting interpretation.
Without a confirmed target cost or method, report facts rather than inventing stop-loss or scaling thresholds.
Separate platform-attributed results from backend qualified leads or revenue; state known attribution and maturity limits.
If current object states are needed, state their read time separately from the performance period.
Deliver scope and completeness, observations, recommendations with evidence, open questions, sources and next steps.
Analyze only; do not change accounts, budgets, statuses or assets.
```

A complete day is the calendar day that just ended in the account's time zone; conversion backfill and revenue may still arrive later. If the account has never advertised, consider A. An empty response alone does not prove zero spend.

</details>

<details>
<summary><strong>C · Existing SOP: copy this method review</strong></summary>

```text
Read the existing SOP I provide and reuse the verified account and business context.
Trace its scope, fixed rules, allowed changes, metrics and observation conditions to the original source.
List missing information, conflicting terms, and capabilities the current tools lack or have not verified.
Preserve my method rather than automatically replacing it with a default template. Ask only about gaps affecting this task.
Deliver a method review and suggested next task for my confirmation. Do not modify accounts yet.
```

**Done when:** each key rule maps to its source, with supported, unresolved and unavailable parts separated. Host tasks can include reporting; SOPs need not be converted into Python's two creative-test templates.

</details>

<a id="check-result"></a>

## 5. See a result, then check yours

This **fictional report example** for B reuses the numbers in the [course-business example](build-from-zero.md) and adds fictional reporting context. It is neither an actual tool receipt nor verbatim output from this repository's program.

> **Scope:** course account A; 2026-09-23; America/Los_Angeles; USD. This example additionally assumes two separate ad sets, using creative A and B respectively; the figures are at ad-set level and cover both ad sets.
>
> **Source:** fictional platform report; extraction set to 2026-09-24 09:00 in the same time zone, with data as of that time. Event: appointment-form submission; example attribution: 7 days after a click. Use actual source definitions in a real task.
>
> **Overview:** $30 spent, 4 submissions, $7.50 per submission. A: $18 / 3 / $6; B: $12 / 1 / $12.
>
> **Observation:** A had a lower submission cost that day; the sample is small and attribution may backfill.
>
> **Gap:** sales-confirmed qualified appointments are missing, so lead quality cannot be compared. Forms are not automatically qualified customers.
>
> **Next:** the business owner supplies qualified-appointment data; the agent consolidates the review after the agreed observation period. There is insufficient evidence to declare a winner or scale.
>
> **Actions:** analysis only; no account changes.

| Deliverable | What to check |
| --- | --- |
| A: preparation | Known business facts, sources, essential gaps, checklist and candidate directions; unconfirmed budget stays unresolved |
| B: account report | Account, date, time zone, currency, level, event/attribution, extraction time, coverage and gaps |
| C: method review | Original terms mapped to handling; constants, variables, conflicts, support status and next steps |
| All three | Facts separated from interpretation; clear ownership and resumption; preparation or advice is not described as execution |

For B, compare one ad set with the platform UI using the **same date, time zone, level, event and attribution definition**. Record privately: `object | report value | UI value | both read times | matched or unresolved difference`. Keep unresolved differences open. Do not add account totals to their own detail rows.

**Partial delivery needs a clear handoff too.** For example: “Account metadata was read, but report access was denied. Performance data is unavailable. Ask the account administrator to check reporting access, then resume at step 3. No performance conclusion was generated.” This hands off a gap; it does not complete the account report.

<a id="next-task"></a>

## 6. Choose the next task

- **Preparation confirmed:** use the [daily workflow](workflow.md) to prepare a creative-test or campaign batch for review, retaining unresolved conditions.
- **Report checked:** resolve data gaps or propose adjustments for your decision. Before later writes, verify required writing/readback capabilities and authorization for that batch.
- **Method confirmed:** give the agent one task using that method, such as reporting or asset selection. A new task does not require repeating the whole intake.

The agent normally assembles task records from conversation and actual evidence; you check key decisions. When saving is needed, choose your own private directory and use the [task template](../templates/task-record.md). Cross-session reuse requires accessible saved context, not an assumption of permanent memory from one conversation.

<a id="troubleshooting"></a>

## When stuck: resolve the gap and resume

| Symptom | Agent checks and explains | Your action | Resume |
| --- | --- | --- | --- |
| Cannot read `AGENTS.md` | Available file scope and missing path | Open the extracted folder containing it; see [loading help](use-in-agent.md) | Step 1 |
| Connected, but no reading tools | Actual tool inventory and client connection support | Compare server URL and authorization with official guidance | Step 2 |
| Accounts listed, target absent | Returned scope and source; no guessed account IDs | Check platform identity and selected authorized accounts | Step 3 |
| Empty or denied report | Dates, time zone, filters, pagination and actual error category | Supply only missing reading access or scope, not all write permissions | Step 3, then retry B |
| Spend present, results or backend quality missing | Missing event definition, field or source | Supply the definition or backend source; accept a partial report if useful | Original task in step 4 |
| Creation or budget requests appear | Requested task versus intended tool call | Keep this task read-only; review a later write batch separately | Original task in step 4 |

You can ask: “List what is verified, the actual error category, missing conditions, who resolves them and where to resume. Do not substitute example data for real reads or install services or expand permissions yourself.”

<a id="validation"></a>

<details>
<summary><strong>Validation scope and maintainer trial records</strong></summary>

| Item | Current evidence |
| --- | --- |
| Documented route | Agent tool with project-file and remote MCP access → Pipeboard → one Meta account |
| Official source review | 2026-09-25: GitHub downloads, Pipeboard server, authentication and permissions; sources above |
| Business provenance | Historical Meta/TikTok work in the [cases](case-studies.md), not acceptance of this tutorial |
| Complete tutorial run | No recorded end-to-end run from a fresh environment yet |
| Specific client, version, independent users | Pending; no combination or external-user pass is claimed |

Maintainers can next record an actual client's menus and successful reads, then invite 2–3 people uninvolved in development to try the guide. The [independent trial record](../templates/task-record.md#first-use-validation) captures friction and assistance. Keep evidence private, redact and obtain consent before sharing. First-time users do not need to perform extra testing for this appendix.

</details>
