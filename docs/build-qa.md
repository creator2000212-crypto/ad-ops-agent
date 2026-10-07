# Build QA: pre-flight lint and readback receipts

[简体中文](build-qa.zh-CN.md)

Between Sep 10 and 27, 2026 I built Meta and TikTok lead-gen campaigns interactively with WorkBuddy (Tencent's desktop AI agent; not affiliated). Builds followed one protocol: create every object paused, read every object back field by field, then activate; after 09-22, activation also needed my explicit approval of the batch. Two modules here are the offline, tested version of the checks around that protocol:

- [`preflight.py`](../preflight.py) lints a build checklist before anything is created.
- [`readback.py`](../readback.py) compares the plan with what the platform returned after creation and writes a receipt that says HOLD or ACTIVATE.

Both read JSON files and make no platform call. The fixtures use fictional IDs, names, amounts and `example.com` URLs.

## The protocol, live and here

| Stage | On live accounts (Sep 2026) | In this repository |
|---|---|---|
| 1. Pre-flight | — | `preflight.py`: naming, URL, declaration, attribution and duplicate-file checks on the checklist |
| 2. Create paused | Campaigns, ad sets and ads created `PAUSED` as the standing rule | A plan that asks for any other status is refused |
| 3. Field-by-field readback | Objects read back and compared with the plan | `readback.py`: one row per field, HOLD on any mismatch |
| 4. Staged activation | Activated in stages (after 09-22, only on my explicit approval), then status read back again | Not replayed. An ACTIVATE receipt means "eligible", not "approved" |
| 5. Review polling | Platform review status polled after activation | Not replayed. `effective_status` is recorded in the receipt, never gated |

Pre-flight is new in this repository; it moves contradictions that the later stages would find into a check that runs before creation.

## Why these checks exist

| Date (2026) | What happened | What the check does now |
|---|---|---|
| 09-10 | A batch of 25 creatives timed out; the objects that already existed were reconciled before the retry | An object in the readback that the plan does not contain (a duplicate from a retry) holds the build |
| 09-17 | A bulk activation left 8 ads inactive; reading the fields back after activation caught it | Activation is not replayed here. Status is read per object before it, never assumed from the request, and the operating loop's after-state comparison keeps a write that did not land open as "not in effect" |
| 09-18 | I standardized attribution to 7-day click + 1-day view so costs were comparable | Pre-flight fails a campaign whose ad sets use different attribution settings |
| 09-22 | Agent-created automated rules had thresholds written in dollars where the API expects cents, so they were 100x too small and paused ad sets | Money converts by the platform's currency offset for the currency the account reports; there is no x100 default |
| 09-22 | The agent activated a batch after a reply that only answered a pixel question | The receipt says activation still needs the owner's approval of the batch |
| 09-25 | A receipt generator hard-coded `ACTIVE` while the saved readbacks said `PAUSED` / `IN_PROCESS` | Every "Read back" value comes from the readback file; a missing field is "not returned" |

## What `readback.py` checks

`verify_build(plan, readback)` returns `{rows, decision, reasons, ...}`. Each row is `{level, object_key, field, planned, read_back, match}`; `read_back` is `None` when the platform did not return the field. The decision is `activate` only when every row matches and no object is missing or unexpected.

| Field | Meta response path | TikTok response path |
|---|---|---|
| Account currency | ad account `currency` | advertiser `currency` |
| Objective | `objective` | `objective_type` |
| Special ad categories | campaign `special_ad_categories` (compared when the plan states it; an empty list means none declared) | not mapped: a TikTok plan that states it is refused |
| Optimization goal / event | `optimization_goal`, `promoted_object.custom_event_type` | `optimization_goal`, `optimization_event` |
| Daily budget | `daily_budget` (minor units) | `budget` when `budget_mode` is `BUDGET_MODE_DAY` (major units) |
| Bid strategy / amount | `bid_strategy`, `bid_amount` (minor units) | `bid_type`, `conversion_bid_price` |
| Attribution | `attribution_spec` (click and view days) | `click_attribution_window`, `view_attribution_window` |
| Geo / placements | `targeting.geo_locations.countries`, `targeting.publisher_platforms` | `location_ids`, `placements` |
| Destination URL | `creative.object_story_spec.link_data.link` | `landing_page_url` |
| URL parameters | query of the link plus `creative.url_tags` | query of `landing_page_url` |
| CTA | `link_data.call_to_action.type` | `call_to_action` |
| Status | `status` must be `PAUSED` | `operation_status` must be `DISABLE` |

Rules the comparison follows:

- **Missing is not equal.** A field the plan states but the readback lacks is a mismatch shown as *not returned*.
- **Units come from the platform, not a default.** Meta returns money in minor units. The offset table in `readback.py` is copied from Meta's [currency reference](https://developers.facebook.com/docs/marketing-api/currencies) (checked 2026-10-07): USD has two decimals, JPY none, and TWD and HUF none on Meta even though ISO 4217 gives them two. A currency missing from the table is refused. The account currency is read back too, so a plan written in USD against a JPY account fails instead of being off by 100x.
- **Parameters are checked by name and value.** Every required URL parameter must be present with its planned value; extra parameters are allowed.
- **A planned value is never skipped.** A field the plan states at a level where it is not compared (for example a campaign budget, or a geo on an ad), or on a platform with no response path for it, makes the plan invalid instead of passing unchecked.
- **Status is gated; review state is recorded.** Configured status must be paused. Meta's `effective_status` (for example `IN_PROCESS`) is listed under "Not gated" because it reflects review and delivery processing, not configuration.

## What `preflight.py` checks

The checklist is JSON: campaigns with their ad sets, ad sets with their ads. Platform facts live in the policy file, each list with its source and a checked date, so updating the policy changes the verdict without touching code.

| Check | Level | Fails when | Warns when |
|---|---|---|---|
| Name ↔ bid | ad set | The name says `MAX` but the bid strategy is a cost cap (or the reverse); a cap in the name (`CC6.50`) differs from `bid_amount` | The name does not follow the convention or uses an unknown bid token |
| Name ↔ budget | ad set | The budget in the name (`$20`) differs from `daily_budget` | The name has no readable budget token |
| HTTPS | ad | The destination is not `https` or not an absolute URL | — |
| URL parameters | ad | A required parameter is missing; a macro is not in the platform's documented list | A parameter has a different value from the policy |
| Special category | campaign | The offer category needs a declaration (for example `job_listings` → `EMPLOYMENT`) and the campaign does not declare it | No offer category is stated, or the policy has no sourced map for the platform |
| Attribution | campaign | Ad sets in one campaign use different attribution settings | An ad set has no attribution setting |
| Duplicate creative | ad set | Two ads in the same ad set use the same file (by SHA-256) | An ad has no file hash |

The special-category check only confirms that a declaration is present. It does not decide whether an offer belongs to a category; that stays a human decision.

The operating loop flags the same name-versus-bid contradiction on running ad sets (`name_mismatch` in [`operating_rules.py`](../operating_rules.py)). Pre-flight catches it before the ad set exists.

## Run it

```bash
# Readback: print the receipt, or check it against the committed golden file
python3 readback.py --plan examples/readback/meta-plan.json --readback examples/readback/meta-readback.json
python3 readback.py --plan examples/readback/meta-plan.json --readback examples/readback/meta-readback.json \
    --check examples/readback/expected/meta-receipt.md
python3 readback.py --plan examples/readback/tiktok-plan.json --readback examples/readback/tiktok-readback.json \
    --lang zh-CN --check examples/readback/expected/tiktok-receipt.zh-CN.md

# Pre-flight
python3 preflight.py --checklist examples/preflight/checklist.json --policy examples/preflight/policy.json
python3 preflight.py --checklist examples/preflight/checklist.json --policy examples/preflight/policy.json \
    --check examples/preflight/expected/checklist.md

# Tests
python3 -m unittest tests.test_readback tests.test_preflight -v
```

Options shared by both commands: `--lang en|zh-CN` (default `en`), `--json` for the machine-readable result, `--receipt` / `--report` to write the Markdown file, and `--strict` to exit with 3 on HOLD or FAIL. Exit codes: 0 rendered (or golden matches), 1 golden differs (a unified diff is printed), 2 invalid input.

After an intended change, regenerate a golden file with `--receipt` (readback) or `--report` (pre-flight), read the diff, then run `--check`.

## Sample receipt

Excerpt from [`examples/readback/expected/meta-receipt.md`](../examples/readback/expected/meta-receipt.md). The Meta fixture has exactly one mismatch, an ad whose URL parameters lack `utm_content`, so the build holds. The [TikTok receipt](../examples/readback/expected/tiktok-receipt.md) matches every field and says ACTIVATE.

**Created PAUSED 7/7 → Readback 40/41 fields → HOLD**

| Step | Time | Result |
|---|---|---|
| Created PAUSED | 2026-09-23T02:00:00Z | 7 of 7 planned objects returned; 7 read back `PAUSED` |
| Readback | 2026-09-23T02:03:00Z | 40 of 41 fields match the plan |
| Decision | — | HOLD: 1 mismatch · nothing activated |

- `ad-h3` · URL parameters: missing required parameter `utm_content`

| Level | Object | Field | Planned | Read back | Match |
|---|---|---|---|---|:---:|
| ad set | `as-h1` | Daily budget | `20.00 USD` | `20.00 USD (raw 2000)` | ✓ |
| ad set | `as-h3` | Bid amount | `6.50 USD` | `6.50 USD (raw 650)` | ✓ |
| ad | `ad-h3` | URL parameters | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}` | ✗ |
| ad | `ad-h3` | Status | `PAUSED` | `PAUSED` | ✓ |

The pre-flight report for the sample checklist is in [`examples/preflight/expected/checklist.md`](../examples/preflight/expected/checklist.md): 7 fail, 3 warn, 21 pass.

## Limits

- The response-path table (`ADAPTERS` in `readback.py`) follows the public Meta Marketing API and TikTok API for Business references. Check it against the API version you read. The Meta map reads the destination from `link_data`; video ads keep it under `video_data.call_to_action.value.link`, which is not mapped yet.
- The readback fixtures are saved-response shapes with fictional values, not captures from a real account.
- A pre-flight pass and an ACTIVATE receipt are not platform review results and not permission to activate. Approval stays with the owner of the batch.
