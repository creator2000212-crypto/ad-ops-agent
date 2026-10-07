#!/usr/bin/env python3
"""Pre-flight linter: check a build checklist before anything is created.

The first half of the build protocol: catch configuration mistakes while they
are still a JSON file. ``readback.py`` covers the second half, after the
objects exist. Offline; no platform call.

    python3 preflight.py --checklist examples/preflight/checklist.json \\
        --policy examples/preflight/policy.json
    python3 preflight.py ... --report out/preflight.md
    python3 preflight.py ... --lang zh-CN --check examples/preflight/expected/checklist.zh-CN.md

Checks (each cell of the matrix is pass, warn or fail):

* name vs bid    -- an ad set named MAX must not carry a cost cap; a cap amount
                    in the name must equal bid_amount.
* name vs budget -- the budget in the name must equal daily_budget.
* HTTPS          -- every destination URL is https.
* URL parameters -- every required parameter is present; any dynamic macro is
                    one the platform documents (the list lives in the policy
                    file with its source, not in this code).
* special category -- when the offer category needs a special ad category,
                    the campaign declares it. This only checks the declaration.
* attribution    -- every ad set in a campaign uses the same attribution
                    setting, so their costs are comparable.
* duplicate creative -- the same file (by SHA-256) is not used twice inside one
                    ad set.

A pass here is not a platform review result and not permission to create.
"""
import argparse
from decimal import Decimal, InvalidOperation
import difflib
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qsl, unquote, urlsplit

PLATFORMS = ('meta', 'tiktok')
LANGUAGES = ('en', 'zh-CN')
STATUSES = ('pass', 'warn', 'fail')
# Column order of the matrix, and the level each check applies to.
CHECKS = (
    ('special_category', 'campaign'),
    ('attribution', 'campaign'),
    ('name_bid', 'adset'),
    ('name_budget', 'adset'),
    ('duplicate_creative', 'adset'),
    ('url_https', 'ad'),
    ('url_params', 'ad'),
)
SHA256 = re.compile(r'^[0-9a-f]{64}$')
BID_TOKEN = re.compile(r'^(?P<prefix>[A-Z]+)(?P<amount>\d+(?:\.\d+)?)?$')

