# Account audit: checks before a round decides and before anything is written

[简体中文](account-audit.zh-CN.md) · [Build QA](build-qa.md) · [Case studies](case-studies.md) · [How it ran](how-it-ran.md)

From Sep 27 to Oct 29, 2026 I kept operating Meta and TikTok lead-gen accounts with WorkBuddy (Tencent's desktop AI agent; not affiliated). The October incidents were different from September's. September's went wrong while a build was being made: a retried batch, an activation without approval, a receipt copied from the plan. October's went wrong on accounts that were already running: a budget written in the wrong unit, names that no longer described what an ad set did, an outside tool changing budgets between rounds, a "full day" counted from the wrong midnight.

[`account_audit.py`](../account_audit.py) is the offline, tested version of the checks those incidents added to the private live loop. It reads one saved read of the accounts, their change log and the write requests a round wants to send, and makes no platform call. The fixtures are fictional.

## Where it sits

| When | Module | What it answers |
|---|---|---|
| Before a build exists | [`preflight.py`](../preflight.py) | Does the checklist contradict itself or the platform's rules? |
| After the build is created paused | [`readback.py`](../readback.py) | Did the platform store what the plan asked for? |
| At the start of every round, before any write | `account_audit.py` | Is this read safe to judge, and is each requested write safe to send? |
| Before each write | `gate()` in [`operating_rules.py`](../operating_rules.py) | Is the field still at the baseline the proposal was made from? |

A request the audit allows still goes through the write gate and needs the owner's approval of the batch ([AGENTS.md](../AGENTS.md) R1, R2). "allow" means the request passed these checks, nothing more.

## Why these checks exist

| Date (2026) | What happened on live accounts | What the check does now | Case |
|---|---|---|---|
| Oct 25 | A separate workflow wrote a budget meant in cents into a connector field that takes dollars; three ad sets ran at 20–200× their budgets for about 1.6 hours | A money value without an explicit unit is refused; a raise to the ceiling or above is refused; a raise beyond the ratio needs a stated reason; rolling back a runaway budget is never held; every round starts with a budget canary | [WB-11](case-studies.md#wb-11) |
| Oct 24–27 | Names said one offer while the destination links carried another (91% of one account's spend on one day); names also carried budgets 30× off the field | The offer comes from the destination link, never the name; a budget in a name is checked against the field | [WB-12](case-studies.md#wb-12) |
| Oct 24–29 | Budgets kept changing between rounds, from Oct 27 by an application outside my list (22 budget changes in 48 hours, single ad sets moved by −95% to +900%); the 12-hour check went 8 rounds without a promotion because no ad set kept one budget for a full day | Every change in the log is attributed to its writer; an outside writer is a P1 finding and its values are not the round's baseline | [WB-13](case-studies.md#wb-13) |
| Oct 25–26 | A budget that took effect yesterday afternoon counted as a full day, and the account's time zone was hard-coded as UTC+0 after it moved to UTC−1 | A full day needs the budget in effect by 00:00 of the previous day in the account's named time zone; a change log that does not reach back far enough gives "unknown" | [WB-14](case-studies.md#wb-14) |
| Oct 2, Oct 25 | Ad sets whose ads had all stopped still counted as live and as capacity | Live means account, campaign, ad set and at least one ad all active; an active ad set without an active ad is a shell | [WB-15](case-studies.md#wb-15) |
| Oct 7, 12, 21 | A pixel change on an existing ad set was refused; a category added to an existing campaign left its ads in an error that could not be cleared; a targeting update that sent one field would have replaced the rest | Fields fixed at creation are refused (build a new object); a field replaced as a whole must carry every key it has now | [WB-16](case-studies.md#wb-16) |
| Oct 28 | A paused batch repeated the offer and creative of live ad sets in the same account; activating it as built would have raised the account's daily budget about 2.5× | A paused ad set with the same offer and creative as a live one is flagged with the budget jump | [WB-17](case-studies.md#wb-17) |
| Oct 21 | A late-day budget cut below what the ad sets had already spent stopped them for the rest of the day | A cut to or below today's spend waits for the account's next day | [WB-20](case-studies.md#wb-20) |
| Oct 10 | A campaign the owner had paused by hand was resumed under a general "launch" instruction | A request to resume an object a person paused is refused | [WB-21](case-studies.md#wb-21) |
| Oct 21–27 | Writes to disabled accounts failed | Requests to a disabled account wait; the account is a P0 finding | [WB-22](case-studies.md#wb-22) |

## What it checks

### Findings on the accounts

| Code | Severity | Trigger | What to do |
|---|---|---|---|
| `ACCOUNT_DISABLED` | P0 | Account status is not active | Send nothing to it. Read its state again on reinstatement before anything else |
| `BUDGET_CANARY` | P0 | An active or paused ad set's daily budget is at or above the P0 line | Confirm the unit and the intent before the round does anything else |
| `BUDGET_NO_SPEND` | P1 | A live ad set above the P1 line spent nothing over the last full days | Check delivery before trusting the budget as capacity |
| `BUDGET_FAR_ABOVE_SPEND` | P1 | A live ad set's budget is more than the policy multiple of its recent average spend | Check whether the budget was meant; a large raise also restarts its full day |
| `OFFER_LINK_MISMATCH` | P1 | The offer in the name is not the offer in the destination links | Judge the ad set against the linked offer's T; fix the name or the link |
| `EXTERNAL_WRITER` | P1 | A writer outside the owner list changed objects in the window | Do not take its values as the baseline; the owner decides whether it keeps write access |
| `DUPLICATE_ACTIVATION` | P1 | A paused ad set would run the same offer and creative as a live one in the same account | Remove the duplicates or pause the live copy before activating |
| `SHELL_ADSET` | P2 | An active ad set has no active ad | Not live; its budget is not delivery capacity |
| `NAME_BUDGET_STALE` | P2 | A budget written in the name differs from the field | The field is the fact; rename |
| `OFFER_LINK_UNREADABLE` | P2 | No offer code in any destination link | The offer is unverified |
| `OFFER_NOT_DECLARED` | P2 | The name declares no offer | Name it, or keep it out of per-offer reports |

The report also lists who changed what in the window, with the net budget change per object, and the budget tier of every live ad set: when its current budget took effect in account time and whether it has a full day behind it (`yes`, `no` or `unknown`). The answer is `unknown` when the change log does not reach back far enough, or when its last value is not the value in the budget field (something changed it without a log entry).

### Decisions on write requests

| Code | Decision | When |
|---|---|---|
| `UNIT_MISSING` | refuse | A money value has no `minor` or `major` unit |
| `UNIT_INVALID` | refuse | The value is not a whole number of minor units |
| `ABOVE_CEILING` | refuse | A raise to a budget at or above the hard ceiling; no override |
| `RAISE_TOO_LARGE` | refuse | The raise is beyond the ratio and states no reason |
| `RAISE_OVERRIDE` | allow | The raise is beyond the ratio and states a reason, which the report shows |
| `RUNAWAY_CUT` | allow | A cut from a budget at or above the ceiling or the P0 line; never held for tomorrow |
| `INTRADAY_CUT` | wait | Any other cut to or below today's spend so far; wait for the account's next day |
| `SPEND_UNKNOWN` | wait | A cut with no reading of today's spend; read it first |
| `LOCKED_FIELD` | refuse | The platform fixes the field at creation; build a new object |
| `PARTIAL_REPLACE` | refuse | The platform replaces the field as a whole and the value would clear keys it has now |
| `CURRENT_UNKNOWN` | refuse | The current value is not in the read: a whole-object field, or a budget on an object whose budget was not read |
| `RESUME_HUMAN_PAUSE` | refuse | A person paused the object; resuming it is the owner's decision ([AGENTS.md](../AGENTS.md) R5) |
| `PAUSE_UNATTRIBUTED` | wait | The object is paused and the log does not show the owner pausing it (no entry, or an outside writer); ask the owner |
| `ACCOUNT_DISABLED` | wait | The account is disabled |
| `UNKNOWN_OBJECT` | refuse | The object is not in the read |
| `INVALID_REQUEST` | refuse | The request itself is malformed (for example a value of the wrong type); the rest of the audit still runs |
| `ACCOUNT_MISMATCH` | refuse | The request names a different account from the one the object belongs to |
| `BUDGET_OK`, `OK`, `NO_RULE` | allow | Passed, or no audit rule applies; the write gate still applies |

## Inputs

**Snapshot** ([`examples/audit/snapshot.json`](../examples/audit/snapshot.json)): the read time `as_of` with a UTC offset, the currency, and per account its status, IANA `timezone_name` and the start of its change log (`activity_since`); campaigns and ad sets with status, `created_at`, `daily_budget_minor`, spend per account-local day and today's spend so far; ads with status, `creative_fingerprint` and `destination_url`. `activity` is the change log: time, account, object, writer (the application name the platform reports), event and the old and new values. `write_requests` are the writes the round wants to send.

**Policy** ([`examples/audit/policy.json`](../examples/audit/policy.json)): the canary lines and the multiple, the write ceiling and raise ratio, the patterns that find the offer code in a link and in a name, the owner's writers with their roles (human or agent) and the window, and per platform the money fields, the fields fixed at creation and the fields replaced as a whole. The field lists are observations from live accounts with the date each was seen. Re-check them against the platform documentation for the API version you use.

Money is read in minor units and the currency's exponent comes from the policy; an unknown currency, and a platform the policy has no field rules for, are refused. An empty `accounts` list is refused as a failed read, not reported as healthy. A day with no spend reading skips the spend check and makes a spend share "unknown" instead of counting as zero. The ceiling and raise ratio apply to the money fields listed in `budget_writes.fields`, on ad sets and on campaigns whose budget is in the read; other money fields get the unit check only.

## Run it

```bash
python3 account_audit.py --snapshot examples/audit/snapshot.json --policy examples/audit/policy.json
python3 account_audit.py --snapshot examples/audit/snapshot.json --policy examples/audit/policy.json \
    --check examples/audit/expected/audit.md
python3 account_audit.py --snapshot examples/audit/snapshot.json --policy examples/audit/policy.json \
    --lang zh-CN --check examples/audit/expected/audit.zh-CN.md
python3 -m unittest tests.test_account_audit -v
```

`--json` prints the result, `--report` writes the Markdown, and `--strict` exits 3 when there is a P0 finding. The sample report is [`examples/audit/expected/audit.md`](../examples/audit/expected/audit.md): 2 P0, 5 P1, 3 P2; of 12 write requests, 4 allowed, 6 refused and 2 waiting.

## Limits

- It reads a saved file. It does not fetch the change log, so its writer attribution is only as complete as the log you saved; platforms keep a limited history and filter it by their own day boundary.
- It names an outside writer; it cannot stop one. In October the fix was the owner's: take back that application's write access.
- The canary lines, the ceiling and the raise ratio are this project's conventions, not platform rules. A ratio of 2.0 lets one ladder step through. A cut is never refused; at most it waits.
- It checks the requests it is given. A write sent some other way is outside it, which is why the round re-reads state and runs the write gate before every write.
- "allow" is not an approval, and a clean audit is not a statement about performance.
