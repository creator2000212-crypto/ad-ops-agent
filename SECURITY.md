# Security and execution scope

The public Python runtime is an offline prototype. It reads local JSON and writes local Markdown, JSON and SQLite state. It has no advertising API clients, LLM clients, remote callbacks or live execution mode.

Simulation authorization files are unsigned test data. They are not access-control credentials and must not be used to authorize production spending. Plan hashes detect consistency changes; they are not authenticated signatures. Recovery only covers the same plan and local state directory, not distributed or cross-provider execution.

Examples are fictional. Do not commit tokens, cookies, authorization codes, media containing personal data, private account identifiers or raw customer exports. Generated state belongs in ignored directories and may contain local source paths.

A host using connected advertising tools must validate the actual account and operation scope, preserve user approval of the batch, isolate credentials, reconcile uncertain requests and read back affected objects. Project instructions and historical cases are not account authorization. Actual values in receipts must come from tool results, not planned values or hard-coded success labels.

Standalone live Python integrations still require real authentication, plan-bound authorization and operation-specific recovery. These are not security features already delivered by the offline program. Host instruction compliance is also not a substitute for provider-side access control or an integration test.

To report a problem, use the repository's private vulnerability reporting channel if available. Otherwise open an issue with a non-sensitive summary and request a private contact method before sharing exploitable details. Never post secrets or private data in a public issue.

