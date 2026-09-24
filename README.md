# Ad Ops Agent

**A provider-neutral foundation for advertising agents across Meta, TikTok and Google Ads.**

[简体中文](README.zh-CN.md) · [Documentation](docs/index.md) · [Roadmap](docs/roadmap.md) · [MIT license](LICENSE)

Let media buyers focus on understanding the business, interpreting results and deciding what to test next. Let an agent prepare assets, assemble configurations, build experiments, execute approved batches and explain what actually happened.

**Current release: an executable offline Python prototype plus a product and integration blueprint.** It does not connect to ad accounts, upload media, call an LLM, inspect images, publish ads or change budgets. The three platform names are simulation adapters using `generic_draft`; `native_payload` is always `null` and live mode is rejected. Design contracts are not loaded by the runtime.

## The intended workflow

```mermaid
flowchart LR
    A[Verify selected account read and write access] --> B[Set collaboration needs and understand the business]
    B --> C[Prepare assets and test plan]
    C --> D[Review the whole batch]
    D --> E[Execute within approved scope]
    E --> F[Read back objects and collect results]
    F --> G[Human analysis and next decision]
    G --> C
```

First verify that the chosen MCP, API or SDK provides the necessary read and write access for the selected accounts. Then establish the user's experience on the selected platform, preferred level of guidance and current need. Only after that does intake gather the business facts and methodology required by the task. A connection gap keeps intake at setup; supplied business facts can be retained without opening a business questionnaire. There is no requirement to connect all three platforms.

The execution layer is replaceable: you can use official APIs, SDKs or MCP servers for each platform, or a managed connector. An API provides access to platform objects; an SDK wraps that API in code; an MCP server exposes supported operations as tools to an agent. None of them grants account access or publishing permission by itself. Native platform semantics remain in platform adapters.

### Recommended first connection: Pipeboard

