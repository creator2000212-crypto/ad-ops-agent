#!/usr/bin/env python3
"""Reference operating rules for a paid-media test loop. Pure functions, offline.

This module is the *decision* layer of a recurring test loop: turning a settled
observation window into metrics, deciding which declared rule fires, and asking
the write gate to confirm the current state before anything is written back.

Boundaries kept from the rest of the repository:

* No network, no platform SDK, no credentials. Every function takes plain data.
* Deterministic. Same input, same output. Numbers use ``Decimal``, so a budget
  comparison never depends on float representation.
* Advisory versus executable is explicit. A rule returns a *proposal* carrying
  its evidence. It never performs an account operation.
* Unknown is not zero. A metric that cannot be computed is ``None`` and is
  reported as missing evidence, never silently treated as a failure or a zero.

Thresholds are data, not code: they arrive in a methodology document so a team
can version its own numbers without editing this module. The bundled
``examples/operating/methodology-reference.json`` is a fictional reference.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import math

VERSION = '1.0'

MONEY = Decimal('0.01')
RATIO = Decimal('0.0001')

LEVELS = ('P0', 'P1', 'P2')

# Fields a proposal may ask the gate to change, per object type. Kept explicit
# so an unknown field is rejected instead of being written blindly.
WRITABLE_FIELDS = {
    'adset': ('daily_budget', 'status', 'bid_strategy', 'bid_amount'),
}


class RuleError(ValueError):
    """Input did not satisfy the declared observation contract."""


# --------------------------------------------------------------------------
# numeric helpers
# --------------------------------------------------------------------------

def dec(value, label):
    """Parse a declared number. ``None`` stays ``None``; other empties are invalid."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise RuleError(f'{label} 必须是数字或数字字符串，当前为 {type(value).__name__}。')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise RuleError(f'{label} 不是合法十进制数：{value!r}') from exc
    if not result.is_finite():
        raise RuleError(f'{label} 不能是 NaN 或无穷。')
    return result


def integer(value, label):
    parsed = dec(value, label)
    if parsed is None:
        return None
    if parsed != parsed.to_integral_value():
        raise RuleError(f'{label} 必须是整数：{parsed}')
    return int(parsed)