TEXT = {
    'en': {
        'title': 'Pre-flight check — replay, fictional values',
        'meta_line': '{platform} · checklist `{checklist}` · policy `{policy}` (version {version})',
        'scope': ('Runs before anything is created, on the build checklist only. No platform call is '
                  'made; a pass is not a platform review result and not permission to create.'),
        'result': 'Result: {result} — {fail} fail · {warn} warn · {passed} pass',
        'matrix': 'Matrix',
        'columns': ('Level', 'Object', 'Name'),
        'check_labels': {
            'special_category': 'Special category', 'attribution': 'Attribution',
            'name_bid': 'Name ↔ bid', 'name_budget': 'Name ↔ budget',
            'duplicate_creative': 'Duplicate creative', 'url_https': 'HTTPS',
            'url_params': 'URL parameters',
        },
        'cells': {'pass': '✓', 'warn': 'warn', 'fail': '**FAIL**', None: '—'},
        'levels': {'campaign': 'campaign', 'adset': 'ad set', 'ad': 'ad'},
        'findings': 'Findings',
        'colon': ': ',
        'severity': {'warn': 'warn', 'fail': '**fail**'},
        'next': 'Next step',
        'next_fail': ('FAIL: fix the checklist and run this check again. Nothing is created from a '
                      'failing checklist.'),
        'next_warn': ('WARN: a person reviews each warning and either fixes it or records why it is '
                      'acceptable before the build is created PAUSED.'),
        'next_pass': ('PASS: create every object PAUSED, then compare it with `readback.py` before any '
                      'activation.'),
        'codes': {
            'name_unparsed': 'name does not follow the convention ({pattern})',
            'bid_token_unknown': 'bid token {token} is not in the naming convention',
            'bid_token_conflict': 'name says {token} ({expected}) but bid_strategy is {actual}',
            'bid_amount_conflict': 'name says a cap of {expected} but bid_amount is {actual}',
            'budget_token_unparsed': 'budget token {token} is not a {prefix}amount',
            'budget_conflict': 'name says {expected} but daily_budget is {actual}',
            'not_https': 'destination URL is not https: {url}',
            'url_invalid': 'destination URL is not an absolute URL: {url}',
            'param_missing': 'required URL parameter missing: {names}',
            'param_value': '{name} is {actual}, policy expects {expected}',
            'macro_unknown': 'macro not in the documented list for this platform: {names}',
            'category_not_stated': 'offer_category not stated; the declaration cannot be checked',
            'no_category_map': 'no sourced special-ad-category map for this platform; confirm by hand',
            'declaration_missing': 'offer category {category} requires {required} in special_ad_categories',
            'attribution_missing': 'ad set(s) without an attribution setting: {names}',
            'attribution_mixed': 'ad sets use different attribution settings: {settings}',
            'hash_missing': 'creative without a SHA-256 file hash: {names}',
            'duplicate_hash': 'same creative file in one ad set: {names}',
        },
    },
    'zh-CN': {
        'title': '搭建前检查 — 回放，数值均为虚构',
        'meta_line': '{platform} · 清单 `{checklist}` · 规则 `{policy}`（版本 {version}）',
        'scope': '在创建任何对象之前，只检查搭建清单。没有调用平台；通过不代表平台审核结果，也不代表可以创建。',
        'result': '结果：{result} — 不通过 {fail} · 警告 {warn} · 通过 {passed}',
        'matrix': '检查矩阵',
        'columns': ('层级', '对象', '名称'),
        'check_labels': {
            'special_category': '特殊广告类别', 'attribution': '归因一致',
            'name_bid': '名称 ↔ 出价', 'name_budget': '名称 ↔ 预算',
            'duplicate_creative': '重复素材', 'url_https': 'HTTPS', 'url_params': '链接参数',
        },
        'cells': {'pass': '✓', 'warn': '警告', 'fail': '**不通过**', None: '—'},
        'levels': {'campaign': '广告系列', 'adset': '广告组', 'ad': '广告'},
        'findings': '发现',
        'colon': '：',
        'severity': {'warn': '警告', 'fail': '**不通过**'},
        'next': '下一步',
        'next_fail': 'FAIL：修正清单后重新检查。不通过的清单不创建任何对象。',
        'next_warn': 'WARN：由人逐条复核警告，修正或记录可接受的理由后，再以暂停状态创建。',
        'next_pass': 'PASS：以暂停状态创建全部对象，启用前先用 `readback.py` 逐字段回读比对。',
        'codes': {
            'name_unparsed': '名称不符合命名规范（{pattern}）',
            'bid_token_unknown': '出价标记 {token} 不在命名规范中',
            'bid_token_conflict': '名称写 {token}（{expected}），实际 bid_strategy 为 {actual}',
            'bid_amount_conflict': '名称写成本上限 {expected}，实际 bid_amount 为 {actual}',
            'budget_token_unparsed': '预算标记 {token} 不是 {prefix}金额 的格式',
            'budget_conflict': '名称写 {expected}，实际 daily_budget 为 {actual}',
            'not_https': '落地页不是 https：{url}',
            'url_invalid': '落地页不是完整 URL：{url}',
            'param_missing': '缺少必需的链接参数：{names}',
            'param_value': '{name} 为 {actual}，规则要求 {expected}',
            'macro_unknown': '宏不在该平台文档列出的范围内：{names}',
            'category_not_stated': '没有写 offer_category，无法检查声明',
            'no_category_map': '该平台没有带来源的特殊广告类别对照表，需要人工确认',
            'declaration_missing': '产品类别 {category} 需要在 special_ad_categories 中声明 {required}',
            'attribution_missing': '以下广告组没有归因设置：{names}',
            'attribution_mixed': '同一广告系列内的广告组归因设置不一致：{settings}',
            'hash_missing': '以下素材缺少 SHA-256 文件哈希：{names}',
            'duplicate_hash': '同一广告组内重复使用同一素材文件：{names}',
        },
    },
}


class PreflightError(ValueError):
    pass


def load(path):
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise PreflightError(f'not valid JSON: {Path(path).name} ({exc})') from exc


def amount(raw):
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        return None
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate_policy(policy):
    if not isinstance(policy, dict) or policy.get('kind') != 'preflight_policy':
        raise PreflightError('policy kind must be preflight_policy')
    naming = (policy.get('naming') or {}).get('adset')
    if not isinstance(naming, dict) or not naming.get('separator') or not naming.get('tokens'):
        raise PreflightError('policy needs naming.adset.separator and naming.adset.tokens')
    for token in ('bid', 'budget'):
        if token not in naming['tokens']:
            raise PreflightError(f'policy naming.adset.tokens must include {token!r}')
    urls = policy.get('destination_url')
    if not isinstance(urls, dict) or not isinstance(urls.get('platforms'), dict):
        raise PreflightError('policy needs destination_url.platforms')
    for platform, rules in urls['platforms'].items():
        for key in ('required_parameters', 'macro_pattern', 'known_macros', 'source'):
            if key not in rules:
                raise PreflightError(f'policy destination_url.platforms.{platform} needs {key}')
        try:
            re.compile(rules['macro_pattern'])
        except re.error as exc:
            raise PreflightError(f'policy macro_pattern for {platform} is not a regex: {exc}') from exc
    return policy


