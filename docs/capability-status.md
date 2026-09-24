# Capability status: practice, host tools and public code

[简体中文](capability-status.zh-CN.md) · [Project home](../README.md) · [Cases from practice](case-studies.md)

**The public Python code's lack of ad API calls does not describe the author's entire working setup. Historical use of an agent tool does not mean a fresh checkout has connected accounts.** These claims require different evidence.

## Three layers

| Layer | What exists | Evidence or conditions |
|---|---|---|
| **Business practice in an agent tool** | Business conversations, tool operations, asset selection, creation/change records, reports and recurring reviews | Selected local historical records have been reviewed. Each case states its completion boundary. Private originals are not published and do not verify current platform state |
| **Reusable host workflow** | Project instructions, task flow, business and method organization, batch review, execution checks and record templates | The host must load the instructions and have usable, authorized tools for this task. Each new environment requires validation |
| **Public Python validation code** | Structured checks, limited method compilation, knowledge lookup, private records, offline diagnosis and simulated execution/recovery | Runnable locally; no model or ad-platform calls; live mode is rejected |

A host using existing tools does not first need Python platform adapters. Making the Python program a standalone live executor still requires native parameter mapping, authentication, real approval and integration checks.

## What the reviewed working records cover

| Task | Work found in the records | What it does not establish |
|---|---|---|
| Creative and batch preparation | Deduplication, asset/destination matching, user revisions and batch records | Automatic understanding of every asset or proven performance |
| Meta creation, migration and configuration diagnosis | Creation/read records, state checks, user confirmation and unresolved items | Every batch took effect, or an accepted request started spending |
| TikTok creative and delivery work | Multi-product plans, user-supplied creative constraints and object-state records | Every object was approved or spent, or equal support across three platforms |
| Reporting and product mapping | Source tables, account scope, product mapping, missing-data notes and reports | Conversions from different sources can be summed, or missing means zero |
| Recurring reviews and corrections | Prior-item checks, fresh retrieval, method references and report handoffs | Every recommendation was executed or scheduled runs always succeeded |

The reviewed records primarily concern Meta and TikTok. **Google designs and simulated adapters are not presented as verified live business deployment.** See the [anonymized cases](case-studies.md).

## What the public Python code implements

| Module | Implemented scope | Outside that scope |
|---|---|---|
| `onboarding.py` / `guidance.py` | Structured facts, dependencies/gaps, fictional connection snapshots and rule-based guidance | Real connection verification, model interviews or connector installation |
| `methodology.py` / `task.py` | Two limited method candidates, explicit adoption, private task copies and method versions | Arbitrary natural-language SOP parsing or every host-supported method |
| `planning.py` | Metadata and declared component identities, test units, budgets and content-bound plans | Media understanding, performance ranking, native payloads or randomized A/B allocation |
| `knowledge.py` | Versioned knowledge, applicability, source and evidence-gap checks | Automatic platform-fact verification, causal conclusions or autonomous budget changes |
| `memory_store.py` / `personalization.py` | Scoped local records, versions/history/revocation and conditional reuse | Automatic learning, performance certification, multi-tenant security or automatic personal-memory writes |
| `adops.py` | Simulated batch plans/authorization, SQLite objects and same-state recovery | Real identity/approval, platform submission or global network/cross-directory deduplication |
| `operating_loop.py` | Supplied-snapshot diagnosis, field differences, a local ledger and later-snapshot comparison | Platform retrieval, user approval, actual writes or background scheduling |

All three simulated adapters accept only `generic_draft`; `native_payload` is `null`. Neither `completed_simulation` nor `ready` constitutes live publishing approval. Files under `contracts/` do not become loaded runtime features merely by existing.

## Offline validation entry points

Python 3.9+ and system IANA timezone data are required. The programs use the standard library. All examples use fictional inputs and need no account or API key.

```bash
# An ad review and comparison with preset later state
python3 demo/run_demo.py

# Batch planning, simulated execution, interruption and repeat-run recovery
python3 scripts/demo.py

# Saving, revising and conditionally reusing private methods
python3 scripts/demo_private_memory.py

# Six fictional business inputs across two method routes
python3 scripts/demo_methods.py
```

Outputs stay in local Git-ignored run directories. The six business inputs check offline behavior; they are not six customer deployments.

Checks:

```bash
python3 -m unittest discover -s tests -v
python3 demo/run_demo.py --check
python3 scripts/check_repository.py
```

See the [method guide](method-planning.md) for manual tasks and inputs, and the [technical reference](operating-loop.md) for operating-loop fields and commands. Passing local tests does not establish live platform integration.

## Validate your own environment

Use the [host workflow](workflow.md) and [task record](../templates/task-record.md) for an actual task you need. Retain:

1. Task accounts, available tool capabilities, read time and coverage.
2. Confirmed business context and method, plus unresolved inputs.
3. A concrete batch, budget impact, real user confirmation and plan version.
4. Per-object request receipts and later reads, separating review, delivery eligibility and observed impressions/spend.
5. Existing-object checks after interruption and an explicit unresolved-item handoff.

A read-only task requires read and deliverable checks, not ad writes to complete a checklist. Preserve gaps where evidence is unavailable. Host usability, media understanding, connector replacement and business outcomes require evidence in their specific environment.