def ratio(numerator, denominator):
    """Safe divide. A zero denominator returns ``None`` — never 0, never infinity."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def money(value):
    if value is None:
        return None
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def num(value, digits='0.0001'):
    """Render a Decimal for JSON without float artefacts."""
    if value is None:
        return None
    return str(value.quantize(Decimal(digits), rounding=ROUND_HALF_UP))


def num2(value):
    return num(value, '0.01')


def same_number(left, right):
    """Loose equality used by the write gate: ``10``, ``10.0`` and ``'10.00'`` match."""
    if left is None or right is None:
        return left is right
    if str(left) == str(right):
        return True
    try:
        return abs(float(left) - float(right)) < 1e-9
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------
# methodology
# --------------------------------------------------------------------------

REQUIRED_METHODOLOGY_KEYS = (
    'methodology_id', 'version', 'target_roas', 'ladder', 'sample_gate',
    'promotion', 'stop_loss', 'utilisation', 'creative_rules', 'actions',
)
REQUIRED_ACTION_KEYS = ('code', 'level', 'action', 'window', 'acceptance', 'stop_condition')


def validate_methodology(document):
    if not isinstance(document, dict):
        raise RuleError('方法论文档必须是 JSON 对象。')
    missing = [key for key in REQUIRED_METHODOLOGY_KEYS if key not in document]
    if missing:
        raise RuleError('方法论文档缺少必需字段：' + ', '.join(missing))
    if dec(document['target_roas'], 'target_roas') <= 0:
        raise RuleError('target_roas 必须为正数。')
    if not isinstance(document['ladder'], list) or not document['ladder']:
        raise RuleError('ladder 必须是非空数组。')
    actions = document.get('actions')
    if not isinstance(actions, list) or not actions:
        raise RuleError('actions 必须是非空数组。')
    seen = set()
    for action in actions:
        for key in REQUIRED_ACTION_KEYS:
            if not action.get(key):
                raise RuleError(f'动作 {action.get("code", "?")} 缺少 {key}。')
        if action['level'] not in LEVELS:
            raise RuleError(f'动作 {action["code"]} 的 level 必须是 {LEVELS} 之一。')
        if action['code'] in seen:
            raise RuleError(f'动作 code 重复：{action["code"]}')
        seen.add(action['code'])
    for key in ('measured_in_t',):
        if key not in document['stop_loss']:
            raise RuleError(f'stop_loss 缺少 {key}。')
    return document


def load_methodology(path):
    with open(path, encoding='utf-8') as handle:
        document = json.load(handle)
    return validate_methodology(document)


def actions_by_code(methodology):
    return {action['code']: action for action in methodology['actions']}


def target_cost(unit_price, methodology):
    """T — the acceptable cost per result.

    ``T = unit price x quality factor / target ROAS``. With no deduction the
    quality factor is 1, so a 4.00 unit price against an 85% target yields
    4.705882..., the value the ladder then multiplies by 2 and 3.
    """
    price = dec(unit_price, 'unit_price')
    if price is None or price <= 0:
        raise RuleError('unit_price 必须为正数。')
    quality = dec(methodology.get('quality_factor', '1'), 'quality_factor')
    return price * quality / dec(methodology['target_roas'], 'target_roas')


def ladder_multiplier(stage, methodology):
    ladder = methodology['ladder']
    if stage in ladder:
        return Decimal(ladder.index(stage) + 1)
    raise RuleError(f'未知的阶梯阶段 {stage!r}，已声明：{ladder}')


def next_stage(stage, methodology):
    ladder = methodology['ladder']
    if stage not in ladder:
        raise RuleError(f'未知的阶梯阶段 {stage!r}，已声明：{ladder}')
    index = ladder.index(stage)
    return ladder[index + 1] if index + 1 < len(ladder) else None


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------

def adset_metrics(adset, unit_price, methodology):
    """Derive every comparable metric for one ad set.

    Any metric that cannot be computed is ``None``. Callers must treat ``None``
    as missing evidence rather than a zero result.
    """
    spend = dec(adset.get('spend'), 'spend')
    impressions = integer(adset.get('impressions'), 'impressions')
    clicks = integer(adset.get('clicks'), 'clicks')
    results = integer(adset.get('results'), 'results')
    value = dec(adset.get('value'), 'value')
    frequency = dec(adset.get('frequency'), 'frequency')
    budget = dec(adset.get('daily_budget'), 'daily_budget')
    price = dec(unit_price, 'unit_price')

    t = target_cost(price, methodology)

    ctr = ratio(Decimal(clicks), Decimal(impressions)) if clicks is not None and impressions else None
    cvr = ratio(Decimal(results), Decimal(clicks)) if results is not None and clicks else None
    cpm = ratio(spend * 1000, Decimal(impressions)) if spend is not None and impressions else None
    cpc = ratio(spend, Decimal(clicks)) if spend is not None and clicks else None
    cpa = ratio(spend, Decimal(results)) if spend is not None and results else None
    roas = ratio(value, spend) if value is not None and spend else None
    utilisation = ratio(spend, budget) if spend is not None and budget else None
    overcost_margin = (spend - t * Decimal(results)) if spend is not None and results is not None else None

    stop_multiple = dec(methodology['stop_loss']['measured_in_t'], 'measured_in_t')
    return {
        'adset_key': adset.get('adset_key'),
        'name': adset.get('name', ''),
        'stage': adset.get('ladder_stage'),
        'unit_price': num(price),
        'T': num(t),
        'T_display': num2(money(t)),
        'stop_loss_line': num2(money(t * stop_multiple)),
        'spend': num2(spend),
        'impressions': impressions,
        'clicks': clicks,
        'results': results,
        'value': num2(value),
        'frequency': num(frequency, '0.01'),
        'daily_budget': num2(budget),
        'ctr': num(ctr),
        'cvr': num(cvr),
        'cpm': num2(cpm),
        'cpc': num2(cpc),
        'cpa': num2(cpa),
        'roas': num(roas),
        'expected_results': num(expected_results_v(spend, t)),
        'overcost_margin': num2(overcost_margin),
        'utilisation': num(utilisation),
        # Raw Decimals kept alongside the rendered strings so the decision layer
        # never has to re-parse its own output.
        '_spend': spend, '_impressions': impressions, '_clicks': clicks,
        '_results': results, '_cpa': cpa, '_cpc': cpc, '_ctr': ctr, '_cvr': cvr,
        '_utilisation': utilisation, '_overcost_margin': overcost_margin,
        '_frequency': frequency, '_daily_budget': budget, '_T': t,
    }


def expected_results_v(spend, t):
    return ratio(spend, t)


def raw(values, key):
    """Read a raw Decimal back out of an ``adset_metrics`` result."""
    return values.get('_' + key)


# --------------------------------------------------------------------------
# attribution
# --------------------------------------------------------------------------

def attribution(reference, observed):
    """Split a CPA gap into CPM, CTR and CVR contributions.

    ``CPA = CPM / (1000 x CTR x CVR)``, so after taking logs the gaps add up:
    ``log(CPA/CPA_ref) = dlog(CPM) - dlog(CTR) - dlog(CVR)``.

    The three signed terms are returned with their share of the absolute total,
    which answers "which stage of the funnel moved the cost" instead of
    "which number looks biggest". A term is ``None`` when either input metric is
    missing, so an incomplete comparison stays visibly incomplete.
    """
    keys = ('cpm', 'ctr', 'cvr', 'cpa')
    if any(reference.get(key) is None or observed.get(key) is None for key in keys):
        return {'complete': False, 'terms': None, 'shares': None,
                'reason': '参考组或观察组缺少 CPM / CTR / CVR / CPA 之一，不做归因。'}
    terms = {
        'cpm': math.log(observed['cpm'] / reference['cpm']),
        'ctr': -math.log(observed['ctr'] / reference['ctr']),
        'cvr': -math.log(observed['cvr'] / reference['cvr']),
    }
    observed_total = math.log(observed['cpa'] / reference['cpa'])
    magnitude = sum(abs(value) for value in terms.values())
    shares = ({key: (abs(value) / magnitude if magnitude else 0.0) for key, value in terms.items()}
              if magnitude else {key: 0.0 for key in terms})
    return {
        'complete': True,
        'terms': {key: round(value, 4) for key, value in terms.items()},
        'shares': {key: round(value, 4) for key, value in shares.items()},
        'observed_total': round(observed_total, 4),
        'residual': round(observed_total - sum(terms.values()), 6),
    }


# --------------------------------------------------------------------------
# creative level checks
# --------------------------------------------------------------------------

def creative_findings(adset, values, methodology):
    """Spend concentration, circuit breaker and fatigue for one ad set.

    The circuit breaker needs at least two creatives to be meaningful: with a
    single creative "it consumed all the spend" is trivially true and says
    nothing, and the ad set level stop-loss already covers that case.
    """
    creative_rules = methodology['creative_rules']
    creatives = adset.get('creatives') or []
    total_spend = values['_spend']
    findings = []
    if not creatives or not total_spend:
        return findings

    cap = int(methodology.get('max_creatives_per_adset', 8))
    if len(creatives) > cap:
        findings.append({
            'kind': 'creative_count',
            'detail': f'组内素材 {len(creatives)} 条，超过硬上界 {cap} 条 ⇒ 先裁剪再扩量。',
            'severity': 'structure',
        })

    share_limit = dec(creative_rules['circuit_breaker_spend_share_above'],
                      'circuit_breaker_spend_share_above')
    cpa_multiple = dec(creative_rules['circuit_breaker_cpa_multiple_above'],
                       'circuit_breaker_cpa_multiple_above')
    if len(creatives) >= 2:
        for creative in creatives:
            spend = dec(creative.get('spend'), 'creative.spend')
            share = ratio(spend, total_spend)
            creative_results = dec(creative.get('results'), 'creative.results')
            creative_cpa = ratio(spend, creative_results) if creative_results else None
            if share is None or creative_cpa is None:
                continue
            if share > share_limit and creative_cpa > values['_T'] * cpa_multiple:
                findings.append({
                    'kind': 'circuit_breaker',
                    'creative_key': creative.get('creative_key'),
                    'detail': (f"素材 {creative.get('creative_key')} 吃掉组内 {num(share, '0.001')} 花费、"
                               f"CPA {num2(creative_cpa)} > 目标 x{num(cpa_multiple, '0.1')}"
                               f"（{num2(values['_T'] * cpa_multiple)}）⇒ 熔断该素材，不动整组。"),
                    'spend_share': num(share, '0.0001'),
                    'creative_cpa': num2(creative_cpa),
                })

    min_frequency = dec(creative_rules['fatigue_frequency_at_least'], 'fatigue_frequency_at_least')
    min_drop = dec(creative_rules['fatigue_drop_at_least'], 'fatigue_drop_at_least')
    for creative in creatives:
        frequency = dec(creative.get('frequency'), 'creative.frequency')
        ctr, prior_ctr = dec(creative.get('ctr'), 'creative.ctr'), dec(creative.get('prior_ctr'), 'creative.prior_ctr')
        cvr, prior_cvr = dec(creative.get('cvr'), 'creative.cvr'), dec(creative.get('prior_cvr'), 'creative.prior_cvr')
        if None in (frequency, ctr, prior_ctr, cvr, prior_cvr) or not prior_ctr or not prior_cvr:
            continue
        ctr_drop = ratio(prior_ctr - ctr, prior_ctr)
        cvr_drop = ratio(prior_cvr - cvr, prior_cvr)
        if frequency < min_frequency or ctr_drop is None or cvr_drop is None:
            continue
        # All three conditions must hold together. One or two of them is noise.
        if ctr_drop >= min_drop and cvr_drop >= min_drop:
            findings.append({
                'kind': 'fatigue',
                'creative_key': creative.get('creative_key'),
                'detail': (f"素材 {creative.get('creative_key')} 三条同时满足：频次 {num(frequency, '0.01')} >= "
                           f"{num(min_frequency, '0.1')}、CTR 降 {num(ctr_drop, '0.001')}、CVR 降 "
                           f"{num(cvr_drop, '0.001')} ⇒ 判衰竭，换素材。"),
                'frequency': num(frequency, '0.01'),
                'ctr_drop': num(ctr_drop, '0.0001'),
                'cvr_drop': num(cvr_drop, '0.0001'),
            })
    return findings


def structure_findings(account, methodology):
    """Declared-versus-actual structure problems that need no metric to detect."""
    findings = []
    for adset in account.get('adsets', []):
        name = adset.get('name', '')
        strategy = adset.get('bid_strategy')
        if 'MAX' in name.upper() and strategy and strategy != 'LOWEST_COST_WITHOUT_CAP':
            findings.append({
                'kind': 'name_mismatch',
                'object_key': adset.get('adset_key'),
                'detail': (f'组名写「MAX」但实际 bid_strategy = {strategy}'
                           f'（{adset.get("bid_amount") or "无 bid"}）⇒ 命名与实际不符，'
                           '读结构一律以详情接口的 bid_strategy 为准。'),
            })
        if adset.get('configured_status') == 'ACTIVE' and adset.get('effective_status') == 'DISAPPROVED':
            findings.append({
                'kind': 'effective_status',
                'object_key': adset.get('adset_key'),
                'detail': ('configured_status=ACTIVE 但 effective_status=DISAPPROVED'
                           ' ⇒ 判「能不能投」必须看 effective_status。'),
            })
        if account.get('spend_cap') is None:
            findings.append({
                'kind': 'capability_gap',
                'object_key': account.get('account_key'),
                'detail': 'spend_cap 读回为 null ⇒ 余量预警无法计算，如实标注，不得用 balance 反推。',
            })
            break
    return findings


# --------------------------------------------------------------------------
# decisions
# --------------------------------------------------------------------------

def proposal(account, adset, code, methodology, *, object_key=None, parent_key=None,
             baseline=None, target=None, question=None, evidence=None):
    """Build one proposal in the shape the write gate expects.

    ``object_key`` is what the proposal acts on; ``parent_key`` is the ad set it
    belongs to. They differ for creative-level findings, and the report needs the
    parent so a creative finding is not silently detached from its ad set.
    """
    action = actions_by_code(methodology)[code]
    adset_key = adset.get('adset_key') if adset else None
    proposal = {
        'code': code,
        'level': action['level'],
        'account_key': account.get('account_key'),
        'offer_key': (account.get('offer') or {}).get('offer_key'),
        'object_type': 'adset',
        'object_key': object_key if object_key is not None else adset_key,
        'parent_key': parent_key if parent_key is not None else adset_key,
        'object_name': adset.get('name', '') if adset else '',
        'action': action['action'],
        'window': action['window'],
        'acceptance': action['acceptance'],
        'stop_condition': action['stop_condition'],
        'evidence': evidence or [],
    }
    if question:
        proposal['question'] = question
    # Only attach a write intent when the rule actually wants a field changed.
    # A proposal without 基线/变更 is a *finding*, and the gate will report it as
    # "cannot compare" rather than silently passing it.
    if target is not None:
        proposal['baseline'] = baseline or {}
        proposal['target'] = target
    return proposal


def decide_account(account, methodology):
    """Produce every proposal for one account from a settled snapshot."""
    offer = account.get('offer') or {}
    unit_price = offer.get('unit_price')
    proposals, diagnostics = [], []
    adsets = account.get('adsets') or []

    if not adsets:
        proposals.append(proposal(account, None, 'ACC_STOPPED', methodology,
                                  object_key=account.get('account_key'),
                                  evidence=['账户下没有任何广告组记录。']))
        return proposals, diagnostics

    # ACC_STOPPED is about "nothing is even configured to run". An ad set that is
    # configured ACTIVE but not effective is a *delivery blocker*, not a stopped
    # account — reporting both would misattribute a creative problem to the
    # account and hide which action actually fixes it.
    configured_live = [a for a in adsets if a.get('configured_status') == 'ACTIVE']
    effective_live = [a for a in configured_live if a.get('effective_status') == 'ACTIVE']
    if not configured_live:
        proposals.append(proposal(account, None, 'ACC_STOPPED', methodology,
                                  object_key=account.get('account_key'),
                                  evidence=['没有任何 configured_status 为 ACTIVE 的广告组。']))
    elif account.get('today_spend') is not None and dec(account.get('today_spend'), 'today_spend') == 0:
        proposals.append(proposal(account, None, 'ACC_NO_DELIVERY', methodology,
                                  object_key=account.get('account_key'),
                                  evidence=[f'configured_status 为 ACTIVE 的组有 {len(configured_live)} 个'
                                            f'（其中 effective 可投 {len(effective_live)} 个），但今日消耗为 0。']))
    balance = dec(account.get('balance'), 'balance')
    low = dec(methodology.get('balance_alert_below', '50'), 'balance_alert_below')
    if balance is not None and low is not None and balance <= low:
        proposals.append(proposal(account, None, 'ACC_BALANCE_LOW', methodology,
                                  object_key=account.get('account_key'),
                                  evidence=[f'余额 {num2(balance)} <= 警示线 {num2(low)}。']))

    promotion = methodology['promotion']
    min_results = integer(promotion['min_results'], 'min_results')
    require_full_day = bool(promotion['require_full_day'])
    day_complete = bool((account.get('observation') or {}).get('complete_delivery_day'))

    for adset in adsets:
        values = adset_metrics(adset, unit_price, methodology)
        diagnostics.append({'account_key': account.get('account_key'), **{
            key: value for key, value in values.items() if not key.startswith('_')}})

        creatives = creative_findings(adset, values, methodology)
        for finding in creatives:
            if finding['kind'] == 'circuit_breaker':
                proposals.append(proposal(account, adset, 'CREATIVE_BREAKER', methodology,
                                          object_key=finding.get('creative_key'),
                                          parent_key=adset.get('adset_key'),
                                          evidence=[finding['detail']]))
            elif finding['kind'] == 'fatigue':
                proposals.append(proposal(account, adset, 'CREATIVE_FATIGUE', methodology,
                                          evidence=[finding['detail']]))
            else:
                proposals.append(proposal(account, adset, 'CREATIVE_OVERFLOW', methodology,
                                          evidence=[finding['detail']]))

        if adset.get('configured_status') == 'ACTIVE' and adset.get('effective_status') == 'DISAPPROVED':
            proposals.append(proposal(account, adset, 'AD_STATUS', methodology,
                                      evidence=['effective_status=DISAPPROVED，configured_status 仍为 ACTIVE。']))
            continue

        if adset.get('linked') is False or adset.get('tracking_ok') is False:
            proposals.append(proposal(account, adset, 'LINK_OR_TRACKING_BAD', methodology,
                                      evidence=['声明的链接有效性或回传完整性未通过。'],
                                      target={'status': 'PAUSED'},
                                      baseline={'status': adset.get('configured_status')}))
            continue

        # A metric we could not read is missing evidence, not a passing result.
        if values['_spend'] is None or values['_results'] is None or values['_impressions'] is None:
            diagnostics[-1]['blocked'] = '缺少 spend / impressions / results，无法判定。'
            continue

        code, question, evidence = _classify_adset(
            adset, values, methodology, min_results, require_full_day, day_complete)
        if code is None:
            continue
        target, baseline = _write_intent(code, adset, values, methodology)
        proposals.append(proposal(account, adset, code, methodology, question=question,
                                  evidence=evidence, target=target, baseline=baseline))
    return proposals, diagnostics


def _classify_adset(adset, values, methodology, min_results, require_full_day, day_complete):
    """Return ``(code, question, evidence)`` for one ad set, or ``(None, ...)``."""
    results = values['_results']
    spend = values['_spend']
    impressions = values['_impressions']
    sample = methodology['sample_gate']
    dead_impressions = integer(sample['impressions_for_dead'], 'impressions_for_dead')
    early_cpc = dec(sample.get('early_stop_cpc_above'), 'early_stop_cpc_above')
    early_ctr = dec(sample.get('early_stop_ctr_below'), 'early_stop_ctr_below')

    if results == 0:
        enough_sample = impressions >= dead_impressions
        if values['_overcost_margin'] is not None and \
                values['_overcost_margin'] >= values['_T'] * dec(methodology['stop_loss']['measured_in_t'], 'm') \
                and enough_sample:
            return ('TEST_STOP_NOCONV', '链路与回传是否正常？',
                    [f'零转化且展示 {impressions} >= 判死门槛 {dead_impressions}，'
                     f"累计花费 {num2(spend)} >= 止损线 {num2(values['_T'] * Decimal(str(methodology['stop_loss']['measured_in_t'])))}。"])
        early = []
        if early_cpc is not None and values['_cpc'] is not None and values['_cpc'] > early_cpc:
            early.append(f"CPC {num2(values['_cpc'])} > {num2(early_cpc)}")
        if early_ctr is not None and values['_ctr'] is not None and values['_ctr'] < early_ctr:
            early.append(f"CTR {num(values['_ctr'], '0.0001')} < {num(early_ctr, '0.0001')}")
        if early:
            return ('TEST_EARLY_STOP', '钩子是否需要先修？',
                    ['早停触线（' + '；'.join(early) + '），但展示 '
                     f'{impressions} < 判死门槛 {dead_impressions} ⇒ 停新增花费、不下「素材无效」结论。'])
        return ('TEST_UNDERTESTED', '是出价进不了场，还是预算撞顶？',
                [f"零转化但展示 {impressions} < 判死门槛 {dead_impressions} ⇒ 样本不足，只记录。"])
    if values['_overcost_margin'] is not None and \
            values['_overcost_margin'] >= values['_T'] * dec(methodology['stop_loss']['measured_in_t'], 'm'):
        return ('TEST_STOP_OVERCOST', '回传是否已成熟？',
                [f"累计花费 − T x 转化数 = {num2(values['_overcost_margin'])} >= 止损线 "
                 f"{num2(values['_T'] * Decimal(str(methodology['stop_loss']['measured_in_t'])))}。"])

    if results < min_results:
        return ('TEST_UNDERTESTED', '现有预算下还要多久才能攒够样本？',
                [f'转化 {results} < 最低可判样本 {min_results} ⇒ 样本不足，不判素材好坏。'])

    stage = adset.get('ladder_stage')
    target_stage = next_stage(stage, methodology)
    utilisation = values['_utilisation']
    under = dec(methodology['utilisation']['under_delivering_below'], 'under_delivering_below')
    if utilisation is not None and under is not None and utilisation <= under:
        return ('TEST_UNDERTESTED', '是出价进不了场，还是预算撞顶？',
                [f'预算利用率 {num(utilisation, "0.001")} <= {num(under, "0.01")} ⇒ 花不动，'
                 '先解决能不能花的问题，而不是换素材。'])

    cpa_ok = values['_cpa'] is not None and values['_cpa'] <= values['_T']
    fresh = (not require_full_day) or day_complete
    if cpa_ok and fresh and target_stage:
        return ('LADDER_PROMOTE', f'本档 CPA {num2(values["_cpa"])} <= T {num2(values["_T"])}，是否升到 {target_stage}？',
                [f'转化 {results} >= {min_results}、覆盖完整投放日 = {day_complete}、'
                 f"CPA {num2(values['_cpa'])} <= T {num2(values['_T'])}。"])
    if cpa_ok and not fresh:
        return (None, None, [f'CPA 达标但该档未覆盖完整投放日 ⇒ 本轮不晋级。'])
    if not cpa_ok:
        return ('TEST_UNDERTESTED', '这一档的 CPA 是否已到不可接受？',
                [f"CPA {num2(values['_cpa'])} > T {num2(values['_T'])}，但未达止损线 "
                 f"{num2(values['_T'] * Decimal(str(methodology['stop_loss']['measured_in_t'])))}"
                 ' ⇒ 保持预算、不继续加钱。'])
    return (None, None, [])


def _write_intent(code, adset, values, methodology):
    """Translate a rule into the field change the gate must verify."""
    budget = values['_daily_budget']
    if code == 'LADDER_PROMOTE' and budget is not None:
        multiple = Decimal(str(methodology['promotion']['budget_multiple']))
        new_budget = money(budget * multiple)
        return ({'daily_budget': num2(new_budget)},
                {'daily_budget': num2(budget)})
    if code in ('TEST_STOP_NOCONV', 'TEST_STOP_OVERCOST', 'TEST_EARLY_STOP'):
        return ({'status': 'PAUSED'}, {'status': adset.get('configured_status')})
    return (None, None)


# --------------------------------------------------------------------------
# write gate
# --------------------------------------------------------------------------

READY, SATISFIED, CONFLICT, UNKNOWN, ADVISORY = (
    'ready', 'satisfied', 'conflict', 'unknown', 'advisory')

GATE_LABEL = {
    READY: '可执行',
    SATISFIED: '已满足',
    CONFLICT: '冲突隔离',
    UNKNOWN: '未知',
    ADVISORY: '仅建议',
}

# States that need a human to look before the round can be considered closed.
NEEDS_HUMAN = (CONFLICT, UNKNOWN)


def gate(proposals, writeback):
    """Decide what may be written, using the state read back just before writing.

    Five outcomes, per proposal:

    ``satisfied``  the target value is already in place — write nothing. Writing
                   anyway would be a significant edit and would reset learning.
    ``ready``      the field still holds the value it held when the plan was
                   built, so only the differing fields are sent.
    ``conflict``   the field holds neither the baseline nor the target, so
                   somebody changed it in between. Isolate this row; do not
                   overwrite, and do not restart the whole batch.
    ``unknown``    the current state was not read, or the field is absent from
                   the read. Absent is not the same as equal — never pass it.
    ``advisory``   the finding declares no field change, so there is nothing to
                   gate. Reported separately: counting these as "unknown" would
                   inflate the number of rows that actually need attention.

    Only ``ready`` rows may proceed, and only for their differing fields.
    """
    objects = (writeback or {}).get('objects') or {}
    results = []
    for item in proposals:
        target = item.get('target')
        if not target:
            results.append(_verdict(item, ADVISORY,
                                    ['该发现不涉及写入字段（仅建议），不过闸门。']))
            continue
        current = objects.get(item.get('object_key'))
        if not isinstance(current, dict):
            results.append(_verdict(item, UNKNOWN,
                                    [f"写前状态里没有 {item.get('object_key')!r} 的记录 ⇒ 先复拉，不要盲写。"]))
            continue
        absent = [field for field in target if field not in current]
        if absent:
            results.append(_verdict(item, UNKNOWN,
                                    [f'{field}：写前状态里读不到（不是值为空，是字段不在快照里）⇒ 先复拉确认现状。'
                                     for field in absent]))
            continue
        baseline = item.get('baseline') or {}
        detail, conflicts, writes, done = [], [], [], []
        for field, wanted in target.items():
            present = current.get(field)
            held = baseline.get(field)
            if same_number(present, wanted):
                detail.append(f'{field}：已是目标值（{wanted}）⇒ 跳过不写。')
                done.append(field)
            elif held is None or same_number(present, held):
                detail.append(f'{field}：{present} -> {wanted}（与基线一致，只发这个字段）。')
                writes.append(field)
            else:
                detail.append(f'{field}：现值 {present} 既非基线 {held} 也非目标 {wanted} ⇒ 人工改过，隔离该行。')
                conflicts.append(field)
        if conflicts:
            results.append(_verdict(item, CONFLICT, detail, conflict_fields=conflicts))
        elif not writes:
            results.append(_verdict(item, SATISFIED, detail, satisfied_fields=done))
        else:
            results.append(_verdict(item, READY, detail, writable_fields=writes))
    return results


def _verdict(item, state, detail, writable_fields=(), satisfied_fields=(), conflict_fields=()):
    verdict = dict(item)
    verdict['gate'] = state
    verdict['gate_label'] = GATE_LABEL[state]
    verdict['gate_detail'] = detail
    verdict['writable_fields'] = sorted(writable_fields)
    verdict['satisfied_fields'] = sorted(satisfied_fields)
    verdict['conflict_fields'] = sorted(conflict_fields)
    return verdict


def gate_summary(verdicts):
    summary = {state: 0 for state in (READY, SATISFIED, CONFLICT, UNKNOWN, ADVISORY)}
    for verdict in verdicts:
        summary[verdict['gate']] += 1
    summary['total'] = len(verdicts)
    summary['needs_human'] = summary[CONFLICT] + summary[UNKNOWN]
    return summary


def writable_rows(verdicts):
    """Only ``ready`` rows may proceed, and only for their differing fields."""
    rows = []
    for verdict in verdicts:
        if verdict['gate'] != READY:
            continue
        rows.append({
            'object_type': verdict['object_type'],
            'object_key': verdict['object_key'],
            'patch': {field: verdict['target'][field] for field in verdict['writable_fields']},
            'code': verdict['code'],
            'level': verdict['level'],
        })
    return rows


# --------------------------------------------------------------------------
# write-back reconciliation
# --------------------------------------------------------------------------

def reconcile(verdicts, after_objects):
    """Compare the state read after writing against each declared target."""
    report = []
    for verdict in verdicts:
        if verdict['gate'] != READY:
            report.append({'object_key': verdict['object_key'], 'code': verdict['code'],
                           'checked': False, 'reason': f"闸门为 {verdict['gate_label']}，本轮未写入。"})
            continue
        current = (after_objects or {}).get(verdict['object_key'])
        if not isinstance(current, dict):
            report.append({'object_key': verdict['object_key'], 'code': verdict['code'],
                           'checked': False, 'reason': '写后回读里没有该对象。'})
            continue
        missed = [f'{field}：期望 {wanted}，实读 {current.get(field)}'
                  for field, wanted in verdict['target'].items()
                  if not same_number(current.get(field), wanted)]
        report.append({
            'object_key': verdict['object_key'],
            'code': verdict['code'],
            'checked': True,
            'effective': not missed,
            'detail': ('写后回读与目标一致。' if not missed
                       else '写后回读与目标不一致 ⇒ 视为未真正生效，不要按已执行推进下一档：' + '；'.join(missed)),
        })
    return report
