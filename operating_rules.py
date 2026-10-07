#!/usr/bin/env python3
"""Reference operating rules for a paid-media test loop. Pure functions, offline.

This module is the *decision* layer of a recurring test loop: turning a settled
observation window into metrics, deciding which declared rule fires, checking
the platform view against the settlement view, and asking the write gate to
confirm the current state before anything is written back.

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

Human-readable text (evidence, gate details, labels) is generated in English
(``lang='en'``, the default) or Chinese (``lang='zh-CN'``) from the same numbers.
Codes and gate states are language-neutral, so a decision never depends on the
language it is reported in.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import math

VERSION = '1.1'

MONEY = Decimal('0.01')
RATIO = Decimal('0.0001')
HUNDRED = Decimal('100')

LEVELS = ('P0', 'P1', 'P2')
LANGUAGES = ('en', 'zh-CN')

# Fields a proposal may ask the gate to change, per object type. Kept explicit
# so an unknown field is rejected instead of being written blindly: ``gate()``
# raises ``RuleError`` for any target field outside this table, which blocks the
# whole round rather than inventing a sixth gate state. Account-level findings
# are advisory only, so ``account`` allows no field at all.
WRITABLE_FIELDS = {
    'adset': ('daily_budget', 'status', 'bid_strategy', 'bid_amount'),
    'creative': ('status',),
    'account': (),
}

# Every code the engine can emit, and the one field it asks the gate to change
# (``None``: an advisory finding with nothing to write). A methodology must
# declare an action for each of these; an action it marks ``"implemented": true``
# must appear here, and one marked ``false`` must not.
ENGINE_CODES = {
    'LADDER_PROMOTE': 'daily_budget',
    'LADDER_HOLD': None,
    'TEST_STOP_NOCONV': 'status',
    'TEST_STOP_OVERCOST': 'status',
    'TEST_EARLY_STOP': 'status',
    'TEST_UNDERTESTED': None,
    'LINK_OR_TRACKING_BAD': 'status',
    'AD_STATUS': None,
    'CREATIVE_BREAKER': None,
    'CREATIVE_FATIGUE': None,
    'CREATIVE_OVERFLOW': None,
    'ACC_NO_DELIVERY': None,
    'ACC_STOPPED': None,
    'ACC_BALANCE_LOW': None,
}

# Settlement reconciliation outcomes, in precedence order: the first that
# applies is the account's status.
RECON_SCOPE, RECON_WINDOW, RECON_TZ, RECON_GAP, RECON_OK = (
    'RECON_SCOPE', 'RECON_WINDOW', 'RECON_TZ', 'RECON_GAP', 'RECON_OK')
RECON_CODES = (RECON_SCOPE, RECON_WINDOW, RECON_TZ, RECON_GAP, RECON_OK)

DRIVER_KEYS = ('cpm', 'ctr', 'cvr')


class RuleError(ValueError):
    """Input did not satisfy the declared observation contract."""


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------

TEXT = {
    'en': {
        # creative findings
        'creative_count': '{count} creatives in the ad set, above the cap of {cap} ⇒ trim before scaling.',
        'circuit_breaker': ('Creative {key} took {share_pct} of ad-set spend at CPA {cpa} > {multiple}× T '
                            '({line}) ⇒ switch off this creative; leave the ad set running.'),
        'fatigue': ('Creative {key} meets all three: frequency {frequency} >= {min_frequency}, CTR down '
                    '{ctr_drop_pct}, CVR down {cvr_drop_pct} ⇒ fatigued; add a new creative.'),
        # structure findings
        'name_mismatch': ('Name says MAX but bid_strategy = {strategy} ({bid}) ⇒ the name does not match '
                          'the setup; read structure from bid_strategy, not from the name.'),
        'no_bid': 'no bid',
        'effective_status': ('configured_status=ACTIVE but effective_status=DISAPPROVED ⇒ judge whether '
                             'it can deliver by effective_status.'),
        'capability_gap': ('spend_cap reads back null ⇒ the headroom alert cannot be computed; reported '
                           'as a gap, never inferred from the balance.'),
        # account findings
        'acc_no_adsets': 'No ad set returned for this account.',
        'acc_none_configured': 'No ad set has configured_status ACTIVE.',
        'acc_no_delivery': ('{configured} ad set(s) configured ACTIVE ({effective} able to deliver), '
                            "but today's spend is 0."),
        'acc_balance_low': 'Balance {balance} <= alert line {low}.',
        # ad-set findings
        'hold': ('Promotion blocked by {blockers} ⇒ resolve the creative, structure or account issue '
                 'first; budget unchanged this round; one change per ad set per round.'),
        'list_sep': ', ',
        'ad_status': 'effective_status=DISAPPROVED while configured_status is still ACTIVE.',
        'link_bad': 'The declared destination or tracking check failed.',
        'blocked': 'Missing spend / impressions / results; cannot classify.',
        'q_noconv': 'Are the destination and conversion tracking working?',
        'noconv': ('Zero leads with {impressions} impressions >= sample floor {floor}, and spend '
                   '{spend} >= stop line {line}.'),
        'q_early': 'Does the hook need fixing first?',
        'early_cpc': 'CPC {cpc} > {limit}',
        'early_ctr': 'CTR {ctr} < {limit}',
        'early_sep': '; ',
        'early': ('Early-stop line crossed ({parts}), but {impressions} impressions < sample floor '
                  '{floor} ⇒ stop new spend; no verdict on the creative.'),
        'q_bid_or_budget': 'Is the bid failing to enter auctions, or is the budget capped?',
        'undertested_zero': ('Zero leads but {impressions} impressions < sample floor {floor} ⇒ sample '
                             'too small; record only.'),
        'q_overcost': 'Has conversion reporting matured?',
        'overcost': 'Spend − T × leads = {margin} >= stop line {line}.',
        'q_sample_time': 'How long until the current budget gathers enough sample?',
        'undertested_few': '{results} leads < minimum sample {min} ⇒ too few to judge the creative.',
        'undertested_util': ('Budget utilisation {utilisation} <= {under} ⇒ limited delivery; fix whether '
                             'it can spend before changing creatives.'),
        'q_promote': 'This step\'s CPA {cpa} <= T {t}; move up to {stage}?',
        'promote': 'Leads {results} >= {min}, full delivery day = {day}, CPA {cpa} <= T {t}.',
        'yes': 'yes', 'no': 'no',
        'not_fresh': 'CPA meets T but the step has not covered a full delivery day ⇒ no promotion this round.',
        'q_cpa_acceptable': "Is this step's CPA already unacceptable?",
        'undertested_cpa': ('CPA {cpa} > T {t} but below the stop line {line} ⇒ keep the budget; add no '
                            'more money.'),
        # settlement downgrade
        'downgrade': ('Measurement unreconciled ({status}): {detail} ⇒ advisory only; no budget or status '
                      'change on platform numbers until they reconcile with the settlement.'),
        # write gate
        'gate_advisory': 'The finding declares no field change (advisory only); nothing to gate.',
        'gate_downgraded': ('Measurement unreconciled ({status}): advisory only this round; nothing to '
                            'gate.'),
        'gate_no_record': 'The pre-write read has no record of {key} ⇒ re-read first; never write blind.',
        'gate_absent_field': ('{field}: not in the pre-write read (the field is missing, not empty) ⇒ '
                              're-read to confirm current state.'),
        'gate_satisfied': '{field}: already at target ({wanted}) ⇒ skip, nothing to write.',
        'gate_no_baseline': ('{field}: the baseline does not record this field, so current value '
                             '{present} cannot be checked against the plan ⇒ hold the change; recover '
                             "the plan's baseline, or regenerate and review the plan."),
        'gate_null_baseline': ('{field}: the baseline is explicitly null, so there is no usable baseline '
                               'for this change ⇒ hold the change; verify what the null means and the '
                               "plan's baseline, or regenerate and review the plan."),
        'gate_write': '{field}: {present} -> {wanted} (matches the baseline; only this field is sent).',
        'gate_conflict': ('{field}: current value {present} matches neither baseline {held} nor target '
                          '{wanted} ⇒ isolate the row, hold the change and check where the difference '
                          'came from.'),
        # after-snapshot comparison
        'recon_not_written': 'Gate is {label}; not written this round.',
        'recon_not_in_after': 'Object not in the after snapshot.',
        'recon_match': 'After snapshot matches the target.',
        'recon_miss_field': '{field}: expected {wanted}, read {current}',
        'recon_miss_sep': '; ',
        'recon_mismatch': ('After snapshot differs from the target ⇒ treat as not in effect; do not '
                           'move to the next step as if it ran: {details}'),
        # settlement reconciliation
        'settle_ok': 'Spend and settled leads are within tolerance.',
        'settle_scope_platform': ('In the snapshot but not in the settlement export: outside the '
                                  "settlement's scope; reported as missing, not as zero."),
        'settle_scope_settlement': ('In the settlement export but not returned by the platform pull: '
                                    'the platform side is missing, not zero; re-pull before reading '
                                    'totals.'),
        'settle_window': ('Settlement has this account for {settled} but the observation date is '
                          '{platform}; dates must match before comparing.'),
        'settle_tz': ('Account time zone {account_tz} differs from settlement time zone {settle_tz}; '
                      'the day buckets differ, so the gap cannot be read. Align time zones first.'),
        'settle_tz_undeclared': ('Time zone not declared (account {account_tz}, settlement {settle_tz}); '
                                 'the day buckets cannot be matched.'),
        'settle_platform_incomplete': ('Platform totals are incomplete (an ad set has no spend or '
                                       'leads); missing is not zero.'),
        'settle_settled_missing': 'Settlement row has no spend or leads.',
        'settle_price': 'Settlement unit price {settled} differs from the offer price {platform}.',
        'settle_spend': 'Spend differs by {delta} (tolerance ±{tolerance}%).',
        'settle_spend_from_zero': 'Settled spend {settled} where the platform shows 0.',
        'settle_results': ('Settlement approved {settled} of {platform} leads; expected {expected} at the '
                           'declared approval rate {rate} ({delta}, tolerance ±{tolerance}%).'),
        'settle_results_from_zero': 'Settled leads {settled} where the platform shows none.',
        'undeclared': 'not declared',
    },
    'zh-CN': {
        'creative_count': '组内素材 {count} 条，超过硬上界 {cap} 条 ⇒ 先裁剪再扩量。',
        'circuit_breaker': ('素材 {key} 吃掉组内 {share_ratio} 花费、CPA {cpa} > 目标 x{multiple}'
                            '（{line}）⇒ 熔断该素材，不动整组。'),
        'fatigue': ('素材 {key} 三条同时满足：频次 {frequency} >= {min_frequency}、CTR 降 {ctr_drop}、'
                    'CVR 降 {cvr_drop} ⇒ 判衰竭，换素材。'),
        'name_mismatch': ('组名写「MAX」但实际 bid_strategy = {strategy}（{bid}）⇒ 命名与实际不符，'
                          '读结构一律以详情接口的 bid_strategy 为准。'),
        'no_bid': '无 bid',
        'effective_status': ('configured_status=ACTIVE 但 effective_status=DISAPPROVED'
                             ' ⇒ 判「能不能投」必须看 effective_status。'),
        'capability_gap': 'spend_cap 读回为 null ⇒ 余量预警无法计算，如实标注，不得用 balance 反推。',
        'acc_no_adsets': '账户下没有任何广告组记录。',
        'acc_none_configured': '没有任何 configured_status 为 ACTIVE 的广告组。',
        'acc_no_delivery': 'configured_status 为 ACTIVE 的组有 {configured} 个（其中 effective 可投 {effective} 个），但今日消耗为 0。',
        'acc_balance_low': '余额 {balance} <= 警示线 {low}。',
        'hold': '晋级被阻断：{blockers} ⇒ 先处理素材/结构/账户问题，本轮预算不变；每个广告组每轮只做一项变更。',
        'list_sep': '、',
        'ad_status': 'effective_status=DISAPPROVED，configured_status 仍为 ACTIVE。',
        'link_bad': '声明的链接有效性或回传完整性未通过。',
        'blocked': '缺少 spend / impressions / results，无法判定。',
        'q_noconv': '链路与回传是否正常？',
        'noconv': '零转化且展示 {impressions} >= 判死门槛 {floor}，累计花费 {spend} >= 止损线 {line}。',
        'q_early': '钩子是否需要先修？',
        'early_cpc': 'CPC {cpc} > {limit}',
        'early_ctr': 'CTR {ctr} < {limit}',
        'early_sep': '；',
        'early': '早停触线（{parts}），但展示 {impressions} < 判死门槛 {floor} ⇒ 停新增花费、不下「素材无效」结论。',
        'q_bid_or_budget': '是出价进不了场，还是预算撞顶？',
        'undertested_zero': '零转化但展示 {impressions} < 判死门槛 {floor} ⇒ 样本不足，只记录。',
        'q_overcost': '回传是否已成熟？',
        'overcost': '累计花费 − T x 转化数 = {margin} >= 止损线 {line}。',
        'q_sample_time': '现有预算下还要多久才能攒够样本？',
        'undertested_few': '转化 {results} < 最低可判样本 {min} ⇒ 样本不足，不判素材好坏。',
        'undertested_util': '预算利用率 {utilisation} <= {under} ⇒ 花不动，先解决能不能花的问题，而不是换素材。',
        'q_promote': '本档 CPA {cpa} <= T {t}，是否升到 {stage}？',
        'promote': '转化 {results} >= {min}、覆盖完整投放日 = {day}、CPA {cpa} <= T {t}。',
        'yes': '是', 'no': '否',
        'not_fresh': 'CPA 达标但该档未覆盖完整投放日 ⇒ 本轮不晋级。',
        'q_cpa_acceptable': '这一档的 CPA 是否已到不可接受？',
        'undertested_cpa': 'CPA {cpa} > T {t}，但未达止损线 {line} ⇒ 保持预算、不继续加钱。',
        'downgrade': '口径未对齐（{status}）：{detail} ⇒ 仅建议；平台数与结算数对齐之前，不按平台数改预算或状态。',
        'gate_advisory': '该发现不涉及写入字段（仅建议），不过闸门。',
        'gate_downgraded': '口径未对齐（{status}）：本轮仅建议，不过闸门。',
        'gate_no_record': '写前状态里没有 {key} 的记录 ⇒ 先复拉，不要盲写。',
        'gate_absent_field': '{field}：写前状态里读不到（不是值为空，是字段不在快照里）⇒ 先复拉确认现状。',
        'gate_satisfied': '{field}：已是目标值（{wanted}）⇒ 跳过不写。',
        'gate_no_baseline': ('{field}：基线未记录该字段，无法核对当前值 {present} 与原方案是否一致 '
                             '⇒ 暂缓修改，补充原方案基线证据；必要时重新生成并审阅计划。'),
        'gate_null_baseline': ('{field}：基线明确为 null，尚无可用于本次修改的基线值 '
                               '⇒ 暂缓修改，核实空值含义与原方案基线；必要时重新生成并审阅计划。'),
        'gate_write': '{field}：{present} -> {wanted}（与基线一致，只发这个字段）。',
        'gate_conflict': '{field}：当前值 {present} 与基线 {held}、目标 {wanted} 均不一致 ⇒ 隔离该行，暂缓修改并核对变更来源。',
        'recon_not_written': '闸门为 {label}，本轮未写入。',
        'recon_not_in_after': '写后回读里没有该对象。',
        'recon_match': '写后回读与目标一致。',
        'recon_miss_field': '{field}：期望 {wanted}，实读 {current}',
        'recon_miss_sep': '；',
        'recon_mismatch': '写后回读与目标不一致 ⇒ 视为未真正生效，不要按已执行推进下一档：{details}',
        'settle_ok': '花费与结算线索数均在容差内。',
        'settle_scope_platform': '快照里有、结算导出里没有：不在结算范围内；按缺失报告，不补零。',
        'settle_scope_settlement': '结算导出里有、平台拉取没有返回：平台侧是缺失，不是零；先复拉再看合计。',
        'settle_window': '结算里该账户的日期是 {settled}，观察日是 {platform}；日期一致后才能比较。',
        'settle_tz': '账户时区 {account_tz} 与结算时区 {settle_tz} 不同，自然日切分不一致，差额无法解读；先对齐时区。',
        'settle_tz_undeclared': '时区未声明（账户 {account_tz}，结算 {settle_tz}），无法对齐自然日。',
        'settle_platform_incomplete': '平台合计不完整（有广告组缺少花费或线索数）；缺失不等于零。',
        'settle_settled_missing': '结算行缺少花费或线索数。',
        'settle_price': '结算单价 {settled} 与 offer 单价 {platform} 不一致。',
        'settle_spend': '花费差 {delta}（容差 ±{tolerance}%）。',
        'settle_spend_from_zero': '平台花费为 0，结算花费却是 {settled}。',
        'settle_results': '结算认可 {settled}/{platform} 条线索；按声明通过率 {rate} 应为 {expected}（{delta}，容差 ±{tolerance}%）。',
        'settle_results_from_zero': '平台没有线索，结算却有 {settled} 条。',
        'undeclared': '未声明',
    },
}

GATE_LABELS = {
    'en': {'ready': 'Ready for review', 'satisfied': 'Satisfied', 'conflict': 'Conflict (isolated)',
           'unknown': 'Unknown', 'advisory': 'Advisory'},
    'zh-CN': {'ready': '可执行', 'satisfied': '已满足', 'conflict': '冲突隔离',
              'unknown': '未知', 'advisory': '仅建议'},
}


def check_lang(lang):
    if lang not in LANGUAGES:
        raise RuleError(f'lang must be one of {list(LANGUAGES)}, got {lang!r}.')
    return lang


def say(lang, message, /, **values):
    """Render one message in ``lang`` from named values."""
    return TEXT[check_lang(lang)][message].format(**values)


# --------------------------------------------------------------------------
# numeric helpers
# --------------------------------------------------------------------------

def dec(value, label):
    """Parse a declared number. ``None`` stays ``None``; other empties are invalid."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise RuleError(f'{label} must be a number or numeric string, got {type(value).__name__}.')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise RuleError(f'{label} is not a valid decimal: {value!r}') from exc
    if not result.is_finite():
        raise RuleError(f'{label} cannot be NaN or infinite.')
    return result


