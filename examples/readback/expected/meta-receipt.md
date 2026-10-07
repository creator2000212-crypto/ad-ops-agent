# Build receipt — replay, fictional values

Meta · account `fictional-meta-account-a` · currency USD · plan `meta-plan.json` · readback `meta-readback.json`

> Replayed offline from saved files: no platform call was made. Every value under "Read back" comes from the readback file; a field the platform did not return counts as a mismatch.

## Timeline

**Created PAUSED 7/7 → Readback 40/41 fields → HOLD**

| Step | Time | Result |
|---|---|---|
| Created PAUSED | 2026-09-23T02:00:00Z | 7 of 7 planned objects returned; 7 read back `PAUSED` |
| Readback | 2026-09-23T02:03:00Z | 40 of 41 fields match the plan |
| Decision | — | HOLD: 1 mismatch · nothing activated |

## Problems

- `ad-h3` · URL parameters: missing required parameter `utm_content`

## Fields

| Level | Object | Field | Planned | Read back | Match |
|---|---|---|---|---|:---:|
| account | `fictional-meta-account-a` | Account currency | `USD` | `USD` | ✓ |
| campaign | `cmp-quote-01` | Objective | `OUTCOME_LEADS` | `OUTCOME_LEADS` | ✓ |
| campaign | `cmp-quote-01` | Special ad categories | `(none)` | `(none)` | ✓ |
| campaign | `cmp-quote-01` | Status | `PAUSED` | `PAUSED` | ✓ |
| ad set | `as-h1` | Optimization goal | `OFFSITE_CONVERSIONS` | `OFFSITE_CONVERSIONS` | ✓ |
| ad set | `as-h1` | Optimization event | `LEAD` | `LEAD` | ✓ |
| ad set | `as-h1` | Daily budget | `20.00 USD` | `20.00 USD (raw 2000)` | ✓ |
| ad set | `as-h1` | Bid strategy | `LOWEST_COST_WITHOUT_CAP` | `LOWEST_COST_WITHOUT_CAP` | ✓ |
| ad set | `as-h1` | Attribution | `click 7d, view 1d` | `click 7d, view 1d` | ✓ |
| ad set | `as-h1` | Geo | `US` | `US` | ✓ |
| ad set | `as-h1` | Placements | `facebook, instagram` | `facebook, instagram` | ✓ |
| ad set | `as-h1` | Status | `PAUSED` | `PAUSED` | ✓ |
| ad set | `as-h2` | Optimization goal | `OFFSITE_CONVERSIONS` | `OFFSITE_CONVERSIONS` | ✓ |
| ad set | `as-h2` | Optimization event | `LEAD` | `LEAD` | ✓ |
| ad set | `as-h2` | Daily budget | `20.00 USD` | `20.00 USD (raw 2000)` | ✓ |
| ad set | `as-h2` | Bid strategy | `LOWEST_COST_WITHOUT_CAP` | `LOWEST_COST_WITHOUT_CAP` | ✓ |
| ad set | `as-h2` | Attribution | `click 7d, view 1d` | `click 7d, view 1d` | ✓ |
| ad set | `as-h2` | Geo | `US` | `US` | ✓ |
| ad set | `as-h2` | Placements | `facebook, instagram` | `facebook, instagram` | ✓ |
| ad set | `as-h2` | Status | `PAUSED` | `PAUSED` | ✓ |
| ad set | `as-h3` | Optimization goal | `OFFSITE_CONVERSIONS` | `OFFSITE_CONVERSIONS` | ✓ |
| ad set | `as-h3` | Optimization event | `LEAD` | `LEAD` | ✓ |
| ad set | `as-h3` | Daily budget | `20.00 USD` | `20.00 USD (raw 2000)` | ✓ |
| ad set | `as-h3` | Bid strategy | `COST_CAP` | `COST_CAP` | ✓ |
| ad set | `as-h3` | Bid amount | `6.50 USD` | `6.50 USD (raw 650)` | ✓ |
| ad set | `as-h3` | Attribution | `click 7d, view 1d` | `click 7d, view 1d` | ✓ |
| ad set | `as-h3` | Geo | `US` | `US` | ✓ |
| ad set | `as-h3` | Placements | `facebook, instagram` | `facebook, instagram` | ✓ |
| ad set | `as-h3` | Status | `PAUSED` | `PAUSED` | ✓ |
| ad | `ad-h1` | Destination URL | `https://example.com/quote` | `https://example.com/quote` | ✓ |
| ad | `ad-h1` | URL parameters | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | ✓ |
| ad | `ad-h1` | CTA | `LEARN_MORE` | `LEARN_MORE` | ✓ |
| ad | `ad-h1` | Status | `PAUSED` | `PAUSED` | ✓ |
| ad | `ad-h2` | Destination URL | `https://example.com/quote` | `https://example.com/quote` | ✓ |
| ad | `ad-h2` | URL parameters | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | ✓ |
| ad | `ad-h2` | CTA | `LEARN_MORE` | `LEARN_MORE` | ✓ |
| ad | `ad-h2` | Status | `PAUSED` | `PAUSED` | ✓ |
| ad | `ad-h3` | Destination URL | `https://example.com/quote` | `https://example.com/quote` | ✓ |
| ad | `ad-h3` | URL parameters | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}` | `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}` | ✗ |
| ad | `ad-h3` | CTA | `LEARN_MORE` | `LEARN_MORE` | ✓ |
| ad | `ad-h3` | Status | `PAUSED` | `PAUSED` | ✓ |

## Not gated: review and delivery state at read time

Configured status is gated above. These values come from the platform's review and delivery processing; they are recorded, not compared.

| Object | Field | Value |
|---|---|---|
| `cmp-quote-01` | effective_status | `PAUSED` |
| `as-h1` | effective_status | `PAUSED` |
| `as-h2` | effective_status | `PAUSED` |
| `as-h3` | effective_status | `PAUSED` |
| `ad-h1` | effective_status | `IN_PROCESS` |
| `ad-h2` | effective_status | `IN_PROCESS` |
| `ad-h3` | effective_status | `IN_PROCESS` |

## Next step

HOLD: fix the fields listed above on the platform, read every object back again and re-run this check. A HOLD receipt never leads to activation.
