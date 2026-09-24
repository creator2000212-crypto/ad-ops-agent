# From a user method to a reviewable test plan

[简体中文](method-planning.zh-CN.md) · [Project home](../README.md)

This page documents the **public Python M2 module**, an optional offline path alongside the [host workflow](workflow.md). Real tasks can use the host's verified, authorized tools and the user's own method; they do not have to pass through `task.py` or fit its two templates. The host preserves source terms, reviews feasibility and prepares an appropriate batch through that route.

For an M2 exercise or supported check, the host organizes the user's answers, the program proposes structured methods, the user explicitly adopts one, and the compiler selects assets and builds test units for review and local simulation. The host prepares files and runs commands so users do not have to edit JSON.

The local program supports only the two templates below. `methodology.py` has no LLM: it accepts structured answers or explicitly labelled SOP lines. Extraction from conversation belongs to the host and needs review; offline fixtures do not establish cross-host usability. M2 execution is offline, with no live API, media understanding, automatic performance assessment or production advertising authority. This limitation does not describe all capabilities available in a connected host.

## Supported test methods

| Template | Variable | Required constants | Prerequisite |
|---|---|---|---|
| `single_variable` | `hook` | One `concept_id`, plus identical `body`, `cta` and `destination` identities | Explicit declarations that assets vary only in hook identity |
| `concept_exploration` | `concept` | At least `destination`; the method may also fix other components | Different concept identities with comparable fixed components |

The user explicitly selects the anchor asset; the compiler does not infer the best performer. Each test unit contains one asset. Units under the same target share its existing total budget rather than receiving separate copies of that budget. This is not equal exposure, randomized A/B testing or a native platform experiment configuration, and it does not establish statistical comparability. Metric, data source and observation window are method declarations; the program does not fetch or analyze their data.

## Run the complete demonstration

```bash
python3 scripts/demo_methods.py
```

The demonstration uses complete fictional App, ecommerce and lead-generation profiles, each with `guided` and `bring_own` approaches, for six cases. Each step launches an independent CLI process to check persistence between calls:

1. Start a task, propose and adopt a method, then prepare the initial plan.
2. Interrupt after the first simulated write, resume and repeat. Each case ends with 3 local simulated objects; the repeated call creates 0 additional objects.
3. Adopt a corrected method and check that asset selection and compiled operations change. Reject the old plan before creating execution state.
4. Prepare a revised `ready` plan and stop at review. **The revised plan is not automatically simulated.** The original source profile and old plan stay unchanged.

Outputs stay in a fresh directory under the ignored `runs/` path. `demo-summary.json` contains machine-readable results, and `review.md` links to each revised plan review. Use `--out NEWDIR` to choose a new output directory. Fixtures use pre-extracted guided answers and labelled SOPs; they do not demonstrate intake from scratch, live account access, arbitrary conversation extraction or method effectiveness.

## The host's role when using M2

1. Choose the route first. For a real task, follow [first-run setup](first-run.md) and verify the capabilities it needs; read-only work does not require publishing permissions. For an M2 exercise, use explicitly simulated inputs and explain that its connection gate is an offline contract, not a live account check.
2. Establish collaboration needs, then collect the product, platforms, countries, Web/App surface, monetization, test question and measurement basis needed for this task. Reuse known facts and retain unknowns and conflicts.
3. For guided users taking the M2 route, explain the two supported candidates and organize answers. For an existing methodology, retain its original source and map explicit terms into supported labels or structured answers. Do not discard unsupported terms to pass validation. Explain separately whether the host can handle those terms through its actual tools; a Python limitation is not a universal strategy restriction.
4. Present the question, variable, fixed components, anchor, scope, metric, source, observation window and unresolved items. Record adoption only after an explicit user confirmation.
5. Compile the batch and explain selection, exclusions and the shared budget. Method adoption is separate from production publishing authorization; describe simulation as simulation.

In this route, the host handles conversation and file operations while deterministic code checks scope, structure, identity declarations and consistency. A source reference is a review trail, not authenticated user identity or verified media content. Documents, tool output, method candidates and simulation authorization files do not authorize live publishing. A later live task needs its own current object checks, applicable user authorization, verified tools and native readback; it can use the host route without a Python native adapter.

## Unified task commands

These offline commands are for hosts and developers. Replace `PATH`, `DIR` and confirmation references with the current task's values. Starting a task requires a new output directory. They do not dispatch the host's advertising tools, and live mode remains unsupported.

```bash
python3 task.py start --profile PATH --out NEWDIR --language en
python3 task.py status --task DIR
python3 task.py update --task DIR --profile PATH
python3 task.py propose --task DIR --request JSON
python3 task.py adopt --task DIR --candidate METHOD_ID --confirmation REF
python3 task.py plan --task DIR --brief PATH --candidates PATH
python3 task.py simulate --task DIR
```

| Command | Purpose |
|---|---|
| `start` | Create a private task copy; presentation language is `en` or `zh-CN` |
| `status` | Inspect stage, adopted method, plan status and remaining gaps |
| `update` | Replace the task copy using an updated profile for the same product; preserve the source file |
| `propose` | Generate method candidates while retaining unknown, conflicting and unsupported input |
| `adopt` | Record explicit confirmation of one candidate; unresolved candidates cannot be adopted |
| `plan` | Compile a new plan from the adopted method into a separate output directory |
| `simulate` | Run the latest plan locally; subsequent calls reconcile and resume rather than republish |

