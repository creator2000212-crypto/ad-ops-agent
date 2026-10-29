# Changelog

Notable changes to this repository. Dates are 2026, local time (UTC+8).

## Alongside this repository (2026-09-27 to 10-29)

Not code in this repository: the October live operation, sanitized. Details in [How it ran](docs/how-it-ran.md#october-the-same-loop-on-running-accounts).

- Kept operating Meta and TikTok lead-gen accounts with WorkBuddy. Meta moved to a second hosted connector on Oct 21; work moved to a new set of ad accounts on Oct 14–18; one task was handed to Claude on Oct 22, and from mid-October Claude also ran my click tracker, a separate private system.
- Resumed the 12-hour read-only check on Oct 24: 9 rounds to Oct 29, all delivered, 4 with partial coverage stated. Added four steps in front of the classification: a budget canary, writer attribution from the change log, offer codes read from destination links and a strict full day in the account's named time zone.
- Turned October incidents into rules: money has a unit and budget writes go through one guarded path (Oct 25), names are not evidence (Oct 26), an outside writer's values are not the baseline (Oct 27), moved ad sets start at a fixed budget (Oct 15), budget cuts wait for the account's next day (Oct 21) ([case studies WB-11 to WB-22](docs/case-studies.md#wb-11)).

## Before and alongside this repository (2026-09-10 to 09-27)

Not code in this repository: the live operation it was ported from, sanitized. Details in [How it ran](docs/how-it-ran.md).

- Operated Meta and TikTok lead-gen (CPL) accounts with WorkBuddy (Tencent's desktop AI agent; not affiliated) in interactive sessions from Sep 10 to Sep 27; builds followed create paused → field-by-field readback → activate; after the agent activated a batch on an ambiguous reply (Sep 22, [WB-08](docs/case-studies.md#wb-08)), launch approval became an explicit gate.
- Ran two scheduled WorkBuddy jobs: a daily 10:00 data pull (from Sep 20) and a read-only 12-hour check (from Sep 22) that re-verified the previous round's actions before classifying any ad set. Both were paused on Sep 26; the 12-hour check resumed on Oct 24.
- Changed the method on dated triggers: a stricter ROAS floor, one attribution setting, one ad set per creative on a T → 2T → 3T ladder, T per offer, and automated rules made notify-only ([methodology history](docs/methodology-history.md)).
- Turned incidents into rules: reconcile before retrying a timed-out batch, read back after activation, approval names the batch, receipts come only from timed readback, and 0 accounts means the pull failed ([case studies](docs/case-studies.md)).

## [0.3.0] — Unreleased

Ports the October checks on running accounts and updates the record to Oct 29.

### Added

- `account_audit.py`: audits a saved read of running accounts, their change log and a round's write requests, offline. Findings P0–P2 (disabled account, budget canary, budget with no spend or far above spend, shell ad set, name vs budget, offer link vs name, outside writer, duplicate activation), a writers table with net budget change per object, budget tiers judged from local midnight in the account's named time zone (`yes` / `no` / `unknown`), and allow / refuse / wait per write request (unit required, ceiling and raise ratio on raises, a rollback of a runaway budget never held, intraday cut, a cut without today's spend waits, locked fields, whole-object fields, resuming a human pause, a pause the log does not explain, disabled account; a malformed request is refused without stopping the audit). Fictional snapshot and policy in `examples/audit/`, English and Chinese golden reports, `tests/test_account_audit.py`, and a CI step.
- `preflight.py`: a moved-budget check (an ad set marked `moved_from` starts at or below the policy's `moved_adset.daily_budget`, or states a reason a person reviews) and a pixel check against the account's pixel read in `account_assets` (unknown, not shared or unavailable fails; never fired or stale warns). The sample checklist now shows both; its report is 9 fail, 4 warn, 22 pass.
- Docs: [Account audit](docs/account-audit.md) in English and Chinese; case studies WB-11 to WB-22; an October section in [How it ran](docs/how-it-ran.md) with the resumed run log and timeline; October entries in the [methodology history](docs/methodology-history.md); route C in the [roadmap](docs/roadmap.md) (account audit inside the round, tracker reporting rules, creative production checks, audience automation in readback).
- `AGENTS.md` hard rules R6 (money has a unit, and a budget has a ceiling) and R7 (names are labels; read the fields and the log).

### Changed

- README, docs index, capability status and build QA describe the operation as Sep 10 to Oct 29 and list the new checks; the pre-flight policy version is 2026-10-29.

## [0.2.0] — 2026-10-08 (untagged)

Reworks the repository around launch QA, change control and reconciliation, and documents how the workflow ran.

### Added

- `readback.py`: compares a build plan with the saved readback field by field, converts money by the currency's minor-unit offset, and decides `ACTIVATE` or `HOLD`; receipt values come only from the readback. Golden receipts for a fictional Meta build (holds on a missing URL parameter) and a TikTok build (activates).
- `preflight.py`: lints a build checklist before anything is created (name vs bid and budget, HTTPS and required URL parameters, special-ad-category declaration, attribution consistency, duplicate creative files) into a pass/warn/fail matrix.
- Settlement reconciliation (`reconcile_settlement()`): platform vs settled spend, results and CPA with tolerances from the methodology; scope, window and time-zone gaps are reported, never zero-filled; an unreconciled account cannot drive a promotion or an over-cost pause.
- "Why CPA moved": `cpa_driver_decomposition()` splits a CPA change into CPM, CTR and CVR shares plus a residual (`attribution()` kept as an alias).
- English reports and terminal output by default (`--lang en|zh-CN`); both languages are drift-checked in `demo/expected/`.
- `docs/decision-matrix.md`, generated from the methodology by `scripts/render_decision_matrix.py` and drift-checked.
- Docs: [How it ran](docs/how-it-ran.md), [methodology history](docs/methodology-history.md), [build QA](docs/build-qa.md) and [disapproval triage](docs/disapproval-triage.md), with Chinese versions.
- README images generated from the demo round and the readback fixture by `scripts/render_visuals.py`, with a manifest that pins each PNG to its source.
- Repository guards: the checker now flags ad account IDs, Google Ads customer IDs, standalone 15–19-digit IDs, Meta access tokens, email addresses, links to hosts outside a documentation allowlist, tokens in URLs, referral fragments, PNG text or EXIF metadata, and ad-review circumvention, traffic-mixing or incentive-vertical wording in public docs, fixtures and top-level modules (`tests/test_check_repository.py`); owner-only patterns load from an untracked `.private-patterns` file; a pre-commit hook (`.githooks/pre-commit`) that requires a noreply author email and runs the checker, and a commit-msg hook that scans the message; a CI step that checks a pull request's commit emails; a pull-request template; a ruleset for `main`; Dependabot for GitHub Actions; this changelog.
- CI runs on pushes to `main`, pull requests and manual dispatch with a 10-minute timeout and cancels superseded runs; it now also replays the readback and pre-flight goldens, the decision matrix, the demo in both languages and the README image check.
- `AGENTS.md` hard rules R1–R5 for an agent working on real accounts, each tied to the incident that produced it.
- `CLAUDE.md`, which imports `AGENTS.md` so Claude Code loads the same rules; README and [project loading](docs/use-in-agent.md) explain how other agent apps pick them up, and [How it ran](docs/how-it-ran.md#why-workbuddy) explains why WorkBuddy was used.

### Changed

- Connection guidance is vendor-neutral: official APIs, a self-hosted MCP server or a hosted MCP connector are listed unranked with plain URLs.
- Disapproved-ad handling follows fix-or-appeal: fix the content and resubmit, or use the platform's review process; a second rejection for the same reason goes to a human policy review. Re-upload is limited to technical processing failures.
- The write gate rejects a target field that is not writable for the proposal's object type; account and creative proposals carry their own object type.
- Rule precedence: `LADDER_HOLD` replaces a promotion while the same ad set has a creative breaker, creative overflow or naming mismatch, or the account has a P0 finding.
- Thresholds come only from the methodology; the remaining code defaults were removed, including the lead approval rate (`quality_factor`).
- Each promotion moves the budget to the next ladder step (×2 from T to 2T, ×1.5 from 2T to 3T); `promotion.budget_multiple` was removed from the methodology.
- `readback.py` also compares a campaign's special ad categories, and refuses a planned field it would not compare at that level or on that platform.
- The disapproval-triage contract is `contracts/disapproval-triage.json` (was `creative-recovery.json`); its scenarios are `DIS-*`.
- Reference fixtures use synthetic economics in which T is below value per lead; every teaching scenario still occurs.
- README rebuilt around what the engine catches and how it ran; case studies rewritten as incidents with the guardrail each produced; capability status became a real-vs-demo matrix; NOTICE names WorkBuddy.

### Fixed

- A null spend cap on one ad set no longer hides warnings for the ad sets after it.
- A creative-fatigue proposal targets the creative and keeps its parent ad set.
- `same_number()` compares through `Decimal` and rejects booleans.
- A missing ledger path raises an error instead of reporting nothing open.
- A promotion out of 2T proposed 4× the base budget instead of 3×.
- The MAX-name check matched `MAX` anywhere in the name and treated TikTok's no-bid type as a cap; it now matches `MAX` as a whole name segment and accepts both platforms' no-cap values.
- An ad set without a declared ladder stage stopped the whole round; it is now judged without promotion.
- Zero-lead evidence no longer says impressions are below the sample floor when they are above it.
- Malformed inputs (a non-object account, an out-of-range amount, URL parameters or special ad categories of the wrong shape) end in a clear input error instead of a traceback.

### Removed

- Vendor-specific connection instructions (replaced by the vendor-neutral connection guidance under Changed), including the vendor-named route value and the deprecated `recommendation` key in onboarding output.
- The text-card showcase: `docs/assets/showcase/`, `scripts/showcase_content.py`, `docs/showcase-style.md` and `docs/page-template.md`.
- Traffic-mixing fields in the settlement fixture.

## [0.1.0] — 2026-09-25 (untagged)

The first public version: 38 commits from Sep 24 19:25 to Sep 25 22:16, written while the scheduled jobs were still running.

| Phase | Dates | What it added |
|---|---|---|
| Foundation | Sep 24 | Offline agent foundation, product and operations docs, design-only contracts, fictional examples, planning and onboarding tests, demo and repository check scripts, offline CI |
| Connection guidance and knowledge | Sep 24 | Platform integration paths and a Google Ads API application guide, a contextual knowledge catalog, onboarding gated on account capabilities, project instructions for conversational setup |
| Private methods and task workflow | Sep 24 | Scoped private methods with correction history and plan invalidation; structured test methods and resumable offline task workflows |
| Operating loop | Sep 24–25 | An offline operating loop with a write gate, a demo with a drift-checked expected round, a build-from-zero guide |
| Workflow and cases | Sep 25 | Demo walkthrough and handoff report, the host workflow rebuilt around documented WorkBuddy practice, a complete TikTok task, conflicts reported without guessing who changed the value |
| Homepage and first use | Sep 25 | Showcase homepage (retired in 0.2.0), documentation navigation, language switching, first read-only use paths |

### Fixed

- Sep 25: a missing or null baseline passed the write gate as `ready`. A differing field with no concrete baseline is now `unknown` and holds the proposal.
