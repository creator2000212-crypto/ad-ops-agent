# Load Ad Ops Agent in Codex or another host

[简体中文](use-in-agent.zh-CN.md) · [First read-only task](first-check.md) · [Platform connections](platform-connectivity.md)

Load the complete repository, confirm that the host can read its instructions, then check the tools needed for your first task. The conversation entry point is [AGENTS.md](../AGENTS.md); it routes real advertising work, offline exercises and repository development separately.

The host can use verified, authorized MCP/API/SDK tools for real work without first implementing this repository's Python adapters. Loading the files does not install those tools or grant account access. The public Python modules remain a separate offline route; see [capability status](capability-status.md).

## 1. Make the complete repository available

Clone or download the repository and keep its structure, including the root `AGENTS.md`, code and `docs/` directory. A GitHub URL, a README upload or a copied script alone does not establish that the host can read the project instructions and their references.

- **Codex:** use the repository directory as the task's project. CLI users can start Codex from that directory. Project instruction discovery follows the path from the project root to the current directory; overrides and size limits can affect the result. After changing instructions, start a new run and check their source. See the official [project instructions guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [project directory guidance](https://learn.chatgpt.com/docs/projects).
- **Another host:** use its documented project-rule mechanism, if available. Otherwise, explicitly ask it to read the root `AGENTS.md` and make the referenced files accessible through that host's supported file tools. Do not assume every client automatically loads that filename.

The repository has not been validated in every host. Check the files and tools actually available in the current task.

## 2. Check loading and reading tools

Send this prompt in the project task:

```text
Read the repository's root AGENTS.md and confirm the current project directory.
List the instruction files you can verify and report anything inaccessible or uncertain.
I want to begin with a read-only advertising task. Explain which available tools
can discover accounts and read reports, and what platform/account scope is still needed.
Reuse my existing connection or chosen route. If access is missing, identify the
specific gap and point me to the platform connection guide.
Inspect and explain only; do not install services, purchase or write to accounts.
```

A useful response names the instruction sources, distinguishes host tools from offline Python, and reports actual tool evidence or a specific access gap. Discovering a tool is not proof that it can read the selected account. For supplied-file analysis, check the files and their coverage instead of requiring an account connection.

If instructions appear missing, inspect the repository version, working directory, overrides and truncation. A model's claim to have loaded a file helps diagnosis but does not prove subsequent behavior. Use instruction or session logs when the host exposes them; this guide does not authorize changes to global configuration.

## 3. Complete the first read-only task

Follow the [first read-only task tutorial](first-check.md) for a scoped account and report check. It gives a prompt, expected output and acceptance criteria for another host with Pipeboard. If you already use another connection, keep that route and verify the same required reading capabilities.

For missing access or a new connection, use the [platform connection guide](platform-connectivity.md). For broader business work after this check, continue with the [host workflow](workflow.md). Reading access is sufficient for this first task; a later configuration or publishing task needs its own verified writing/readback capabilities, concrete batch and applicable authorization.

## 4. Accept the output

These are manual checks, **not a report of completed tests in a new environment**.

| Check | Acceptable evidence |
|---|---|
| Project loading | The repository and instruction sources are identified; missing files or uncertain loading are disclosed |
| Tool and account access | Actual discovery/read results identify the selected account, or the response explains the specific blocking gap |
| Report scope | Platform, account, dates, time zone, currency and source/extraction time are stated; unavailable fields stay explicit |
| Result and limits | Observed results are separated from interpretations, missing coverage and next decisions; a submission-success receipt or simulation alone does not establish real completion |
| Action boundary | The first task stays read-only and respects the chosen connection; any later write has a reviewable batch, verified capabilities and covered authorization |

Do not create advertisements merely to finish this check. For later authorized writes, retain native IDs and receipts, reconcile uncertain outcomes before retrying, and read back affected objects. The [host workflow](workflow.md) covers those execution and handoff details.

For an explicitly requested offline exercise or a supported deterministic check, use the [method guide](method-planning.md). Simulation does not establish live access or authorize publishing.