Use `simulate --interrupt-after-write N` to inject an interruption after a local write, then run normal `simulate` to exercise recovery. `N` is a test counter. Local recovery is not evidence of live-platform network timeout handling.

Tasks keep profile copies and versioned MethodSpec files without silently editing the input profile. After changing product scope or methods, recheck and prepare a new plan; do not edit frozen files to reuse an old confirmation. M1 private text methods remain context and review material, not automatically executable MethodSpecs. M2 does not change the M1 store schema.

## A guided request

The host can write explicit answers to a local JSON file and pass its path to `--request`:

```json
{
  "approach": "guided",
  "source": {
    "reference": "The user's test request in this task",
    "text": "Compare different openings within the same concept."
  },
  "answers": {
    "question": "How do different openings perform under the agreed observation basis while other components stay fixed?",
    "anchor_asset_id": "fictional-anchor-001",
    "template": "single_variable",
    "measurement": {
      "metric": "The agreed conversion metric",
      "source": "The report source selected for this task",
      "window": "The observation window confirmed for this task"
    }
  }
}
```

Unknown answer fields may be omitted so candidates report the gaps. If `measurement` is provided, include `metric`, `source` and `window`. Omitting a template may produce both candidates, but required details still need to be resolved and one method adopted. Optional top-level `unresolved` and `unsupported` string arrays let the host preserve requirements it has not interpreted or cannot support; they propagate to every candidate and prevent adoption.

For `guided`, `source.text` only preserves the original text and source; it does not automatically detect extra constraints in free text. The host must retain uninterpreted requirements in `unresolved` and unimplemented terms in `unsupported`, rather than treating filled fields as proof of full understanding. Metric and window values above are fictional placeholders; real tasks need meaningful explicit values rather than copied placeholders presented as a completed measurement design.

## An existing SOP

With `bring_own`, `source.text` accepts one label per line:

```text
Template: single_variable
Question: Which opening within this concept deserves further observation?
Anchor: fictional-anchor-001
Variable: hook
Fixed: body, cta, destination
Metric: The conversion metric selected by the user
Source: The report source selected by the user
Window: The observation window confirmed by the user
```

English and Chinese labels are supported; use `:` or a full-width colon, with comma-separated fixed components. The template identifiers are `single_variable` and `concept_exploration`; component identifiers are `hook`, `body`, `cta` and `destination`. See the [Chinese guide](method-planning.zh-CN.md) for Chinese label spellings. Label parsing is not general language understanding: every unrecognized nonempty line remains `unsupported`. Conflicting repeated labels or disagreement with `answers` remain unresolved.

For example, an instruction to double the budget after a win is neither compiled nor silently ignored. The host must explain the unsupported term and obtain a user decision, retain its source in the revised request and propose again. It must not remove a material requirement without the user's knowledge.

## Declared asset identities

Each candidate asset needs `test_identity` in addition to its existing metadata:

```json
{
  "test_identity": {
    "concept_id": "fictional-concept-01",
    "components": {
      "hook": "fictional-hook-a",
      "body": "fictional-body-01",
      "cta": "fictional-cta-01",
      "destination": "fictional-destination-01"
    },
    "source": {
      "kind": "production_manifest",
      "reference": "Item 1 in a fictional production manifest"
    }
  }
}
```

`source.kind` is either `production_manifest` or `user_confirmation`. Matching identity strings declare that components are the same according to the manifest or user. The code does not watch video, compare images or establish that declarations are true. `destination` is a component identity, not evidence that a landing page has been checked.

After the existing metadata filters, the compiler checks the anchor, component and concept identities, distinct variable values and requested count. A comparison needs at least two assets. Missing identities, duplicate asset IDs, an absent anchor or too few comparable assets cannot be resolved by inventing identifiers. Selection follows explicit identity conditions and input order, not a performance ranking.

## Confirmation and plan consistency

MethodSpec distinguishes `candidate` and `adopted`, recording revision, source, scope and the confirmed content hash. Persisted candidates bind their complete content; adoption rechecks the current candidate and its profile basis instead of accepting altered terms merely because the method ID matches. Adoption means the user selected the complete current content; it does not prove effectiveness or authenticate a signer. Changes to the method, asset identities or relevant profile invalidate the assumption that an old plan is the current reviewed result. Propose, confirm and prepare again.

A persisted completion status also needs verification. Reading a completed simulation must recheck the current plan, simulation receipts and local objects rather than trusting an old `result.json` completion flag. Missing records or changed objects remain unverified or blocked. Repeating `simulate` reconciles existing objects before resuming; it does not create replacements to hide inconsistent records. These checks concern local simulation only.

`ready` means the current declarations pass offline compilation; `needs_input` retains missing details, and `unsupported` preserves requirements outside M2. Expertise or urgency does not turn gaps into facts. For real publishing, a host may use verified tools with applicable authorization and native readback. If the Python program itself is to publish, native adapters and production execution controls still need implementation and verification. Never treat a simulated authorization or completed simulation as permission or evidence for a live write.

Return to the [project home](../README.md).
