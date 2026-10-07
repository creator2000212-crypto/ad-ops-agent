# Changelog

Notable changes to this repository. Dates are 2026, local time (UTC+8). SHAs refer to commits on `main`.

## Before and alongside this repository (2026-09-10 to 09-27)

Not code in this repository: the live operation it was ported from, sanitized. Details in [How it ran](docs/how-it-ran.md).

- Operated Meta and TikTok lead-gen (CPL) accounts with WorkBuddy (Tencent's desktop AI agent; not affiliated) in interactive sessions from Sep 10 to Sep 27; every build was created paused, read back field by field, and activated only after I approved it.
- Ran two scheduled WorkBuddy jobs: a daily 10:00 data pull (from Sep 20) and a read-only 12-hour check (from Sep 22) that re-verified the previous round's actions before classifying any ad set. Both have been paused since Sep 26.
- Changed the method on dated triggers: ROAS floor 80% → 85%, one attribution setting, one ad set per creative on a T → 2T → 3T ladder, T per offer, and automated rules made notify-only ([methodology history](docs/methodology-history.md)).
- Turned incidents into rules: reconcile before retrying a timed-out batch, read back after activation, approval names the batch, receipts come only from timed readback, and 0 accounts means the pull failed ([case studies](docs/case-studies.md)).

## [0.2.0] — Unreleased

Reworks the repository around launch QA, change control and reconciliation, and documents how the workflow ran.

### Added

- `readback.py`: compares a build plan with the saved readback field by field, converts money by the currency's minor-unit offset, and decides `ACTIVATE` or `HOLD`; receipt values come only from the readback. Golden receipts for a fictional Meta build (holds on a missing URL parameter) and a TikTok build (activates).
- `preflight.py`: lints a build checklist before anything is created (name vs bid and budget, HTTPS and required URL parameters, special-ad-category declaration, attribution consistency, duplicate creative files) into a pass/warn/fail matrix.
- Settlement reconciliation (`reconcile_settlement()`): platform vs settled spend, results and CPA with tolerances from the methodology; scope, window and time-zone gaps are reported, never zero-filled; an unreconciled account cannot drive a promotion or an over-cost pause.
- "Why CPA moved": `cpa_driver_decomposition()` splits a CPA change into CPM, CTR and CVR shares plus a residual (`attribution()` kept as an alias).
- English reports and terminal output by default (`--lang en|zh-CN`); both languages are drift-checked in `demo/expected/`.
- `docs/decision-matrix.md`, generated from the methodology by `scripts/render_decision_matrix.py` and drift-checked.
- Docs: [How it ran](docs/how-it-ran.md), [methodology history](docs/methodology-history.md), [build QA](docs/build-qa.md) and [disapproval triage](docs/disapproval-triage.md), with Chinese versions.
- README images generated from the demo's own output by `scripts/render_visuals.py`, with a manifest that pins each PNG to its source.
- Repository guards: the checker now flags ad account IDs, standalone 15–19-digit IDs, tokens in URLs, referral fragments, and ad-review circumvention or traffic-mixing wording in public docs and fixtures (`tests/test_check_repository.py`); a pre-commit hook (`.githooks/pre-commit`) that requires a noreply author email and runs the checker; a pull-request template; a ruleset for `main`; Dependabot for GitHub Actions; this changelog.
- CI runs on pushes to `main`, pull requests and manual dispatch with a 10-minute timeout and cancels superseded runs; it now also replays the readback and pre-flight goldens, the decision matrix, the demo in both languages and the README image check.
- `AGENTS.md` hard rules R1–R5 for an agent working on real accounts, each tied to the incident that produced it.

### Changed

- Connection guidance is vendor-neutral: official APIs, a self-hosted MCP server or a hosted MCP connector are listed unranked with plain URLs.
- Disapproved-ad handling follows fix-or-appeal: fix the content and resubmit, or use the platform's review process; a second rejection for the same reason goes to a human policy review. Re-upload is limited to technical processing failures.
- The write gate rejects a target field that is not writable for the proposal's object type; account and creative proposals carry their own object type.
- Rule precedence: `LADDER_HOLD` replaces a promotion while the same ad set has a creative breaker, creative overflow or naming mismatch, or the account has a P0 finding.
- Thresholds come only from the methodology; the remaining code defaults were removed.
- Reference fixtures use synthetic economics in which T is below value per lead; every teaching scenario still occurs.
- Wording about moving campaigns between ad accounts now says restructuring.
- README rebuilt around what the engine catches and how it ran; case studies rewritten as incidents with the guardrail each produced; capability status became a real-vs-demo matrix; NOTICE names WorkBuddy.

### Fixed

- A null spend cap on one ad set no longer hides warnings for the ad sets after it.
- A creative-fatigue proposal targets the creative and keeps its parent ad set.
- `same_number()` compares through `Decimal` and rejects booleans.
- A missing ledger path raises an error instead of reporting nothing open.

### Removed

- The referral link and the instruction to recommend one connection provider first.
- The text-card showcase: `docs/assets/showcase/`, `scripts/showcase_content.py`, `docs/showcase-style.md` and `docs/page-template.md`.
- Traffic-mixing fields in the settlement fixture.

## [0.1.0] — 2026-09-25

The first public version: 38 commits from Sep 24 19:25 to Sep 25 22:16, written while the scheduled jobs were still running.

| Phase | Commits | What it added |
|---|---|---|
| Foundation | `25f4a52`…`2b77a42` (Sep 24) | Offline agent foundation, product and operations docs, design-only contracts, fictional examples, planning and onboarding tests, demo and repository check scripts, offline CI |
| Connection guidance and knowledge | `2aac739`…`3670be1` (Sep 24) | Platform integration paths and a Google Ads API application guide, a contextual knowledge catalog, onboarding gated on account capabilities, project instructions for conversational setup (with a hosted-connector referral link, removed in 0.2.0) |
| Private methods and task workflow | `9d344f1`…`f4b8e85` (Sep 24) | Scoped private methods with correction history and plan invalidation; structured test methods and resumable offline task workflows |
| Operating loop | `d46aa57`…`406dd50` (Sep 24–25) | An offline operating loop with a write gate, a demo with a drift-checked expected round, a build-from-zero guide |
| Workflow and cases | `519762c`…`c3b410e` (Sep 25) | Demo walkthrough and handoff report, the host workflow rebuilt around documented WorkBuddy practice, a complete TikTok task, conflicts reported without guessing who changed the value |
| Homepage and first use | `0db16dd`…`2afd15f` (Sep 25) | Showcase homepage (retired in 0.2.0), documentation navigation, language switching, first read-only use paths |

### Fixed

- `34a36a6`: a missing or null baseline passed the write gate as `ready`. A differing field with no concrete baseline is now `unknown` and holds the proposal.
