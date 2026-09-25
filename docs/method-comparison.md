# One workflow, two buying methods

[简体中文](method-comparison.zh-CN.md) · [Method planning](method-planning.md) · [Project home](../README.md)

**Fictional offline illustration.** The following assets, names and requirements are invented to show how a user method changes the plan. They are not a campaign, live integration, performance test or recommendation that one method is better.

Both requests start from the same pool: videos `V1` and `V2` have different opening hooks but the same concept, body, CTA and destination; `V3` uses another creative concept and the same destination. Asset identities and equivalence must be checked before a real task. The user supplies the product facts, observation metric, data source, window and budget ceiling.

| User request | What the plan must preserve | What changes in the prepared batch |
| --- | --- | --- |
| “Compare two video openings and keep everything else fixed.” | One concept, body, CTA and destination; a declared metric, source and observation window | Treat `V1` and `V2` as the opening-hook variable; identify any mismatched component before presenting a test plan |
| “Explore different creative directions. Keep the original plan and open a separate test.” | The original plan and its history remain intact; destination and agreed measurement basis stay explicit | Prepare a new plan version comparing `V1` and `V3` by concept; mark a separate execution scope and review how the existing budget ceiling would be shared |

The reusable sequence is the same: understand the business → prepare a plan → confirm the whole batch → execute only within the approved scope → read back object states → review against the agreed window. The user chooses the method and budget. A plan, method adoption or local simulation is **not** production publishing approval.

The public M2 Python module supports constrained `single_variable` and `concept_exploration` templates for **offline** planning and simulation. It requires explicit component identities and cannot infer that media differ only in one feature or prove equal exposure, randomized A/B allocation or ad performance. A connected host may use a user's broader SOP only after its tools and task scope are verified; the offline templates do not define a universal buying strategy. [Implementation and limits →](method-planning.md)
