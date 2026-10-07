#!/usr/bin/env python3
"""Readback verifier: compare a build plan with what the platform returned.

Offline, tested version of the build protocol I ran interactively on live Meta
and TikTok lead-gen accounts: create every object PAUSED, read every object
back, compare field by field, and only then activate. This module is the
comparison step. It reads two saved files and makes no platform call.

    python3 readback.py --plan examples/readback/meta-plan.json \\
        --readback examples/readback/meta-readback.json
    python3 readback.py --plan ... --readback ... --receipt out/receipt.md
    python3 readback.py --plan ... --readback ... --lang zh-CN \\
        --check examples/readback/expected/meta-receipt.zh-CN.md

What it enforces:

* Every value in the receipt's "Read back" column comes from the readback file.
  Nothing is copied from the plan. A field the readback does not contain is a
  mismatch ("not returned"), never assumed equal.
* Every object must read back with the platform's paused status before the
  receipt can say ACTIVATE.
* Money returned in minor units is converted with the platform's currency
  offset for the currency the *account* reports. There is no x100 default; an
  unknown currency is refused.
* Every required URL parameter must be present with its planned value.
* An object in the readback that the plan does not contain (for example a
  duplicate left by a retried request) holds the build.

Regenerate a golden receipt after an intended change with ``--receipt``, read
the diff, then confirm with ``--check``.
"""
import argparse
from decimal import Decimal, InvalidOperation
import difflib
import json
from pathlib import Path
import sys
from urllib.parse import parse_qsl, urlsplit, urlunsplit

LEVELS = ('campaign', 'adset', 'ad')
LANGUAGES = ('en', 'zh-CN')

# Meta Marketing API currency offsets
# (https://developers.facebook.com/docs/marketing-api/currencies, checked 2026-10-07).
# Amounts such as daily_budget and bid_amount come back in minor units: offset 100
# means exponent 2, offset 1 means exponent 0. The offset is the platform's, not
# ISO 4217's -- HUF, IDR, TWD and COP have two ISO decimals but offset 1 on Meta.
# A currency missing from this table is refused rather than guessed.
MINOR_UNIT_EXPONENT = dict(
    [(code, 2) for code in ('AED', 'AUD', 'BRL', 'CAD', 'CHF', 'CNY', 'DKK', 'EUR', 'GBP',
                            'HKD', 'ILS', 'INR', 'MXN', 'MYR', 'NOK', 'NZD', 'PHP', 'PLN',
                            'SAR', 'SEK', 'SGD', 'THB', 'TRY', 'USD', 'ZAR')]
    + [(code, 0) for code in ('CLP', 'COP', 'HUF', 'IDR', 'ISK', 'JPY', 'KRW', 'PYG',
                              'TWD', 'VND')])

# What each logical field is, so plan values and returned values are parsed the
# same way. Order here is the order of rows in a receipt.
FIELD_KINDS = {
    'objective': 'enum',
    'optimization_goal': 'enum',
    'optimization_event': 'enum',
    'daily_budget': 'money',
    'bid_strategy': 'enum',
    'bid_amount': 'money',
    'attribution': 'attribution',
    'geo': 'set',
    'placements': 'set',
    'destination_url': 'url',
    'url_parameters': 'params',
    'cta': 'enum',
    'status': 'enum',
}
LEVEL_FIELDS = {
    'campaign': ('objective', 'status'),
    'adset': ('optimization_goal', 'optimization_event', 'daily_budget', 'bid_strategy',
              'bid_amount', 'attribution', 'geo', 'placements', 'status'),
    'ad': ('destination_url', 'url_parameters', 'cta', 'status'),
}
# A plan must state these; the others are checked when the plan sets them.
REQUIRED_PLAN_FIELDS = {
    'campaign': ('objective',),
    'adset': ('optimization_event', 'daily_budget', 'bid_strategy', 'attribution', 'geo',
              'placements'),
    'ad': ('destination_url', 'cta'),
}

