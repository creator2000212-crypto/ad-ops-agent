# Case studies from live operation

[简体中文](case-studies.zh-CN.md) · [How it ran](how-it-ran.md) · [Methodology history](methodology-history.md) · [Real vs demo](capability-status.md)

Ten cases from the Meta and TikTok lead-gen accounts I operated with WorkBuddy (Tencent's desktop AI agent; not affiliated) between Sep 10 and Sep 27, 2026. Each one ends in a guardrail that now exists in this repository as code, a test or a written rule.

The labels `WB-01` to `WB-10` index my private records: plans, scripts, run outputs, readback snapshots and reviews. The records stay private. Partners, accounts, object IDs, amounts, media and tracking links are removed, and the dates are 2026. The live reads and writes ran through WorkBuddy's connectors; the code here replays the checks offline on fictional data and makes 0 platform calls.

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
