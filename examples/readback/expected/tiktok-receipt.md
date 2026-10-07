# Build receipt — replay, fictional values

TikTok · account `fictional-tiktok-account-a` · currency USD · plan `tiktok-plan.json` · readback `tiktok-readback.json`

> Replayed offline from saved files: no platform call was made. Every value under "Read back" comes from the readback file; a field the platform did not return counts as a mismatch.

## Timeline

**Created PAUSED 5/5 → Readback 27/27 fields → ACTIVATE**

| Step | Time | Result |
|---|---|---|
| Created PAUSED | 2026-09-23T02:10:00Z | 5 of 5 planned objects returned; 5 read back `DISABLE` |
| Readback | 2026-09-23T02:12:00Z | 27 of 27 fields match the plan |
| Decision | — | ACTIVATE: every field matches and every object is paused |

## Fields

| Level | Object | Field | Planned | Read back | Match |
|---|---|---|---|---|:---:|
| account | `fictional-tiktok-account-a` | Account currency | `USD` | `USD` | ✓ |
| campaign | `cmp-t-quote-01` | Objective | `WEB_CONVERSIONS` | `WEB_CONVERSIONS` | ✓ |
| campaign | `cmp-t-quote-01` | Status | `DISABLE` | `DISABLE` | ✓ |
| ad group | `ag-t1` | Optimization goal | `CONVERT` | `CONVERT` | ✓ |
| ad group | `ag-t1` | Optimization event | `FORM` | `FORM` | ✓ |
| ad group | `ag-t1` | Daily budget | `30.00 USD` | `30.00 USD` | ✓ |
| ad group | `ag-t1` | Bid strategy | `BID_TYPE_NO_BID` | `BID_TYPE_NO_BID` | ✓ |
| ad group | `ag-t1` | Attribution | `click 7d, view 1d` | `click 7d, view 1d` | ✓ |
| ad group | `ag-t1` | Geo | `6252001` | `6252001` | ✓ |
| ad group | `ag-t1` | Placements | `PLACEMENT_TIKTOK` | `PLACEMENT_TIKTOK` | ✓ |
| ad group | `ag-t1` | Status | `DISABLE` | `DISABLE` | ✓ |
| ad group | `ag-t2` | Optimization goal | `CONVERT` | `CONVERT` | ✓ |
| ad group | `ag-t2` | Optimization event | `FORM` | `FORM` | ✓ |
| ad group | `ag-t2` | Daily budget | `30.00 USD` | `30.00 USD` | ✓ |
| ad group | `ag-t2` | Bid strategy | `BID_TYPE_NO_BID` | `BID_TYPE_NO_BID` | ✓ |
| ad group | `ag-t2` | Attribution | `click 7d, view 1d` | `click 7d, view 1d` | ✓ |
| ad group | `ag-t2` | Geo | `6252001` | `6252001` | ✓ |
| ad group | `ag-t2` | Placements | `PLACEMENT_TIKTOK` | `PLACEMENT_TIKTOK` | ✓ |
| ad group | `ag-t2` | Status | `DISABLE` | `DISABLE` | ✓ |
| ad | `ad-t1` | Destination URL | `https://example.com/quote` | `https://example.com/quote` | ✓ |
| ad | `ad-t1` | URL parameters | `utm_source=tiktok&utm_medium=paid&utm_campaign=__CAMPAIGN_NAME__&utm_content=__CID_NAME__` | `utm_source=tiktok&utm_medium=paid&utm_campaign=__CAMPAIGN_NAME__&utm_content=__CID_NAME__` | ✓ |
| ad | `ad-t1` | CTA | `LEARN_MORE` | `LEARN_MORE` | ✓ |
| ad | `ad-t1` | Status | `DISABLE` | `DISABLE` | ✓ |
| ad | `ad-t2` | Destination URL | `https://example.com/quote` | `https://example.com/quote` | ✓ |
| ad | `ad-t2` | URL parameters | `utm_source=tiktok&utm_medium=paid&utm_campaign=__CAMPAIGN_NAME__&utm_content=__CID_NAME__` | `utm_source=tiktok&utm_medium=paid&utm_campaign=__CAMPAIGN_NAME__&utm_content=__CID_NAME__` | ✓ |
| ad | `ad-t2` | CTA | `LEARN_MORE` | `LEARN_MORE` | ✓ |
| ad | `ad-t2` | Status | `DISABLE` | `DISABLE` | ✓ |

## Next step

ACTIVATE: the configuration matches the plan. Activation still needs the owner's approval of this batch; then activate in stages, read status back and poll review. This receipt is not that approval.
