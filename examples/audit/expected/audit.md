# Account audit — replay, fictional values

Meta · snapshot `snapshot.json` read 2026-10-27 12:00 UTC · policy `policy.json` (version 2026-10-29)

> Runs on a saved read of the accounts, their change log and the write requests, before a round's decisions and before any write. No platform call is made. "allow" means a request passed these checks, not that anyone approved it: it still goes through the write gate and needs the owner's approval of the batch.

**Result: 2 P0 · 5 P1 · 3 P2 · write requests: 4 allow · 6 refuse · 2 wait**

## Accounts

| Account | Status | Time zone | Local time at read | Live / active ad sets | Live daily budget | Full day needs a budget set by | Change log from |
|---|---|---|---|---|---|---|---|
| `acct-a` | `ACTIVE` | `Atlantic/Azores` | 2026-10-27 11:00 (UTC-0100) | 4 / 5 | $70.00 | 2026-10-26 00:00 | 2026-10-20 12:00 |
| `acct-b` | `ACTIVE` | `Etc/GMT` | 2026-10-27 12:00 (UTC+0000) | 3 / 3 | $1,270.00 | 2026-10-26 00:00 | 2026-10-27 06:00 |
| `acct-c` | `DISABLED` | `America/New_York` | 2026-10-27 08:00 (UTC-0400) | 0 / 1 | $0.00 | 2026-10-26 00:00 | 2026-10-20 08:00 |

## Findings

- **P0** · `as-b1` · `BUDGET_CANARY` — daily budget $1,000.00 is at or above the P0 line of $1,000.00
- **P0** · `acct-c` · `ACCOUNT_DISABLED` — account status is `DISABLED`: no write is sent to it; requests wait and the state is read again on reinstatement before anything else
- **P1** · `acct-a` · `DUPLICATE_ACTIVATION` — paused `as-a4, as-a5` repeat the offer and creative of live `as-a1, as-a6`; activating them as they are raises the live daily budget from $70.00 to $170.00 and runs the same creative twice
- **P1** · `acct-a` · `EXTERNAL_WRITER` — `bulk-editor-x` is not in the owner list and made 5 change(s), 5 to budgets, on `as-a6, as-a7`; its values are not this round's baseline and the affected budgets restart their full day
- **P1** · `as-a2` · `OFFER_LINK_MISMATCH` — name declares `o-101` but the destination links carry `o-117`; 21.3% of the account's spend on `2026-10-26`; judge it against the linked offer's T, not the name's
- **P1** · `as-b3` · `BUDGET_FAR_ABOVE_SPEND` — daily budget $120.00 is 15.0× the average spend of the last 3 full days ($8.00); limit is 10.0×
- **P1** · `as-b2` · `BUDGET_NO_SPEND` — daily budget $150.00 is above $100.00 and the last 3 full days spent nothing
- **P2** · `as-a7` · `NAME_BUDGET_STALE` — name says `$5` but daily_budget is $50.00; the field is the fact
- **P2** · `as-a3` · `SHELL_ADSET` — active ad set with no active ad: not live, and its $20.00 daily budget is not delivery capacity
- **P2** · `as-b1` · `NAME_BUDGET_STALE` — name says `$5` but daily_budget is $1,000.00; the field is the fact

## Who changed what (last 48 h)

| Account | Writer | Role | Changes | Budget changes | Net budget change per object |
|---|---|---|---|---|---|
| `acct-a` | `bulk-editor-x` | **outside the owner list** | 5 | 5 | −95.0% … +900.0% |
| `acct-a` | `ops-agent` | owner (agent) | 1 | 1 | +100.0% |
| `acct-a` | `owner-console` | owner (human) | 2 | 1 | +66.7% |

## Budget tiers of live ad sets

| Ad set | Account | Daily budget | Current budget since (local) | Full day at this budget? | Changed by an outside writer? |
|---|---|---|---|---|---|
| `as-a1` | `acct-a` | $5.00 | 2026-10-25 23:30 | yes | no |
| `as-a2` | `acct-a` | $10.00 | 2026-10-26 14:00 | **no** | no |
| `as-a6` | `acct-a` | $5.00 | 2026-10-27 07:11 | **no** | **yes** |
| `as-a7` | `acct-a` | $50.00 | 2026-10-27 08:30 | **no** | **yes** |
| `as-b1` | `acct-b` | $1,000.00 | at or before 2026-10-27 06:00 | unknown | no |
| `as-b2` | `acct-b` | $150.00 | at or before 2026-10-27 06:00 | unknown | no |
| `as-b3` | `acct-b` | $120.00 | at or before 2026-10-27 06:00 | unknown | no |

## Write requests

| Request | Object | Field | Requested | Decision | Why |
|---|---|---|---|---|---|
| `w01` | `as-b1` | `daily_budget` | `1000` | **refuse** | money value without a unit (minor or major); refused, not guessed |
| `w02` | `as-a1` | `daily_budget` | `1000 (major)` | **refuse** | a raise to $1,000.00 is at or above the hard ceiling of $100.00 |
| `w03` | `as-a1` | `daily_budget` | `10.00 (major)` | allow | $5.00 → $10.00 (×2.0) |
| `w04` | `as-a2` | `daily_budget` | `50.00 (major)` | **refuse** | $10.00 → $50.00 is ×5.0; above ×2.0 needs a stated reason |
| `w05` | `as-a6` | `daily_budget` | `20.00 (major)` | allow | $5.00 → $20.00 is ×4.0, above ×2.0; allowed on the stated reason: owner restores the budget an outside tool cut |
| `w06` | `as-a7` | `daily_budget` | `500 (minor)` | wait | $5.00 is at or below today's spend so far ($15.00); the ad set would stop for the rest of the day. Wait until 2026-10-28 00:00 (account time) |
| `w07` | `as-a2` | `targeting` | `{"user_os":["Android"]}` | **refuse** | `targeting` is replaced as a whole; this value would clear `age_max, age_min, geo_locations`. Send the full current value with the change |
| `w08` | `as-a2` | `targeting` | `{"age_max":65,"age_min":18,"geo_locations":{"countries":["US"]},"user_os":["Android"]}` | allow | passed the checks |
| `w09` | `as-a2` | `promoted_object` | `{"pixel_key":"pixel-new"}` | **refuse** | `promoted_object` is fixed when the object is created; build a new ad set instead |
| `w10` | `as-a4` | `status` | `ACTIVE` | **refuse** | `owner-console` paused this object at 2026-10-27 07:00; resuming it is the owner's decision, not the round's |
| `w11` | `as-c1` | `status` | `PAUSED` | wait | account status is `DISABLED`; wait for reinstatement and read state again |
| `w12` | `as-b1` | `daily_budget` | `5.00 (major)` | allow | $1,000.00 → $5.00: rolling back a budget at or above $100.00 is not held for tomorrow |

## Next step

P0 findings first, then P1, before the round decides anything. Refused requests are not sent. Waiting requests are checked again once their condition clears. Allowed requests go through the write gate against the state read just before writing, and only into a batch the owner approved.
