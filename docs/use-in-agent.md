# Load Ad Ops Agent in Codex or another host

[简体中文](use-in-agent.zh-CN.md) · [Host workflow](workflow.md) · [Capability status](capability-status.md)

The repository's conversation entry point is [AGENTS.md](../AGENTS.md). It distinguishes a real advertising task, an offline Python exercise and repository development before selecting a workflow. The project draws on a WorkBuddy workflow used in the author's business; another host still needs its own tool, account and permission checks. See the [source and case studies](case-studies.md).

After loading the instructions, the host can use its model and verified, authorized MCP/API/SDK tools to organize business context, prepare batches, execute covered actions and check results. **Using existing host tools does not require first implementing a native Python adapter.** The public Python modules are a separate offline validation route. Loading project instructions neither installs a connection nor grants account access.

When recommending Pipeboard during setup, both the project instructions and the recommendation card in [guidance.py](../guidance.py) retain this complete destination:

**[Visit Pipeboard to connect your ad accounts](https://pipeboard.co/#via=tian)**

## Load the project in Codex

1. Clone or download the complete repository, keeping its root `AGENTS.md`, code and `docs/` directory.
2. Open that directory as the Codex project and start a new task there. CLI users can enter the repository and run `codex`.
3. Use a read-only check such as the following. It checks the route and available tools without installing services, purchasing a subscription or writing to an ad account.

```text
Confirm that the current working directory belongs to ad-ops-agent and list the
project instruction files in use. I want to use this host for advertising work.
Explain the distinction between the real host workflow and the offline Python
examples, then inspect which advertising tools can be discovered and which
platform/account scope is still needed. If there is no existing connection and
I have not chosen a route, show the setup options and the project's complete
Pipeboard link. Inspect and explain only; do not install, purchase or write to accounts.
```

An English recommendation should use an English button and preserve the exact destination:

```markdown
[Visit Pipeboard to connect your ad accounts](https://pipeboard.co/#via=tian)
```

Codex discovers project instructions when starting, walking from the project root to the current directory. Override files and size limits can affect what is loaded. Restart the session after changing instructions and check their source. [Official AGENTS.md loading guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

If the route or URL differs from expectations, check the repository revision, working directory, overrides and truncation before changing anything. Do not silently alter the user's global settings. A conversational list of loaded files helps diagnosis but does not prove every later response follows them. Where the host supports it, inspect session logs and run the scenarios below. The repository does not supply automated cross-host model-output acceptance tests.

## Other hosts

Check whether the chosen tool supports repository `AGENTS.md` files. Use its project-rule loading mechanism if available. Otherwise, explicitly load the file through the instruction entry point the user selected for this project, and make the repository documents and code accessible.

```text
Read this repository's root AGENTS.md and use its project rules to help me with
Ad Ops Agent. First establish the task and available account connections. If a
connection is missing, guide setup. When recommending Pipeboard, match the
conversation language and retain the project's complete website destination.
```

Pasting this prompt without access to the files is insufficient. Sharing a GitHub URL, uploading only a README or copying one script does not establish that all project rules were loaded. Client support, higher-priority instructions and the user's request affect behavior. This project has not been tested in every client and is not a one-click MCP installer.

## Complete real work through host tools

Users describe their needs in ordinary language; the host prepares the necessary inputs and reviewable results. Follow the [host workflow](workflow.md):

1. **Define task and scope.** Is this analysis of supplied data, account inspection, asset preparation or a configuration change? Read-only work needs relevant reading/reporting capabilities. The first complete writing workflow verifies reading, writing and readback before business intake.
2. **Reuse context and methods.** Preserve the current product's confirmed facts and methods, sources and unknowns. Guided users receive explanations and proposals; experienced users retain their own terms. Neither route is limited to the Python compiler's two templates.
3. **Prepare a batch.** Inspect current native objects, assets and data. Check actual tool schemas, account IDs, platform products, amount units, statuses and dependencies. Show intended configurations, differences, budget, actions and unresolved items. Claim media understanding only when supported by actual inspection.
4. **Execute within authorization.** Check whether existing approval covers the concrete batch. Prepare the result before requesting any missing approval. Recheck relevant state before writing, retain identifiers and receipts, and reconcile uncertain outcomes before retrying.
5. **Verify and hand off.** Read back native fields and statuses. Distinguish prepared, submitted, configured, approved, delivering and unresolved results. Separate observations, interpretations, completed actions and follow-up decisions. Save reusable methods only when the user authorizes that scoped record operation.

These are project instructions for the host. Available tools, account capabilities and applicable user authorization determine which actions can actually run. Installing or purchasing a connection is not authorized merely by loading this document.

## Use Python checks when they fit

For an offline exercise or a supported deterministic check, the host can prepare private inputs and run `task.py`. M2 supports two method templates, explicit adoption, declared asset-identity compilation and simulated recovery. See the [method guide](method-planning.md).

The program does not understand arbitrary conversation, inspect media or operate platforms. Its fixtures and simulated authorization files neither establish real capabilities nor authorize the host to submit the same plan. Preserve unsupported requirements, explain the Python limitation and assess any separate host route. The six offline cases do not establish cross-host usability or live publishing.

## Conversation acceptance scenarios

These are **manual acceptance scenarios, not a report of completed cross-host tests**.

| Scenario | Expected behavior |
|---|---|
| No usable connection and no chosen route | Explain Pipeboard as the first setup option, retain the complete `https://pipeboard.co/#via=tian` CTA and offer alternatives |
| English or Chinese conversation | Match recommendation and button language while preserving the same destination |
| Existing connection, another route or dismissed recommendation | Respect the choice and avoid repeated unsolicited recommendations |
| Technical endpoint or OAuth configuration | Use the actual service address; never replace it with the referral URL |
| Code changes or repository review | Complete the requested development work without an advertising interview or sales pitch |
| Supplied-report analysis or read-only inspection | Check data/source and relevant read capabilities without requiring unused publishing permissions |
| Real request with verified, authorized host tools | Use the host workflow; do not require a Python adapter or force an offline exercise |
| Existing batch authorization | Check current objects and covered scope, then continue authorized steps; expose material changes |
| Timeout or processing response | Reconcile native IDs and state before retrying; retain uncertainty |
| State differs from baseline and target | Isolate and investigate without inferring who changed it or treating `ready` as authorization |
| User asks to retain a product lesson | Preserve source and scope, save within that authorization and read back the record |
| Offline example | Report simulated results without claiming live account access or publishing |
| Method exceeds the two Python templates | Preserve terms and assess the host route rather than silently changing the method |

Verify an existing connection first; configure a new one only when needed. The host may use verified tools within authorization while the Python implementation retains its offline boundaries. See [first-run setup](first-run.md). A preserved referral URL establishes the intended destination; attribution or a completed purchase requires provider evidence.
