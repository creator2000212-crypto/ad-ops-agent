# Documentation guide

[Project home](../README.md) · [中文导航](index.md) · [Capability scope](capability-status.md)

**Choose the question you have now. You do not need to read the technical documents in order.** Pages without an English version are marked **Chinese**.

## See the work

Start with the [Meta preparation](case-studies.md#meta-task) and [TikTok status handoff](case-studies.md#tiktok-task), then read the [six anonymized cases](case-studies.md) and [product design (Chinese)](product.md). The original private records are not public.

## Start a task

[First setup](first-run.md) → [Load and validate](use-in-agent.md) → [Host workflow](workflow.md) → [Task record](../templates/task-record.md). Confirm this task's account scope, tools and authorization; reuse known product context and methods, and ask about missing items.

## Run the public code

[Offline demonstration](../demo/README.md) → [Commands and capability scope](capability-status.md) → [Architecture (Chinese)](architecture.md) → [Roadmap (Chinese)](roadmap.md). Public Python uses fictional inputs and does not execute on an ad platform.

## Find a topic

### Business and buying methods

| Question | Read |
| --- | --- |
| Build a workflow from a concrete business and assets | [Worked example](build-from-zero.md) |
| Understand the business and preserve source context | [Business onboarding (Chinese)](onboarding.md) |
| Bring a SOP and prepare a reviewable test | [Method planning](method-planning.md) · [Two-method comparison](method-comparison.md) |
| Check knowledge applicability and evidence gaps | [Knowledge base (Chinese)](knowledge-base.zh-CN.md) |
| Save or revise private methods within a product scope | [Private methods (Chinese)](private-memory.zh-CN.md) |

### Connection and first use

| Question | Read |
| --- | --- |
| Configure the project for the first time | [First setup](first-run.md) |
| Verify that the host loaded project instructions | [Loading and validation](use-in-agent.md) |
| Explore Meta, TikTok and Google connection routes | [Platform connectivity](platform-connectivity.md) |
| Apply for Google Ads API access | [Application guide (Chinese)](google-ads-api-application.zh-CN.md) |

### Execution, checks and review

| Question | Read |
| --- | --- |
| Prepare, confirm, execute, read back and hand off | [Host workflow](workflow.md) |
| Record a plan, confirmation and next actions | [Task record template](../templates/task-record.md) |
| Check assets, posts, links, budgets and states | [Operations cards (Chinese)](operations.md) · [Meta creative recovery (Chinese)](meta-creative-recovery.md) |
| Inspect offline monitoring fields, formulas and commands | [Technical reference](operating-loop.md) |

### Evidence, implementation and contribution

| Question | Read |
| --- | --- |
| Understand actual work and its evidence limits | [Anonymized cases](case-studies.md) |
| Distinguish business history, host tools and public Python | [Capability matrix](capability-status.md) |
| Understand modules and future work | [Architecture (Chinese)](architecture.md) · [Roadmap (Chinese)](roadmap.md) |
| Contribute a workflow or native adapter | [Contributing](../CONTRIBUTING.md) |

<details>
<summary><strong>Structured design contracts</strong></summary>

| File | Purpose |
| --- | --- |
| [connector-contract.json](../contracts/connector-contract.json) | Vendor-neutral connector and capability mapping |
| [creative-recovery.json](../contracts/creative-recovery.json) | Conditional recovery actions, records and checks |
| [acceptance-scenarios.json](../contracts/acceptance-scenarios.json) | Integration scenarios, not completed test results |
| [experience-catalog.json](../contracts/experience-catalog.json) | Scoped candidate experience, not automatic optimization rules |
| [onboarding-extensions.json](../contracts/onboarding-extensions.json) | Proposed field extensions, not a list of fields the CLI already accepts |

`contracts/` is an implementation reference; the offline program does not load those files automatically. Public knowledge data lives in [knowledge/catalog.json](../knowledge/catalog.json). Explicitly enabled local storage keeps private methods scoped to a product.
</details>

### Working rule

A read-only task checks only the access it needs. Creating, changing or migrating objects requires a concrete plan, an action scope and user confirmation. Verify prior actions before judging outcomes. Actual capability depends on the current host, tools, accounts and ad product.
