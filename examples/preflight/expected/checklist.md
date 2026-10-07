# Pre-flight check — replay, fictional values

Meta · checklist `checklist.json` · policy `policy.json` (version 2026-10-07)

> Runs before anything is created, on the build checklist only. No platform call is made; a pass is not a platform review result and not permission to create.

**Result: FAIL — 7 fail · 3 warn · 21 pass**

## Matrix

| Level | Object | Name | Special category | Attribution | Name ↔ bid | Name ↔ budget | Duplicate creative | HTTPS | URL parameters |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| campaign | `cmp-quote-01` | `LG \| Home quote` | ✓ | ✓ | — | — | — | — | — |
| ad set | `as-h1` | `1n1 \| H1 \| MAX \| $20` | — | — | ✓ | ✓ | ✓ | — | — |
| ad | `ad-h1` | `H1` | — | — | — | — | — | ✓ | ✓ |
| ad set | `as-h2` | `1n1 \| H2 \| MAX \| $20` | — | — | **FAIL** | ✓ | ✓ | — | — |
| ad | `ad-h2` | `H2` | — | — | — | — | — | ✓ | warn |
| ad set | `as-h3` | `1n1 \| H3 \| CC6.50 \| $25` | — | — | ✓ | **FAIL** | ✓ | — | — |
| ad | `ad-h3` | `H3` | — | — | — | — | — | **FAIL** | **FAIL** |
| campaign | `cmp-hire-01` | `LG \| Hiring` | **FAIL** | **FAIL** | — | — | — | — | — |
| ad set | `as-j1` | `1n1 \| J1 \| MAX \| $15` | — | — | ✓ | ✓ | ✓ | — | — |
| ad | `ad-j1` | `J1` | — | — | — | — | — | ✓ | ✓ |
| ad set | `as-j2` | `J2 test` | — | — | warn | warn | **FAIL** | — | — |
| ad | `ad-j2a` | `J2a` | — | — | — | — | — | ✓ | ✓ |
| ad | `ad-j2b` | `J2b` | — | — | — | — | — | ✓ | ✓ |

## Findings

- **fail** · `as-h2` · Name ↔ bid: name says `MAX` (`LOWEST_COST_WITHOUT_CAP`) but bid_strategy is `COST_CAP`
- **fail** · `as-h3` · Name ↔ budget: name says `$25` but daily_budget is `20.00`
- **fail** · `ad-h3` · HTTPS: destination URL is not https: `http://example.com/quote`
- **fail** · `ad-h3` · URL parameters: macro not in the documented list for this platform: `{{ad_name}}`
- **fail** · `cmp-hire-01` · Special category: offer category `job_listings` requires `EMPLOYMENT` in special_ad_categories
- **fail** · `cmp-hire-01` · Attribution: ad sets use different attribution settings: click 1d, view 0d (as-j2); click 7d, view 1d (as-j1)
- **fail** · `as-j2` · Duplicate creative: same creative file in one ad set: `ad-j2a = ad-j2b`
- warn · `ad-h2` · URL parameters: `utm_content` is `h2`, policy expects `{{ad.name}}`
- warn · `ad-h3` · URL parameters: `utm_content` is `{{ad_name}}`, policy expects `{{ad.name}}`
- warn · `as-j2` · Name ↔ bid: name does not follow the convention (`structure | creative | bid | budget`)
- warn · `as-j2` · Name ↔ budget: name does not follow the convention (`structure | creative | bid | budget`)

## Next step

FAIL: fix the checklist and run this check again. Nothing is created from a failing checklist.
