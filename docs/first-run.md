# First-run setup: connect the required capabilities, then understand the work

[简体中文](first-run.zh-CN.md) · [Host workflow](workflow.md)

Begin with the task, selected platforms and accounts. A complete configuration/publishing workflow follows **connection → verification of necessary reading, writing and readback → collaboration preferences → business context and methods → preparation, review and execution**. Connecting all three platforms is unnecessary. Read-only analysis needs the relevant reading/reporting access; analysis of supplied reports does not require advertising write permissions.

**The host workflow and public Python modules are separate routes.** The original WorkBuddy workflow has been used in the author's business. In a new host, verify its available tools and account scope. A host can use verified, authorized tools without first implementing Python adapters. Public Python modules evaluate structured inputs and simulated snapshots, compile two bounded method templates and exercise local recovery; they do not connect to real platforms. `ready_simulation` is not proof of live access. See [capability status](capability-status.md).

Load the root [AGENTS.md](../AGENTS.md) to apply project instructions in conversation. The [host loading guide](use-in-agent.md) distinguishes loading rules from installing tools or authorizing accounts.

## 1. Select the task scope and connection route

Establish which platforms/accounts the task uses, whether a connection already exists and which necessary capabilities are missing. Before the first full writing workflow, resolve connection requirements instead of presenting a long business questionnaire. Retain information the user already supplied. For supplied-data analysis, check its scope, definitions and source.

### Without an existing connection, consider Pipeboard first

**Pipeboard is the project's first setup recommendation for users who want less connection maintenance.** Its Ads MCP describes a unified route for authorized Meta, Google Ads and TikTok accounts. Actual operations depend on account permissions, service capabilities and the supported platform product. [Official Ads MCP guide](https://pipeboard.co/guides/ads-mcp)

- A common MCP entry point for supported tools.
- Less custom connection code to maintain.
- Connection of the accounts selected for the current work.

**[Visit Pipeboard to connect your ad accounts](https://pipeboard.co/#via=tian)**

Check current plans, limits and required tools before choosing. The service helps with connectivity; it does not replace methods, assets, measurement or platform review. The host uses the capabilities actually available after connection. A purchase does not add live execution to the Python modules, and the recommendation itself does not authorize installing, purchasing or submitting credentials.

### With an existing connection or a self-managed route

Keep a working MCP/API/SDK connection, use another MCP or follow the [platform connectivity guide](platform-connectivity.md). Verify existing access instead of asking users to switch. Respect another chosen route or a dismissed recommendation.

The offline input records these preferences in `setup_preferences.route` and `setup_preferences.recommendation_dismissed`. Route values are `undecided`, `pipeboard`, `existing`, `self_managed` and `other_mcp`. Choosing a route is a preference, not evidence of successful access.

## 2. Verify the capabilities this task needs

The host checks:

1. Native account IDs, platform identity and authorized account scope.
2. Current connection health and the required reading/reporting tools and permissions.
3. For configuration or publishing, the necessary writing capabilities and a way to read back affected objects.

Read-only access can support inventory, reporting and diagnosis; it cannot replace write capabilities for a writing task. Unselected accounts or platforms need not be connected. Recheck requirements when the task, account or platform changes.

Explain missing capabilities and the steps they block, while continuing independent work that current access supports. For the first complete writing workflow, resolve missing connection capabilities before business intake. Passing a capability check does not authorize publishing, spending or increasing budgets.

Use account discovery, reading results, actual tool schemas and permission evidence. Preserve execution and readback evidence for authorized operations. An installation receipt or the existence of a creation tool is insufficient; do not create live objects merely to test access. Keep tokens in secure configuration, never in the repository, fixtures or logs.

The unchanged Python `onboarding.py` contract still checks simulated reading and `create_simulated_draft` capabilities for its four readiness evaluations. Its `connection_gate` and `guidance` outputs describe that offline route. They are neither a universal gate for host read-only tasks nor a substitute for actual capability evidence.

## 3. Establish how the user wants to collaborate

After the required capabilities are available, reuse known context and ask only missing questions. Start with at most three relevant questions; platform experience may remain unknown and must not independently block progress.

| Information | Example question | Use |
|---|---|---|
| Relevant platform experience | “Have you used Meta Ads before?” | Adjust explanation depth without inferring permissions |
| Collaboration approach | “Would you like step-by-step guidance or to use your existing method?” | Choose `guided` or `bring_own` |
| Current need | “What would you most like to accomplish this time?” | Limit intake to the current task |

For the Python route, these values are recorded in `collaboration`:

```json
{
  "experience_by_platform": {"meta": "new", "tiktok": "unknown", "google": "unknown"},
  "approach": "guided",
  "current_need": "Prepare a creative test plan for my first product",
  "explanation": "detailed"
}
```

Experience values are `new`, `experienced` and `unknown`; approaches are `guided`, `bring_own` and `undecided`; explanation is `detailed` or `concise`. The current need must be nonempty for the offline collaboration gate. Experience and explanation preferences do not expand account, budget or publishing authority.

A user may be experienced on Meta and new to Google Ads, or change approach between tasks. The host adapts its explanations accordingly. Python records these preferences and varies questions by approach; it does not implement a complete adaptive conversation interface.

## 4. Complete context and methods, then work

Gather only the product, market, event, measurement, asset, method and budget information needed for the task. Attribute facts supplied by tools, leave unknowns visible and distinguish user decisions from observed history.

- For `guided`, explain the choices and prepare a reviewable method proposal. A suggestion is not a confirmed method.
- For `bring_own`, preserve original terms, sources, applicable scope and fixed conditions. The method is not restricted to the two Python templates. Explain actual tool limitations without silently deleting requirements.
- Resolve an unknown approach or missing current need before expanding business questions.

Users work through conversation and need not edit JSON. The host explains variables, constants, scope, measurement, asset selection/exclusions and budget before preparing native configurations. If a supported offline check is useful, it can separately prepare inputs for `task.py`. M2 compiles only hook comparisons and concept exploration; private text methods do not automatically become adopted MethodSpecs. See the [method guide](method-planning.md).

For real writes, prepare the batch, check existing authorization or obtain missing confirmation, execute covered steps and read back native objects. Reconcile uncertain outcomes before retrying. Analysis tasks end with sourced results and suggestions without an unnecessary publishing step. See the [host workflow](workflow.md).

## Run the separate offline example

From the repository root:

```bash
python3 onboarding.py --input examples/onboarding-setup-required.json --out runs/setup
```

This deliberately incomplete fixture returns **exit code `2`**. Inspect `setup.md`, `setup.json` and the `connection_gate` / `guidance` fields in `context.json`. Manually changing a field to `ready_simulation` does not verify a real connection.

`examples/onboarding-learning.json` is a complete fictional profile; `examples/onboarding-app-hybrid-discovery.json` has business gaps. Run `python3 scripts/demo.py` to generate and check fresh fictional inputs. `python3 scripts/demo_methods.py` demonstrates method proposals, adoption, compilation and simulated recovery across six fictional cases. None of these examples reads real accounts or proves cross-host usability.