# Where each logical field lives in a native API response. Field names follow the
# public Meta Marketing API (campaign, ad set, ad with its creative expanded) and
# TikTok API for Business (campaign, ad group, ad) references. Check this table
# against the API version you read before relying on it.
TIKTOK_WINDOW_DAYS = {'OFF': 0, 'ONE_DAY': 1, 'SEVEN_DAYS': 7, 'FOURTEEN_DAYS': 14,
                      'TWENTY_EIGHT_DAYS': 28}
ADAPTERS = {
    'meta': {
        'name': 'Meta',
        'labels': {'campaign': 'campaign', 'adset': 'ad set', 'ad': 'ad'},
        'paused': 'PAUSED',
        'money': 'minor',
        'attribution': 'spec_list',
        'paths': {
            'objective': ('objective',),
            'status': ('status',),
            'optimization_goal': ('optimization_goal',),
            'optimization_event': ('promoted_object', 'custom_event_type'),
            'daily_budget': ('daily_budget',),
            'bid_strategy': ('bid_strategy',),
            'bid_amount': ('bid_amount',),
            'attribution': ('attribution_spec',),
            'geo': ('targeting', 'geo_locations', 'countries'),
            'placements': ('targeting', 'publisher_platforms'),
            'destination_url': ('creative', 'object_story_spec', 'link_data', 'link'),
            'url_parameters': (('creative', 'object_story_spec', 'link_data', 'link'),
                               ('creative', 'url_tags')),
            'cta': ('creative', 'object_story_spec', 'link_data', 'call_to_action', 'type'),
        },
        # Review and delivery state: recorded in the receipt, never compared.
        'observed': ('effective_status',),
    },
    'tiktok': {
        'name': 'TikTok',
        'labels': {'campaign': 'campaign', 'adset': 'ad group', 'ad': 'ad'},
        'paused': 'DISABLE',
        'money': 'major',
        'attribution': 'window_enums',
        'paths': {
            'objective': ('objective_type',),
            'status': ('operation_status',),
            'optimization_goal': ('optimization_goal',),
            'optimization_event': ('optimization_event',),
            'daily_budget': ('budget',),
            'bid_strategy': ('bid_type',),
            'bid_amount': ('conversion_bid_price',),
            'attribution': (('click_attribution_window',), ('view_attribution_window',)),
            'geo': ('location_ids',),
            'placements': ('placements',),
            'destination_url': ('landing_page_url',),
            'url_parameters': (('landing_page_url',),),
            'cta': ('call_to_action',),
        },
        # ``budget`` is only a daily budget when budget_mode says so.
        'daily_budget_mode': ('budget_mode', 'BUDGET_MODE_DAY'),
        'observed': (),
    },
}