def validate_checklist(checklist):
    if not isinstance(checklist, dict) or checklist.get('kind') != 'build_checklist':
        raise PreflightError('checklist kind must be build_checklist')
    if checklist.get('platform') not in PLATFORMS:
        raise PreflightError(f'checklist platform must be one of {list(PLATFORMS)}')
    campaigns = checklist.get('campaigns')
    if not isinstance(campaigns, list) or not campaigns:
        raise PreflightError('checklist needs a non-empty campaigns list')
    seen = set()

    def key_of(item, field, what):
        key = item.get(field) if isinstance(item, dict) else None
        if not isinstance(key, str) or not key:
            raise PreflightError(f'every {what} needs {field}')
        if key in seen:
            raise PreflightError(f'duplicate key {key!r}')
        seen.add(key)
        return key

    for campaign in campaigns:
        key_of(campaign, 'campaign_key', 'campaign')
        if not isinstance(campaign.get('adsets'), list) or not campaign['adsets']:
            raise PreflightError(f"campaign {campaign['campaign_key']!r} needs adsets")
        for adset in campaign['adsets']:
            key = key_of(adset, 'adset_key', 'ad set')
            for field in ('name', 'bid_strategy'):
                if not isinstance(adset.get(field), str) or not adset[field]:
                    raise PreflightError(f'ad set {key!r} needs {field}')
            if adset.get('daily_budget') in (None, ''):
                raise PreflightError(f'ad set {key!r} needs daily_budget')
            if not isinstance(adset.get('ads'), list) or not adset['ads']:
                raise PreflightError(f'ad set {key!r} needs ads')
            for ad in adset['ads']:
                ad_key = key_of(ad, 'ad_key', 'ad')
                if not isinstance(ad.get('destination_url'), str):
                    raise PreflightError(f'ad {ad_key!r} needs destination_url')
    return checklist


# --------------------------------------------------------------------------
# checks: each returns a list of (status, code, detail)
# --------------------------------------------------------------------------

def check_special_category(campaign, platform, policy):
    table = (policy.get('special_ad_categories') or {}).get(platform)
    if not table:
        return [('warn', 'no_category_map', {})]
    category = campaign.get('offer_category')
    if not category:
        return [('warn', 'category_not_stated', {})]
    required = (table.get('offer_categories') or {}).get(category)
    declared = campaign.get('special_ad_categories') or []
    if required and required not in declared:
        return [('fail', 'declaration_missing', {'category': category, 'required': required})]
    return []


def attribution_text(value):
    return f"click {value.get('click_days')}d, view {value.get('view_days')}d"


def check_attribution(campaign):
    missing, settings = [], {}
    for adset in campaign['adsets']:
        value = adset.get('attribution')
        if not isinstance(value, dict):
            missing.append(adset['adset_key'])
            continue
        settings.setdefault(attribution_text(value), []).append(adset['adset_key'])
    found = []
    if len(settings) > 1:
        described = '; '.join(f"{text} ({', '.join(keys)})" for text, keys in sorted(settings.items()))
        found.append(('fail', 'attribution_mixed', {'settings': described}))
    if missing:
        found.append(('warn', 'attribution_missing', {'names': ', '.join(missing)}))
    return found


def name_tokens(adset, naming):
    parts = [part.strip() for part in adset['name'].split(naming['separator'].strip())]
    if len(parts) != len(naming['tokens']) or not all(parts):
        return None
    return dict(zip(naming['tokens'], parts))


def check_name_bid(adset, tokens, naming, platform):
    if tokens is None:
        return [('warn', 'name_unparsed', {'pattern': naming['separator'].join(naming['tokens'])})]
    token = tokens['bid']
    match = BID_TOKEN.match(token)
    strategies = (naming.get('bid_tokens') or {}).get(platform) or {}
    if not match or match.group('prefix') not in strategies:
        return [('warn', 'bid_token_unknown', {'token': token})]
    expected = strategies[match.group('prefix')]
    found = []
    if adset['bid_strategy'] != expected:
        found.append(('fail', 'bid_token_conflict',
                      {'token': token, 'expected': expected, 'actual': adset['bid_strategy']}))
    if match.group('amount') is not None:
        actual = amount(adset.get('bid_amount'))
        if actual is None or actual != Decimal(match.group('amount')):
            found.append(('fail', 'bid_amount_conflict',
                          {'expected': match.group('amount'), 'actual': adset.get('bid_amount')}))
    return found


