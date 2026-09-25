# Advertising task record

[简体中文](task-record.zh-CN.md) · [Workflow](../docs/workflow.md)

**Who fills it:** the agent normally organizes it from this conversation, supplied material and actual tool results, in the private location the user allows for this task. The user checks scope, plan, budget and decisions rather than manually completing every field.

**How to use it:** enter through [first use](../docs/first-check.md) or the [daily task workflow](../docs/workflow.md). Keep only relevant sections: read-only analysis normally needs task/evidence and handoff; creating or changing objects also needs a proposal, authorization and readback. Mark irrelevant items as not applicable and required missing evidence as unknown. Do not guess to complete the template.

This is a host work record, not an executable tool or Python input format. Never store passwords, tokens or keys, and keep business data and account identities out of the public repository. When the user separately requests reusable learning to be saved, record that persistence scope and authorization.

## Task and evidence

- Task / plan version: [local reference and version]
- User's question: [intent, source and time]
- Platform / account / product scope: [this task only]
- Connection and required capabilities: [verified tools, time and gaps]
- Date / timezone / currency / data cutoff: [definitions]
- Current method: [version, scope and adoption evidence]
- Related previous open items: [none / records to recheck]
- Facts / assumptions / unknowns / conflicts: [separate entries]

## Batch proposal

| Object or new unit | Current state and read time | Proposed fields / assets | Target | Reason and evidence | Budget impact | Unknowns |
|---|---|---|---|---|---|---|
| [fill in] | [do not fabricate] | [fill in] | [fill in] | [source] | [currency/period/owner] | [fill in] |

- Constants and excluded changes: [user boundaries]
- Selection and exclusion reasons: [inspected content, production notes or metadata]
- Order and partial-failure handling: [dependencies and stopping conditions]
- Batch totals: [avoid counting shared budgets twice; show overlapping spend]

## User confirmation

- Confirmed plan version: [version]
- Source and time: [actual confirmation reference; otherwise unconfirmed]
- Authorized actions and limits: [include whether paused creation, activation and updates are allowed]
- Material changes: [revised version and reviewed differences, if any]

## Execution and readback

| Operation | Request time / receipt reference | Native object reference | Target | Actual value / time / source | Review and effective state | Conclusion / open item |
|---|---|---|---|---|---|---|
| [fill in] | [timeout remains unknown] | [private identity] | [planned value] | [must come from a later read] | [record separately; missing is unknown] | [more than a success label] |

Observed impressions/spend: [window, source and result, or not yet observed].
Performance observation: [comparability, maturity, findings and limits; unexecuted is not ineffective].

## Handoff and next check

- Verified results: [objects and evidence]
- Open items: [state, next step, owner or required decision]
- Next-check conditions: [needed data; schedule only with user authorization]
- Candidate learning: [product, conditions, source, candidate or adopted state]
- Persistence authorization and version: [without a save request, retain only this task's record]

<a id="first-use-validation"></a>

<details>
<summary>Maintainer appendix: independent first-use validation (not required for ordinary tasks)</summary>

## First independent use validation

This section supports maintainer-run trials; it is not a prerequisite for a user to receive their first result. Use this section for a trial of the [first-use tutorial](../docs/first-check.md). The owner may invite 2–3 external users who did not build the project, keeping one private copy per participant. This is a blank template: no complete run of that tutorial or independent-user trial is recorded here. It sends no invitations. Mark unrelated publishing sections above as not applicable for the read-only trial.

- Anonymous participant reference / category: [alias; relevant role and experience, no name or contact details]
- Participated in building this project: [yes / no / unknown; explain involvement if relevant]
- Repository revision: [commit SHA and any local changes]
- Host / version / connector: [actual client, version, connector and checked date]
- Platform / read-only scope: [selected account alias, period, reporting level and allowed reads; distinguish requested scope from enforced restrictions]
- Selected first task: [launch preparation / read-only report / import an existing method; its tutorial deliverables]

| Stage | Observed result and private evidence reference | First blocker | Elapsed time, if measured |
| --- | --- | --- | --- |
| Load project instructions | [complete / partial / blocked / not attempted; source] | [observed issue / none observed] | [measurement or not measured] |
| Discover connector tools | [status; actual tools and source] | [observed issue / none observed] | [measurement or not measured] |
| Read selected account and task inputs | [status; identity, coverage and source; no historical report required when the account has not run ads] | [observed issue / none observed] | [measurement or not measured] |
| Complete selected task and check its basis | [status; business summary, report or method review; comparison source] | [observed issue / none observed] | [measurement or not measured] |

- First point of friction overall: [stage, what the participant tried and what happened]
- Author interventions: [count / not tracked; for each, record stage and exact help, including any author takeover; do not infer zero from silence]
- Total elapsed time: [only if measured; start/end, timezone and treatment of pauses, otherwise not measured]
- Actual output / reproducible private evidence: [selected deliverable or gap report, tool/read times and private references; include sampled comparison for reports, sufficient for an authorized reviewer to repeat the check]
- Outcome: [complete / partial / blocked, with evidence and remaining work; complete requires the selected tutorial task's deliverables; reports need sample checks, preparation and method tasks need confirmed key inputs, beyond connection or tool success]
- Can the participant explain the result's limits: [yes / partly / no / not checked; their own explanation of missing business facts, method gaps, data coverage or other actual limits]
- Next fix / owner: [specific change tied to the observed blocker; conditions for a retest]

Keep real account IDs, commercial data, raw outputs and evidence in the participant's authorized private location; never retain credentials or secrets. Before any public sharing, remove identifying data and obtain participant consent. A template, an author-assisted run and an independently completed run are distinct evidence; record assistance even when the final result is complete.

</details>
