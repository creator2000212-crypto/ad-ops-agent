# Six cases from advertising work

[中文](case-studies.zh-CN.md) · [Host workflow](workflow.md) · [Capabilities and evidence](capability-status.md)

These cases were reconstructed on September 25, 2026 from local records of the maintainer's advertising work in an agent tool: plans, creative audits, scripts, execution records, platform-read snapshots and later reviews. They preserve the process and its evidence limits while removing clients, accounts, advertising object identifiers, financial amounts, media and tracking links.

Labels such as `WB-01` correspond to the maintainer's private source index. The original records are not public, and the labels do not provide access to them. This is not a check of current advertising accounts. The cases explain why the project needs these working practices; **importing the project does not provide the same tools, authorization or execution capabilities**, and the cases do not establish that the offline Python runtime performed these live operations.

## WB-01 · A file in the creative library is not necessarily ready to advertise

Historical records: September 22–23, 2026. Record types: local creative audit, launch plan and candidate list.

- **Input:** Local videos, the product version to promote, previously used creatives and a proposed test structure.
- **Human decision:** Whether previously used creatives are acceptable, whether new files are needed and whether content made for another product version can be reused. The plans leave these choices unresolved; they do not establish agreement.
- **What the agent did:** Extracted frames, inspected visible copy and dimensions, and separated content mismatch from technical limitations. A related launch plan marked whether each candidate had already been used and identified copy still requiring customization.
- **What the evidence establishes:** The audit and candidate plans exist. Some content looked more suitable but lacked sufficient resolution; other files met technical conditions while presenting unsuitable claims. This does not establish publication, approval or performance. An old “usable” label also does not replace a product-match check for the current task.
- **Reusable mechanism:** Record technical readiness, business fit, previous use, the user's selection and inspection evidence separately. Candidate, selected, uploaded, available and delivering are different states.

## WB-02 · Completing a TikTok creative set does not make every item in the batch ready

Historical records: September 22–23, 2026. Record types: revised plan for three business lines, creation state files, readback script and launch receipt.

- **Input:** Three business lines, existing creatives and account settings, and older structures considered for replacement or pausing.
- **Human decision:** Review the structure, creative selection and treatment of the old lines. The receipt still lists settlement definitions, available account capacity and some creative rules as unresolved; the record does not support filling them in as confirmed facts.
- **What the agent did:** Expanded the creative sets from the initial draft, created the structures, read campaign, ad-group and ad states, and preserved the old-line pause results and outstanding questions in the receipt.
- **What the evidence establishes:** The receipt records two lines as `AD_STATUS_DELIVERY_OK` and one as `AD_STATUS_AUDIT`. Its generator reads the native objects. Earlier preparation snapshots also record disabled parents, so files from different stages cannot be treated as one simultaneous observation. “Submitted” cannot be rewritten as “all three delivering normally,” and the pending-review item has no demonstrated performance outcome here.
- **Reusable mechanism:** Report configuration, review state, effective state, parent state and observation time for each item. Follow up on unfinished items without recreating the entire batch. The historical creative count is not a universal requirement for every TikTok advertising product.

## WB-03 · Missing sources and renamed campaigns change what a daily report means

Historical records: September 22–24, 2026. Record types: channel reports, mapping checks, missing-source notice, structure audit and rename history.

- **Input:** Channel data for a defined date, a user-provided business export, account scope, business mapping rules and native object relationships.
- **Human decision:** Set the account population and data sources, resolve authorization gaps and confirm whether a changed name represents a real change in business ownership.
- **What the agent did:** Produced channel tables, a combined table and mapping checks. When one channel could not be retrieved, it marked the combined table incomplete. A separate read-only audit used landing associations, pixels and rename records to distinguish mixed business content within a campaign from drift in name-based reporting rules.
- **What the evidence establishes:** One day's missing-source notice explicitly says Meta data is present and TikTok data is absent. Another daily report says its source differs from the previous day's, limiting direct row-by-row comparison. The ownership audit identifies a rename affecting the mapping, but did not change advertising settings and does not prove all subsequent reports were repaired.
- **Reusable mechanism:** Attach date, time zone, account coverage, sources, missing data and mapping evidence to each report. Keep stable object identity separate from editable names. A partial report can be useful while remaining explicitly partial.

