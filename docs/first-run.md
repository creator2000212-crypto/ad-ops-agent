# Help the agent understand your business and working style

[简体中文](first-run.zh-CN.md) · [First use](first-check.md) · [Everyday task workflow](workflow.md)

**Who this is for:** people who have checked the required account connection and want the agent to work with their business and methods. **What you will get:** a reviewable business brief, a current task and a list of missing information. Provide context through conversation; you do not need to write program configuration.

If you have not opened the project or checked its connection, start with [first use](first-check.md). This page reuses verified accounts, tools and existing information, without reinstalling connectors or repeating the whole questionnaire. When analyzing supplied reports, check their sources and scope; advertising write permissions are unnecessary for that task.

## 1. Establish what can be done this time

The agent first identifies the selected platforms, accounts and capabilities actually available. Read-only tasks need relevant reading or reporting access. Before a first complete configuration and publishing workflow, verify necessary reading, writing and the ability to re-read affected objects, then begin full business intake. Unselected platforms and accounts need not be connected; do not create ads just to probe permissions.

When a capability is missing, the agent explains the affected steps and the next connection action. Retain information already supplied and continue independent work supported by current access. If no usable connection or route has been chosen, consider [Pipeboard](https://pipeboard.co/#via=tian) first; an existing MCP, API, SDK or another connection route remains valid. Choices and setup details live in the [connectivity guide](platform-connectivity.md).

A working connection does not authorize publishing or spending. Actual account reads, available tools and permission evidence establish capabilities; public Python offline results cannot replace that evidence. See [capability status](capability-status.md) for scope.

## 2. Use three questions to establish a working style

The agent reuses known information and asks only about gaps, starting with at most three relevant questions.

| What to establish | Plain-language question | How the answer guides the work |
|---|---|---|
| Current stage and need | “Are you already running ads? What would you most like to accomplish this time?” | Distinguishes launch preparation, account analysis and a specific operation |
| Platform experience | “Have you advertised on this platform before?” | Adjusts explanation depth; unknown experience does not block progress |
| Working style | “Would you like help developing a plan, or should I use your method or SOP?” | Offers candidate methods or preserves and checks an existing method |

Experience is platform-specific, and the working style can change between tasks. An experienced Meta buyer starting with Google Ads can request detailed guidance. Advertising expertise does not require knowledge of code or configuration files.

**If you do not have an established method, you can say:**

> The account is connected. I have a course website and want appointment leads, but I do not have an established advertising method. Understand my product, markets, appointment process and existing assets, asking only about gaps that affect the next step. Start with a business brief, a preparation checklist and candidate testing directions. I will confirm the budget.

The agent explains choices and their applicability, then proposes candidates. An unconfirmed suggestion remains a candidate rather than becoming an adopted user method.

**If you already have a method, you can say:**

> The account is connected. Read my SOP and identify the rules to preserve, what may vary, observation conditions and missing information. Then check whether the available tools can support it. Keep my method and prepare a reviewable execution outline; do not modify the account yet.

The agent preserves source terms and references, identifies conflicts, gaps and requirements unsupported by the current tools, and lets the user decide how to handle them. User methods may cover reports, inspections, creative tests or other tasks; they are not limited to the public Python program's two test templates.

## 3. Collect only the context needed for this task

These are prompts to use when relevant, not a questionnaire to complete from top to bottom. The agent reads tool-accessible facts and identifies their sources; the user supplies business meanings, goals and trade-offs. Reuse known information and retain unknowns rather than guessing.

| Current task | What the user provides | What the agent reads, organizes and checks | First deliverable |
|---|---|---|---|
| A product that has not launched ads | Product, markets, audience, conversion journey and existing assets; undecided budget limits stay open | Website or app destinations, available accounts and events, missing materials | Business brief, preparation checklist and candidate testing directions |
| Review existing advertising | Account and date range, question to answer, adopted metrics or methods | Reports, time zone, currency, data coverage and definitions | Sourced observations, suggestions and open questions |
| Work from an existing SOP | Original SOP or file, applicability, current task and fixed conditions | Rules mapped to actual tools, current objects, conflicts and gaps | Restated method, feasible scope and batch draft |

Different businesses call for different context:

- **Web:** where the ad sends users and what counts as a conversion; whether a form submission becomes a qualified lead only after sales confirms it.
- **App:** store destination, operating system and in-app events; whether revenue comes from advertising (IAA), in-app purchases (IAP), or both.
- **Revenue decisions:** the data source, observation window and treatment of refunds; matching metric names do not establish matching definitions.
- **Creative testing or writes:** what to compare, what stays fixed, available assets, whether the budget is total or daily, and observation or adjustment conditions. Undecided write conditions remain in the draft rather than receiving invented defaults.

Ask about these only when they affect the current task. Analyzing yesterday's existing report does not require rebuilding the entire creative strategy.

## 4. Check a business brief, then start the task

This **fictional course website example** illustrates the deliverable. It is not a real account record or a recommended budget.

> **Current task:** prepare initial creative testing directions; do not modify the account.
>
> **Known business:** an English course website for adults in the US; the goal is to book a 15-minute trial lesson.
>
> **Existing materials:** three videos; the user has no established testing method.
>
> **Outcomes to distinguish:** form submissions, qualified appointments and subsequent purchases are separate results.
>
> **Candidate directions:** compare openings for one selling point, or compare different selling points; inspect assets before choosing.
>
> **Open questions:** qualified-appointment definition and source, available conversion event, budget type and cap, observation conditions.
>
> **Next step:** the user confirms or corrects the brief; the agent organizes assets and a plan using confirmed conditions. Unresolved conditions remain in the draft.

| Who is responsible | What they do |
|---|---|
| You | Supply business information unavailable from the account, correct the brief, and decide goals, method and spending boundaries |
| Agent | Read permitted materials, cite sources, distinguish facts, candidate judgments and unknowns, and organize the brief and gaps |
| You and the agent | Confirm the current task scope, identify gaps that affect the next step, and enter the relevant workflow |

**Done means:** both sides can explain the current task, confirmed inputs, remaining gaps and first deliverable. A business brief or method choice does not authorize publishing. Once a concrete write batch is prepared, check existing authorization or obtain missing confirmation, execute covered work and re-read results. Read-only tasks deliver their report directly.

Next, choose the relevant [everyday task workflow](workflow.md). For a complete business example, read the [course website walkthrough](build-from-zero.md). Continue to the appendix only if you need the code interface.

## Developer appendix: offline fields and examples

Ordinary users can skip this section. The host turns conversation into private inputs; the following is the public Python offline contract, not a universal gate for real host tools.

### Connection preferences and simulated capabilities

`setup_preferences.route` records `undecided`, `pipeboard`, `existing`, `self_managed` or `other_mcp`; `setup_preferences.recommendation_dismissed` records a dismissed recommendation. Do not repeat unsolicited recommendations after a route is selected or the recommendation is dismissed. Choosing a route does not prove access.

`onboarding.py` uses `connection_gate` to check simulated reading and `create_simulated_draft` capabilities for four readiness evaluations; `guidance` stays at connection setup when that gate fails. This contract is unchanged. It does not require real read-only tasks to have write permission, and `ready_simulation` is not a live account check.

### Collaboration fields

```json
{
  "experience_by_platform": {"meta": "new", "tiktok": "unknown", "google": "unknown"},
  "approach": "guided",
  "current_need": "Prepare a creative test plan for my first product",
  "explanation": "detailed"
}
```

Store this object in the profile's `collaboration` field. Experience values are `new`, `experienced` and `unknown`; approaches are `guided`, `bring_own` and `undecided`; explanation preferences are `detailed` or `concise`. The offline collaboration gate requires a selected approach and nonempty current need; experience may remain unknown. Python varies questions by approach and records preferences; it does not implement a complete adaptive conversational interface. None of these fields expands account, budget or publishing authority.

M2 is the optional offline method module and compiles only hook comparisons and concept exploration. M1 private text methods provide context and review material; they do not automatically become adopted MethodSpecs. Real host work need not pass through M2. See the [Python method reference](method-planning.md) for its interface and constraints.

### Inspect a deliberately incomplete check

Run from the repository root:

```bash
python3 onboarding.py --input examples/onboarding-setup-required.json --out runs/setup
```

This fictional input lacks connectivity, so **exit code `2` is expected**. Open `runs/setup/setup.md` for guidance, `runs/setup/setup.json` for structured output, and `runs/setup/context.json` for `connection_gate` / `guidance`. Do not edit success fields to claim live access.

`examples/onboarding-learning.json` is a complete fictional profile; `examples/onboarding-app-hybrid-discovery.json` retains business gaps. `python3 scripts/demo.py` checks freshly generated fictional inputs. For method proposals, adoption and recovery, follow the [Python method reference](method-planning.md). None of these examples reads real accounts or establishes cross-host usability.
