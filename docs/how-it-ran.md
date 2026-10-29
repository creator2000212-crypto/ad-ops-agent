# How it ran

[简体中文](how-it-ran.zh-CN.md) · [Case studies](case-studies.md) · [Methodology history](methodology-history.md) · [Real vs demo](capability-status.md)

The rules are ported from the read-only 12-hour check I ran as a scheduled WorkBuddy (Tencent's desktop AI agent; not affiliated) job on live Meta and TikTok lead-gen accounts (Sep 22–26 and Oct 24–29, 2026). Builds ran interactively: create paused → field-by-field readback → activate. This repo is the offline, tested version.

This page is the operating record behind that sentence: what ran in WorkBuddy, what each piece became here, the scheduled runs as they happened, and where the setup fell short. I operated the accounts in interactive sessions from Sep 10 to Oct 29, 2026, on behalf of a partner I do not name. September comes first; [October](#october-the-same-loop-on-running-accounts) has its own section, because what went wrong then was different. Times are local (UTC+8). Account names, IDs, amounts and partner details are left out. The code in this repository makes 0 platform calls.

## What ran where

| WorkBuddy piece | What it did on live accounts | Public counterpart |
|---|---|---|
| Project memory and the method file | Held the current method: how T is computed, the T → 2T → 3T ladder, stop lines, action codes. The 12-hour check had to read it first and cite its entries; it was not allowed to invent thresholds or actions | [`examples/operating/methodology-reference.json`](../examples/operating/methodology-reference.json) (thresholds as data, no code defaults) and [methodology history](methodology-history.md) |
| Skills the agent captured during sessions, curated by me | Reusable procedures: the build protocol, readback, reporting, what to ask before acting | [`AGENTS.md`](../AGENTS.md) and the [host workflow](workflow.md) |
| Daily 10:00 data pull | Pulled yesterday's Meta and TikTok delivery into a fixed 20-column daily sheet | Settlement reconciliation in [`operating_rules.py`](../operating_rules.py) with [`settlement-daily.json`](../examples/operating/settlement-daily.json) |
| 12-hour read-only check | Re-checked the previous round's actions, pulled data, classified every ad set, wrote an action list, reported | `operating_loop.py round` in [`operating_loop.py`](../operating_loop.py); replayed in the [demo](../demo/README.md) |
| Interactive builds | Create every object paused → read every field back → activate (after Sep 22, only on my explicit approval) → read status again | [`readback.py`](../readback.py), [`preflight.py`](../preflight.py), the [task record](../templates/task-record.md); see [Build QA](build-qa.md) |
| Connectors | Meta through a hosted MCP connector, called by a small JSON-RPC wrapper script, and from Oct 21 through a second hosted connector; TikTok through a TikTok API for Business client the agent built for me | [Platform connectivity](platform-connectivity.md) (vendor-neutral routes) |
| October additions to the 12-hour check | A budget canary, writer attribution from the change log, offer codes read from destination links, a strict full-day rule in the account's time zone | [`account_audit.py`](../account_audit.py); see [Account audit](account-audit.md) |

## Why WorkBuddy

I chose WorkBuddy because the job needed one agent that could work end to end on my own machine:

- **Local files.** The creative library lived on my laptop. Frame checks ran through ffmpeg, data handling through Python scripts, and deliverables were CSV, Excel and HTML files.
- **Platform access in the same session.** Meta through a hosted MCP connector and TikTok through an API client, called from the same conversation that read the files and ran the scripts.
- **Scheduled jobs without a server.** The daily pull and the 12-hour check ran as app automations.
- **Memory across sessions.** Project memory and captured skills kept the method and the build protocol from one session to the next.
- **Chinese.** I operate and report in Chinese.

The same setup also set the limits listed under [Honest limits](#honest-limits): a laptop-bound scheduler and read-only by instruction rather than by permission. Nothing in this repository depends on WorkBuddy; any agent app that reads `AGENTS.md` and can run shell commands can use it ([project loading](use-in-agent.md)).

## The two recurring jobs

Both were WorkBuddy automations on the app's local scheduler. They ran only while the laptop was awake and the app open, and delivered results inside the app (no push notification). Both were paused on Sep 26; the 12-hour check was resumed on Oct 24 ([October](#october-the-same-loop-on-running-accounts)), the daily pull was not.

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
| Sep 27 | Last session in the September record; [October](#october-the-same-loop-on-running-accounts) continues below |

## October: the same loop on running accounts

From Sep 27 to Oct 29 the work moved from building to keeping running accounts honest. The September guards held, and the incidents came from a different place: the accounts themselves changed under the loop. The cases are [WB-11 to WB-22](case-studies.md#wb-11); the checks they produced are replayed offline by the [account audit](account-audit.md) and two new [pre-flight](build-qa.md) checks.

### What changed around the loop

- **Connections.** On Oct 2 the hosted connector's login identity changed and the daily pull silently returned 0 rows for some accounts; two accounts lost authorization. On Oct 21 the connector's token stopped working and Meta work moved to a second hosted connector, whose OAuth token a small daily WorkBuddy job kept renewed. On Oct 22 an official Meta connector could not be added to WorkBuddy, and one task (swapping creatives on existing ads) was handed to Claude with a written handoff. The same day the second connector's daily quota ran out.
- **Accounts.** Two September accounts were disabled by the platform, on Sep 27 and Oct 4. From Oct 8 new ad accounts came in through a new connection (five by Oct 16), and by Oct 18 the September accounts were no longer in the connection, so work continued on the new set. Three of the new accounts were disabled by Oct 27 ([WB-22](case-studies.md#wb-22)). The new accounts had no automated rules, so stop-loss depended on the 12-hour check, which only proposes.
- **More writers.** A separate creative workflow in another WorkBuddy session launched ads into the same accounts ([WB-11](case-studies.md#wb-11), [WB-17](case-studies.md#wb-17)), and from Oct 27 an application outside my list changed budgets ([WB-13](case-studies.md#wb-13)).
- **TikTok.** Reporting continued in each round; from Oct 24 the TikTok accounts had no spend. On Oct 28 a new TikTok line restricted to Android was built; the simplified campaign endpoint dropped the operating-system setting without an error, so it was rebuilt on the standard endpoint and read back.
- **Claude.** From mid-October I also used Claude for my own click tracker (attribution, spend sync and partner reporting): an overhaul from Oct 11 and its daily operations from Oct 18. The tracker is a separate private system and is not part of this repository; the parts that could become offline modules here are listed in the [roadmap](roadmap.md) (Chinese).

### The 12-hour check, resumed (Oct 24–29)

Same order as in September (re-check the ledger, pull, classify on the T ladder, write the action list, report), now on the second connector and with four steps added in front of the classification: run the budget canary, attribute every change in the log to its writer, read each ad's offer from its destination link, and judge a full day from local midnight in the account's named time zone.

| Round (local, UTC+8) | Outcome | Coverage and notes |
|---|---|---|
| 10-24 04:11 | Delivered | 5 accounts through the second connector, 0 errors; the retired connector's script returned 0 accounts, reported as expected. 7 new actions (4 P0: two accounts disabled, one disapproval, one over-cost stop). No promotion. The new accounts had no automated rules |
| 10-25 18:53 | Delivered | Strict full day adopted: all 6 live ad sets short of a full day. 6 actions. No promotion |
| 10-26 06:50 | Delivered | Canary clean. 5 actions. No promotion: 9 live ad sets, none with a full day |
| 10-26 19:04 | Delivered | First round computed in UTC−1 (the account's zone had moved on Oct 25). 1 stop proposed. No promotion |
| 10-27 07:18 | Delivered | Five live ad sets had their budgets changed in the previous 6–12 hours. No promotion |
| 10-27 19:34 | Delivered, partial | The canary script stopped on an unreachable account. 3 of 5 accounts readable (two removed from the connector's project, stated). One more account disabled |
| 10-28 07:49 | Delivered, partial | Canary fixed (the unreachable accounts skipped and named). 3 of 5 accounts |
| 10-28 20:00 | Delivered, partial | 3 of 5 accounts. Two P0 disapprovals in a new batch. Eighth round without a promotion |
| 10-29 08:26 | Delivered, partial | 3 of 5 accounts. One promotion proposed, the first after eight rounds without one |

Totals: 9 rounds, all delivered; 4 with partial coverage, each stating which accounts were missing; 1 failed step (the canary), fixed in the next round. The ledger re-check found most proposals not executed (for example 19 of 21 on the evening of Oct 27 and 20 of 21 on the evening of Oct 28); those count as "not executed", never as proposals that failed. The daily pull was not resumed; daily settlement sheets were made by hand on request until Oct 13.

### October timeline

| Date (2026) | Event |
|---|---|
| Oct 2 | Connector login identity changes; the daily pull returns 0 rows for some accounts and two accounts lose authorization |
| Oct 2–3 | Ad sets with no running ads still carry about 40% of one offer's nominal daily budget ([WB-15](case-studies.md#wb-15)); a pixel not shared with the account blocks new ads ([WB-19](case-studies.md#wb-19)) |
| Oct 7 | A pixel change on a running ad set is refused: conversion settings are locked at creation ([WB-16](case-studies.md#wb-16)) |
| Oct 10 | A campaign I paused by hand is resumed under a "launch" instruction ([WB-21](case-studies.md#wb-21)) |
| Oct 12 | A category added after creation leaves ads in an error that does not clear; the campaign is rebuilt ([WB-16](case-studies.md#wb-16)) |
| Oct 8–18 | New ad accounts arrive through a new connection; by Oct 18 the September accounts are no longer in it |
| Oct 15 | Moved ad sets copy their source budgets and spend a day's budget within minutes; moved ad sets now start at a fixed small budget ([WB-18](case-studies.md#wb-18)) |
| Oct 16 | A pixel is marked unavailable; ads created or reactivated under it are stopped ([WB-19](case-studies.md#wb-19)) |
| Oct 18 | Claude takes over the click tracker's daily operations |
| Oct 21 | First connector's token fails; Meta work moves to a second hosted connector. All ad sets switched to one operating system with the full targeting sent ([WB-16](case-studies.md#wb-16)). An evening budget cut stops delivery and is rolled back ([WB-20](case-studies.md#wb-20)). The first of three accounts is disabled ([WB-22](case-studies.md#wb-22)) |
| Oct 22 | One creative swap handed to Claude; the second connector's daily quota runs out |
| Oct 24 | 12-hour check resumed |
| Oct 25 | A budget written in the wrong unit runs 20–200× too high for about 1.6 hours; budget wrapper and canary added ([WB-11](case-studies.md#wb-11)). Strict full day adopted ([WB-14](case-studies.md#wb-14)) |
| Oct 26 | Offer codes read from destination links; names stop counting as evidence ([WB-12](case-studies.md#wb-12)) |
| Oct 27 | An outside application starts changing budgets; writer attribution becomes the first step of each round ([WB-13](case-studies.md#wb-13)) |
| Oct 28 | A paused batch would have duplicated eight live ad sets; kept paused ([WB-17](case-studies.md#wb-17)). New TikTok line built and read back |
| Oct 29 | Last round in this record; open decisions: the outside writer's access, the duplicate batch, one offer's value per lead |

### What October added to the limits

- **The loop only proposes, and that cuts both ways.** Most October proposals were not executed, and the accounts had no automated rules. Stop-loss on the new accounts was a human decision every time.
- **Other writers are outside its control.** The check can name an application that changes budgets; only the owner can take its access away.
- **Coverage still depended on connections.** Two accounts became unreachable through the connector on Oct 27, and the rounds said so instead of filling them in.

## Honest limits

- **Read-only by instruction, not by permission.** The 12-hour check was told not to build, change budgets, pause or activate, and its reports say it did not. It ran with broad tool access: the sandbox was disabled so scripts could reach the platforms, and the connectors were the same ones my builds used. Nothing technical prevented a write.
- **A laptop-bound scheduler.** Runs needed the laptop awake and the app open: 6 of 14 started late, and a failed run was visible only when I opened the app.
- **Most optimization was still manual.** Builds, budget changes, pauses and activations happened in interactive sessions, normally with my approval; the two exceptions (automated rules that paused ad sets, [WB-04](case-studies.md#wb-04); an activation on an ambiguous reply, [WB-08](case-studies.md#wb-08)) are why rules became notify-only and launch approval an explicit gate. The jobs proposed; they did not act.
- **Coverage depended on manual re-authorization** for TikTok, which left three days Meta-only.
- **A schedule only on the laptop.** The 12-hour check ran again from Oct 24 to Oct 29 on the same local scheduler. Nothing in this repository runs on a schedule.
- **Next step:** read-scoped tokens for scheduled jobs and a tool allow-list, so "read-only" is enforced by permission rather than wording, plus an alert when a run fails or covers only part of the accounts.

## Who did what

I defined the operating rules, thresholds and write-gate behavior from campaigns I ran, and I approved launches and budget changes; the agent executed them. The WorkBuddy skills, scripts and scheduled jobs were created by the agent at my direction. This repository's code and docs were drafted with AI coding agents; I specified and reviewed the decision engine and its tests.
