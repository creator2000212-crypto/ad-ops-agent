# Security and execution scope

The current runtime is an offline prototype. It reads local JSON and writes local Markdown, JSON and SQLite state. It has no advertising API clients, LLM clients, remote callbacks or live execution mode.

Simulation authorization files are unsigned test data. They are not access-control credentials and must not be used to authorize production spending. Plan hashes detect consistency changes; they are not authenticated signatures. Recovery only covers the same plan and local state directory, not distributed or cross-provider execution.

Examples are fictional. Do not commit tokens, cookies, authorization codes, media containing personal data, private account identifiers or raw customer exports. Generated state belongs in ignored directories and may contain local source paths.

Future live integrations need real authentication, scope validation, credential isolation, plan-bound authorization, uncertainty reconciliation and operation-specific readback. These are design requirements, not security features already delivered by this prototype.

To report a problem, use the repository's private vulnerability reporting channel if available. Otherwise open an issue with a non-sensitive summary and request a private contact method before sharing exploitable details. Never post secrets or private data in a public issue.