**For users without an existing connection, we recommend considering Pipeboard first, especially when getting started.** Its unified Ads MCP connects authorized Meta, Google Ads and TikTok accounts. It offers a single tool entry point, reduces connection maintenance and lets you scope access to selected accounts. See the [official multi-platform MCP guide](https://pipeboard.co/guides/ads-mcp) for supported operations and authorization details.

**[前往 Pipeboard 官网连接广告账户](https://pipeboard.co/#via=tian)**

通过此链接订阅，项目维护者可能获得佣金。

Visit Pipeboard to connect ad accounts. If you subscribe through this link, the project maintainer may earn a commission.

Check current plans, account access and required capabilities before choosing. Purchasing or connecting Pipeboard does not make this offline prototype a live publishing agent. Existing working APIs, SDKs and other MCP servers remain valid routes; users who choose another route or dismiss the recommendation are not repeatedly asked to switch.

Read-only access can help diagnose a connection, but this agent's operational setup gate also requires the necessary write capabilities before collaboration and business intake continue. Passing that gate does not authorize publishing or spending. The current rules ask guided users for information needed to discuss candidate methods, and ask users with their own methods to import or describe them. They do not generate methods or parse an SOP. Platform experience and explanation preferences are recorded; neither changes permissions.

Start with the [first-run guide (Chinese)](docs/first-run.zh-CN.md). For source-linked self-managed Meta, TikTok and Google Ads access routes, see the [integration guide (Chinese)](docs/platform-connectivity.zh-CN.md).

## What runs today

| Capability | Implementation status |
|---|---|
| Connection-first setup and collaboration guidance | Offline gate, route recommendation and rule-based questions; `setup.json` / `setup.md`, no UI or real configuration |
| Business facts with source/status and conditional workflow dependencies | Offline JSON input and readiness evaluation |
| Web/App and monetization-dependent questions | Structured rules; no conversational LLM |
| Connection discovery, scope and freshness | Fictional snapshots only; no actual permission check |
| Asset selection | Explicit metadata filters and input order; no media inspection |
| Budget allocation and batch review | Decimal arithmetic, frozen plan hash, Markdown review |
| Contextual advertising knowledge | Runtime catalog retrieval, applicability/evidence/source review, intake and plan integration; advisory only |
| Execution and recovery | Local SQLite simulation, readback comparison, resume in the same state directory |
| Real Meta/TikTok/Google operations | Planned; not implemented |
| Additional operational recipes and design contracts | Human-readable guides and unloaded design JSON; separate from the runtime knowledge catalog |

The simulation authorization file is an unsigned test artifact, not authentication or a user's real publishing approval. Recovery is scoped to the same frozen plan and local state directory; it is not a distributed or cross-provider exactly-once guarantee.

## Quick start

Python 3.9+ with an IANA timezone database. The prototype uses the standard library; no advertising credentials or package installation are needed. Commands below assume a shell with `python3` (use your Python command on other systems).

```bash
git clone https://github.com/creator2000212-crypto/ad-ops-agent.git
cd ad-ops-agent
python3 scripts/demo.py
```

The demo writes a new, uniquely named directory under `runs/` and verifies:

1. A fresh fictional business profile and connection snapshot produce a ready context.
2. A frozen plan creates three local simulated drafts.
3. Resuming the same state creates no duplicates.
4. An intentionally interrupted write is reconciled before remaining operations continue.

It prints the output directory, `review.md` location and the expected object counts. All accounts and assets are fictional; fixture timestamps are refreshed only in a new copy. The demo never makes a network request.

Run the checks:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_repository.py
```

## Use the individual CLI steps

To see the first-run connection guidance without a configured connection:

```bash
python3 onboarding.py --input examples/onboarding-setup-required.json --out runs/setup
```

Exit code `2` is expected for this deliberately incomplete fixture. Read `runs/setup/setup.md`, `setup.json` and the `connection_gate` / `guidance` fields in `context.json`; business questions wait for a ready connection gate. This is an offline simulation, not an MCP installer or a real account check.

Use a new output directory for each new frozen plan. For an existing run, resume it without rebuilding its source profile.

```bash
python3 onboarding.py --input examples/onboarding-learning.json --out runs/manual/profile.json --refresh-simulation-fixture
python3 onboarding.py --input runs/manual/profile.json --out runs/manual/context
python3 adops.py plan --brief examples/brief.json --candidates examples/candidates.json --context runs/manual/context/context.json --out runs/manual/plan
python3 adops.py authorize-simulation --plan runs/manual/plan/plan.json --out runs/manual/simulation-authorization.json
python3 adops.py execute --plan runs/manual/plan/plan.json --authorization runs/manual/simulation-authorization.json --state runs/manual/state
python3 adops.py resume --plan runs/manual/plan/plan.json --authorization runs/manual/simulation-authorization.json --state runs/manual/state
```

`authorize-simulation` does not approve real spending. Readiness checks return their state in JSON; a successful onboarding command can still report missing prerequisites. Plans and execution re-read the original business-profile source to detect drift. Unsupported native advertising settings are rejected rather than silently discarded.

For an incomplete App + hybrid monetization example, replace the onboarding input with `examples/onboarding-app-hybrid-discovery.json` and write to another output directory. It illustrates focused gaps and conflicting information, not a publish-ready setup.

## Operational knowledge included

- [Runtime knowledge base (Chinese)](docs/knowledge-base.zh-CN.md): source-linked knowledge with platform and business conditions, evidence gaps and review dates. `knowledge.py` supports deterministic search and assessment; onboarding and plan reviews use the same catalog without granting execution permissions.
- Sixteen [operation cards](docs/operations.md): media readiness, duplicate versus variant selection, existing posts, placement previews, tracking, parent status, copy defaults, budget ownership, concurrent human edits, timezone boundaries, attribution maturity, testing observations, Spark, RSA and ValueTrack.
- [Meta creative recovery](docs/meta-creative-recovery.md): separate local hashes, media references, creative IDs, ad IDs and post identities; distinguish technical repair, suspected false rejection and content revision.
- [Connector contract](contracts/connector-contract.json): native identity, capability/version records, normalization, uncertainty reconciliation and equivalent provider switching.
- [Google Ads API application guide (Chinese)](docs/google-ads-api-application.zh-CN.md): Cloud project setup, Test-to-production access upgrades, OAuth, brand verification and readback checks.
- [Experience catalog](contracts/experience-catalog.json) and [onboarding extensions](contracts/onboarding-extensions.json): reusable candidates with scope and evidence boundaries.
- [Acceptance scenarios](contracts/acceptance-scenarios.json): specifications for future implementation, separate from executable tests.

Try a knowledge lookup or an assessment using fictional observations:

```bash
python3 knowledge.py search --query '归因' --stage measurement --platform meta
python3 knowledge.py assess --profile examples/onboarding-learning.json --observations examples/knowledge-observations.json --stage diagnosis --out runs/knowledge-review
```

The assessment writes `report.json` and `review.md`. Results distinguish applicable knowledge from missing context, missing evidence and sources requiring review. They remain advisory: the engine does not fetch ad data, prove causes or execute recommendations. Catalog changes invalidate frozen plans, requiring a new plan review and simulation authorization.

## Repository map

```text
adops.py                 Offline plan, simulated authorization, execution and resume
onboarding.py            Connection gate, collaboration guidance and business readiness
knowledge.py             Deterministic knowledge search and advisory assessment
knowledge/               Runtime knowledge catalog with sources and conditions
examples/                Fictional JSON inputs
tests/                   Executable offline contract tests
scripts/                 Demonstration and repository checks
docs/                    Product, architecture, onboarding and operational guides
contracts/               Unloaded design contracts and candidate knowledge
.github/workflows/        Offline CI
```

See the [documentation index](docs/index.md) for a reading path and the [roadmap](docs/roadmap.md) for integration milestones. Contributions should preserve the distinction between observed evidence, proposed behavior and implemented functionality. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

## License and provenance

MIT. This project develops the reusable workflow direction of `ads-ops-playbook`; its existing copyright notice is retained. Public examples are fictional. Private campaign records, credentials and generated execution state are not distributed. See [NOTICE.md](NOTICE.md) and [SECURITY.md](SECURITY.md).
