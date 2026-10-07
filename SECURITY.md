# Security and execution scope

## Reporting a vulnerability

Report privately through GitHub: **[Report a vulnerability](https://github.com/creator2000212-crypto/ad-ops-agent/security/advisories/new)**. Include what you found, how to reproduce it with fictional data, and what an attacker or a careless agent could do with it. Never post secrets, account identifiers or private data in a public issue; if private reporting is unavailable, open an issue with a non-sensitive summary and ask for a private contact.

In scope, for example:

- a way for the public code to make a network call or platform write, or to treat a check as approval;
- a path through the write gate, readback verifier or pre-flight linter that reports `ready` / `ACTIVATE` / `pass` on missing, null or mismatched state;
- a disclosure that `scripts/check_repository.py` should catch but does not (tokens, keys, ad account or long numeric IDs, local paths);
- instructions in `AGENTS.md` or the docs that would let an agent write without an approved batch, or get an ad past review without fixing it.

## Execution scope

The public code is offline by design and makes 0 platform calls. It reads local JSON and writes local Markdown, JSON and SQLite state. It has no advertising API client, LLM client, remote callback or live execution mode. The live reads and writes described in [How it ran](docs/how-it-ran.md) went through WorkBuddy's connectors under my approval; none of that access ships here.

- The write gate's `ready`, a readback receipt's `ACTIVATE` and a pre-flight `pass` mean "this check passed". They are not approval and not credentials.
- Simulation authorization files in the planning prototype are unsigned test data. Plan hashes detect consistency changes; they are not signatures. Never use them to authorize real spend.
- Examples and fixtures are fictional and use `example.com`. Do not commit tokens, cookies, authorization codes, media with personal data, account identifiers or raw exports. Generated state belongs in ignored directories (`runs/`, `demo/out/`).

A host that connects this workflow to real accounts must verify the actual account and operation scope, hold credentials in the client's or provider's secure configuration, get the user's approval for the exact batch, reconcile uncertain requests before retrying, and fill receipts only from timed readback. Instructions in this repository do not replace provider-side access control: give scheduled or read-only work read-scoped tokens and a tool allow-list, so "read-only" is enforced by permission rather than wording.
