# Methodology history

[简体中文](methodology-history.zh-CN.md) · [How it ran](how-it-ran.md) · [Case studies](case-studies.md)

How the method I used on live Meta and TikTok lead-gen accounts changed between Sep 13 and Sep 26, 2026, one entry per change: what triggered it, what changed, and what it did. Thresholds are described in relative terms; the economics in this repository's fixtures are synthetic. The current reference version is [`examples/operating/methodology-reference.json`](../examples/operating/methodology-reference.json).

## Sep 13 · First written cost floor

- **Trigger:** The first cost rule in my method notes.
- **Change:** Target ROAS floor set at 80%. T, the highest acceptable cost per lead, is derived from the value of a lead and that floor.
- **Effect:** T follows from the value of a lead and the floor, so changing either changes every verdict the same way. In this repo: `target_roas` and `target_cost()` in [`operating_rules.py`](../operating_rules.py).

## Sep 18 · Floor raised to 85%, every conclusion recomputed

- **Trigger:** I wanted more return per unit of spend than an 80% floor required.
- **Change:** Target ROAS floor 80% → 85%, which lowers T.
- **Effect:** Every earlier conclusion was recomputed at the new T, so no report mixed verdicts made under two floors.

## Sep 18 · One attribution setting

- **Trigger:** Cost per lead had to be comparable across ad sets, accounts and reports.
- **Change:** Attribution standardised from 1-day click to 7-day click + 1-day view.
- **Effect:** Cost per lead became comparable across ad sets and accounts. In this repo: `preflight.py` fails a campaign whose ad sets use different attribution settings (`test_mixed_attribution_in_one_campaign_fails` in [`tests/test_preflight.py`](../tests/test_preflight.py)).

## Sep 20 · Daily sheet scoped to settlement

- **Trigger:** The daily sheet, pulled from every connected account, came out 19.6% above the partner's settlement export.
- **Change:** The pull was limited to the accounts settlement covers, and the scope was written into the pull's configuration.
- **Effect:** The gap closed to about 0.1% on the checked day. In this repo: settlement reconciliation in [`operating_rules.py`](../operating_rules.py) reports a row present on one side only as a scope gap instead of zero-filling it. Case [WB-09](case-studies.md#wb-09).

## Sep 22 · One ad set per creative, judged on a ladder

- **Trigger:** In the earlier structure several creatives shared one budget, starting budgets were fixed, and judgments leaned on a Poisson interval, so results could not be read per creative.
- **Change:** Each new creative gets its own ad set and budget. Budget moves up the ladder T → 2T → 3T in the same ad set, judged per ad set after a full delivery day; stop lines are measured in T. The Poisson interval only answers "how many more conversions before the sample is enough". Older structures were left as they were, not rebuilt.
- **Effect:** A promotion or a stop names one creative and one budget step. In this repo: `ladder`, `promotion` and `stop_loss` in the methodology, applied by `decide_account()` in [`operating_rules.py`](../operating_rules.py).

## Sep 22 · Launch approval as an explicit gate

- **Trigger:** The agent activated a 25-ad-set batch after a reply that only answered a pixel question.
- **Change:** A batch goes live only on a reply that approves that batch. Answers to other questions, silence and "looks fine" are not approval.
- **Effect:** Activation became a separate, named decision. In this repo: an ACTIVATE receipt from [`readback.py`](../readback.py) means "eligible", not "approved"; the write gate's `ready` means "state check passed". Case [WB-08](case-studies.md#wb-08).

## Sep 22–24 · Automated rules made notify-only

- **Trigger:** Agent-created Meta automated rules had thresholds written in dollars where the API expects cents, so they were 100× too small and paused ad sets across several accounts.
- **Change:** Rules disabled, ad sets restored, rules rebuilt after a precheck of the money fields; then switched to notify-only.
- **Effect:** Pauses stay a human decision. In this repo: a pause is a proposal that passes the write gate, never an automatic action; money converts by the platform's currency offset with no ×100 default (`test_budget_minor_units_follow_currency_offset` in [`tests/test_readback.py`](../tests/test_readback.py)). Case [WB-04](case-studies.md#wb-04).

## Sep 23 · T per offer

- **Trigger:** Offers with different values per lead were judged against one account-wide T.
- **Change:** T computed per offer from that offer's value per lead.
- **Effect:** An ad set is judged against the T of the offer it promotes. In this repo: `offer.unit_price` is required on every account and the snapshot is refused without it (`test_snapshot_without_unit_price_is_rejected` in [`tests/test_operating_loop.py`](../tests/test_operating_loop.py)).

## Sep 24 · Advantage+ creative defaults for new builds only

- **Trigger:** A read-only settings audit found 72 of 84 Advantage+ creative enhancements off at audit time.
- **Change:** I chose 8 enhancements as defaults for new builds. Running ads were not changed.
- **Effect:** New builds start from a stated default instead of whatever the build script carried. Case [WB-10](case-studies.md#wb-10).

## Sep 24 · Acceptance criteria, stop conditions and the five-state gate

- **Trigger:** An action in the list said what to do, not what result would count as success or when to stop.
- **Change:** Every action got an acceptance criterion and a stop condition. The five-state write gate (`ready`, `satisfied`, `conflict`, `unknown`, `advisory`) was ported into the private live loop.
- **Effect:** An action can be judged done, failed or not yet judgeable against a stated test, and a write needs a fresh state check first. In this repo: each action in the methodology carries `acceptance` and `stop_condition`; `gate()` in [`operating_rules.py`](../operating_rules.py).

## Sep 26 · Manual builds that diverged, logged as an open decision

- **Trigger:** My own manual builds that day used cost-cap structures the playbook did not describe.
- **Change:** None to the method. The divergence was logged as an open decision.
- **Effect:** The playbook was not rewritten after the fact to match what I did; it changes only when I decide it should.