def check_name_budget(adset, tokens, naming):
    if tokens is None:
        return [('warn', 'name_unparsed', {'pattern': naming['separator'].join(naming['tokens'])})]
    token, prefix = tokens['budget'], naming.get('budget_prefix', '')
    named = amount(token[len(prefix):]) if token.startswith(prefix) else None
    if named is None:
        return [('warn', 'budget_token_unparsed', {'token': token, 'prefix': prefix})]
    actual = amount(adset['daily_budget'])
    if actual is None or actual != named:
        return [('fail', 'budget_conflict', {'expected': token, 'actual': adset['daily_budget']})]
    return []


def check_duplicate_creative(adset):
    by_hash, missing = {}, []
    for ad in adset['ads']:
        digest = (ad.get('creative') or {}).get('sha256')
        if not isinstance(digest, str) or not SHA256.match(digest):
            missing.append(ad['ad_key'])
            continue
        by_hash.setdefault(digest, []).append(ad['ad_key'])
    found = []
    duplicates = [keys for keys in by_hash.values() if len(keys) > 1]
    if duplicates:
        found.append(('fail', 'duplicate_hash',
                      {'names': '; '.join(' = '.join(keys) for keys in duplicates)}))
    if missing:
        found.append(('warn', 'hash_missing', {'names': ', '.join(missing)}))
    return found


def check_url_https(ad):
    parts = urlsplit(ad['destination_url'])
    if not parts.scheme or not parts.netloc:
        return [('fail', 'url_invalid', {'url': ad['destination_url']})]
    if parts.scheme.lower() != 'https':
        return [('fail', 'not_https', {'url': ad['destination_url']})]
    return []


def check_url_params(ad, rules):
    raw_tags = ad.get('url_parameters') or ''
    pairs = parse_qsl(urlsplit(ad['destination_url']).query, keep_blank_values=True)
    pairs += parse_qsl(raw_tags, keep_blank_values=True)
    present = {}
    for key, value in pairs:
        present.setdefault(key, value)
    found = []
    required = rules['required_parameters']
    missing = [name for name in required if not present.get(name)]
    if missing:
        found.append(('fail', 'param_missing', {'names': ', '.join(missing)}))
    macros = re.findall(rules['macro_pattern'], unquote(ad['destination_url'] + '&' + raw_tags))
    unknown = sorted(set(macro for macro in macros if macro not in rules['known_macros']))
    if unknown:
        found.append(('fail', 'macro_unknown', {'names': ', '.join(unknown)}))
    for name, expected in required.items():
        if expected is not None and present.get(name) and present[name] != expected:
            found.append(('warn', 'param_value',
                          {'name': name, 'actual': present[name], 'expected': expected}))
    return found


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------

def worst(found):
    statuses = [status for status, _, _ in found]
    return 'fail' if 'fail' in statuses else 'warn' if 'warn' in statuses else 'pass'


def lint(checklist, policy):
    """Lint a build checklist and return ``{result, counts, rows, findings}``."""
    validate_policy(policy)
    validate_checklist(checklist)
    platform = checklist['platform']
    naming = policy['naming']['adset']
    url_rules = policy['destination_url']['platforms'].get(platform)
    if url_rules is None:
        raise PreflightError(f'policy has no destination_url rules for {platform}')

    rows, findings = [], []

    def record(level, key, name, results):
        cells = {check: None for check, _ in CHECKS}
        for check, found in results:
            cells[check] = worst(found)
            for status, code, detail in found:
                findings.append({'status': status, 'level': level, 'object_key': key,
                                 'check': check, 'code': code, 'detail': detail})
        rows.append({'level': level, 'object_key': key, 'name': name, 'cells': cells})

    for campaign in checklist['campaigns']:
        record('campaign', campaign['campaign_key'], campaign.get('name', ''), [
            ('special_category', check_special_category(campaign, platform, policy)),
            ('attribution', check_attribution(campaign)),
        ])
        for adset in campaign['adsets']:
            tokens = name_tokens(adset, naming)
            record('adset', adset['adset_key'], adset['name'], [
                ('name_bid', check_name_bid(adset, tokens, naming, platform)),
                ('name_budget', check_name_budget(adset, tokens, naming)),
                ('duplicate_creative', check_duplicate_creative(adset)),
            ])
            for ad in adset['ads']:
                record('ad', ad['ad_key'], ad.get('name', ''), [
                    ('url_https', check_url_https(ad)),
                    ('url_params', check_url_params(ad, url_rules)),
                ])

    counts = {status: 0 for status in STATUSES}
    for row in rows:
        for status in row['cells'].values():
            if status:
                counts[status] += 1
    result = 'fail' if counts['fail'] else 'warn' if counts['warn'] else 'pass'
    return {'platform': platform, 'policy_version': policy.get('version'), 'result': result,
            'counts': counts, 'rows': rows, 'findings': findings, 'native_platform_calls': 0}


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def cell(value):
    return '`' + str(value).replace('|', '\\|') + '`'


