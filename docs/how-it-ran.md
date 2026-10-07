# How it ran

[简体中文](how-it-ran.zh-CN.md) · [Case studies](case-studies.md) · [Methodology history](methodology-history.md) · [Real vs demo](capability-status.md)

The rules are ported from the read-only 12-hour check I ran as a scheduled WorkBuddy (Tencent's desktop AI agent; not affiliated) job on live Meta and TikTok lead-gen accounts (Sep 22–26, 2026). Builds ran interactively: create paused → field-by-field readback → activate. This repo is the offline, tested version.

This page is the operating record behind that sentence: what ran in WorkBuddy, what each piece became here, the scheduled runs as they happened, and where the setup fell short. I operated the accounts in interactive sessions from Sep 10 to Sep 27, 2026, on behalf of a partner I do not name. Times are local (UTC+8). Account names, IDs, amounts and partner details are left out. The code in this repository makes 0 platform calls.

## What ran where

| WorkBuddy piece | What it did on live accounts | Public counterpart |
|---|---|---|
| Project memory and the method file | Held the current method: how T is computed, the T → 2T → 3T ladder, stop lines, action codes. The 12-hour check had to read it first and cite its entries; it was not allowed to invent thresholds or actions | [`examples/operating/methodology-reference.json`](../examples/operating/methodology-reference.json) (thresholds as data, no code defaults) and [methodology history](methodology-history.md) |
| Skills the agent captured during sessions, curated by me | Reusable procedures: the build protocol, readback, reporting, what to ask before acting | [`AGENTS.md`](../AGENTS.md) and the [host workflow](workflow.md) |
| Daily 10:00 data pull | Pulled yesterday's Meta and TikTok delivery into a fixed 20-column daily sheet | Settlement reconciliation in [`operating_rules.py`](../operating_rules.py) with [`settlement-daily.json`](../examples/operating/settlement-daily.json) |
| 12-hour read-only check | Re-checked the previous round's actions, pulled data, classified every ad set, wrote an action list, reported | `operating_loop.py round` in [`operating_loop.py`](../operating_loop.py); replayed in the [demo](../demo/README.md) |
| Interactive builds | Create every object paused → read every field back → activate (after Sep 22, only on my explicit approval) → read status again | [`readback.py`](../readback.py), [`preflight.py`](../preflight.py), the [task record](../templates/task-record.md); see [Build QA](build-qa.md) |
| Connectors | Meta through a hosted MCP connector, called by a small JSON-RPC wrapper script; TikTok through a TikTok API for Business client the agent built for me | [Platform connectivity](platform-connectivity.md) (vendor-neutral routes) |

## The two recurring jobs

Both were WorkBuddy automations on the app's local scheduler. They ran only while the laptop was awake and the app open, delivered results inside the app (no push notification), and have been paused since Sep 26.

### Daily 10:00 data pull (created Sep 20)

- Pulled yesterday's delivery for every live offer from Meta and TikTok, using each ad account's own day boundary.
- Wrote a fixed 20-column sheet with the same columns as the partner's settlement sheet, one row per offer, plus a merged Meta + TikTok sheet.
- Scope: Meta accounts limited to the ones settlement covers, written into the pull's configuration (see [WB-09](case-studies.md#wb-09)).
- Two guards in the merge step: a channel that could not be pulled is named in the output and the merged sheet is marked incomplete; a source file dated differently from the requested day stops the merge with no output, so a stale file is never merged in.
- Before delivery it re-read every cell of every sheet and reported empty cells. TikTok accounts in different time zones produced a warning that was passed on as-is; totals across time zones were not presented as comparable.

### 12-hour read-only check (created Sep 22)

0. Re-verify the previous round's actions in an append-only ledger: executed and improved, executed and not improved, not executed, or cannot judge yet.
1. Pull Meta and TikTok.
2. Classify each ad set against the T ladder and the stop lines.
3. Write the action list to the ledger: code, evidence, observation window and expected result for each action.
4. Report: ledger status first, then the action list and the "leave alone" list.

Its instructions said: conclusions and an action list only; no builds, budget changes, pauses, activations or archiving; hand the list back for my approval. Coverage came before speed: a missing channel is reported as missing, never estimated or filled with older numbers, and `accounts=0` means the pull failed, so no conclusions are drawn.

### Retired the same day: a 2-hour Meta watch (Sep 20)

Created and deleted on Sep 20. Its only run returned 0 accounts because the connector's authorization had dropped; the script still exited 0 and wrote a report that looked healthy. The agent reported "no data, no conclusions" instead. That run is [WB-07](case-studies.md#wb-07) and the reason the 12-hour check treats `accounts=0` as a failure.

## Run log

Recomputed read-only from WorkBuddy's local automation database. One-off jobs and an hourly test job created and deleted on Sep 10 are excluded; the 2-hour watch is kept because of what its run showed.

| Date | Job | Outcome | Coverage note |
|---|---|---|---|
| 09-20 | 2-hour watch | Completed, no data | 0 accounts: the connector's authorization had dropped. Reported as a data-source outage; did not reuse an earlier pull |
| 09-21 | Daily pull | Delivered | Meta + TikTok. TikTok accounts in mixed time zones: warning passed on, totals flagged as not comparable |
| 09-22 | Daily pull (manual test) | Interrupted | Manual test just before that day's 10:00 slot; no report |
| 09-22 | Daily pull | Delivered | Meta + TikTok; time-zone warning passed on |
| 09-22 | 12-hour check | Delivered | First round. Meta + TikTok; ledger re-checked first; no write executed |
| 09-23 | Daily pull | Delivered, 16 min late | Meta only. TikTok's access token had expired; gap disclosed and the merged sheet marked incomplete |
| 09-23 | 12-hour check | Delivered | Meta only; TikTok gap disclosed, nothing substituted |
| 09-24 | 12-hour check | Delivered | Meta only; TikTok gap disclosed |
| 09-24 | Daily pull | Delivered, 25 min late | Meta only. The first attempt failed on a local network fault that looked like an expired connector authorization; fixed and re-run. TikTok gap disclosed |
| 09-24 | 12-hour check | Delivered | Meta only; TikTok gap disclosed (third round) |
| 09-25 | 12-hour check | Delivered | Meta only; TikTok gap disclosed (fourth round) |
| 09-25 | Daily pull | Failed | Started 3 h 26 min late; no report |
| 09-25 | 12-hour check | Failed | Catch-up run, 19 min late; stopped after about 3 minutes with no output |
| 09-26 | 12-hour check | Delivered, 13 h 26 min late | Meta + TikTok; TikTok restored |
| 09-26 | Daily pull | Delivered, 5 h 44 min late | Meta + TikTok |

Totals for the two recurring jobs: 14 runs (7 each). 11 delivered a report, 2 failed, 1 was an interrupted test. 6 delivered reports covered Meta only and said so. 6 runs started late after the scheduler missed a slot while the laptop was asleep or the app was closed.

The TikTok gap had one cause: the TikTok client's access token lasted 24 hours and the app had no refresh token, so it needed a manual re-authorization; it stayed undone from Sep 23 until Sep 26. The Sep 24 network failure is the one where the first diagnosis was wrong: the error looked like the Meta connector's authorization had expired, but a local network component had failed. The agent added a connectivity check to the wrapper scripts and re-ran.

## Timeline

| Date (2026) | Event |
|---|---|
| Sep 10 | Interactive operation starts. A batch of 25 creatives times out; existing objects are reconciled before the retry |
| Sep 13 | Target ROAS floor first written down |
| Sep 17 | A bulk activation leaves 8 ads inactive; field readback after activation catches it |
| Sep 18 | ROAS floor raised and every conclusion recomputed; attribution standardized to 7-day click + 1-day view |
| Sep 20 | 2-hour watch returns 0 accounts and refuses to conclude; job deleted. Daily pull created. Daily sheet scoped to settlement (gap 19.6% → about 0.1%). 10 build scripts found hard-coding Advantage+ audience off; fixed, audit script added |
| Sep 21 | First scheduled daily pull |
| Sep 22 | One-ad-set-per-creative ladder adopted. 12-hour check created. Agent-created automated rules misread money units and pause ad sets; rules disabled, ad sets restored, rules rebuilt after a precheck and, by Sep 24, made notify-only. A 25-ad-set batch activated after an ambiguous reply; launch approval becomes an explicit gate |
| Sep 23 | T computed per offer. TikTok token expires; reports are Meta-only until Sep 26 |
| Sep 24 | Read-only settings audit: 72 of 84 Advantage+ creative enhancements off; 8 chosen as defaults for new builds. Acceptance criteria and stop conditions on every action; five-state write gate ported into the private live loop. First commit of this repository (19:25) |
| Sep 25 | Review finds a receipt generator hard-coding `ACTIVE`. A Sep 25 fix stops a missing or null baseline passing the gate as `ready`. Both jobs fail once. 38 commits on `main` by 22:16 |
| Sep 26 | My manual builds diverge from the playbook (cost-cap structures), logged as an open decision. Both jobs paused |
| Sep 27 | Last interactive session |

## Honest limits

- **Read-only by instruction, not by permission.** The 12-hour check was told not to build, change budgets, pause or activate, and its reports say it did not. It ran with broad tool access: the sandbox was disabled so scripts could reach the platforms, and the connectors were the same ones my builds used. Nothing technical prevented a write.
- **A laptop-bound scheduler.** Runs needed the laptop awake and the app open: 6 of 14 started late, and a failed run was visible only when I opened the app.
- **Most optimization was still manual.** Builds, budget changes, pauses and activations happened in interactive sessions, normally with my approval; the two exceptions (automated rules that paused ad sets, [WB-04](case-studies.md#wb-04); an activation on an ambiguous reply, [WB-08](case-studies.md#wb-08)) are why rules became notify-only and launch approval an explicit gate. The jobs proposed; they did not act.
- **Coverage depended on manual re-authorization** for TikTok, which left three days Meta-only.
- **Paused since Sep 26.** Nothing in this repository runs on a schedule.
- **Next step:** read-scoped tokens for scheduled jobs and a tool allow-list, so "read-only" is enforced by permission rather than wording, plus an alert when a run fails or covers only part of the accounts.

## Who did what

I defined the operating rules, thresholds and write-gate behavior from campaigns I ran, and I approved launches and budget changes; the agent executed them. The WorkBuddy skills, scripts and scheduled jobs were created by the agent at my direction. This repository's code and docs were drafted with AI coding agents; I specified and reviewed the decision engine and its tests.