TEXT = {
    'en': {
        'title': 'Build receipt — replay, fictional values',
        'meta_line': '{platform} · account `{account}` · currency {currency} · plan `{plan}` · readback `{readback}`',
        'scope': ('Replayed offline from saved files: no platform call was made. Every value under '
                  '"Read back" comes from the readback file; a field the platform did not return '
                  'counts as a mismatch.'),
        'timeline': 'Timeline',
        'chain': 'Created PAUSED {paused}/{objects} → Readback {matched}/{fields} fields → {decision}',
        'step': 'Step', 'time': 'Time', 'result': 'Result',
        'created': 'Created PAUSED',
        'created_result': '{returned} of {objects} planned objects returned; {paused} read back `{paused_value}`',
        'readback': 'Readback',
        'readback_result': '{matched} of {fields} fields match the plan',
        'decision': 'Decision',
        'decision_hold': 'HOLD: {count} {problems}; nothing is activated',
        'decision_activate': 'ACTIVATE: every field matches and every object is paused',
        'fields': 'Fields',
        'columns': ('Level', 'Object', 'Field', 'Planned', 'Read back', 'Match'),
        'problems': 'Problems',
        'colon': ': ',
        'observed': 'Not gated: review and delivery state at read time',
        'observed_note': ('Configured status is gated above. These values come from the platform\'s '
                          'review and delivery processing; they are recorded, not compared.'),
        'observed_columns': ('Object', 'Field', 'Value'),
        'next': 'Next step',
        'next_hold': ('HOLD: fix the fields listed above on the platform, read every object back '
                      'again and re-run this check. A HOLD receipt never leads to activation.'),
        'next_activate': ('ACTIVATE: the configuration matches the plan. Activation still needs the '
                          'owner\'s approval of this batch; then activate in stages, read status back '
                          'and poll review. This receipt is not that approval.'),
        'not_returned': '*not returned*',
        'account': 'account',
        'field_labels': {
            'currency': 'Account currency', 'objective': 'Objective',
            'optimization_goal': 'Optimization goal', 'optimization_event': 'Optimization event',
            'daily_budget': 'Daily budget', 'bid_strategy': 'Bid strategy', 'bid_amount': 'Bid amount',
            'attribution': 'Attribution', 'geo': 'Geo', 'placements': 'Placements',
            'destination_url': 'Destination URL', 'url_parameters': 'URL parameters', 'cta': 'CTA',
            'status': 'Status', 'effective_status': 'effective_status',
        },
        'reasons': {
            'not_returned': 'not returned by the platform',
            'mismatch': 'planned {planned}, read back {read_back}',
            'not_paused': 'read back {read_back}, must be {planned} before activation',
            'missing_url_parameter': 'required parameter missing: {names}',
            'url_parameter_value': 'parameter value differs: {names}',
            'object_not_returned': 'planned object not found in the readback',
            'unexpected_object': 'object in the readback that the plan does not contain',
        },
    },
    'zh-CN': {
        'title': '搭建回执 — 回放，数值均为虚构',
        'meta_line': '{platform} · 账户 `{account}` · 币种 {currency} · 计划 `{plan}` · 回读 `{readback}`',
        'scope': ('离线回放已保存的文件，没有调用任何平台。「回读值」一列全部来自回读文件；'
                  '平台没有返回的字段一律记为不一致。'),
        'timeline': '时间线',
        'chain': '暂停创建 {paused}/{objects} → 回读 {matched}/{fields} 个字段 → {decision}',
        'step': '步骤', 'time': '时间', 'result': '结果',
        'created': '暂停创建',
        'created_result': '计划中 {objects} 个对象有 {returned} 个返回；{paused} 个回读为 `{paused_value}`',
        'readback': '回读',
        'readback_result': '{fields} 个字段中 {matched} 个与计划一致',
        'decision': '结论',
        'decision_hold': 'HOLD：{count} 个问题；不启用任何对象',
        'decision_activate': 'ACTIVATE：所有字段一致，所有对象均为暂停',
        'fields': '字段',
        'columns': ('层级', '对象', '字段', '计划值', '回读值', '一致'),
        'problems': '问题',
        'colon': '：',
        'observed': '不参与判定：回读时的审核与投放状态',
        'observed_note': '上表已判定配置状态。下列值来自平台的审核与投放处理，只记录、不比较。',
        'observed_columns': ('对象', '字段', '值'),
        'next': '下一步',
        'next_hold': ('HOLD：先在平台上修正上面列出的字段，重新回读全部对象后再跑一次本检查。'
                      'HOLD 回执永远不会进入启用。'),
        'next_activate': ('ACTIVATE：配置与计划一致。启用仍需负责人批准这一批次；之后分阶段启用、'
                          '回读状态并跟进审核。本回执不等于批准。'),
        'not_returned': '*未返回*',
        'account': '账户',
        'field_labels': {
            'currency': '账户币种', 'objective': '目标', 'optimization_goal': '优化目标',
            'optimization_event': '优化事件', 'daily_budget': '日预算', 'bid_strategy': '出价策略',
            'bid_amount': '出价金额', 'attribution': '归因设置', 'geo': '地区', 'placements': '版位',
            'destination_url': '落地页', 'url_parameters': '链接参数', 'cta': '行动号召',
            'status': '状态', 'effective_status': 'effective_status',
        },
        'reasons': {
            'not_returned': '平台没有返回该字段',
            'mismatch': '计划 {planned}，回读 {read_back}',
            'not_paused': '回读为 {read_back}，启用前必须是 {planned}',
            'missing_url_parameter': '缺少必需参数：{names}',
            'url_parameter_value': '参数值与计划不同：{names}',
            'object_not_returned': '回读中找不到这个计划对象',
            'unexpected_object': '回读中出现了计划里没有的对象',
        },
    },
}
LEVEL_LABELS_ZH = {'campaign': '广告系列', 'adset': '广告组', 'ad': '广告', 'account': '账户'}