def code(value):
    return '`' + str(value) + '`'


def render_report(result, lang='en', checklist_name='checklist.json', policy_name='policy.json'):
    if lang not in TEXT:
        raise PreflightError(f'language must be one of {list(LANGUAGES)}')
    text = TEXT[lang]
    platform = {'meta': 'Meta', 'tiktok': 'TikTok'}[result['platform']]
    counts = result['counts']
    labels = [text['check_labels'][check] for check, _ in CHECKS]
    lines = [
        f"# {text['title']}", '',
        text['meta_line'].format(platform=platform, checklist=checklist_name, policy=policy_name,
                                 version=result['policy_version'] or '—'),
        '', f"> {text['scope']}", '',
        '**' + text['result'].format(result=result['result'].upper(), fail=counts['fail'],
                                     warn=counts['warn'], passed=counts['pass']) + '**',
        '', f"## {text['matrix']}", '',
        '| ' + ' | '.join(list(text['columns']) + labels) + ' |',
        '|---|---|---|' + ':---:|' * len(labels),
    ]
    for row in result['rows']:
        name = cell(row['name']) if row['name'] else '—'
        cells = [text['cells'][row['cells'][check]] for check, _ in CHECKS]
        lines.append(f"| {text['levels'][row['level']]} | {cell(row['object_key'])} | {name} | "
                     + ' | '.join(cells) + ' |')
    if result['findings']:
        lines += ['', f"## {text['findings']}", '']
        order = {'fail': 0, 'warn': 1}
        for item in sorted(result['findings'], key=lambda entry: order[entry['status']]):
            detail = {key: value if key == 'settings' else code(value)
                      for key, value in item['detail'].items()}
            message = text['codes'][item['code']].format(**detail)
            lines.append(f"- {text['severity'][item['status']]} · {cell(item['object_key'])} · "
                         f"{text['check_labels'][item['check']]}{text['colon']}{message}")
    lines += ['', f"## {text['next']}", '', text['next_' + result['result']], '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--checklist', required=True, type=Path, help='build checklist JSON')
    parser.add_argument('--policy', required=True, type=Path, help='pre-flight policy JSON')
    parser.add_argument('--report', type=Path, help='write the Markdown report here')
    parser.add_argument('--check', type=Path,
                        help='compare the report with a committed golden file; exit 1 on difference')
    parser.add_argument('--lang', choices=LANGUAGES, default='en', help='report language (default en)')
    parser.add_argument('--json', action='store_true', help='print the lint result as JSON')
    parser.add_argument('--strict', action='store_true', help='exit 3 when the result is fail')
    args = parser.parse_args(argv)

    try:
        result = lint(load(args.checklist), load(args.policy))
        report = render_report(result, args.lang, args.checklist.name, args.policy.name)
    except (OSError, PreflightError) as exc:
        print(f'preflight: {exc}', file=sys.stderr)
        return 2

    counts = result['counts']
    summary = (f"{result['result'].upper()} · {counts['fail']} fail · {counts['warn']} warn · "
               f"{counts['pass']} pass · 0 platform calls")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding='utf-8')
    if args.check:
        try:
            expected = args.check.read_text(encoding='utf-8')
        except OSError as exc:
            print(f'preflight: cannot read {args.check}: {exc.strerror}', file=sys.stderr)
            return 2
        if expected != report:
            sys.stderr.writelines(difflib.unified_diff(
                expected.splitlines(True), report.splitlines(True),
                fromfile=str(args.check), tofile='fresh report'))
            print(f'\npreflight: report differs from {args.check}; regenerate it with --report '
                  'and review the diff', file=sys.stderr)
            return 1
        print(f'{summary} · matches {args.check}')
        return 0
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.report:
        print(f'{summary} · report written to {args.report}')
    else:
        sys.stdout.write(report)
    return 3 if args.strict and result['result'] == 'fail' else 0


if __name__ == '__main__':
    sys.exit(main())
