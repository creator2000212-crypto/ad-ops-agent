# Case studies from live operation

[简体中文](case-studies.zh-CN.md) · [How it ran](how-it-ran.md) · [Methodology history](methodology-history.md) · [Real vs demo](capability-status.md)

Twenty-two cases from the Meta and TikTok lead-gen accounts I operated with WorkBuddy (Tencent's desktop AI agent; not affiliated) between Sep 10 and Oct 29, 2026. Each one ends in a guardrail that now exists in this repository as code, a test or a written rule. `WB-01` to `WB-10` happened while builds were being made in September; `WB-11` to `WB-22` happened on accounts that were already running, in October, and are replayed by the [account audit](account-audit.md) and two new pre-flight checks.

The labels `WB-01` to `WB-22` index my private records: plans, scripts, run outputs, readback snapshots and reviews. The records stay private. Partners, accounts, object IDs, amounts, media and tracking links are removed, and the dates are 2026. The live reads and writes ran through WorkBuddy's connectors; the code here replays the checks offline on fictional data and makes 0 platform calls.

| Case | Outcome | Guardrail in this repo |
|---|---|---|
| [WB-01](#wb-01) | 20 proposed ads held for review before creation | Duplicate-file check in pre-flight |
| [WB-02](#wb-02) | TikTok build for three business lines, handed off object by object | Field-by-field readback receipt |
| [WB-03](#wb-03) | Daily report labeled incomplete when a source was missing | Missing is not zero |
| [WB-04](#wb-04) | Automated rules with a 100× unit error traced, reversed, made notify-only | Currency-aware money conversion |
| [WB-05](#wb-05) | Every round starts by checking the last round's actions | Append-only ledger; `open` keeps failures visible |
| [WB-06](#wb-06) | A receipt that hard-coded `ACTIVE` caught in review | Receipts only from timed readback |
| [WB-07](#wb-07) | A 0-account run reported "no data", not "all healthy" | Empty input fails loudly |
| [WB-08](#wb-08) | Activation after an ambiguous reply turned into an approval gate | `ACTIVATE` means eligible, not approved |
| [WB-09](#wb-09) | Daily sheet vs settlement gap closed from about 20% to about 0.1% | Settlement reconciliation with scope gaps |
| [WB-10](#wb-10) | Build scripts that contradicted a standing rule fixed and audited | Settings as data, not code |
| [WB-11](#wb-11) | A budget written in the wrong unit ran 20–200× too high for about 1.6 hours | Money needs a unit; ceiling, raise ratio and a budget canary |
| [WB-12](#wb-12) | 91% of one account's spend went to an offer no name mentioned | The offer comes from the destination link, not the name |
| [WB-13](#wb-13) | An outside application made 22 budget changes in 48 hours | Every change attributed to its writer |
| [WB-14](#wb-14) | A full day counted from the wrong midnight | Local midnight in the account's named time zone |
| [WB-15](#wb-15) | Ad sets with no running ads counted as live | Live needs an active ad |
| [WB-16](#wb-16) | A locked pixel, a late category and a one-field targeting update | Locked and whole-object fields checked before writing |
| [WB-17](#wb-17) | A paused batch that would have run eight ad sets twice | Duplicate activation check |
| [WB-18](#wb-18) | Moved ad sets spent a day's budget within minutes | Moved ad sets start at a fixed budget |
| [WB-19](#wb-19) | A pixel not shared with the account, then one marked unavailable | Pixel check in pre-flight |
| [WB-20](#wb-20) | An evening budget cut stopped delivery for the rest of the day | Cuts below today's spend wait for the next day |
| [WB-21](#wb-21) | A campaign the owner paused was resumed by the agent | Resuming a human pause is refused |
| [WB-22](#wb-22) | Writes to disabled accounts failed | Requests to a disabled account wait |

<a id="wb-01"></a>
<a id="meta-task"></a>

## WB-01 · Creative selection: technical fit and business fit are separate checks

**I turned a folder of local videos and two business lines into 20 proposed ads with 20 copy sets, held as "awaiting creation" for my review.**

**Situation.** On Sep 22 two Meta business lines needed creatives. Some local files had run before, some were made for a different product version, and some were too low in resolution. A TikTok creative audit ran in parallel (Sep 22–23).

**What I did.** I had the agent build a candidate list with, for each file, a selection reason, the visual hook, media details, a prior-use flag and the setup fields, plus three body texts, four headlines, a description and a CTA per entry. The TikTok audit extracted frames and kept "wrong claim for this product" apart from "technically unusable". I decided which files went in, the budget scope, attribution and whether to pause older structures. All 20 entries were recorded as "awaiting creation"; open questions in the plan stayed open.

**Guardrail now in this repo.** [`preflight.py`](../preflight.py) fails an ad set that uses the same file twice, by SHA-256 (`test_duplicate_file_in_one_adset_fails` in [`tests/test_preflight.py`](../tests/test_preflight.py)). The [task record](../templates/task-record.md) keeps candidate, selected, uploaded and live as separate states.

**Evidence:** launch plan, CSV checklist of 20 entries and per-entry copy, Sep 22; TikTok creative audit, Sep 22–23.

<a id="wb-02"></a>
<a id="tiktok-task"></a>

## WB-02 · TikTok build for three business lines: hand off each object's state, not "done"

**I handed off a three-line TikTok build with a per-object status receipt (two lines eligible to deliver, one still in review) instead of a single "launched" message.**

**Situation.** Sep 22–23: three business lines on TikTok, existing creatives and account settings, and older ad groups due to be paused.

**What I did.** I reviewed a revised plan with a fuller creative set. The agent created the structures, read campaign, ad group and ad states back, paused the old lines, and wrote a receipt that listed settlement definitions, account capacity and some creative rules as still open.

| Business line (label) | Status in the receipt | Meaning at handoff |
|---|---|---|
| A | `AD_STATUS_DELIVERY_OK` | Eligible to deliver; spend still to be read separately |
| B | `AD_STATUS_DELIVERY_OK` | Eligible to deliver; spend still to be read separately |
| C | `AD_STATUS_AUDIT` | In review; status check kept open |

A/B/C are labels for this page, not platform names or IDs.

**Guardrail now in this repo.** [`readback.py`](../readback.py) compares every planned field with what the platform returned and records review state separately from configuration (`test_review_state_is_recorded_not_gated` and `test_tiktok_case_matches_every_field` in [`tests/test_readback.py`](../tests/test_readback.py)). See [Build QA](build-qa.md).

**Evidence:** revised plan, creation state files, readback script and launch receipt, Sep 22–23.

<a id="wb-03"></a>

## WB-03 · Daily report: a missing source and a renamed campaign change what the numbers mean

**I kept the daily report honest when TikTok data was missing and a campaign had been renamed: the merged sheet said "incomplete" instead of passing for a full day.**

**Situation.** Sep 22–24. The daily report merged Meta and TikTok. On some days TikTok could not be pulled. One Meta campaign had been renamed to a word with no business meaning, which broke the name-based mapping to its business line.

**What I did.** I required the merged sheet to name the missing channel and never be used as a full day; no stale file and no other channel's numbers were substituted. The agent traced the renamed campaign's owner from its ad names, copy, landing page and pixel association and proposed a mapping fix. I decided the account scope and which business owned the campaign.

**Guardrail now in this repo.** In [`operating_rules.py`](../operating_rules.py) a zero denominator is missing, not zero (`test_zero_denominator_is_missing_not_zero`), and an unreadable metric blocks instead of passing (`test_unreadable_metric_blocks_instead_of_passing`, both in [`tests/test_operating_loop.py`](../tests/test_operating_loop.py)). Settlement reconciliation reports a row present on one side only as a scope gap, never zero-filled (`tests/test_reconciliation.py`).

**Evidence:** channel reports, mapping checks, missing-source notice and rename audit, Sep 22–24.

<a id="wb-04"></a>
<a id="meta-rule-check"></a>

## WB-04 · Automated rules: money units are a field property, not a guess

**When agent-created Meta automated rules paused ad sets they should not have, I traced it to money units, had the ad sets restored, and made the rules notify-only so pauses stay a human decision.**

**Situation.** Sep 22. The agent had written the rules' thresholds in dollars; the API expects cents. Every threshold was 100× too small, and the rules paused ad sets across several accounts.

**What I did.** Disabled the rules and restored the ad sets. The rules were rebuilt after a precheck that remapped only the named money filters against known before-and-after values, with no blanket ×100. By Sep 24 the rules only notified.

**Guardrail now in this repo.** [`readback.py`](../readback.py) converts money by the platform's currency offset, reads the account currency back and refuses a currency it does not know (`test_budget_minor_units_follow_currency_offset`, `test_unknown_currency_is_refused_not_guessed` in [`tests/test_readback.py`](../tests/test_readback.py)). In the operating loop a pause is a proposal that must pass the write gate.

**Evidence:** incident report, money-filter repair script, rule snapshots and activity records, Sep 22–23.

<a id="wb-05"></a>

## WB-05 · Each round starts by checking whether the last round's actions happened

**I made every 12-hour round start by re-verifying the previous round's actions, so an unexecuted recommendation was never scored as a failed one.**

**Situation.** Sep 23–24. Monitoring rounds produced action lists; some were executed, some were not, and some could not be judged yet.

**What I did.** I defined four ledger outcomes: executed and improved (the object goes on a "leave alone" list), executed and not improved (escalate one step), not executed (stays open but is not re-listed every round), cannot judge yet. Each report opened with the ledger status. Executing, adjusting, deferring or rejecting stayed my decision.

**Guardrail now in this repo.** [`operating_loop.py`](../operating_loop.py) keeps an append-only ledger, and `open` shows unresolved rows, including writes that did not take effect (`test_ledger_is_append_only_and_folds`, `test_open_rows_keep_the_ineffective_write_visible`). A missing ledger raises an error instead of reporting nothing open (`test_missing_ledger_raises`, all in [`tests/test_operating_loop.py`](../tests/test_operating_loop.py)).

**Evidence:** monitoring reports, follow-up read scripts and the action and verification ledger, Sep 23–24.

<a id="wb-06"></a>

## WB-06 · An ACTIVE row is not evidence of activation

**Reviewing my own launch records, I found a receipt generator that wrote `ACTIVE` on every row while the saved readbacks said `PAUSED` / `IN_PROCESS`. Receipts now come only from timed readback.**

**Situation.** A Meta batch, Sep 20–22: objects created paused, readbacks saved, an activation and polling script, and a CSV launch table for handoff.

**What I did.** In the Sep 25 review I compared the CSV with the saved snapshots and found that the generator hard-coded the status instead of filling it from the final readback. The review found no saved final readback for that batch, so the batch became "to verify": read current state before deciding what to resume, and never replay the whole batch.

**Guardrail now in this repo.** Every "Read back" value in a [`readback.py`](../readback.py) receipt comes from the readback file, and a field the platform did not return is "not returned" (`test_receipt_status_comes_from_readback_not_plan`, `test_missing_field_is_not_returned_never_assumed_equal`). In the operating loop, an after snapshot that still shows the old value keeps the row open as `verified_not_effective` (`test_reconcile_detects_a_write_that_did_not_take_effect`).

**Evidence:** Meta batch CSV, receipt generator, paused-stage readbacks and activation script, Sep 20–22; conflict found in the Sep 25 review.

<a id="wb-07"></a>

## WB-07 · A run that returned 0 accounts refused to conclude

**A scheduled check that came back with 0 accounts reported "no data" instead of "all healthy", and "0 accounts means the pull failed" became a rule of the 12-hour check.**

**Situation.** Sep 20, the only run of a 2-hour Meta watch. The connector's authorization had dropped. The script parsed an error message as data, exited 0, and wrote a report that read like 0 accounts, 0 spend and no urgent issues.

**What I did.** The agent treated 0 accounts as implausible, ruled out the local network and the script, confirmed the failure across accounts, tools and a second connector, and reported a data-source outage with no conclusions; it did not reuse an earlier pull. It also pointed out that exit code 0 with a healthy-looking report is the worst failure mode for an unattended job. That job was deleted the same day. The 12-hour check I set up on Sep 22 treats `accounts=0` as a failed pull and draws no conclusions.

**Guardrail now in this repo.** [`operating_loop.py`](../operating_loop.py) refuses a snapshot with no accounts (`validate_snapshot()`, `test_snapshot_without_accounts_is_rejected`) and raises on a missing ledger instead of reporting `open: 0` (`test_missing_ledger_raises`). A zero denominator is "missing", not 0.

**Evidence:** automation run record and the run's report, Sep 20; the 12-hour check's instructions, Sep 22.

<a id="wb-08"></a>

## WB-08 · An ambiguous reply is not launch approval

**After the agent activated a 25-ad-set batch on a reply that only answered a pixel question, I made launch approval an explicit gate.**

**Situation.** Sep 22. A batch had been built paused and read back. The agent asked about the pixel; I answered that question, and it took the answer as permission to activate.

**What I did.** I removed the judgment call. Approval names the batch; an answer to another question, "looks fine" or silence is not approval. Activation after approval is still read back object by object.

**Guardrail now in this repo.** A [`readback.py`](../readback.py) receipt can say ACTIVATE only when every field matches, and it states that activation still needs the owner's approval of the batch. The write gate's `ready` means "state check passed", not "approved" ([operating loop](operating-loop.md)). [`AGENTS.md`](../AGENTS.md) requires checking that the user's authorization covers that exact batch.

**Evidence:** interactive session record and batch readback, Sep 22.

<a id="wb-09"></a>

## WB-09 · Daily sheet vs settlement: fix the scope before judging costs

**I closed a 19.6% gap between my daily sheet and the partner's settlement export to about 0.1% by scoping the pull to the accounts settlement actually covers.**

**Situation.** Sep 20. The daily sheet pulled from every connected account. For the checked day it came out 19.6% above the settlement export.

**What I did.** Compared the two by account, found accounts that settlement did not cover, and restricted the pull to the covered ones. The scope went into the pull's configuration so a later run could not widen it silently. The checked day then matched within about 0.1%.

**Guardrail now in this repo.** Settlement reconciliation in [`operating_rules.py`](../operating_rules.py) joins platform and settlement rows on account and date, compares spend, results and CPA against tolerances in the methodology, reports a row present on one side only as a scope gap without zero-filling it, and downgrades stop and promote decisions on an unreconciled account to advisory (`tests/test_reconciliation.py`).

**Evidence:** reconciliation notes and the daily pull configuration, Sep 20.

<a id="wb-10"></a>

## WB-10 · Build scripts that contradicted a standing rule

**I found that 10 build scripts hard-coded Advantage+ audience off while my standing rule was on; the scripts were fixed and an audit script was added.**

**Situation.** Sep 20. The audience setting was hard-coded in the build scripts instead of coming from the plan or the standing rule, so every build that used them inherited it.

**What I did.** Fixed the 10 scripts so the value came from the standing rule, and had an audit script check builds against it. On Sep 24 a read-only settings audit found 72 of 84 Advantage+ creative enhancements off; I chose 8 as defaults for new builds only and left running ads unchanged.

**Guardrail now in this repo.** Settings live in data, not code. The operating loop has no code defaults for thresholds (`test_rules_never_fall_back_to_a_code_default` in [`tests/test_operating_loop.py`](../tests/test_operating_loop.py)); [`preflight.py`](../preflight.py) reads platform facts from a sourced policy file; [`readback.py`](../readback.py) refuses a plan that does not state the fields it wants checked (`test_plan_must_state_fields_it_wants_checked`). Audience automation is not yet one of the fields `readback.py` compares.

**Evidence:** build scripts and audit script, Sep 20; settings audit output, Sep 24.

<a id="wb-11"></a>

## WB-11 · A budget field in major units written as minor units

**Three ad sets ran at 20 to 200 times their budgets for about 1.6 hours after a separate workflow wrote a budget in the wrong unit. Budget writes now go through one guarded path, and every round starts with a budget canary.**

**Situation.** Oct 25. A creative workflow running in another WorkBuddy session launched three ad sets through a second connector. That connector's normalized budget field takes major units (dollars); the script treated it as minor units (cents), so a small budget landed as a large one. The budgets were rolled back by hand about 1.6 hours later. In that window the three ad sets bought leads at about 2.1 times the target cost.

**What I did.** Budget writes now go through one wrapper: it only lowers by default, a raise needs an explicit flag and a reason, a value above a hard ceiling is refused, and after writing it reads the native field back in minor units and rolls back on a mismatch. Each 12-hour round starts with a canary over every budget: one at or above a P0 line, or a large one that spent nothing or far more than it usually spends.

**Guardrail now in this repo.** [`account_audit.py`](../account_audit.py) refuses a money value without an explicit `minor` or `major` unit (`test_money_without_unit_is_refused_not_guessed`), refuses a raise to the ceiling or above even with a reason (`test_budget_at_ceiling_is_refused_even_with_a_reason`), needs a stated reason for a raise beyond the ratio (`test_one_ladder_step_passes_and_a_larger_raise_needs_a_reason`), lets the rollback of a runaway budget through at once (`test_rollback_of_a_runaway_budget_is_not_held_for_tomorrow`) and reports a budget at the P0 line as P0, paused or not (`test_budget_at_p0_line_is_p0_even_when_paused`; all in [`tests/test_account_audit.py`](../tests/test_account_audit.py)). [WB-04](#wb-04) was the same class of mistake in automated rules. [`AGENTS.md`](../AGENTS.md) R6.

**Evidence:** incident note, budget wrapper and canary scripts, budget readbacks and the change log, Oct 25–26.

<a id="wb-12"></a>

## WB-12 · Names are labels, not facts

**On one account 91% of a day's spend went to an offer that no ad set name mentioned. The offer is now read from each ad's destination link, and the name is only checked against it.**

**Situation.** Oct 24–27. Ad set names carried the offer and the budget. On Oct 24 three names showed budgets 30 times lower than the budget field, and a fourth about 100 times lower. On Oct 26–27 the links of ad sets named for one offer pointed to a different offer whose value per lead was not yet confirmed; on Oct 27 that was 91% of one account's spend. A cost verdict against the named offer's T said nothing about those ad sets.

**What I did.** Every round extracts the offer code from each ad's destination link and reconciles it with the name. Analysis reads the budget field, never the name. That account's T stayed open until the linked offer's value was confirmed; the decision was still pending on Oct 29.

**Guardrail now in this repo.** [`account_audit.py`](../account_audit.py) reports `OFFER_LINK_MISMATCH` with the ad set's share of the account's spend (`test_name_and_link_disagree`, `test_two_offers_in_one_ad_set_is_a_mismatch`), `OFFER_LINK_UNREADABLE` when no link carries an offer code, and `NAME_BUDGET_STALE` when a name's budget differs from the field (`test_name_budget_that_drifted_from_the_field`). [`AGENTS.md`](../AGENTS.md) R7.

**Evidence:** round reports and link-extraction scripts, Oct 24–29.

<a id="wb-13"></a>

## WB-13 · An outside writer kept resetting the budgets

**Budgets kept changing between rounds, from Oct 27 by an application outside my list that made 22 budget changes in 48 hours. The 12-hour check went 8 rounds without a promotion because no ad set kept one budget for a full day. Every round now starts by attributing each change to its writer.**

**Situation.** Oct 24–29. The change log showed budget updates from applications other than my own console and agent: first from the second connector's own process, then, from Oct 27, from an application I had not set up as a writer for these accounts. In 48 hours it made 22 budget changes; per ad set the net moves ranged from −95% to +900%, with none of the step limits my method uses. Each change restarted that ad set's full day, so the ladder never had a full day to judge.

**What I did.** Writer attribution became the first step of each round: changes are counted per application, an outside writer's values are not taken as the baseline, and the report names the ad sets it touched. Taking back that application's write access went to the owner as the decision every other verdict depended on; it was still open on Oct 29.

**Guardrail now in this repo.** [`account_audit.py`](../account_audit.py) lists who changed what in the window with the net budget change per object, reports a writer outside the owner list as `EXTERNAL_WRITER` and marks the affected budget tiers (`test_outside_writer_is_named_with_its_net_changes`); a change with no writer counts as outside (`test_change_without_writer_is_outside_the_owner_list`). The write gate already holds a value that matches neither baseline nor target as a conflict without guessing who changed it ([`AGENTS.md`](../AGENTS.md) R2).

**Evidence:** change logs and round reports, Oct 24–29.

<a id="wb-14"></a>

## WB-14 · The wrong midnight

**A budget set yesterday afternoon counted as a full day, and the account's day was computed at UTC+0 after the account's time zone moved to UTC−1. A full day is now counted from local midnight in the account's named time zone.**

**Situation.** Oct 25–26. The promotion check treated any budget whose start date was yesterday or earlier as having a full day behind it, so a budget set yesterday afternoon passed. The account's time zone was hard-coded as UTC+0; on Oct 25 the zone left daylight-saving time and moved to UTC−1, shifting every day boundary by an hour.

**What I did.** A full day now means the current budget took effect at or before 00:00 of the previous day in the account's time zone, looked up by name; a budget changed during the day is flagged. Under that rule one round found no ad set ready, and the report gave the time at which the next one would be.

**Guardrail now in this repo.** [`account_audit.py`](../account_audit.py) gives every live ad set's budget tier as yes, no or unknown (`test_budget_set_yesterday_afternoon_has_no_full_day`, `test_named_time_zone_follows_the_daylight_saving_change`). A change log that does not reach back far enough gives "unknown", never "yes" (`test_short_change_log_gives_unknown_not_yes`).

**Evidence:** round reports and judging scripts, Oct 25–29.

<a id="wb-15"></a>

## WB-15 · Active is not live

**Ad sets whose ads had all stopped still counted as live and as capacity. Live now means the account, campaign, ad set and at least one ad are all active.**

**Situation.** On Oct 2 two ad sets whose only ads had stopped still carried about 40% of one offer's nominal daily budget. On Oct 25 a round counted four ad sets with no active ad as live because it looked at the ad set status alone.

**What I did.** The round checks all four levels before it calls an ad set live, lists the rest as shells, and does not take an ad set's past results as a reason to restart it.

**Guardrail now in this repo.** [`account_audit.py`](../account_audit.py) reports an active ad set without an active ad as `SHELL_ADSET`, leaves it out of the live count and the live budget, and judges budget tiers for live ad sets only (`test_active_ad_set_without_active_ad_is_a_shell`, `test_paused_campaign_makes_its_ad_sets_not_live_without_a_finding`).

**Evidence:** daily reports, Oct 2–3; round report, Oct 25.

<a id="wb-16"></a>

## WB-16 · Fields the platform treats differently

**A pixel change on an existing ad set was refused, a category added to an existing campaign left its ads in an error that could not be cleared, and a one-field targeting update would have replaced the rest of the targeting. These fields are now checked before a write is sent.**

**Situation.** On Oct 7 a pixel change on a running ad set was refused: the platform locks an ad set's conversion settings at creation. On Oct 12 a special ad category added to a campaign after creation left its ads in an error state that did not clear; the campaign was rebuilt with the category declared at creation. On Oct 21, switching every ad set to one operating system, the agent noted that the platform replaces targeting as a whole: it sent the full current targeting with the one change and read back that nothing else moved. Ad sets that had been deleted could not be changed at all.

**What I did.** Fields fixed at creation are decided before the build, and a change to one means a new object. Whole-object fields are sent complete.

**Guardrail now in this repo.** [`account_audit.py`](../account_audit.py) refuses a write to a field the policy lists as fixed at creation (`LOCKED_FIELD`, `test_locked_field_needs_a_new_object`) and a whole-object value that would clear keys the object has now (`PARTIAL_REPLACE`, `test_partial_targeting_is_refused_with_the_keys_it_would_clear`). [`preflight.py`](../preflight.py) already fails a campaign that needs a category and does not declare it before creation (`test_undeclared_special_category_fails` in [`tests/test_preflight.py`](../tests/test_preflight.py)). The field lists live in the policy with the date each was observed.

**Evidence:** build logs, error responses and rebuild scripts, Oct 7, Oct 12 and Oct 21.

<a id="wb-17"></a>

## WB-17 · A paused batch that would have run eight ad sets twice

**A new batch was built paused, as the protocol requires, but eight of its ad sets repeated the offer and creative of running ones in the same account. Activating it as built would have raised that account's daily budget about 2.5 times and run each creative twice.**

**Situation.** Oct 28. Another workflow built a new batch, all paused. In one account eight of the new ad sets had the same names, offer and creatives as live ad sets. The same day a selection that picked the new batch by start time also caught live ad sets whose budgets an outside writer had just changed.

**What I did.** Kept the batch paused, listed the overlap per account with the budget before and after, and left the choice to the owner; it was still open on Oct 29. The batch filter now excludes live ad sets.

**Guardrail now in this repo.** [`account_audit.py`](../account_audit.py) reports `DUPLICATE_ACTIVATION` when a paused ad set would run the same offer and creative as a live one in the same account, with the account's live daily budget before and after activation (`test_paused_copy_of_a_live_ad_set_is_flagged_with_the_budget_jump`, `test_same_creative_for_another_offer_is_not_a_duplicate`).

**Evidence:** round report and batch listing, Oct 28–29.

<a id="wb-18"></a>

## WB-18 · Moved ad sets started cold with warm budgets

**Four ad sets rebuilt in another account copied their source budgets; within about 15 minutes of activation one had spent its whole day's budget and another nearly all of it. Moved ad sets now start at a fixed small budget.**

**Situation.** Oct 15. Four ad sets were rebuilt in another account with the budgets their sources were running at. The new account had no delivery history, the bids were uncapped, and it was night in the target market, so the platform spent the day's budgets almost at once.

**What I did.** I set a standing rule: an ad set moved into another account starts at a fixed small daily budget unless I say otherwise. It went into the agent's build procedures.

**Guardrail now in this repo.** [`preflight.py`](../preflight.py) fails an ad set marked `moved_from` whose budget is above the policy's moved-ad-set budget, and turns it into a warning when the checklist states a reason a person reviews (`test_moved_adset_with_copied_budget_fails`, `test_stated_reason_turns_the_fail_into_a_warning`). `moved_from` is for moving work between accounts you are allowed to use. It is not a way to rebuild disapproved or restricted ads in another account; those go through [disapproval triage](disapproval-triage.md).

**Evidence:** build plan, activation readings and the rule record, Oct 15.

<a id="wb-19"></a>

## WB-19 · Pixel availability is an account fact

**New ads failed because the pixel was not shared with the ad account, and two weeks later because a pixel was marked unavailable. Builds now check the account's pixels first.**

**Situation.** On Oct 3 ad creation failed with a permission error: the pixel was not shared with that ad account. The ad set had accepted it; only the ad was refused. On Oct 16 a pixel was marked as no longer available; ads created or reactivated under it were stopped about a minute after activation, while ads already running were not affected.

**What I did.** Before a build, read the account's pixels: shared or not, marked unavailable or not, and when each last fired. Take the pixel from a running ad set's configuration rather than guess it.

**Guardrail now in this repo.** [`preflight.py`](../preflight.py) fails an ad set whose pixel is not in the account read, not shared or marked unavailable, and warns when it has never fired or not fired recently (`PixelTests` in [`tests/test_preflight.py`](../tests/test_preflight.py)).

**Evidence:** error responses and build logs, Oct 3 and Oct 16.

<a id="wb-20"></a>

## WB-20 · An evening budget cut stopped delivery

**Twelve ad sets cut to a lower budget late in the account's day stopped for the rest of the day, and all twelve were restored. A cut below today's spend now waits for the account's next day.**

**Situation.** Oct 21. On my instruction the agent lowered twelve daily budgets late in the account's day and read them back. Most of those ad sets had already spent more than the new budget, so they stopped delivering until the day ended. I asked for the old budgets back; all twelve were restored and read back against the values before the change.

**What I did.** Budget cuts happen after the account's day boundary, not in the evening.

**Guardrail now in this repo.** [`account_audit.py`](../account_audit.py) holds a cut to or below today's spend so far as "wait" until 00:00 account time (`test_cut_below_todays_spend_waits_for_the_next_account_day`).

**Evidence:** session record and budget readbacks before the change, after it and after the rollback, Oct 21.

<a id="wb-21"></a>

## WB-21 · Resuming what a person paused

**Asked to launch a creative, the agent found its campaign paused and resumed it; I had just paused it by hand. A round now refuses to resume a manual pause; that happens only when the owner asks for it.**

**Situation.** Oct 10. The instruction was to launch one creative. The agent read the campaign as paused and set it active, which also resumed a second creative under it. The change log showed I had paused that campaign by hand shortly before. On Oct 27 a scheduled round listed as a new action something the agent had finished hours earlier in an interactive session.

**What I did.** Before acting, read the change log; resuming a manual pause is never a default and is stated in the handoff when the owner asks for it. A round reads the day's session log before writing its action list.

**Guardrail now in this repo.** [`account_audit.py`](../account_audit.py) refuses a request to set an object active when the last pause in the log came from a writer the policy marks as human (`test_resuming_a_human_pause_is_refused`), waits when the log does not show who paused it (`test_pause_not_in_the_log_waits`), and leaves a pause made by the agent to the write gate (`test_resuming_an_agent_pause_is_left_to_the_gate`). [`AGENTS.md`](../AGENTS.md) R5.

**Evidence:** change log and session record, Oct 10; round report, Oct 27.

<a id="wb-22"></a>

## WB-22 · Disabled accounts take no writes

**When the platform disabled accounts, writes to them failed while media uploads still worked. Requests to a disabled account now wait.**

**Situation.** Oct 21–27. Three accounts were disabled by the platform in that week. Write calls to them returned errors; uploading media still succeeded, which made the account look partly usable.

**What I did.** Actions for a disabled account went to a "wait for reinstatement" list instead of being retried, and the first step on reinstatement is to read every object again before acting.

**Guardrail now in this repo.** [`account_audit.py`](../account_audit.py) reports a disabled account as `ACCOUNT_DISABLED` (P0) and returns "wait" for every request to it (`test_disabled_account_is_p0_and_its_requests_wait`).

**Evidence:** account status reads, error responses and round reports, Oct 21–27.
