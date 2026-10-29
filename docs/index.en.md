# Documentation guide

[Project home](../README.md) · [中文导航](index.md) · [Real vs demo](capability-status.md)

**Choose the question you have now. You do not need to read the technical documents in order.** Pages without an English version are marked **Chinese**.

## See the work

Start with [How it ran](how-it-ran.md): what ran in WorkBuddy on live Meta and TikTok accounts in Sep–Oct 2026, the run log of the scheduled jobs, and what each piece became here. Then read the [twenty-two case studies](case-studies.md), the [methodology history](methodology-history.md) and [Real vs demo](capability-status.md). To see the checks run, try the [offline demo](../demo/README.md), [Build QA](build-qa.md), the [account audit](account-audit.md) and the [decision matrix](decision-matrix.md). The original private records are not public.

## Start a task

**Start with [First use: get your first useful result](first-check.md).** This is the main first-use path: open the project → verify connection/account access → establish the need → choose preparation, an account check or SOP review → check the result. Reuse completed steps that still apply; no other page is mandatory reading first.

Open a reference only when needed:

- Files or project rules are inaccessible: [project loading and troubleshooting](use-in-agent.md); then return to the same tutorial step.
- Unsure what business context to provide: [business and working preferences](first-run.md).
- Need a different connector or platform: [connection reference](platform-connectivity.md).
- First result complete, ready for ongoing work: [daily workflow](workflow.md). The agent can assemble a [task record](../templates/task-record.md) from evidence in a private location you authorize.

## Run the public code

[Offline demonstration](../demo/README.md) → [Build QA](build-qa.md) → [Real vs demo](capability-status.md) → [Architecture (Chinese)](architecture.md) → [Roadmap (Chinese)](roadmap.md). Public Python uses fictional inputs and does not execute on an ad platform.

## Find a topic

### Business and buying methods

| Question | Read |
| --- | --- |
| Build a workflow from a concrete business and assets | [Worked example](build-from-zero.md) |
| Explain the business, goals and working preferences | [Business and working preferences](first-run.md) |
| Bring a SOP or compare test methods | [Daily workflow](workflow.md) · [Two-method comparison](method-comparison.md) |
| Check knowledge applicability and evidence gaps | [Knowledge base (Chinese)](knowledge-base.zh-CN.md) |
| Save or revise private methods within a product scope | [Private methods (Chinese)](private-memory.zh-CN.md) |

### Connection and first use

| Question | Read |
| --- | --- |
| Follow one route to your first result | [First use](first-check.md) |
| Complete task-relevant context after connecting | [Business and working preferences](first-run.md) |
| Verify that the host loaded project instructions | [Project loading and troubleshooting](use-in-agent.md) |
| Explore Meta, TikTok and Google connection routes | [Platform connectivity](platform-connectivity.md) |
| Apply for Google Ads API access | [Application guide (Chinese)](google-ads-api-application.zh-CN.md) |

### Execution, checks and review

| Question | Read |
| --- | --- |
| Prepare, confirm, execute, read back and hand off | [Host workflow](workflow.md) |
| Record a plan, confirmation and next actions | [Task record template](../templates/task-record.md) |
| Check assets, posts, links, budgets and states | [Operations cards (Chinese)](operations.md) |
| Handle a disapproval or a failed media upload | [Disapproval triage: fix or appeal](disapproval-triage.md) |
| Lint a build before creating it; check readback before activating | [Build QA: pre-flight and readback](build-qa.md) |
| Audit running accounts before a round decides; check each write's unit, ceiling and locked fields | [Account audit](account-audit.md) |
| See every action with its window, acceptance and stop condition | [Decision matrix](decision-matrix.md) |
| Inspect offline monitoring fields, formulas and commands | [Technical reference](operating-loop.md) |

### Evidence, implementation and contribution

| Question | Read |
| --- | --- |
| See what ran live, the run log and the limits | [How it ran](how-it-ran.md) |
| Read the cases and the guardrail each one produced | [Case studies](case-studies.md) |
| See how the method changed and why | [Methodology history](methodology-history.md) |
| Separate what ran live from what runs here | [Real vs demo](capability-status.md) |
| Understand modules and future work | [Architecture (Chinese)](architecture.md) · [Roadmap (Chinese)](roadmap.md) |
| Contribute a workflow or native adapter | [Contributing](../CONTRIBUTING.md) |

Developer references: [Python method planning](method-planning.md) · [Onboarding state design (Chinese)](onboarding.md). These are not prerequisites for using the host workflow.

<details>
<summary><strong>Structured design contracts</strong></summary>

| File | Purpose |
| --- | --- |
| [connector-contract.json](../contracts/connector-contract.json) | Vendor-neutral connector and capability mapping |
| [disapproval-triage.json](../contracts/disapproval-triage.json) | Disapproval triage routes, prohibited actions, records and stop conditions |
| [acceptance-scenarios.json](../contracts/acceptance-scenarios.json) | Integration scenarios, not completed test results |
| [experience-catalog.json](../contracts/experience-catalog.json) | Scoped candidate experience, not automatic optimization rules |
| [onboarding-extensions.json](../contracts/onboarding-extensions.json) | Proposed field extensions, not a list of fields the CLI already accepts |

`contracts/` is an implementation reference; the offline program does not load those files automatically. Public knowledge data lives in [knowledge/catalog.json](../knowledge/catalog.json). Explicitly enabled local storage keeps private methods scoped to a product.
</details>

### Working rule

A read-only task checks only the access it needs. Creating, changing or restructuring objects requires a concrete plan, an action scope and user confirmation. Verify prior actions before judging outcomes. Without a connection, choose among the official platform APIs, a self-hosted MCP server and a hosted MCP connector by their trade-offs, in no particular order; verify an existing connection directly. Actual capability depends on the current host, tools, accounts and ad product.