## WB-04 · Automatic rules need field-specific units and a verifiable repair

Historical records: September 22–23, 2026. Record types: incident report, monetary-filter repair script, rule snapshots and activity records.

- **Input:** Unexpected pauses, rule definitions, the intended business thresholds and trigger/recovery records.
- **Human decision:** Confirm which objects should be restored and which thresholds and actions the rules should use. The historical project's thresholds are not defaults for another team.
- **What the agent did:** The incident report attributed the unexpected actions to inconsistent monetary units. The repair script remaps specified monetary filter fields and known old values rather than changing every number. Later records continue to inspect rules and object states.
- **What the evidence establishes:** The incident description and code support units being the diagnosis and repair direction at that time. The report's statement that recovery completed does not independently establish every object's final state, every rule's corrected value or the absence of later incidents.
- **Reusable mechanism:** A connector declares field units and value semantics. The plan shows business and native values, validates before writing, and reads back the specific filters and affected object states. Check conversions against explicit known examples instead of multiplying or dividing an entire configuration.

## WB-05 · The next monitoring round starts with whether the previous action happened

Historical records: September 23–24, 2026. Record types: monitoring reports, follow-up reads and an action/verification ledger.

- **Input:** Current data, earlier recommendations, native configuration, actual operations and the agreed observation window.
- **Human decision:** Execute, adjust, defer or reject a recommendation. Operation reviews also record differences between manual changes and the earlier structure; a user's method cannot be inferred solely from the AI's suggestions.
- **What the agent did:** Follow-up scripts read the objects awaiting verification. The ledger pairs “not executed” with “unable to assess,” alongside other entries recording execution and improvement. Monitoring reports keep proposed actions, observations and unresolved items distinct.
- **What the evidence establishes:** The ledger does not label every unresolved problem as a failed method. However, its improvement labels still need the underlying platform data and observation window; they do not establish causality by themselves. A report's budget or pause recommendation is also not evidence that the action happened.
- **Reusable mechanism:** Keep recommendation, execution, object state and outcome assessment as separate records. Do not evaluate the effect of an unexecuted action or finalize a judgment before its observation window. Review pending follow-ups before repeating the same recommendations.

## WB-06 · An ACTIVE row is not necessarily preserved evidence of activation

Historical records: September 20–22, 2026; the evidence conflict was identified during the September 25 review. Record types: Meta batch CSV, receipt generator, paused-stage readbacks and activation script.

- **Input:** A creative batch's plan, created objects, execution state files and launch record being prepared for handoff.
- **Human decision:** Use the batch's actual state to decide whether to observe, investigate or complete remaining work. A conflicting “complete” table should trigger reconciliation rather than make that decision on the user's behalf.
- **What the agent did:** The historical process saved readbacks from paused creation, provided an activation/polling script, and generated a CSV marking every item `ACTIVE`. Review found that the CSV generator hard-coded that value instead of filling it from the final readback of the same run.
- **What the evidence establishes:** The independently saved snapshots remain `PAUSED` / `IN_PROCESS`, and this review did not find the corresponding preserved final readback for that batch. This does not prove activation never happened, but the CSV does not prove every item went live. A separate batch record also shows configured `ACTIVE` items with rejected or pending-review effective states.
- **Reusable mechanism:** Generate receipts from native observations with an explicit check time and keep expected and observed values. Configuration success, approval and delivery remain separate. When final evidence is missing, mark the result for verification and read the objects before deciding what to resume; do not replay the entire batch.

## How these cases inform the project

The public core can reuse task decomposition, creative inspection, measurement checks, batch execution, object readback, partial-failure recovery and follow-up observation. The user's method supplies targeting, budgets, bidding, fixed test structures and business thresholds. A historical conclusion proposed for the knowledge base still needs its applicable conditions, source, evidence limits and review requirements.

Choose the current task through the [host workflow](workflow.md), and use the [capability guide](capability-status.md) to establish what has actually been verified in your host and tools.
