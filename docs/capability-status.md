# Real vs demo

[简体中文](capability-status.zh-CN.md) · [Project home](../README.md) · [How it ran](how-it-ran.md) · [Case studies](case-studies.md)

What ran on live accounts, what this repository implements, and how to run it. The live work was Meta and TikTok lead-gen from Sep 10 to Oct 29, 2026 through WorkBuddy (Tencent's desktop AI agent; not affiliated); the [operating record](how-it-ran.md) has the dates and the run log.

**Scope.** This repository is offline by design: every module reads local files (JSON; SQLite for the prototype's simulation and private-memory store) and makes 0 platform calls. Live reads and writes ran through WorkBuddy's connectors, and I approved launches and budget changes ([WB-08](case-studies.md#wb-08) is the time that broke, and why approval is now an explicit gate). Opening this project in an agent does not connect an ad account.

## The matrix

| Capability | Ran live (2026) | Public code | Run it here |
|---|---|---|---|
| Field-by-field readback before activation | Interactive builds, Sep 10–Oct 29, followed create paused → read back → activate ([WB-06](case-studies.md#wb-06): one batch lacked a saved final readback; [WB-08](case-studies.md#wb-08): one activation without approval) | [`readback.py`](../readback.py): `verify_build()`, HOLD/ACTIVATE receipt | `python3 readback.py --plan examples/readback/meta-plan.json --readback examples/readback/meta-readback.json` |
| Pre-flight lint of a build checklist | Mostly new here; live builds relied on readback. Two checks ran live as rules: moved ad sets start at a fixed budget (from Oct 15, [WB-18](case-studies.md#wb-18)) and the account's pixels are read before a build (from Oct 3, [WB-19](case-studies.md#wb-19)) | [`preflight.py`](../preflight.py): naming vs config, URL parameters, special-category declaration, attribution, duplicate files, moved budget, pixel availability | `python3 preflight.py --checklist examples/preflight/checklist.json --policy examples/preflight/policy.json` |
| Account audit before a round and before writes | Added to the 12-hour round, Oct 25–27: budget canary and a guarded budget-write path (Oct 25, [WB-11](case-studies.md#wb-11)), strict full day (Oct 25, [WB-14](case-studies.md#wb-14)), offer codes from links (Oct 26, [WB-12](case-studies.md#wb-12)), writer attribution (Oct 27, [WB-13](case-studies.md#wb-13)); 9 rounds Oct 24–29 | [`account_audit.py`](../account_audit.py): findings P0–P2, writers, budget tiers, allow / refuse / wait per write request | `python3 account_audit.py --snapshot examples/audit/snapshot.json --policy examples/audit/policy.json` |
| Daily pull in the settlement's 20-column format | Daily job, Sep 21–26; one-off comparison with the settlement export and scope fix Sep 20 ([WB-09](case-studies.md#wb-09)) | Settlement reconciliation in [`operating_rules.py`](../operating_rules.py): spend, results and CPA gaps; scope gaps never zero-filled | `python3 demo/run_demo.py` (section "Platform vs settlement") |
| Classifying ad sets against the T ladder | 12-hour job, Sep 22–26 and Oct 24–29 | `decide_account()` in [`operating_rules.py`](../operating_rules.py) with thresholds from [`methodology-reference.json`](../examples/operating/methodology-reference.json) | `python3 demo/run_demo.py` |
| Re-checking the previous round first | Every 12-hour round, Sep 22–26 and Oct 24–29 | Append-only ledger in [`operating_loop.py`](../operating_loop.py): `apply`, `verify`, `open` | `python3 scripts/demo_operating_loop.py` |
| Five-state write gate and after-state comparison | Ported into the private live loop, Sep 24 | `gate()` and `reconcile()` in [`operating_rules.py`](../operating_rules.py) | `python3 demo/run_demo.py --steps` |
| Acceptance criteria and stop conditions per action | On every action from Sep 24 | Action catalogue in the methodology, rendered by `scripts/render_decision_matrix.py` | [Decision matrix](decision-matrix.md) |
| Why CPA moved (CPM, CTR, CVR) | New here | `cpa_driver_decomposition()` in [`operating_rules.py`](../operating_rules.py) | `python3 demo/run_demo.py` (section "Why CPA moved") |
| Reading and writing ad accounts | Through WorkBuddy's connectors: a hosted MCP connector for Meta (a second one from Oct 21), a TikTok API for Business client the agent built at my direction | None: 0 platform calls | — |
| Scheduling | WorkBuddy's local scheduler, Sep 20–26 and Oct 24–29 (the 12-hour check only) | None | — |

Google Ads appears only in the connection guidance and the simulated adapters; the live work covered Meta and TikTok.

## The pre-launch prototype

These modules came from a separate planning and onboarding prototype. They were not part of what ran live; they run on fictional inputs.

| Module | Implements | Does not |
|---|---|---|
| `onboarding.py` / `guidance.py` | Structured business facts, gaps, fictional connection snapshots, rule-based guidance | Verify a real connection or install a connector |
| `methodology.py` / `task.py` | Two method templates, explicit adoption, private task copies and versions | Parse an arbitrary SOP written in natural language |
| `planning.py` | Test units, budgets and plans from declared component identities | Understand media, rank performance or randomize A/B allocation |
| `knowledge.py` | Versioned knowledge with applicability, source and evidence gaps | Verify platform facts or make causal claims |
| `memory_store.py` / `personalization.py` | Product-scoped private records with versions, history and revocation | Learn automatically or certify performance |
| `adops.py` | Simulated batch plans, simulated authorization, SQLite objects, same-state recovery | Submit to a platform; `native_payload` stays `null` |

```bash
python3 scripts/demo.py                  # simulated batch, interruption and recovery
python3 scripts/demo_private_memory.py   # saving, revising and reusing private methods
python3 scripts/demo_methods.py          # six fictional inputs across two method routes
```

## Checks

Python 3.9+ and the standard library only; no account or API key.

```bash
python3 -m unittest discover -s tests -v
python3 demo/run_demo.py --check
python3 readback.py --plan examples/readback/meta-plan.json --readback examples/readback/meta-readback.json \
    --check examples/readback/expected/meta-receipt.md
python3 preflight.py --checklist examples/preflight/checklist.json --policy examples/preflight/policy.json \
    --check examples/preflight/expected/checklist.md
python3 account_audit.py --snapshot examples/audit/snapshot.json --policy examples/audit/policy.json \
    --check examples/audit/expected/audit.md
python3 scripts/check_repository.py
```

Passing these shows the offline logic is consistent. It says nothing about a live account.

## Using it on your own accounts

Use the [host workflow](workflow.md) with tools you have verified and are authorized to use, and keep a [task record](../templates/task-record.md) for each batch: the accounts and tools in scope with the read time, the confirmed business context and method, the concrete batch with its budget impact and your approval, per-object readback that keeps review, eligibility and delivery apart, and the open items at handoff. A read-only task needs only read access; do not write to an account to complete a checklist.