class ReadbackError(ValueError):
    pass


_MISSING = object()


# --------------------------------------------------------------------------
# small parsers shared by plan values and returned values
# --------------------------------------------------------------------------

def dig(value, path):
    for part in path:
        if not isinstance(value, dict) or value.get(part) is None:
            return _MISSING
        value = value[part]
    return value


def decimal_of(raw):
    """A Decimal from a JSON number or numeric string; ``None`` if it is not one."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        return None
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def money_text(value, exponent):
    if exponent is None:
        return str(value)
    return str(value.quantize(Decimal(1).scaleb(-exponent)))


def base_url(raw):
    parts = urlsplit(raw)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or '/', '', ''))


def query_pairs(raw):
    if '?' in raw or '://' in raw:
        raw = urlsplit(raw).query
    return parse_qsl(raw, keep_blank_values=True)


def params_text(pairs):
    return '&'.join(f'{key}={value}' for key, value in pairs)


def attribution_text(click, view):
    return f'click {click}d, view {view}d'


# --------------------------------------------------------------------------
# input validation
# --------------------------------------------------------------------------

def load(path):
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ReadbackError(f'not valid JSON: {Path(path).name} ({exc})') from exc


def exponent_for(currency, adapter):
    exponent = MINOR_UNIT_EXPONENT.get(currency)
    if exponent is None and adapter['money'] == 'minor':
        raise ReadbackError(f'currency {currency!r} has no minor-unit offset in the table; add it '
                            'from the platform\'s currency reference instead of assuming x100')
    return exponent


def plan_value(field, raw, exponent, currency, object_key):
    """Parse a planned value into ``(comparable, display)``."""
    kind = FIELD_KINDS[field]
    where = f'plan object {object_key!r} field {field!r}'
    if kind == 'enum':
        if not isinstance(raw, str) or not raw:
            raise ReadbackError(f'{where} must be a non-empty string')
        return raw, raw
    if kind == 'money':
        value = decimal_of(raw)
        if value is None or value < 0:
            raise ReadbackError(f'{where} must be a non-negative amount in major units')
        if exponent is not None and value != value.quantize(Decimal(1).scaleb(-exponent)):
            raise ReadbackError(f'{where} has more decimals than the currency allows')
        return (currency, value), f'{money_text(value, exponent)} {currency}'
    if kind == 'attribution':
        if not isinstance(raw, dict):
            raise ReadbackError(f'{where} must be {{"click_days": n, "view_days": n}}')
        click, view = raw.get('click_days'), raw.get('view_days')
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (click, view)):
            raise ReadbackError(f'{where} needs integer click_days and view_days')
        return (click, view), attribution_text(click, view)
    if kind == 'set':
        if not isinstance(raw, list) or not raw or not all(isinstance(x, str) and x for x in raw):
            raise ReadbackError(f'{where} must be a non-empty list of strings')
        items = tuple(sorted(raw))
        return items, ', '.join(items)
    if kind == 'url':
        if not isinstance(raw, str) or not urlsplit(raw).netloc:
            raise ReadbackError(f'{where} must be an absolute URL')
        return base_url(raw), base_url(raw)
    if kind == 'params':
        if not isinstance(raw, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                                for k, v in raw.items()):
            raise ReadbackError(f'{where} must map parameter names to string values')
        pairs = tuple(raw.items())
        return pairs, params_text(pairs)
    raise ReadbackError(f'unknown field kind for {field!r}')


def validate_plan(plan):
    if not isinstance(plan, dict) or plan.get('kind') != 'build_plan':
        raise ReadbackError('plan kind must be build_plan')
    adapter = ADAPTERS.get(plan.get('platform'))
    if adapter is None:
        raise ReadbackError(f"plan platform must be one of {sorted(ADAPTERS)}")
    for key in ('account_key', 'currency'):
        if not isinstance(plan.get(key), str) or not plan[key]:
            raise ReadbackError(f'plan needs {key}')
    objects = plan.get('objects')
    if not isinstance(objects, list) or not objects:
        raise ReadbackError('plan needs a non-empty objects list')
    seen = set()
    for item in objects:
        key = item.get('object_key') if isinstance(item, dict) else None
        if not isinstance(key, str) or not key:
            raise ReadbackError('every plan object needs an object_key')
        if key in seen:
            raise ReadbackError(f'duplicate plan object_key {key!r}')
        seen.add(key)
        if item.get('level') not in LEVELS:
            raise ReadbackError(f'plan object {key!r} level must be one of {list(LEVELS)}')
        for field in REQUIRED_PLAN_FIELDS[item['level']]:
            if item.get(field) is None:
                raise ReadbackError(f'plan object {key!r} must state {field!r}; the readback is '
                                    'checked against what the plan says')
        if item.get('status') not in (None, 'PAUSED'):
            raise ReadbackError(f'plan object {key!r}: the build protocol creates every object '
                                'PAUSED; activation is a separate, approved step')
    return adapter


def validate_readback(readback, plan):
    if not isinstance(readback, dict) or readback.get('kind') != 'build_readback':
        raise ReadbackError('readback kind must be build_readback')
    if readback.get('platform') != plan['platform']:
        raise ReadbackError('readback platform does not match the plan')
    objects = readback.get('objects')
    if not isinstance(objects, list):
        raise ReadbackError('readback needs an objects list')
    for item in objects:
        if not isinstance(item, dict) or not isinstance(item.get('object_key'), str) \
                or not isinstance(item.get('response'), dict):
            raise ReadbackError('every readback object needs an object_key and a response object')
        if item.get('level') not in LEVELS:
            raise ReadbackError(f"readback object {item['object_key']!r} has no valid level")


# --------------------------------------------------------------------------
# reading one returned field
# --------------------------------------------------------------------------

def read_value(field, response, adapter, currency, exponent):
    """Parse a returned value into ``(comparable, display)`` or ``_MISSING``.

    The display string is built only from what the response contains.
    """
    kind = FIELD_KINDS[field]
    path = adapter['paths'][field]

    if field == 'attribution' and adapter['attribution'] == 'spec_list':
        spec = dig(response, path)
        if spec is _MISSING:
            return _MISSING
        if not isinstance(spec, list):
            return ('invalid', repr(spec)), json.dumps(spec)
        days = {'CLICK_THROUGH': 0, 'VIEW_THROUGH': 0}
        for entry in spec:
            if isinstance(entry, dict) and entry.get('event_type') in days:
                days[entry['event_type']] = entry.get('window_days')
        click, view = days['CLICK_THROUGH'], days['VIEW_THROUGH']
        return (click, view), attribution_text(click, view)
    if field == 'attribution':
        click_raw, view_raw = dig(response, path[0]), dig(response, path[1])
        if click_raw is _MISSING or view_raw is _MISSING:
            return _MISSING
        click, view = TIKTOK_WINDOW_DAYS.get(click_raw), TIKTOK_WINDOW_DAYS.get(view_raw)
        if click is None or view is None:
            return ('invalid', click_raw, view_raw), f'{click_raw} / {view_raw}'
        return (click, view), attribution_text(click, view)

    if kind == 'params':
        sources = [dig(response, source) for source in path]
        if all(source is _MISSING for source in sources):
            return _MISSING
        pairs = []
        for source in sources:
            if isinstance(source, str):
                pairs.extend(query_pairs(source))
        return tuple(pairs), params_text(pairs) or '(none)'

    raw = dig(response, path)
    if raw is _MISSING:
        return _MISSING

    if kind == 'money':
        if field == 'daily_budget' and adapter.get('daily_budget_mode'):
            mode_field, daily = adapter['daily_budget_mode']
            mode = dig(response, (mode_field,))
            if mode is _MISSING:
                return _MISSING
            if mode != daily:
                return ('budget_mode', mode), f'{mode} {raw}'
        value = decimal_of(raw)
        if value is None:
            return ('invalid', repr(raw)), f'{raw} (not an amount)'
        if adapter['money'] == 'minor':
            if currency is None:
                return ('unconverted', raw), f'{raw} (minor units; account currency not returned)'
            if value != value.to_integral_value():
                return ('invalid', repr(raw)), f'{raw} (not a whole number of minor units)'
            major = value.scaleb(-exponent)
            return (currency, major), f'{money_text(major, exponent)} {currency} (raw {raw})'
        if currency is None:
            return ('unconverted', raw), f'{raw} (account currency not returned)'
        return (currency, value), f'{money_text(value, exponent)} {currency}'
    if kind == 'set':
        if not isinstance(raw, list):
            return ('invalid', repr(raw)), str(raw)
        items = tuple(sorted(str(x) for x in raw))
        return items, ', '.join(items) or '(empty)'
    if kind == 'url':
        if not isinstance(raw, str):
            return ('invalid', repr(raw)), str(raw)
        return base_url(raw), base_url(raw)
    if isinstance(raw, (dict, list)):
        return ('invalid', json.dumps(raw, sort_keys=True)), json.dumps(raw, sort_keys=True)
    return raw, str(raw)


# --------------------------------------------------------------------------
# the comparison
# --------------------------------------------------------------------------

def compare_params(planned, returned):
    """Return ``(missing, different)`` parameter names for a required-parameter row."""
    present = {}
    for key, value in returned:
        present.setdefault(key, []).append(value)
    missing = [key for key, _ in planned if key not in present]
    different = [key for key, value in planned if key in present and value not in present[key]]
    return missing, different


def verify_build(plan, readback):
    """Compare a build plan with a saved readback and decide ``activate`` or ``hold``.

    Returns ``{rows, decision, reasons, ...}``. Each row is
    ``{level, object_key, field, planned, read_back, match}``; ``read_back`` is
    ``None`` when the platform did not return the field.
    """
    adapter = validate_plan(plan)
    validate_readback(readback, plan)
    paused = adapter['paused']

    rows, reasons, observed = [], [], []

    def add(level, key, field, planned, read, match, code=None, names=None):
        rows.append({'level': level, 'object_key': key, 'field': field,
                     'planned': planned, 'read_back': read, 'match': match})
        if not match:
            reason = {'code': code, 'object_key': key, 'field': field,
                      'planned': planned, 'read_back': read}
            if names:
                reason['names'] = names
            reasons.append(reason)

    # The account currency decides how minor units convert, so it is read back
    # too: a plan written for USD against a JPY account is a 100x error.
    currency = dig(readback.get('account') or {}, ('response', 'currency'))
    if currency is _MISSING:
        add('account', plan['account_key'], 'currency', plan['currency'], None, False, 'not_returned')
        currency = None
    else:
        add('account', plan['account_key'], 'currency', plan['currency'], currency,
            currency == plan['currency'], 'mismatch')
    plan_exponent = exponent_for(plan['currency'], adapter)
    read_exponent = exponent_for(currency, adapter) if currency else None

    returned = {}
    for item in readback['objects']:
        if item['object_key'] in returned:
            raise ReadbackError(f"readback lists {item['object_key']!r} twice")
        returned[item['object_key']] = item

    planned_keys = set()
    paused_count = returned_count = 0
    for item in plan['objects']:
        key, level = item['object_key'], item['level']
        planned_keys.add(key)
        found = returned.get(key)
        if found is not None and found['level'] != level:
            raise ReadbackError(f'{key!r} is a {level} in the plan but a {found["level"]} in the readback')
        if found is None:
            reasons.append({'code': 'object_not_returned', 'object_key': key, 'field': None,
                            'planned': None, 'read_back': None})
        else:
            returned_count += 1
        response = found['response'] if found is not None else {}

        for field in LEVEL_FIELDS[level]:
            if field == 'status':
                planned_raw = paused
            elif field == 'url_parameters':
                planned_raw = dict(plan.get('url_parameters') or {})
                planned_raw.update(item.get('url_parameters') or {})
                if not planned_raw:
                    continue
            else:
                planned_raw = item.get(field)
                if planned_raw is None:
                    continue
            planned_cmp, planned_text = plan_value(field, planned_raw, plan_exponent,
                                                   plan['currency'], key)
            if found is None:
                rows.append({'level': level, 'object_key': key, 'field': field,
                             'planned': planned_text, 'read_back': None, 'match': False})
                continue
            reading = read_value(field, response, adapter, currency, read_exponent)
            if reading is _MISSING:
                add(level, key, field, planned_text, None, False, 'not_returned')
                continue
            read_cmp, read_text = reading
            if field == 'status':
                if read_cmp == paused:
                    paused_count += 1
                add(level, key, field, planned_text, read_text, read_cmp == paused, 'not_paused')
            elif field == 'url_parameters':
                missing, different = compare_params(planned_cmp, read_cmp)
                if missing:
                    add(level, key, field, planned_text, read_text, False,
                        'missing_url_parameter', missing)
                elif different:
                    add(level, key, field, planned_text, read_text, False,
                        'url_parameter_value', different)
                else:
                    add(level, key, field, planned_text, read_text, True)
            else:
                add(level, key, field, planned_text, read_text, read_cmp == planned_cmp, 'mismatch')

        if found is not None:
            for name in adapter['observed']:
                value = dig(response, (name,))
                if value is not _MISSING:
                    observed.append({'object_key': key, 'field': name, 'value': str(value)})

    for item in readback['objects']:
        if item['object_key'] not in planned_keys:
            reasons.append({'code': 'unexpected_object', 'object_key': item['object_key'],
                            'field': None, 'planned': None, 'read_back': None})

    matched = sum(1 for row in rows if row['match'])
    return {
        'platform': plan['platform'],
        'account_key': plan['account_key'],
        'currency': plan['currency'],
        'paused_value': paused,
        'created_at': readback.get('created_at'),
        'read_at': readback.get('read_at'),
        'objects': len(plan['objects']),
        'objects_returned': returned_count,
        'objects_paused': paused_count,
        'fields': len(rows),
        'fields_matched': matched,
        'rows': rows,
        'observed': observed,
        'decision': 'hold' if reasons else 'activate',
        'reasons': reasons,
        'native_platform_calls': 0,
    }


# --------------------------------------------------------------------------
# receipt
# --------------------------------------------------------------------------

def cell(value):
    return '`' + str(value).replace('|', '\\|') + '`'


def level_label(level, platform, lang):
    if lang == 'zh-CN':
        return LEVEL_LABELS_ZH[level]
    if level == 'account':
        return TEXT['en']['account']
    return ADAPTERS[platform]['labels'][level]


def reason_text(reason, text):
    def code(value):
        return '`' + str(value) + '`'
    return text['reasons'][reason['code']].format(
        planned=code(reason.get('planned')), read_back=code(reason.get('read_back')),
        names=', '.join(code(name) for name in reason.get('names') or ()))


def render_receipt(result, lang='en', plan_name='plan.json', readback_name='readback.json'):
    if lang not in TEXT:
        raise ReadbackError(f'language must be one of {list(LANGUAGES)}')
    text = TEXT[lang]
    platform = result['platform']
    hold = result['decision'] == 'hold'
    count = len(result['reasons'])
    chain = text['chain'].format(paused=result['objects_paused'], objects=result['objects'],
                                 matched=result['fields_matched'], fields=result['fields'],
                                 decision=result['decision'].upper())
    created = text['created_result'].format(returned=result['objects_returned'],
                                            objects=result['objects'], paused=result['objects_paused'],
                                            paused_value=result['paused_value'])
    readback = text['readback_result'].format(matched=result['fields_matched'], fields=result['fields'])
    decision = (text['decision_hold'].format(count=count, problems='problem' if count == 1 else 'problems')
                if hold else text['decision_activate'])
    lines = [
        f"# {text['title']}", '',
        text['meta_line'].format(platform=ADAPTERS[platform]['name'], account=result['account_key'],
                                 currency=result['currency'], plan=plan_name, readback=readback_name),
        '', f"> {text['scope']}", '',
        f"## {text['timeline']}", '', f'**{chain}**', '',
        f"| {text['step']} | {text['time']} | {text['result']} |", '|---|---|---|',
        f"| {text['created']} | {result['created_at'] or '—'} | {created} |",
        f"| {text['readback']} | {result['read_at'] or '—'} | {readback} |",
        f"| {text['decision']} | — | {decision} |",
    ]
    if result['reasons']:
        lines += ['', f"## {text['problems']}", '']
        for reason in result['reasons']:
            where = cell(reason['object_key'])
            if reason['field']:
                where += ' · ' + text['field_labels'][reason['field']]
            lines.append(f"- {where}{text['colon']}{reason_text(reason, text)}")
    lines += ['', f"## {text['fields']}", '',
              '| ' + ' | '.join(text['columns']) + ' |', '|---|---|---|---|---|:---:|']
    for row in result['rows']:
        read = text['not_returned'] if row['read_back'] is None else cell(row['read_back'])
        lines.append(f"| {level_label(row['level'], platform, lang)} | {cell(row['object_key'])} | "
                     f"{text['field_labels'][row['field']]} | {cell(row['planned'])} | {read} | "
                     f"{'✓' if row['match'] else '✗'} |")
    if result['observed']:
        lines += ['', f"## {text['observed']}", '', text['observed_note'], '',
                  '| ' + ' | '.join(text['observed_columns']) + ' |', '|---|---|---|']
        for item in result['observed']:
            lines.append(f"| {cell(item['object_key'])} | {text['field_labels'][item['field']]} | "
                         f"{cell(item['value'])} |")
    lines += ['', f"## {text['next']}", '', text['next_hold'] if hold else text['next_activate'], '']
    return '\n'.join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--plan', required=True, type=Path, help='build plan JSON')
    parser.add_argument('--readback', required=True, type=Path, help='saved readback JSON')
    parser.add_argument('--receipt', type=Path, help='write the Markdown receipt here')
    parser.add_argument('--check', type=Path,
                        help='compare the receipt with a committed golden file; exit 1 on difference')
    parser.add_argument('--lang', choices=LANGUAGES, default='en', help='receipt language (default en)')
    parser.add_argument('--json', action='store_true', help='print the comparison result as JSON')
    parser.add_argument('--strict', action='store_true', help='exit 3 when the decision is HOLD')
    args = parser.parse_args(argv)

    try:
        plan = load(args.plan)
        readback = load(args.readback)
        result = verify_build(plan, readback)
        receipt = render_receipt(result, args.lang, args.plan.name, args.readback.name)
    except (OSError, ReadbackError) as exc:
        print(f'readback: {exc}', file=sys.stderr)
        return 2

    summary = (f"{result['decision'].upper()} · {result['fields_matched']}/{result['fields']} fields · "
               f"{result['objects_paused']}/{result['objects']} objects paused · 0 platform calls")
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(receipt, encoding='utf-8')
    if args.check:
        try:
            expected = args.check.read_text(encoding='utf-8')
        except OSError as exc:
            print(f'readback: cannot read {args.check}: {exc.strerror}', file=sys.stderr)
            return 2
        if expected != receipt:
            sys.stderr.writelines(difflib.unified_diff(
                expected.splitlines(True), receipt.splitlines(True),
                fromfile=str(args.check), tofile='fresh receipt'))
            print(f'\nreadback: receipt differs from {args.check}; regenerate it with --receipt '
                  'and review the diff', file=sys.stderr)
            return 1
        print(f'{summary} · matches {args.check}')
        return 0
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.receipt:
        print(f'{summary} · receipt written to {args.receipt}')
    else:
        sys.stdout.write(receipt)
    return 3 if args.strict and result['decision'] == 'hold' else 0


if __name__ == '__main__':
    sys.exit(main())