def integer(value, label):
    parsed = dec(value, label)
    if parsed is None:
        return None
    if parsed != parsed.to_integral_value():
        raise RuleError(f'{label} must be an integer: {parsed}')
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


def pct(value, digits='0.1'):
    """Render a ratio (0.619) as a percentage (``61.9%``)."""
    if value is None:
        return None
    return num(value * HUNDRED, digits) + '%'


def signed_pct(value, digits='0.1'):
    """Render a percentage change with its sign (``+0.5%``, ``-52.4%``)."""
    if value is None:
        return None
    text = num(value, digits)
    return ('+' + text if not text.startswith('-') else text) + '%'


def same_number(left, right):
    """Equality used by the write gate: ``10``, ``10.0`` and ``'10.00'`` match.

    Numbers are compared as ``Decimal`` (exact, no float tolerance); other values
    such as ``'PAUSED'`` must match as text. A boolean is never a number here:
    ``True`` does not equal ``1`` and ``False`` does not equal ``0``.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    if left is None or right is None:
        return left is right
    if str(left) == str(right):
        return True
    if not isinstance(left, (str, int, float, Decimal)) or not isinstance(right, (str, int, float, Decimal)):
        return False
    try:
        a, b = Decimal(str(left)), Decimal(str(right))
        return a.is_finite() and b.is_finite() and a == b
    except (InvalidOperation, ValueError):
        return False


# --------------------------------------------------------------------------
# methodology
# --------------------------------------------------------------------------

REQUIRED_METHODOLOGY_KEYS = (
    'methodology_id', 'version', 'target_roas', 'ladder', 'sample_gate',
    'promotion', 'stop_loss', 'utilisation', 'creative_rules', 'actions',
    'balance_alert_below', 'max_creatives_per_adset',
)
REQUIRED_ACTION_KEYS = ('code', 'level', 'action', 'window', 'acceptance', 'stop_condition')
ACTION_TEXT_KEYS = ('action', 'window', 'acceptance', 'stop_condition')


def required(methodology, key):
    """Read a threshold that must come from the methodology. No code default."""
    if not isinstance(methodology, dict) or methodology.get(key) is None:
        raise RuleError(f'Methodology is missing required threshold {key}; thresholds come only from '
                        'the methodology document, never from a code default.')
    return methodology[key]


def validate_methodology(document):
    if not isinstance(document, dict):
        raise RuleError('Methodology document must be a JSON object.')
    missing = [key for key in REQUIRED_METHODOLOGY_KEYS if document.get(key) is None]
    if missing:
        raise RuleError('Methodology document is missing required fields: ' + ', '.join(missing))
    if dec(document['target_roas'], 'target_roas') <= 0:
        raise RuleError('target_roas must be positive.')
    if 'quality_factor' in document:
        quality = dec(document['quality_factor'], 'quality_factor')
        if quality is None or quality <= 0 or quality > 1:
            raise RuleError('quality_factor (lead approval rate) must be in (0, 1].')
    if dec(document['balance_alert_below'], 'balance_alert_below') < 0:
        raise RuleError('balance_alert_below cannot be negative.')
    if integer(document['max_creatives_per_adset'], 'max_creatives_per_adset') < 1:
        raise RuleError('max_creatives_per_adset must be a positive integer.')
    if not isinstance(document['ladder'], list) or not document['ladder']:
        raise RuleError('ladder must be a non-empty array.')
    actions = document.get('actions')
    if not isinstance(actions, list) or not actions:
        raise RuleError('actions must be a non-empty array.')
    seen = set()
    for action in actions:
        if not isinstance(action, dict):
            raise RuleError('Every action must be a JSON object.')
        for key in REQUIRED_ACTION_KEYS:
            if not action.get(key):
                raise RuleError(f'Action {action.get("code", "?")} is missing {key}.')
        code = action['code']
        if action['level'] not in LEVELS:
            raise RuleError(f'Action {code} level must be one of {LEVELS}.')
        if code in seen:
            raise RuleError(f'Duplicate action code: {code}')
        seen.add(code)
        english = action.get('en')
        if english is not None:
            if not isinstance(english, dict):
                raise RuleError(f'Action {code}: en must be an object.')
            absent = [key for key in ACTION_TEXT_KEYS if not english.get(key)]
            if absent:
                raise RuleError(f'Action {code}: en is missing ' + ', '.join(absent))
        implemented = action.get('implemented')
        if implemented is True and code not in ENGINE_CODES:
            raise RuleError(f'Action {code} is marked implemented but the engine never emits it.')
        if implemented is False and code in ENGINE_CODES:
            raise RuleError(f'Action {code} is marked not implemented but the engine emits it.')
    absent = sorted(code for code in ENGINE_CODES if code not in seen)
    if absent:
        raise RuleError('Methodology declares no action for engine codes: ' + ', '.join(absent))
    for key in ('measured_in_t',):
        if key not in document['stop_loss']:
            raise RuleError(f'stop_loss is missing {key}.')
    if document.get('reconciliation') is not None:
        reconciliation_policy(document)
    return document


def load_methodology(path):
    with open(path, encoding='utf-8') as handle:
        document = json.load(handle)
    return validate_methodology(document)


def actions_by_code(methodology):
    return {action['code']: action for action in methodology['actions']}


def action_text(action, lang='en'):
    """The four reviewer-facing texts of one action, in ``lang`` when declared.

    The base fields hold the methodology author's own language; an optional
    ``en`` object holds the English version. Without it, the base text is used.
    """
    check_lang(lang)
    source = action.get('en') if lang == 'en' and isinstance(action.get('en'), dict) else action
    return {key: source[key] for key in ACTION_TEXT_KEYS}


def target_cost(unit_price, methodology):
    """T — the acceptable cost per result.

    ``T = unit price x quality factor / target ROAS``. The unit price is the
    value of one lead, the quality factor is the share of leads the buyer
    approves, and the target ROAS is the return required on spend. A 10.00 lead
    with a 0.90 approval rate against a 1.25 target gives ``T = 7.20``, safely
    below the value of the lead; the ladder then multiplies T by 2 and 3.
    An omitted quality factor means no deduction (1).
    """
    price = dec(unit_price, 'unit_price')
    if price is None or price <= 0:
        raise RuleError('unit_price must be positive.')
    quality = quality_factor(methodology)
    roas = dec(methodology.get('target_roas'), 'target_roas')
    if roas is None or roas <= 0:
        raise RuleError('target_roas must be positive.')
    return price * quality / roas


def quality_factor(methodology):
    quality = dec(methodology.get('quality_factor', '1'), 'quality_factor')
    if quality is None or quality <= 0 or quality > 1:
        raise RuleError('quality_factor (lead approval rate) must be in (0, 1].')
    return quality


def ladder_multiplier(stage, methodology):
    ladder = methodology['ladder']
    if stage in ladder:
        return Decimal(ladder.index(stage) + 1)
    raise RuleError(f'Unknown ladder stage {stage!r}; declared: {ladder}')


def next_stage(stage, methodology):
    ladder = methodology['ladder']
    if stage not in ladder:
        raise RuleError(f'Unknown ladder stage {stage!r}; declared: {ladder}')
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
        '_cpm': cpm, '_utilisation': utilisation, '_overcost_margin': overcost_margin,
        '_frequency': frequency, '_daily_budget': budget, '_T': t,
    }


def expected_results_v(spend, t):
    return ratio(spend, t)


def raw(values, key):
    """Read a raw Decimal back out of an ``adset_metrics`` result."""
    return values.get('_' + key)


# --------------------------------------------------------------------------
# why CPA moved
# --------------------------------------------------------------------------

def cpa_driver_decomposition(reference, observed):
    """Split a CPA change into CPM, CTR and CVR contributions.

    ``CPA = CPM / (1000 x CTR x CVR)``, so after taking logs the changes add up:
    ``log(CPA/CPA_ref) = dlog(CPM) - dlog(CTR) - dlog(CVR)``.

    Each term is that metric's signed contribution to the change in log CPA
    (negative pushed CPA down), returned with its share of the absolute total.
    That answers "which stage of the funnel moved the cost" instead of "which
    number looks biggest". It is an accounting identity, not a causal claim.
    ``residual`` is the part of the observed CPA change the three terms do not
    explain: zero when the inputs are internally consistent, small when a quoted
    CPA was rounded, large when the windows or definitions differ.

    A comparison with a missing or non-positive metric is returned as
    incomplete, naming what is missing, so it stays visibly incomplete.
    """
    keys = DRIVER_KEYS + ('cpa',)
    missing = []
    for side, values in (('reference', reference), ('observed', observed)):
        for key in keys:
            value = (values or {}).get(key)
            if value is None or isinstance(value, bool) or float(value) <= 0:
                missing.append(f'{side}.{key}')
    if missing:
        return {'complete': False, 'terms': None, 'shares': None, 'driver': None,
                'missing': missing,
                'reason': 'Missing or non-positive ' + ', '.join(missing) + '; not decomposed.'}

    def log_ratio(key):
        return math.log(float(observed[key]) / float(reference[key]))

    terms = {'cpm': log_ratio('cpm'), 'ctr': -log_ratio('ctr'), 'cvr': -log_ratio('cvr')}
    observed_total = log_ratio('cpa')
    magnitude = sum(abs(value) for value in terms.values())
    shares = ({key: abs(value) / magnitude for key, value in terms.items()}
              if magnitude else {key: 0.0 for key in terms})
    driver = max(DRIVER_KEYS, key=lambda key: shares[key]) if magnitude else None
    return {
        'complete': True,
        'terms': {key: round(value, 4) for key, value in terms.items()},
        'shares': {key: round(value, 4) for key, value in shares.items()},
        'observed_total': round(observed_total, 4),
        'residual': round(observed_total - sum(terms.values()), 6),
        'driver': driver,
        'missing': [],
    }


# Kept so existing callers keep working; the name described the maths poorly.
attribution = cpa_driver_decomposition


def cpa_drivers(account, methodology):
    """Decompose the CPA change of every ad set that declares a prior window."""
    unit_price = (account.get('offer') or {}).get('unit_price')
    entries = []
    for adset in account.get('adsets') or []:
        prior = adset.get('prior_window')
        if prior is None:
            continue
        if not isinstance(prior, dict):
            raise RuleError(f"{adset.get('adset_key')}: prior_window must be an object.")
        values = adset_metrics(adset, unit_price, methodology)
        current = {key: raw(values, key) for key in DRIVER_KEYS + ('cpa',)}
        reference = {key: dec(prior.get(key), f'prior_window.{key}') for key in DRIVER_KEYS + ('cpa',)}
        result = cpa_driver_decomposition(reference, current)
        entries.append({
            'account_key': account.get('account_key'),
            'adset_key': adset.get('adset_key'),
            'prior_date': prior.get('date'),
            'prior': {key: num(value) for key, value in reference.items()},
            'current': {key: num(value) for key, value in current.items()},
            'prior_cpa': num2(reference['cpa']),
            'current_cpa': num2(current['cpa']),
            **result,
        })
    return entries


# --------------------------------------------------------------------------
# creative level checks
# --------------------------------------------------------------------------

def creative_findings(adset, values, methodology, lang='en'):
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

    cap = integer(required(methodology, 'max_creatives_per_adset'), 'max_creatives_per_adset')
    if len(creatives) > cap:
        findings.append({
            'kind': 'creative_count',
            'detail': say(lang, 'creative_count', count=len(creatives), cap=cap),
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
                    'detail': say(lang, 'circuit_breaker', key=creative.get('creative_key'),
                                  share_ratio=num(share, '0.001'), share_pct=pct(share),
                                  cpa=num2(creative_cpa), multiple=num(cpa_multiple, '0.1'),
                                  line=num2(values['_T'] * cpa_multiple)),
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
                'detail': say(lang, 'fatigue', key=creative.get('creative_key'),
                              frequency=num(frequency, '0.01'), min_frequency=num(min_frequency, '0.1'),
                              ctr_drop=num(ctr_drop, '0.001'), cvr_drop=num(cvr_drop, '0.001'),
                              ctr_drop_pct=pct(ctr_drop), cvr_drop_pct=pct(cvr_drop)),
                'frequency': num(frequency, '0.01'),
                'ctr_drop': num(ctr_drop, '0.0001'),
                'cvr_drop': num(cvr_drop, '0.0001'),
            })
    return findings


def name_mismatch(adset):
    """The ad set name promises MAX (no cap) but the bid strategy says otherwise."""
    name = adset.get('name') or ''
    strategy = adset.get('bid_strategy')
    return 'MAX' in name.upper() and bool(strategy) and strategy != 'LOWEST_COST_WITHOUT_CAP'


def structure_findings(account, methodology, lang='en'):
    """Declared-versus-actual structure problems that need no metric to detect.

    Ad-set checks run for every ad set; the account-level capability gap is
    reported once per account, so it can never hide a later ad set's warning.
    """
    findings = []
    for adset in account.get('adsets') or []:
        strategy = adset.get('bid_strategy')
        if name_mismatch(adset):
            findings.append({
                'kind': 'name_mismatch',
                'object_key': adset.get('adset_key'),
                'detail': say(lang, 'name_mismatch', strategy=strategy,
                              bid=adset.get('bid_amount') or say(lang, 'no_bid')),
            })
        if adset.get('configured_status') == 'ACTIVE' and adset.get('effective_status') == 'DISAPPROVED':
            findings.append({
                'kind': 'effective_status',
                'object_key': adset.get('adset_key'),
                'detail': say(lang, 'effective_status'),
            })
    if account.get('spend_cap') is None:
        findings.append({
            'kind': 'capability_gap',
            'object_key': account.get('account_key'),
            'detail': say(lang, 'capability_gap'),
        })
    return findings


# --------------------------------------------------------------------------
# decisions
# --------------------------------------------------------------------------

def proposal(account, adset, code, methodology, *, object_type='adset', object_key=None,
             parent_key=None, baseline=None, target=None, question=None, evidence=None, lang='en'):
    """Build one proposal in the shape the write gate expects.

    ``object_type`` is ``account``, ``adset`` or ``creative`` and decides which
    fields the gate will accept (``WRITABLE_FIELDS``). ``object_key`` is what the
    proposal acts on; ``parent_key`` is the ad set it belongs to. They differ for
    creative-level findings, and the report needs the parent so a creative
    finding is not silently detached from its ad set.
    """
    if object_type not in WRITABLE_FIELDS:
        raise RuleError(f'Unknown object_type {object_type!r}; declared: {sorted(WRITABLE_FIELDS)}')
    actions = actions_by_code(methodology)
    if code not in actions:
        raise RuleError(f'The methodology action catalogue has no {code}.')
    action = actions[code]
    adset_key = adset.get('adset_key') if adset else None
    proposal = {
        'code': code,
        'level': action['level'],
        'account_key': account.get('account_key'),
        'offer_key': (account.get('offer') or {}).get('offer_key'),
        'object_type': object_type,
        'object_key': object_key if object_key is not None else adset_key,
        'parent_key': parent_key if parent_key is not None else adset_key,
        'object_name': adset.get('name', '') if adset else '',
        **action_text(action, lang),
        'evidence': evidence or [],
    }
    if question:
        proposal['question'] = question
    # Only attach a write intent when the rule actually wants a field changed.
    # A proposal without baseline/target is a *finding*, and the gate reports it
    # as advisory rather than silently passing it.
    if target is not None:
        proposal['baseline'] = baseline or {}
        proposal['target'] = target
    return proposal


def decide_account(account, methodology, lang='en'):
    """Produce every proposal for one account from a settled snapshot."""
    check_lang(lang)
    offer = account.get('offer') or {}
    unit_price = offer.get('unit_price')
    proposals, diagnostics = [], []
    adsets = account.get('adsets') or []

    account_key = account.get('account_key')
    if not adsets:
        proposals.append(proposal(account, None, 'ACC_STOPPED', methodology,
                                  object_type='account', object_key=account_key,
                                  evidence=[say(lang, 'acc_no_adsets')], lang=lang))
        return proposals, diagnostics

    # ACC_STOPPED is about "nothing is even configured to run". An ad set that is
    # configured ACTIVE but not effective is a *delivery blocker*, not a stopped
    # account — reporting both would misattribute a creative problem to the
    # account and hide which action actually fixes it.
    configured_live = [a for a in adsets if a.get('configured_status') == 'ACTIVE']
    effective_live = [a for a in configured_live if a.get('effective_status') == 'ACTIVE']
    if not configured_live:
        proposals.append(proposal(account, None, 'ACC_STOPPED', methodology,
                                  object_type='account', object_key=account_key,
                                  evidence=[say(lang, 'acc_none_configured')], lang=lang))
    elif account.get('today_spend') is not None and dec(account.get('today_spend'), 'today_spend') == 0:
        proposals.append(proposal(account, None, 'ACC_NO_DELIVERY', methodology,
                                  object_type='account', object_key=account_key,
                                  evidence=[say(lang, 'acc_no_delivery', configured=len(configured_live),
                                                effective=len(effective_live))], lang=lang))
    balance = dec(account.get('balance'), 'balance')
    low = dec(required(methodology, 'balance_alert_below'), 'balance_alert_below')
    if balance is not None and balance <= low:
        proposals.append(proposal(account, None, 'ACC_BALANCE_LOW', methodology,
                                  object_type='account', object_key=account_key,
                                  evidence=[say(lang, 'acc_balance_low', balance=num2(balance),
                                                low=num2(low))], lang=lang))
    # Any P0 account finding outranks scaling: no ad set in this account is
    # promoted until the account itself can deliver.
    account_blockers = [item['code'] for item in proposals
                        if item['object_type'] == 'account' and item['level'] == 'P0']

    promotion = methodology['promotion']
    min_results = integer(promotion['min_results'], 'min_results')
    require_full_day = bool(promotion['require_full_day'])
    day_complete = bool((account.get('observation') or {}).get('complete_delivery_day'))

    for adset in adsets:
        values = adset_metrics(adset, unit_price, methodology)
        diagnostics.append({'account_key': account_key, **{
            key: value for key, value in values.items() if not key.startswith('_')}})

        creatives = creative_findings(adset, values, methodology, lang)
        for finding in creatives:
            if finding['kind'] in ('circuit_breaker', 'fatigue'):
                code = 'CREATIVE_BREAKER' if finding['kind'] == 'circuit_breaker' else 'CREATIVE_FATIGUE'
                proposals.append(proposal(account, adset, code, methodology,
                                          object_type='creative',
                                          object_key=finding.get('creative_key'),
                                          parent_key=adset.get('adset_key'),
                                          evidence=[finding['detail']], lang=lang))
            else:
                proposals.append(proposal(account, adset, 'CREATIVE_OVERFLOW', methodology,
                                          evidence=[finding['detail']], lang=lang))

        if adset.get('configured_status') == 'ACTIVE' and adset.get('effective_status') == 'DISAPPROVED':
            proposals.append(proposal(account, adset, 'AD_STATUS', methodology,
                                      evidence=[say(lang, 'ad_status')], lang=lang))
            continue

        if adset.get('linked') is False or adset.get('tracking_ok') is False:
            proposals.append(proposal(account, adset, 'LINK_OR_TRACKING_BAD', methodology,
                                      evidence=[say(lang, 'link_bad')],
                                      target={'status': 'PAUSED'},
                                      baseline=({'status': adset['configured_status']}
                                                if 'configured_status' in adset else {}), lang=lang))
            continue

        # A metric we could not read is missing evidence, not a passing result.
        if values['_spend'] is None or values['_results'] is None or values['_impressions'] is None:
            diagnostics[-1]['blocked'] = say(lang, 'blocked')
            continue

        code, question, evidence = _classify_adset(
            adset, values, methodology, min_results, require_full_day, day_complete, lang)
        if code is None:
            continue
        if code == 'LADDER_PROMOTE':
            blockers = promotion_blockers(adset, creatives, account_blockers)
            if blockers:
                # Rule precedence: one change per ad set per round, and a
                # creative or account problem is fixed before money is added.
                code, question = 'LADDER_HOLD', None
                evidence = evidence + [say(lang, 'hold', blockers=say(lang, 'list_sep').join(blockers))]
        target, baseline = _write_intent(code, adset, values, methodology)
        proposals.append(proposal(account, adset, code, methodology, question=question,
                                  evidence=evidence, target=target, baseline=baseline, lang=lang))
    return proposals, diagnostics


def promotion_blockers(adset, creative_items, account_blockers):
    """Why a promotion that met its numbers must wait, in a stable order.

    A promotion is replaced by advisory ``LADDER_HOLD`` when the same ad set has
    a creative circuit breaker, too many creatives, or a name that contradicts
    its bid strategy, or when the account has any P0 account-level finding.
    """
    kinds = {item['kind'] for item in creative_items}
    blockers = []
    if 'circuit_breaker' in kinds:
        blockers.append('CREATIVE_BREAKER')
    if 'creative_count' in kinds:
        blockers.append('CREATIVE_OVERFLOW')
    if name_mismatch(adset):
        blockers.append('name_mismatch')
    blockers.extend(account_blockers)
    return blockers


def _classify_adset(adset, values, methodology, min_results, require_full_day, day_complete, lang='en'):
    """Return ``(code, question, evidence)`` for one ad set, or ``(None, ...)``."""
    results = values['_results']
    spend = values['_spend']
    impressions = values['_impressions']
    sample = methodology['sample_gate']
    dead_impressions = integer(sample['impressions_for_dead'], 'impressions_for_dead')
    early_cpc = dec(sample.get('early_stop_cpc_above'), 'early_stop_cpc_above')
    early_ctr = dec(sample.get('early_stop_ctr_below'), 'early_stop_ctr_below')
    stop_line = values['_T'] * dec(methodology['stop_loss']['measured_in_t'], 'stop_loss.measured_in_t')
    line = num2(money(stop_line))

    if results == 0:
        enough_sample = impressions >= dead_impressions
        if values['_overcost_margin'] is not None and \
                values['_overcost_margin'] >= stop_line and enough_sample:
            return ('TEST_STOP_NOCONV', say(lang, 'q_noconv'),
                    [say(lang, 'noconv', impressions=impressions, floor=dead_impressions,
                         spend=num2(spend), line=line)])
        early = []
        if early_cpc is not None and values['_cpc'] is not None and values['_cpc'] > early_cpc:
            early.append(say(lang, 'early_cpc', cpc=num2(values['_cpc']), limit=num2(early_cpc)))
        if early_ctr is not None and values['_ctr'] is not None and values['_ctr'] < early_ctr:
            early.append(say(lang, 'early_ctr', ctr=num(values['_ctr'], '0.0001'),
                             limit=num(early_ctr, '0.0001')))
        if early:
            return ('TEST_EARLY_STOP', say(lang, 'q_early'),
                    [say(lang, 'early', parts=say(lang, 'early_sep').join(early),
                         impressions=impressions, floor=dead_impressions)])
        return ('TEST_UNDERTESTED', say(lang, 'q_bid_or_budget'),
                [say(lang, 'undertested_zero', impressions=impressions, floor=dead_impressions)])
    if values['_overcost_margin'] is not None and values['_overcost_margin'] >= stop_line:
        return ('TEST_STOP_OVERCOST', say(lang, 'q_overcost'),
                [say(lang, 'overcost', margin=num2(values['_overcost_margin']), line=line)])

    if results < min_results:
        return ('TEST_UNDERTESTED', say(lang, 'q_sample_time'),
                [say(lang, 'undertested_few', results=results, min=min_results)])

    stage = adset.get('ladder_stage')
    target_stage = next_stage(stage, methodology)
    utilisation = values['_utilisation']
    under = dec(methodology['utilisation']['under_delivering_below'], 'under_delivering_below')
    if utilisation is not None and under is not None and utilisation <= under:
        return ('TEST_UNDERTESTED', say(lang, 'q_bid_or_budget'),
                [say(lang, 'undertested_util', utilisation=num(utilisation, '0.001'),
                     under=num(under, '0.01'))])

    cpa_ok = values['_cpa'] is not None and values['_cpa'] <= values['_T']
    fresh = (not require_full_day) or day_complete
    cpa, t = num2(values['_cpa']), num2(values['_T'])
    if cpa_ok and fresh and target_stage:
        return ('LADDER_PROMOTE', say(lang, 'q_promote', cpa=cpa, t=t, stage=target_stage),
                [say(lang, 'promote', results=results, min=min_results,
                     day=say(lang, 'yes' if day_complete else 'no'), cpa=cpa, t=t)])
    if cpa_ok and not fresh:
        return (None, None, [say(lang, 'not_fresh')])
    if not cpa_ok:
        return ('TEST_UNDERTESTED', say(lang, 'q_cpa_acceptable'),
                [say(lang, 'undertested_cpa', cpa=cpa, t=t, line=line)])
    return (None, None, [])


def _write_intent(code, adset, values, methodology):
    """Translate a rule into the field change the gate must verify."""
    budget = values['_daily_budget']
    if code == 'LADDER_PROMOTE' and budget is not None:
        multiple = dec(methodology['promotion']['budget_multiple'], 'promotion.budget_multiple')
        new_budget = money(budget * multiple)
        return ({'daily_budget': num2(new_budget)},
                {'daily_budget': num2(budget)})
    if code in ('TEST_STOP_NOCONV', 'TEST_STOP_OVERCOST', 'TEST_EARLY_STOP'):
        return ({'status': 'PAUSED'},
                {'status': adset['configured_status']} if 'configured_status' in adset else {})
    return (None, None)


# --------------------------------------------------------------------------
# platform vs settlement
# --------------------------------------------------------------------------

def reconciliation_policy(methodology):
    """Read the tolerances and downgrade rules. No code default for any of them."""
    block = required(methodology, 'reconciliation')
    if not isinstance(block, dict):
        raise RuleError('reconciliation must be an object.')
    policy = {}
    for key in ('spend_tolerance_pct', 'results_tolerance_pct'):
        value = dec(block.get(key), f'reconciliation.{key}')
        if value is None or value < 0:
            raise RuleError(f'reconciliation.{key} is required and cannot be negative.')
        policy[key] = value
    downgrade_on = block.get('downgrade_on')
    if not isinstance(downgrade_on, list) or any(code not in RECON_CODES or code == RECON_OK
                                                 for code in downgrade_on):
        raise RuleError('reconciliation.downgrade_on must list codes from '
                        + ', '.join(code for code in RECON_CODES if code != RECON_OK) + '.')
    downgrade_codes = block.get('downgrade_codes')
    if not isinstance(downgrade_codes, list) or any(ENGINE_CODES.get(code) is None
                                                    for code in downgrade_codes):
        raise RuleError('reconciliation.downgrade_codes must list engine codes that carry a write intent.')
    policy['downgrade_on'] = tuple(downgrade_on)
    policy['downgrade_codes'] = tuple(downgrade_codes)
    return policy


def _platform_totals(account):
    """Sum the ad-set rows. No rows, or any row without spend or leads, is ``None``."""
    adsets = account.get('adsets') or []
    if not adsets:
        return None, None
    spends = [dec(adset.get('spend'), 'spend') for adset in adsets]
    results = [integer(adset.get('results'), 'results') for adset in adsets]
    spend = None if any(value is None for value in spends) else sum(spends, Decimal('0'))
    leads = None if any(value is None for value in results) else sum(results)
    return spend, leads


def reconcile_settlement(snapshot, settlement, methodology, lang='en'):
    """Check the platform view of each account against the settlement view.

    Rows are joined on account and date. Each account gets the first status
    that applies, in this order:

    ``RECON_SCOPE``   the account is on one side only. The missing side stays
                      missing; it is never zero-filled.
    ``RECON_WINDOW``  the settlement has the account, but not for the
                      observation date.
    ``RECON_TZ``      account and settlement time zones differ (or one is not
                      declared), so the day buckets cannot be matched.
    ``RECON_GAP``     spend, or settled leads against platform leads x the
                      declared approval rate, is outside tolerance; or the unit
                      price differs; or a side's totals are incomplete.
    ``RECON_OK``      within tolerance.

    Settled CPA is spend per *approved* lead, so it is compared with
    ``T / quality_factor`` (value per lead / target ROAS), not with T.
    Tolerances, and which statuses downgrade which codes, come only from the
    methodology's ``reconciliation`` block.
    """
    check_lang(lang)
    policy = reconciliation_policy(methodology)
    if not isinstance(settlement, dict) or settlement.get('kind') != 'settlement_daily':
        raise RuleError('Settlement document kind must be settlement_daily.')
    rows = settlement.get('rows')
    if not isinstance(rows, list):
        raise RuleError('Settlement rows must be an array.')
    default_date = settlement.get('date')
    default_tz = settlement.get('timezone')
    quality = quality_factor(methodology)
    roas_target = dec(methodology['target_roas'], 'target_roas')
    platform_date = (snapshot.get('observation') or {}).get('date')

    settled = {}
    order = []
    for row in rows:
        if not isinstance(row, dict) or not row.get('account_key'):
            raise RuleError('Every settlement row needs an account_key.')
        key = row['account_key']
        date = row.get('date', default_date)
        if key not in settled:
            settled[key] = {}
            order.append(key)
        if date in settled[key]:
            raise RuleError(f'Duplicate settlement row for {key} on {date}.')
        settled[key][date] = row

    accounts = snapshot.get('accounts') or []
    snapshot_keys = {account.get('account_key') for account in accounts}
    output = []
    for account in accounts:
        output.append(_reconcile_account(account, settled.get(account.get('account_key')), platform_date,
                                         default_date, default_tz, policy, quality, roas_target,
                                         methodology, lang))
    for key in order:
        if key in snapshot_keys:
            continue
        for date, row in settled[key].items():
            spend = dec(row.get('spend'), 'settlement.spend')
            leads = integer(row.get('results'), 'settlement.results')
            output.append(_settlement_row(
                key, row.get('platform'), RECON_SCOPE, 'settlement_only', policy,
                [say(lang, 'settle_scope_settlement')],
                platform_date=platform_date, settled_date=date,
                settled_spend=spend, settled_results=leads,
                settled_cpa=ratio(spend, Decimal(leads)) if spend is not None and leads else None,
                settlement_timezone=row.get('timezone', default_tz),
                unit_price_settled=num(dec(row.get('unit_price'), 'settlement.unit_price'))))

    summary = {code: 0 for code in RECON_CODES}
    for row in output:
        summary[row['status']] += 1
    return {
        'date': default_date,
        'timezone': default_tz,
        'currency': settlement.get('currency'),
        'tolerances': {'spend_pct': num(policy['spend_tolerance_pct'], '0.1'),
                       'results_pct': num(policy['results_tolerance_pct'], '0.1')},
        'approval_rate': num(quality, '0.01'),
        'target_roas': num(roas_target, '0.01'),
        'downgrade_on': list(policy['downgrade_on']),
        'downgrade_codes': list(policy['downgrade_codes']),
        'summary': summary,
        'rows': output,
    }


def _settlement_row(account_key, platform, status, side, policy, reasons, **fields):
    row = {
        'account_key': account_key, 'platform': platform, 'status': status, 'side': side,
        'platform_date': None, 'settled_date': None,
        'account_timezone': None, 'settlement_timezone': None,
        'platform_spend': None, 'settled_spend': None, 'spend_delta_pct': None,
        'platform_results': None, 'settled_results': None, 'expected_settled_results': None,
        'results_delta_pct': None, 'approval_rate': None,
        'platform_cpa': None, 'settled_cpa': None, 'T': None, 'settled_target': None,
        'settled_roas': None, 'unit_price': None, 'unit_price_settled': None,
    }
    for key, value in fields.items():
        if isinstance(value, Decimal):
            value = num2(value) if key in ('platform_spend', 'settled_spend', 'platform_cpa',
                                           'settled_cpa', 'T', 'settled_target') else num(value)
        row[key] = value
    row['reasons'] = reasons
    row['downgrade'] = status in policy['downgrade_on']
    return row


def _reconcile_account(account, dated_rows, platform_date, default_date, default_tz, policy, quality,
                       roas_target, methodology, lang):
    key = account.get('account_key')
    offer = account.get('offer') or {}
    price = dec(offer.get('unit_price'), 'unit_price')
    t = target_cost(price, methodology)
    settled_target = t / quality
    platform_spend, platform_leads = _platform_totals(account)
    common = dict(
        platform_date=platform_date, account_timezone=account.get('account_timezone'),
        platform_spend=platform_spend, platform_results=platform_leads,
        platform_cpa=(ratio(platform_spend, Decimal(platform_leads))
                      if platform_spend is not None and platform_leads else None),
        T=money(t), settled_target=money(settled_target), unit_price=num2(price))
    platform = account.get('platform')
    if not dated_rows:
        return _settlement_row(key, platform, RECON_SCOPE, 'platform_only', policy,
                               [say(lang, 'settle_scope_platform')], **common)
    row = dated_rows.get(platform_date) if platform_date else None
    if row is None:
        dates = sorted(str(date) for date in dated_rows)
        return _settlement_row(key, platform, RECON_WINDOW, 'both', policy,
                               [say(lang, 'settle_window', settled=', '.join(dates),
                                    platform=platform_date or say(lang, 'undeclared'))],
                               settled_date=', '.join(dates), **common)

    settle_tz = row.get('timezone', default_tz)
    settled_spend = dec(row.get('spend'), 'settlement.spend')
    settled_leads = integer(row.get('results'), 'settlement.results')
    settled_value = dec(row.get('value'), 'settlement.value')
    settled_price = dec(row.get('unit_price'), 'settlement.unit_price')
    spend_delta = None
    if platform_spend is not None and settled_spend is not None:
        if platform_spend:
            spend_delta = (settled_spend - platform_spend) / platform_spend * HUNDRED
        elif settled_spend == 0:
            spend_delta = Decimal('0')
    expected = platform_leads * quality if platform_leads is not None else None
    results_delta = None
    if expected is not None and settled_leads is not None:
        if expected:
            results_delta = (Decimal(settled_leads) - expected) / expected * HUNDRED
        elif settled_leads == 0:
            results_delta = Decimal('0')
    fields = dict(
        common, settled_date=platform_date, settlement_timezone=settle_tz,
        settled_spend=settled_spend, settled_results=settled_leads,
        spend_delta_pct=num(spend_delta, '0.01'),
        expected_settled_results=num(expected, '0.01'),
        results_delta_pct=num(results_delta, '0.01'),
        approval_rate=(num(Decimal(settled_leads) / Decimal(platform_leads), '0.001')
                       if settled_leads is not None and platform_leads else None),
        settled_cpa=(ratio(settled_spend, Decimal(settled_leads))
                     if settled_spend is not None and settled_leads else None),
        settled_roas=(num(ratio(settled_value, settled_spend), '0.0001')
                      if settled_value is not None and settled_spend else None),
        unit_price_settled=num2(settled_price))

    account_tz = account.get('account_timezone')
    if not account_tz or not settle_tz:
        return _settlement_row(key, platform, RECON_TZ, 'both', policy,
                               [say(lang, 'settle_tz_undeclared',
                                    account_tz=account_tz or say(lang, 'undeclared'),
                                    settle_tz=settle_tz or say(lang, 'undeclared'))], **fields)
    if account_tz != settle_tz:
        return _settlement_row(key, platform, RECON_TZ, 'both', policy,
                               [say(lang, 'settle_tz', account_tz=account_tz, settle_tz=settle_tz)],
                               **fields)

    gaps = []
    if settled_price is not None and settled_price != price:
        gaps.append(say(lang, 'settle_price', settled=num2(settled_price), platform=num2(price)))
    if platform_spend is None or platform_leads is None:
        gaps.append(say(lang, 'settle_platform_incomplete'))
    if settled_spend is None or settled_leads is None:
        gaps.append(say(lang, 'settle_settled_missing'))
    tolerance = policy['spend_tolerance_pct']
    if platform_spend is not None and settled_spend is not None:
        if spend_delta is None:
            gaps.append(say(lang, 'settle_spend_from_zero', settled=num2(settled_spend)))
        elif abs(spend_delta) > tolerance:
            gaps.append(say(lang, 'settle_spend', delta=signed_pct(spend_delta),
                            tolerance=num(tolerance, '0.1')))
    tolerance = policy['results_tolerance_pct']
    if expected is not None and settled_leads is not None:
        if results_delta is None:
            gaps.append(say(lang, 'settle_results_from_zero', settled=settled_leads))
        elif abs(results_delta) > tolerance:
            gaps.append(say(lang, 'settle_results', settled=settled_leads, platform=platform_leads,
                            expected=num(expected, '0.1'), rate=num(quality, '0.01'),
                            delta=signed_pct(results_delta), tolerance=num(tolerance, '0.1')))
    if gaps:
        return _settlement_row(key, platform, RECON_GAP, 'both', policy, gaps, **fields)
    return _settlement_row(key, platform, RECON_OK, 'both', policy, [say(lang, 'settle_ok')], **fields)


def downgrade_unreconciled(proposals, reconciliation, lang='en'):
    """Make cost-based writes advisory in accounts whose numbers do not reconcile.

    A proposal whose code is in ``downgrade_codes``, in an account whose status
    is in ``downgrade_on``, keeps its code and evidence but loses its write
    intent, so the gate reports it as advisory. Nothing is dropped.
    """
    check_lang(lang)
    rows = {row['account_key']: row for row in (reconciliation or {}).get('rows', [])
            if row['side'] != 'settlement_only'}
    codes = set((reconciliation or {}).get('downgrade_codes') or ())
    result = []
    for item in proposals:
        row = rows.get(item.get('account_key'))
        if row and row['downgrade'] and item.get('code') in codes:
            item = dict(item)
            item.pop('target', None)
            item.pop('baseline', None)
            detail = ' '.join(row['reasons'])
            item['downgraded'] = {'reason': 'measurement_unreconciled', 'status': row['status'],
                                  'detail': detail}
            item['evidence'] = list(item.get('evidence') or []) + [
                say(lang, 'downgrade', status=row['status'], detail=detail)]
        result.append(item)
    return result


# --------------------------------------------------------------------------
# write gate
# --------------------------------------------------------------------------

READY, SATISFIED, CONFLICT, UNKNOWN, ADVISORY = (
    'ready', 'satisfied', 'conflict', 'unknown', 'advisory')

GATE_LABEL = GATE_LABELS['en']

# States that need a human to look before the round can be considered closed.
NEEDS_HUMAN = (CONFLICT, UNKNOWN)


def gate(proposals, writeback, lang='en'):
    """Decide what may be written, using the state read back just before writing.

    Five outcomes, per proposal:

    ``satisfied``  the target value is already in place — write nothing. Writing
                   anyway would be a significant edit and would reset learning.
    ``ready``      the field still holds the value it held when the plan was
                   built, so only the differing fields are sent.
    ``conflict``   the field holds neither the baseline nor the target.
                   Isolate this row and check the source of the difference;
                   the values alone do not identify who or what changed it.
                   Do not overwrite or restart the whole batch.
    ``unknown``    the current state was not read, a target field is absent from
                   the read, or a differing field has no concrete baseline.
                   Missing and explicit null baselines have distinct reasons;
                   neither establishes a safe comparison for a change.
    ``advisory``   the finding declares no field change, so there is nothing to
                   gate. Reported separately: counting these as "unknown" would
                   inflate the number of rows that actually need attention.

    An already satisfied field needs no baseline because it will not be changed.
    Any unknown field holds the whole proposal; other proposals remain independent.
    Only ``ready`` rows may proceed, and only for their differing fields.

    Before any comparison, every target field must be allowed for the
    proposal's ``object_type`` by ``WRITABLE_FIELDS``. A field outside that
    table is a malformed plan, not a state question, so it raises ``RuleError``
    and blocks the round instead of becoming a sixth gate state.
    """
    check_lang(lang)
    objects = (writeback or {}).get('objects') or {}
    results = []
    for item in proposals:
        target = item.get('target')
        _check_writable(item, target)
        if not target:
            downgraded = item.get('downgraded')
            detail = (say(lang, 'gate_downgraded', status=downgraded.get('status'))
                      if isinstance(downgraded, dict) else say(lang, 'gate_advisory'))
            results.append(_verdict(item, ADVISORY, [detail], lang))
            continue
        current = objects.get(item.get('object_key'))
        if not isinstance(current, dict):
            results.append(_verdict(item, UNKNOWN,
                                    [say(lang, 'gate_no_record', key=repr(item.get('object_key')))], lang))
            continue
        absent = [field for field in target if field not in current]
        if absent:
            results.append(_verdict(item, UNKNOWN,
                                    [say(lang, 'gate_absent_field', field=field) for field in absent], lang))
            continue
        baseline = item.get('baseline') or {}
        detail, conflicts, unknown, writes, done = [], [], [], [], []
        for field, wanted in target.items():
            present = current.get(field)
            held = baseline.get(field)
            if same_number(present, wanted):
                detail.append(say(lang, 'gate_satisfied', field=field, wanted=wanted))
                done.append(field)
            elif field not in baseline:
                detail.append(say(lang, 'gate_no_baseline', field=field, present=present))
                unknown.append(field)
            elif held is None:
                detail.append(say(lang, 'gate_null_baseline', field=field))
                unknown.append(field)
            elif same_number(present, held):
                detail.append(say(lang, 'gate_write', field=field, present=present, wanted=wanted))
                writes.append(field)
            else:
                detail.append(say(lang, 'gate_conflict', field=field, present=present, held=held,
                                  wanted=wanted))
                conflicts.append(field)
        if unknown:
            results.append(_verdict(item, UNKNOWN, detail, lang, conflict_fields=conflicts,
                                    satisfied_fields=done))
        elif conflicts:
            results.append(_verdict(item, CONFLICT, detail, lang, conflict_fields=conflicts))
        elif not writes:
            results.append(_verdict(item, SATISFIED, detail, lang, satisfied_fields=done))
        else:
            results.append(_verdict(item, READY, detail, lang, writable_fields=writes))
    return results


def _check_writable(item, target):
    """Reject a target that names a field its object type may not change."""
    if target is None:
        return
    if not isinstance(target, dict):
        raise RuleError(f"{item.get('code')} · {item.get('object_key')}: target must be an object.")
    if not target:
        return
    object_type = item.get('object_type')
    allowed = WRITABLE_FIELDS.get(object_type)
    if allowed is None:
        raise RuleError(f"{item.get('code')} · {item.get('object_key')}: object_type {object_type!r} "
                        f'declares no writable fields (declared: {sorted(WRITABLE_FIELDS)}) ⇒ the whole '
                        'gate stops.')
    outside = sorted(field for field in target if field not in allowed)
    if outside:
        raise RuleError(f"{item.get('code')} · {item.get('object_key')}: field(s) {', '.join(outside)} "
                        f'are not writable for {object_type} {list(allowed)} ⇒ the whole gate stops; '
                        'no row is written.')


def _verdict(item, state, detail, lang='en', writable_fields=(), satisfied_fields=(), conflict_fields=()):
    verdict = dict(item)
    verdict['gate'] = state
    verdict['gate_label'] = GATE_LABELS[lang][state]
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

def reconcile(verdicts, after_objects, lang='en'):
    """Compare the state read after writing against each declared target."""
    check_lang(lang)
    report = []
    for verdict in verdicts:
        if verdict['gate'] != READY:
            report.append({'object_key': verdict['object_key'], 'code': verdict['code'],
                           'checked': False,
                           'reason': say(lang, 'recon_not_written', label=verdict['gate_label'])})
            continue
        current = (after_objects or {}).get(verdict['object_key'])
        if not isinstance(current, dict):
            report.append({'object_key': verdict['object_key'], 'code': verdict['code'],
                           'checked': False, 'reason': say(lang, 'recon_not_in_after')})
            continue
        missed = [say(lang, 'recon_miss_field', field=field, wanted=wanted, current=current.get(field))
                  for field, wanted in verdict['target'].items()
                  if not same_number(current.get(field), wanted)]
        report.append({
            'object_key': verdict['object_key'],
            'code': verdict['code'],
            'checked': True,
            'effective': not missed,
            'detail': (say(lang, 'recon_match') if not missed
                       else say(lang, 'recon_mismatch', details=say(lang, 'recon_miss_sep').join(missed))),
        })
    return report
