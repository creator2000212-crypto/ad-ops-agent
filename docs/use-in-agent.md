# Project loading and troubleshooting

[简体中文](use-in-agent.zh-CN.md) · [Back to first use](first-check.md) · [Documentation](index.en.md)

**For:** users already following the first-use tutorial who cannot read files, load rules or access tools. **Outcome:** identify the gap and return to the interrupted step. Start with the [first-use tutorial](first-check.md); this page is a reference, not another required onboarding sequence.

## Distinguish three states

| State | How to check | What it does not establish |
| --- | --- | --- |
| Project files are readable | File tools read the root `AGENTS.md` and its workflow references | An advertising account connection |
| This task uses the rules | Response identifies rule sources; check host instruction logs and subsequent behavior where available | Publishing or budget authority |
| Selected account is readable | An actual read returns that account, required fields, source and time | Access to every account or every write capability |

The repository supplies working instructions and reference material, the agent tool supplies the model and file/tool access, and a connector supplies authorized platform operations. Public Python is a separate offline route. [Capability scope](capability-status.md)

## Files or rules are inaccessible

**You check:** obtain the complete repository through [step 1](first-check.md#open-project) and open the folder containing `AGENTS.md` and `docs/`. Uploading only a README, copying a script or sharing a GitHub URL does not establish access to referenced files.

Hosts load instructions differently:

- **Codex:** use the repository directory as the task project; CLI users can start there. Project paths, overrides and instruction-size limits may affect loading. After instruction changes, check sources in a new run. See the official [project instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md) and [project directory guidance](https://learn.chatgpt.com/docs/projects).
- **Other agent tools:** use their documented project-rule mechanism. Without automatic loading, explicitly ask the host to read the root `AGENTS.md` and supply referenced files through supported file tools. Do not assume all clients load that filename automatically.

**Ask the agent to diagnose:**

```text
I am having trouble loading Ad Ops Agent. Inspect only:
1. Identify the project directory, AGENTS.md and docs/workflow.md actually accessible to this task.
2. State which files you read and which are missing or uncertain; do not just say "loaded".
3. If instruction overrides or truncation information are visible, identify the source; otherwise mark unknown.
4. Give the specific action I need to take and the step to retry afterward.
Do not change global configuration, install services or operate on ad accounts.
```

**Resolved when:** required files are actually readable, rule sources are identified and uncertainty stays explicit. A model's claim alone does not prove subsequent behavior; instruction or session logs can help where available. Return to the [step 1 completion check](first-check.md#open-project), then continue with connection setup.

## Files load, but accounts or reports are unavailable

| Situation | Evidence the agent should provide | Your action | Resume |
| --- | --- | --- | --- |
| No advertising reading tools | Actual visible tools or discovery results, with missing capabilities | Check the existing route; see connection options if none chosen | [Connection](first-check.md#connect) |
| Tools visible, account read fails | Call category, error category and target scope, without credentials | Check platform identity, selected accounts and necessary permissions | [Account check](first-check.md#verify-account) |
| Account readable, report empty | Date, time zone, filters, pagination and coverage | Confirm scope; choose preparation if advertising has not started | [Task selection](first-check.md#choose-task) |
| Response is offline JSON or `ready_simulation` | Identify the fixture or local simulation source | A real task still requires a real read; simulation can be a separate exercise | [Account check](first-check.md#verify-account) |

Ask: “Explain what the real tools can read, the last successful step, the gap and who resolves it. Do not turn empty responses into zeros or create ads to diagnose access.” See the [connection reference](platform-connectivity.md) for other routes.

A read-only task needs only its reading capabilities; missing write access does not invalidate supplied-report analysis. When users explicitly choose supplied-file analysis, check file coverage and source, and label it as file analysis rather than live account validation.

## After resolving the gap

Resume the interrupted step in the first-use tutorial and retain verified context. See its [delivery checks](first-check.md#check-result). Later configuration or publishing follows the [daily workflow](workflow.md): a concrete batch, necessary capabilities, covered authorization and readback.

Use the [Python method planning reference](method-planning.md) only when running a program example is intended. This troubleshooting guidance is not a report of completed fresh-environment validation.
