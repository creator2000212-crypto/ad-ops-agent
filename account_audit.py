#!/usr/bin/env python3
"""Account audit: the checks the October 2026 incidents added, on a saved read.

Runs before a round's decisions and before any write, on a saved read of the
accounts, their change log and the write requests the round wants to send.
Offline; no platform call. ``preflight.py`` checks a build before it exists and
``readback.py`` checks it after; this module checks the accounts that are
already running and the changes about to be made to them.

    python3 account_audit.py --snapshot examples/audit/snapshot.json \\
        --policy examples/audit/policy.json
    python3 account_audit.py ... --report out/audit.md
    python3 account_audit.py ... --lang zh-CN --check examples/audit/expected/audit.zh-CN.md

Account findings (P0 to P2):

* account state    -- a disabled account takes no writes; its requests wait.
* live definition  -- an ad set is live only when its account, campaign, ad set
                      and at least one ad are active. An active ad set without
                      an active ad holds budget it cannot spend.
* budget canary    -- a daily budget at or above the P0 line, or a live one above
                      the P1 line that spent nothing over the last full days or is
                      more than the policy multiple of its average spend over them.
* name vs budget   -- a budget written in a name that no longer matches the
                      field. Names are labels, not facts.
* offer link       -- the offer an ad set's name declares must be the offer its
                      ads' destination links carry.
* writers          -- each change in the log is attributed to its writer; changes
                      by a writer outside the owner's list are not the round's
                      baseline.
* full day         -- a live ad set's current budget has a full day behind it
                      only when it took effect at or before 00:00 of the previous
                      day in the account's named time zone. A log that does not
                      reach back far enough gives "unknown", not "yes".
* duplicate activation -- a paused ad set that would run the same offer and
                      creative as a live ad set in the same account.

Write requests (allow, refuse or wait):

* money has a unit   -- a money value without an explicit ``minor`` or ``major``
                        unit is refused.
* ceiling and raise  -- a raise to a budget at or above the hard ceiling is
                        refused; a raise beyond the ratio is refused unless it
                        carries a reason.
* intraday cut       -- a cut to or below today's spend so far waits for the
                        account's next day, unless it rolls back a budget at or
                        above the ceiling; a cut with no reading of today's spend
                        waits too.
* locked fields      -- fields the platform fixes at creation are refused: build
                        a new object instead.
* whole-object fields -- a field the platform replaces as a whole must carry every
                        key it has now, or the missing keys would be cleared.
* human pause        -- resuming an object a person paused is the owner's call;
                        a pause the log does not explain waits.
* disabled account   -- every request to it waits.

"allow" means a request passed these checks. It is not an approval: it still
goes through the write gate and needs the owner's approval of the batch.
"""
import argparse
from datetime import datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
import difflib
import json
from pathlib import Path
import re
import sys

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python 3.9+ ships zoneinfo
    ZoneInfo = None
    ZoneInfoNotFoundError = KeyError

LANGUAGES = ('en', 'zh-CN')
LEVELS = ('P0', 'P1', 'P2')
DECISIONS = ('allow', 'refuse', 'wait')
ACTIVE, PAUSED = 'ACTIVE', 'PAUSED'
UNITS = ('minor', 'major')
NOTICE = ('Offline account audit on a saved read. No platform call was made. "allow" is not an approval: '
          'the write gate and the owner\'s approval of the batch still apply.')

# Severity of each finding code; the lines that trigger them come from the policy.
SEVERITY = {
    'ACCOUNT_DISABLED': 'P0',
    'BUDGET_CANARY': 'P0',
    'BUDGET_NO_SPEND': 'P1',
    'BUDGET_FAR_ABOVE_SPEND': 'P1',
    'OFFER_LINK_MISMATCH': 'P1',
    'EXTERNAL_WRITER': 'P1',
    'DUPLICATE_ACTIVATION': 'P1',
    'SHELL_ADSET': 'P2',
    'NAME_BUDGET_STALE': 'P2',
    'OFFER_LINK_UNREADABLE': 'P2',
    'OFFER_NOT_DECLARED': 'P2',
}

TEXT = {
    'en': {
        'title': 'Account audit — replay, fictional values',
        'meta_line': '{platform} · snapshot `{snapshot}` read {as_of} · policy `{policy}` (version {version})',
        'scope': ('Runs on a saved read of the accounts, their change log and the write requests, before a '
                  "round's decisions and before any write. No platform call is made. \"allow\" means a request "
                  'passed these checks, not that anyone approved it: it still goes through the write gate and '
                  "needs the owner's approval of the batch."),
        'result': 'Result: {p0} P0 · {p1} P1 · {p2} P2 · write requests: {allow} allow · {refuse} refuse · {wait} wait',
        'accounts': 'Accounts',
        'account_columns': ('Account', 'Status', 'Time zone', 'Local time at read', 'Live / active ad sets',
                            'Live daily budget', 'Full day needs a budget set by', 'Change log from'),
        'findings': 'Findings',
        'no_findings': 'No findings.',
        'writers': 'Who changed what (last {hours} h)',
        'writer_columns': ('Account', 'Writer', 'Role', 'Changes', 'Budget changes', 'Net budget change per object'),
        'no_writers': 'No changes in the window.',
        'roles': {'human': 'owner (human)', 'agent': 'owner (agent)', None: '**outside the owner list**'},
        'tiers': 'Budget tiers of live ad sets',
        'tier_columns': ('Ad set', 'Account', 'Daily budget', 'Current budget since (local)',
                         'Full day at this budget?', 'Changed by an outside writer?'),
        'full_day': {'yes': 'yes', 'no': '**no**', 'unknown': 'unknown'},
        'bounded': 'at or before {when}',
        'log_mismatch': ' (log ends at {value}, not the field\'s value)',
        'unknown_share': 'an unknown share',
        'yes_no': {True: '**yes**', False: 'no'},
        'requests': 'Write requests',
        'request_columns': ('Request', 'Object', 'Field', 'Requested', 'Decision', 'Why'),
        'decisions': {'allow': 'allow', 'refuse': '**refuse**', 'wait': 'wait'},
        'no_requests': 'No write requests.',
        'next': 'Next step',
        'next_text': ('P0 findings first, then P1, before the round decides anything. Refused requests are not sent. '
                      'Waiting requests are checked again once their condition clears. Allowed requests go '
                      "through the write gate against the state read just before writing, and only into a batch "
                      'the owner approved.'),
        'separator': '; ',
        'codes': {
            'ACCOUNT_DISABLED': ('account status is {status}: no write is sent to it; requests wait and the state '
                                 'is read again on reinstatement before anything else'),
            'BUDGET_CANARY': 'daily budget {budget} is at or above the P0 line of {line}',
            'BUDGET_NO_SPEND': ('daily budget {budget} is above {line} and the last {days} full days spent nothing'),
            'BUDGET_FAR_ABOVE_SPEND': ('daily budget {budget} is {multiple}× the average spend of the last {days} '
                                       'full days ({average}); limit is {limit}×'),
            'SHELL_ADSET': ('active ad set with no active ad: not live, and its {budget} daily budget is not '
                            'delivery capacity'),
            'NAME_BUDGET_STALE': 'name says {named} but daily_budget is {budget}; the field is the fact',
            'OFFER_LINK_MISMATCH': ('name declares {declared} but the destination links carry {linked}; '
                                    '{share} of the account\'s spend on {day}; judge it against the linked '
                                    "offer's T, not the name's"),
            'OFFER_LINK_UNREADABLE': 'no offer code found in any active destination link; the offer is unverified',
            'OFFER_NOT_DECLARED': 'name declares no offer; destination links carry {linked}',
            'EXTERNAL_WRITER': ('{writer} is not in the owner list and made {changes} change(s), {budget_changes} '
                                'to budgets, on {objects}; its values are not this round\'s baseline and the '
                                'affected budgets restart their full day'),
            'DUPLICATE_ACTIVATION': ('paused {paused} repeat the offer and creative of live {live}; activating them '
                                     'as they are raises the live daily budget from {before} to {after} and runs '
                                     'the same creative twice'),
        },
        'request_codes': {
            'OK': 'passed the checks',
            'NO_RULE': 'no audit rule for this field; the write gate still applies',
            'UNKNOWN_OBJECT': 'object not in the snapshot; read it first',
            'ACCOUNT_MISMATCH': 'the request names account {named}, but the object belongs to {actual}',
            'ACCOUNT_DISABLED': 'account status is {status}; wait for reinstatement and read state again',
            'LOCKED_FIELD': '{field} is fixed when the object is created; build a new {level} instead',
            'CURRENT_UNKNOWN': 'the current {field} is not in the snapshot; read it before replacing it',
            'PARTIAL_REPLACE': ('{field} is replaced as a whole; this value would clear {missing}. Send the full '
                                'current value with the change'),
            'UNIT_MISSING': 'money value without a unit (minor or major); refused, not guessed',
            'INVALID_REQUEST': 'malformed request: {problem}',
            'RUNAWAY_CUT': '{current} → {target}: rolling back a budget at or above {line} is not held for tomorrow',
            'SPEND_UNKNOWN': 'a cut to {target} with no reading of today\'s spend; read it first',
            'PAUSE_UNATTRIBUTED': ('the change log does not show a pause by the owner (last writer: {writer}); ask '
                                   'the owner before resuming'),
            'UNIT_INVALID': 'value {value} is not a whole number of {unit} units',
            'ABOVE_CEILING': 'a raise to {target} is at or above the hard ceiling of {ceiling}',
            'RAISE_TOO_LARGE': '{current} → {target} is ×{ratio}; above ×{limit} needs a stated reason',
            'RAISE_OVERRIDE': '{current} → {target} is ×{ratio}, above ×{limit}; allowed on the stated reason: {reason}',
            'INTRADAY_CUT': ('{target} is at or below today\'s spend so far ({spent}); the ad set would stop for the '
                             'rest of the day. Wait until {when} (account time)'),
            'BUDGET_OK': '{current} → {target} (×{ratio})',
            'RESUME_HUMAN_PAUSE': ('{writer} paused this object at {when}; resuming it is the owner\'s decision, '
                                   'not the round\'s'),
        },
    },
    'zh-CN': {
        'title': '账户审计 — 回放，数值均为虚构',
        'meta_line': '{platform} · 快照 `{snapshot}` 读取于 {as_of} · 规则 `{policy}`（版本 {version}）',
        'scope': ('在一轮判定之前、任何写入之前，对已保存的账户读数、变更流水和写入请求做检查。没有调用平台。'
                  '“放行”只表示请求通过了这些检查，不代表有人批准：它仍要经过写前闸门，并且只能进入用户批准的批次。'),
        'result': '结果：P0 {p0} · P1 {p1} · P2 {p2} · 写入请求：放行 {allow} · 拒绝 {refuse} · 等待 {wait}',
        'accounts': '账户',
        'account_columns': ('账户', '状态', '时区', '读取时的当地时间', '在投 / 开启的广告组', '在投日预算',
                            '满一天要求预算生效不晚于', '流水起点'),
        'findings': '发现',
        'no_findings': '没有发现。',
        'writers': '谁改了什么（近 {hours} 小时）',
        'writer_columns': ('账户', '写入方', '身份', '变更次数', '预算变更', '各对象预算净变化'),
        'no_writers': '窗口内没有变更。',
        'roles': {'human': '本人（手动）', 'agent': '本人（Agent）', None: '**不在本人名单内**'},
        'tiers': '在投广告组的预算档',
        'tier_columns': ('广告组', '账户', '日预算', '当前预算生效于（当地）', '本档是否已满一天', '是否被外部写入方改过'),
        'full_day': {'yes': '是', 'no': '**否**', 'unknown': '未知'},
        'bounded': '不晚于 {when}',
        'log_mismatch': '（流水最后的值是 {value}，与字段不一致）',
        'unknown_share': '未知比例',
        'yes_no': {True: '**是**', False: '否'},
        'requests': '写入请求',
        'request_columns': ('请求', '对象', '字段', '请求值', '结论', '原因'),
        'decisions': {'allow': '放行', 'refuse': '**拒绝**', 'wait': '等待'},
        'no_requests': '没有写入请求。',
        'next': '下一步',
        'next_text': ('先处理 P0，再处理 P1，然后才做本轮判定。被拒绝的请求不发送；等待中的请求在条件解除后重新检查；'
                      '放行的请求还要对照写入前一刻的读数过写前闸门，并且只能进入用户批准的批次。'),
        'separator': '；',
        'codes': {
            'ACCOUNT_DISABLED': '账户状态为 {status}：不向它发送任何写入；请求进入等待，恢复后第一件事是重新读取状态',
            'BUDGET_CANARY': '日预算 {budget} 达到或超过 P0 线 {line}',
            'BUDGET_NO_SPEND': '日预算 {budget} 高于 {line}，且最近 {days} 个完整日花费为零',
            'BUDGET_FAR_ABOVE_SPEND': '日预算 {budget} 是最近 {days} 个完整日平均花费（{average}）的 {multiple} 倍，上限 {limit} 倍',
            'SHELL_ADSET': '广告组已开启，但下面没有开启的广告：不算在投，它的日预算 {budget} 不是投放产能',
            'NAME_BUDGET_STALE': '名称写 {named}，实际 daily_budget 为 {budget}；以字段为准',
            'OFFER_LINK_MISMATCH': ('名称写的是 {declared}，落地链接实际是 {linked}；占该账户 {day} 花费的 {share}；'
                                    '要按链接对应 offer 的 T 判定，而不是名称里的'),
            'OFFER_LINK_UNREADABLE': '在投广告的落地链接里找不到 offer 代码；offer 未经核实',
            'OFFER_NOT_DECLARED': '名称里没有写 offer；落地链接是 {linked}',
            'EXTERNAL_WRITER': ('{writer} 不在本人名单内，改了 {changes} 次（其中预算 {budget_changes} 次），涉及 {objects}；'
                                '它写入的值不是本轮基线，受影响的预算档重新计算满日'),
            'DUPLICATE_ACTIVATION': ('暂停中的 {paused} 与在投的 {live} 是同一 offer、同一素材；原样激活会让在投日预算从 '
                                     '{before} 变成 {after}，同一素材双投'),
        },
        'request_codes': {
            'OK': '通过检查',
            'NO_RULE': '该字段没有审计规则；仍要经过写前闸门',
            'UNKNOWN_OBJECT': '快照里没有这个对象；先读取',
            'ACCOUNT_MISMATCH': '请求写的是账户 {named}，但对象属于 {actual}',
            'ACCOUNT_DISABLED': '账户状态为 {status}；等待恢复后重新读取状态',
            'LOCKED_FIELD': '{field} 在创建时就固定；需要新建{level}',
            'CURRENT_UNKNOWN': '快照里没有当前的 {field}；替换之前先读取',
            'PARTIAL_REPLACE': '{field} 会被整体替换；这个值会清掉 {missing}。请把当前完整值连同改动一起发送',
            'UNIT_MISSING': '金额没有写单位（minor 或 major）；拒绝，不猜',
            'INVALID_REQUEST': '请求格式有误：{problem}',
            'RUNAWAY_CUT': '{current} → {target}：回滚达到或超过 {line} 的预算，不等到次日',
            'SPEND_UNKNOWN': '降到 {target}，但读数里没有今日已花；先读取',
            'PAUSE_UNATTRIBUTED': '变更流水里看不到本人做的暂停（最后写入方：{writer}）；恢复前先问用户',
            'UNIT_INVALID': '{value} 不是整数个 {unit} 单位',
            'ABOVE_CEILING': '加到 {target}，达到或超过硬上限 {ceiling}',
            'RAISE_TOO_LARGE': '{current} → {target} 是 {ratio} 倍；超过 {limit} 倍必须写明理由',
            'RAISE_OVERRIDE': '{current} → {target} 是 {ratio} 倍，超过 {limit} 倍；按写明的理由放行：{reason}',
            'INTRADAY_CUT': '{target} 不高于今日已花 {spent}；广告组当天剩余时段会停投。等到 {when}（账户时间）再改',
            'BUDGET_OK': '{current} → {target}（{ratio} 倍）',
            'RESUME_HUMAN_PAUSE': '{writer} 于 {when} 手动暂停了这个对象；是否恢复由用户决定，不由本轮决定',
        },
    },
}
LEVEL_NAMES = {'en': {'campaign': 'campaign', 'adset': 'ad set', 'ad': 'ad'},
               'zh-CN': {'campaign': '广告系列', 'adset': '广告组', 'ad': '广告'}}


class AuditError(ValueError):
    pass


UNKNOWN_SHARE = 'unknown'


def load(path):
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise AuditError(f'not valid JSON: {Path(path).name} ({exc})') from exc


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


# --------------------------------------------------------------------------
# values
# --------------------------------------------------------------------------

def decimal_of(raw, label):
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        raise AuditError(f'{label} must be a number written as an integer or a string')
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation as exc:
        raise AuditError(f'{label} is not a number: {raw!r}') from exc
    if not value.is_finite():
        raise AuditError(f'{label} is not a finite number')
    return value


def minor_of(raw, label):
    value = decimal_of(raw, label)
    if value != value.to_integral_value() or value < 0:
        raise AuditError(f'{label} must be a whole, non-negative number of minor units')
    return int(value)


OFFSET_WITHOUT_COLON = re.compile(r'([+-]\d{2})(\d{2})$')
FRACTION = re.compile(r'\.(\d+)(?=[+-]\d{2}:\d{2}$|$)')


def iso_text(raw):
    """Normalize the ISO 8601 shapes platforms return so Python 3.9 and 3.13 parse them alike."""
    text = raw.strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    text = OFFSET_WITHOUT_COLON.sub(r'\1:\2', text)
    return FRACTION.sub(lambda match: '.' + (match.group(1) + '000000')[:6], text)


def parse_time(raw, label):
    if not isinstance(raw, str) or not raw:
        raise AuditError(f'{label} must be an ISO 8601 time with an offset')
    text = iso_text(raw)
    try:
        value = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AuditError(f'{label} is not an ISO 8601 time: {raw!r}') from exc
    if value.tzinfo is None:
        raise AuditError(f'{label} needs a UTC offset: {raw!r}')
    return value.astimezone(timezone.utc)


def zone_of(name, label):
    if ZoneInfo is None:  # pragma: no cover
        raise AuditError('this Python has no zoneinfo module; Python 3.9 or newer is required')
    if not isinstance(name, str) or not name:
        raise AuditError(f'{label} must be an IANA time zone name such as Atlantic/Azores')
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise AuditError(f'{label}: unknown time zone {name!r} (install the tzdata package if this '
                         'system has no time zone database)') from exc


def local_midnight(day, zone):
    """00:00 of a local calendar day, as a UTC time; daylight-saving aware."""
    return datetime.combine(day, time(0), tzinfo=zone).astimezone(timezone.utc)


class Money:
    """Formats minor units for one currency."""

    def __init__(self, currency, exponent):
        self.currency = currency
        self.exponent = exponent
        self.step = Decimal(1).scaleb(-exponent)

    def major(self, minor):
        return (Decimal(minor) * self.step).quantize(self.step)

    def text(self, minor):
        amount = f'{self.major(minor):,}'
        return f'${amount}' if self.currency == 'USD' else f'{amount} {self.currency}'

    def to_minor(self, raw, unit, label):
        value = decimal_of(raw, label)
        scaled = value if unit == 'minor' else value.scaleb(self.exponent)
        if scaled != scaled.to_integral_value() or scaled < 0:
            return None
        return int(scaled)


def ratio_text(value):
    """One decimal when exact, otherwise two, so 2.05 never prints as the limit 2.0."""
    one = value.quantize(Decimal('0.1'))
    if one == value:
        return str(one)
    return str(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def pct_text(value):
    sign = '+' if value > 0 else '−' if value < 0 else ''
    return f'{sign}{abs(value).quantize(Decimal("0.1"))}%'


def share_text(value):
    return f'{value.quantize(Decimal("0.1"))}%'


def local_text(moment, zone):
    return moment.astimezone(zone).strftime('%Y-%m-%d %H:%M')


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate_policy(policy):
    if not isinstance(policy, dict) or policy.get('kind') != 'account_audit_policy':
        raise AuditError('policy kind must be account_audit_policy')
    for key in ('currency_exponent', 'budget_canary', 'budget_writes', 'offer_link', 'writers', 'fields'):
        if key not in policy:
            raise AuditError(f'policy needs {key}')
    canary = policy['budget_canary']
    for key in ('p0_daily_budget', 'p1_daily_budget', 'full_days', 'p1_multiple_of_average'):
        if key not in canary:
            raise AuditError(f'policy budget_canary needs {key}')
    writes = policy['budget_writes']
    for key in ('fields', 'ceiling_daily_budget', 'max_raise_ratio'):
        if key not in writes:
            raise AuditError(f'policy budget_writes needs {key}')
    if not isinstance(policy['offer_link'], dict):
        raise AuditError('policy offer_link must be an object')
    for key in ('destination_pattern', 'name_pattern'):
        pattern = policy['offer_link'].get(key)
        try:
            compiled = re.compile(pattern or '')
        except re.error as exc:
            raise AuditError(f'policy offer_link.{key} is not a regex: {exc}') from exc
        if 'offer' not in compiled.groupindex:
            raise AuditError(f'policy offer_link.{key} needs a named group (?P<offer>...)')
    naming = policy.get('name_budget_pattern')
    if naming is not None:
        try:
            if 'amount' not in re.compile(naming).groupindex:
                raise AuditError('policy name_budget_pattern needs a named group (?P<amount>...)')
        except re.error as exc:
            raise AuditError(f'policy name_budget_pattern is not a regex: {exc}') from exc
    writers = policy['writers']
    if not isinstance(writers, dict) or not isinstance(writers.get('own'), dict) or 'window_hours' not in writers:
        raise AuditError('policy writers needs own (writer -> human|agent) and window_hours')
    for label, value in (('writers.window_hours', writers['window_hours']),
                         ('budget_canary.full_days', canary['full_days'])):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise AuditError(f'policy {label} must be a whole number of at least 1')
    if not isinstance(policy['fields'], dict):
        raise AuditError('policy fields must be an object keyed by platform')
    for writer, role in writers['own'].items():
        if role not in ('human', 'agent'):
            raise AuditError(f'policy writers.own.{writer} must be human or agent')
    return policy


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('kind') != 'account_audit_snapshot':
        raise AuditError('snapshot kind must be account_audit_snapshot')
    accounts = snapshot.get('accounts')
    if not isinstance(accounts, list) or not accounts:
        # Missing is not zero: an empty read is a failed read, not a healthy one.
        raise AuditError('snapshot has no accounts: treat the read as failed, not as healthy')
    if not isinstance(snapshot.get('activity', []), list):
        raise AuditError('snapshot activity must be a list')
    if not isinstance(snapshot.get('write_requests', []), list):
        raise AuditError('snapshot write_requests must be a list')
    seen = set()

    def key_of(item, field, what):
        key = item.get(field) if isinstance(item, dict) else None
        if not isinstance(key, str) or not key:
            raise AuditError(f'every {what} needs {field}')
        if key in seen:
            raise AuditError(f'duplicate key {key!r}')
        seen.add(key)
        return key

    for account in accounts:
        key = key_of(account, 'account_key', 'account')
        for field in ('status', 'timezone_name', 'activity_since'):
            if field not in account:
                raise AuditError(f'account {key!r} needs {field}')
        if not isinstance(account.get('campaigns'), list):
            raise AuditError(f'account {key!r} needs a campaigns list')
        for campaign in account['campaigns']:
            ckey = key_of(campaign, 'campaign_key', 'campaign')
            if not isinstance(campaign.get('adsets'), list):
                raise AuditError(f'campaign {ckey!r} needs an adsets list')
            for adset in campaign['adsets']:
                akey = key_of(adset, 'adset_key', 'ad set')
                for field in ('name', 'status', 'daily_budget_minor', 'created_at'):
                    if field not in adset:
                        raise AuditError(f'ad set {akey!r} needs {field}')
                if not isinstance(adset.get('ads'), list):
                    raise AuditError(f'ad set {akey!r} needs an ads list')
                for ad in adset['ads']:
                    key_of(ad, 'ad_key', 'ad')
    return snapshot


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

class Account:
    def __init__(self, raw, as_of):
        self.raw = raw
        self.key = raw['account_key']
        self.status = raw['status']
        self.active = raw['status'] == ACTIVE
        self.zone = zone_of(raw['timezone_name'], f'account {self.key!r} timezone_name')
        self.zone_name = raw['timezone_name']
        self.activity_since = parse_time(raw['activity_since'], f'account {self.key!r} activity_since')
        self.local_now = as_of.astimezone(self.zone)
        self.today = self.local_now.date()
        self.yesterday = self.today - timedelta(days=1)
        self.yesterday_start = local_midnight(self.yesterday, self.zone)
        self.tomorrow_start = local_midnight(self.today + timedelta(days=1), self.zone)
        self.adsets = []
        self.campaigns = {}


def build_model(snapshot):
    as_of = parse_time(snapshot.get('as_of'), 'snapshot as_of')
    accounts, adsets, campaigns, ads = [], {}, {}, {}
    for raw in snapshot['accounts']:
        account = Account(raw, as_of)
        accounts.append(account)
        for campaign in raw['campaigns']:
            campaigns[campaign['campaign_key']] = (account, campaign)
            account.campaigns[campaign['campaign_key']] = campaign
            for adset in campaign['adsets']:
                adset_key = adset['adset_key']
                budget = minor_of(adset['daily_budget_minor'], f'ad set {adset_key!r} daily_budget_minor')
                spend = {}
                for day, value in (adset.get('spend_minor_by_day') or {}).items():
                    spend[day] = minor_of(value, f'ad set {adset_key!r} spend on {day}')
                item = {
                    'raw': adset, 'key': adset_key, 'account': account, 'campaign': campaign,
                    'budget': budget, 'spend': spend,
                    # Missing is not zero: no reading of today's spend stays None.
                    'today_spend': (None if adset.get('spend_minor_today') is None else
                                    minor_of(adset['spend_minor_today'], f'ad set {adset_key!r} today spend')),
                    'created_at': parse_time(adset['created_at'], f'ad set {adset_key!r} created_at'),
                    'active_ads': [ad for ad in adset['ads'] if ad.get('status') == ACTIVE],
                }
                item['live'] = (account.active and campaign.get('status') == ACTIVE
                                and adset['status'] == ACTIVE and bool(item['active_ads']))
                account.adsets.append(item)
                adsets[adset_key] = item
                for ad in adset['ads']:
                    ads[ad['ad_key']] = (account, ad)
    return as_of, accounts, adsets, campaigns, ads


def link_offers(adset, pattern):
    """Offers carried by the destination links of an ad set's ads (active ones if any)."""
    ads = adset['active_ads'] or adset['raw']['ads']
    offers = set()
    for ad in ads:
        match = pattern.search(ad.get('destination_url') or '')
        if match:
            offers.add(match.group('offer'))
    return offers


def declared_offer(adset, pattern):
    match = pattern.search(adset['raw']['name'])
    return match.group('offer') if match else None


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def finding(code, account, object_key, **detail):
    return {'level': SEVERITY[code], 'code': code, 'account_key': account.key, 'object_key': object_key,
            'detail': detail}


def check_accounts(accounts):
    return [finding('ACCOUNT_DISABLED', account, account.key, status=account.status)
            for account in accounts if not account.active]


def check_shells(accounts, money):
    found = []
    for account in accounts:
        for adset in account.adsets:
            if (account.active and adset['campaign'].get('status') == ACTIVE
                    and adset['raw']['status'] == ACTIVE and not adset['active_ads']):
                found.append(finding('SHELL_ADSET', account, adset['key'], budget=money.text(adset['budget'])))
    return found


def full_days_spend(adset, account, days):
    """Spend on the last ``days`` complete local days; None for a day with no reading."""
    values = []
    for offset in range(1, days + 1):
        day = (account.today - timedelta(days=offset)).isoformat()
        values.append(adset['spend'].get(day))
    return values


def check_budgets(accounts, policy, money):
    canary = policy['budget_canary']
    p0 = policy_minor(money, canary['p0_daily_budget'], 'budget_canary.p0_daily_budget')
    p1 = policy_minor(money, canary['p1_daily_budget'], 'budget_canary.p1_daily_budget')
    days = int(canary['full_days'])
    limit = decimal_of(canary['p1_multiple_of_average'], 'budget_canary.p1_multiple_of_average')
    name_pattern = re.compile(policy['name_budget_pattern']) if policy.get('name_budget_pattern') else None
    found = []
    for account in accounts:
        for adset in account.adsets:
            status = adset['raw']['status']
            if status not in (ACTIVE, PAUSED):
                continue
            budget = adset['budget']
            if budget >= p0:
                found.append(finding('BUDGET_CANARY', account, adset['key'], budget=money.text(budget),
                                     line=money.text(p0)))
            elif adset['live'] and budget > p1:
                history = full_days_spend(adset, account, days)
                if None not in history:
                    total = sum(history)
                    if total == 0:
                        found.append(finding('BUDGET_NO_SPEND', account, adset['key'], budget=money.text(budget),
                                             line=money.text(p1), days=days))
                    else:
                        average = Decimal(total) / days
                        multiple = Decimal(budget) / average
                        if multiple > limit:
                            found.append(finding('BUDGET_FAR_ABOVE_SPEND', account, adset['key'],
                                                 budget=money.text(budget), days=days,
                                                 average=money.text(int(average.to_integral_value())),
                                                 multiple=ratio_text(multiple), limit=ratio_text(limit)))
            if name_pattern:
                match = name_pattern.search(adset['raw']['name'])
                if match:
                    named = money.to_minor(match.group('amount').replace(',', ''), 'major',
                                           f"name of {adset['key']}")
                    if named is not None and named != budget:
                        found.append(finding('NAME_BUDGET_STALE', account, adset['key'],
                                             named=match.group(0), budget=money.text(budget)))
    return found


def check_offer_links(accounts, policy):
    destination = re.compile(policy['offer_link']['destination_pattern'])
    name = re.compile(policy['offer_link']['name_pattern'])
    found = []
    for account in accounts:
        day = account.yesterday.isoformat()
        existed = [item for item in account.adsets if item['created_at'] < local_midnight(account.today, account.zone)]
        complete = all(day in item['spend'] for item in existed)
        account_spend = sum(item['spend'].get(day, 0) for item in existed)
        for adset in account.adsets:
            if adset['raw']['status'] not in (ACTIVE, PAUSED) or not adset['raw']['ads']:
                continue
            linked = link_offers(adset, destination)
            declared = declared_offer(adset, name)
            if not linked:
                found.append(finding('OFFER_LINK_UNREADABLE', account, adset['key']))
            elif declared is None:
                found.append(finding('OFFER_NOT_DECLARED', account, adset['key'], linked=', '.join(sorted(linked))))
            elif linked != {declared}:
                if complete and account_spend:
                    share = share_text(Decimal(adset['spend'].get(day, 0)) * 100 / account_spend)
                else:
                    share = UNKNOWN_SHARE
                found.append(finding('OFFER_LINK_MISMATCH', account, adset['key'], declared=declared,
                                     linked=', '.join(sorted(linked)), share=share, day=day))
    return found


def window_activity(snapshot, as_of, policy, accounts_by_key, owners):
    start = as_of - timedelta(hours=int(policy['writers']['window_hours']))
    events = []
    for index, raw in enumerate(snapshot.get('activity', [])):
        if not isinstance(raw, dict):
            raise AuditError(f'activity entry {index} must be an object')
        at = parse_time(raw.get('at'), f'activity entry {index} at')
        account_key = raw.get('account_key')
        if account_key not in accounts_by_key:
            raise AuditError(f'activity entry {index} names an unknown account {account_key!r}')
        owner = owners.get(raw.get('object_key'))
        if owner is not None and owner != account_key:
            raise AuditError(f'activity entry {index}: object {raw.get("object_key")!r} belongs to '
                             f'{owner!r}, not {account_key!r}')
        event = dict(raw)
        event['at_utc'] = at
        event['writer'] = raw.get('writer') or 'unknown writer'
        if raw.get('event') == 'budget_change':
            event['old'] = minor_of(raw.get('old_minor'), f'activity entry {index} old_minor')
            event['new'] = minor_of(raw.get('new_minor'), f'activity entry {index} new_minor')
        if at > as_of:
            raise AuditError(f'activity entry {index} is later than the snapshot read time')
        event['in_window'] = at >= start
        events.append(event)
    events.sort(key=lambda item: (item['at_utc'], canonical(item.get('object_key'))))
    return events


def writer_rows(events, policy, accounts):
    own = policy['writers']['own']
    rows, found = [], []
    order = {account.key: index for index, account in enumerate(accounts)}
    grouped = {}
    for event in events:
        if event['in_window']:
            grouped.setdefault((event['account_key'], event['writer']), []).append(event)
    for (account_key, writer), items in sorted(grouped.items(), key=lambda pair: (order[pair[0][0]], pair[0][1])):
        budget = [item for item in items if item.get('event') == 'budget_change']
        net = {}
        for item in budget:
            first, _ = net.get(item['object_key'], (item['old'], item['new']))
            net[item['object_key']] = (first, item['new'])
        changes = []
        for key in sorted(net):
            first, last = net[key]
            if first:
                changes.append(Decimal(last - first) * 100 / first)
        spread = None
        if changes:
            low, high = min(changes), max(changes)
            spread = pct_text(low) if low == high else f'{pct_text(low)} … {pct_text(high)}'
        rows.append({'account_key': account_key, 'writer': writer, 'role': own.get(writer),
                     'changes': len(items), 'budget_changes': len(budget), 'net_change': spread,
                     'objects': sorted({item.get('object_key') for item in items if item.get('object_key')})})
    for row in rows:
        if row['role'] is None:
            account = next(item for item in accounts if item.key == row['account_key'])
            found.append(finding('EXTERNAL_WRITER', account, row['account_key'], writer=row['writer'],
                                 changes=row['changes'], budget_changes=row['budget_changes'],
                                 objects=', '.join(row['objects']) or '—'))
    return rows, found


def tiers(accounts, events, policy, money):
    own = policy['writers']['own']
    rows = []
    for account in accounts:
        for adset in account.adsets:
            if not adset['live']:
                continue
            changes = [event for event in events
                       if event.get('event') == 'budget_change' and event.get('object_key') == adset['key']]
            outside = any(event['writer'] not in own for event in changes if event['in_window'])
            mismatch = bool(changes) and changes[-1]['new'] != adset['budget']
            if changes:
                since, exact = changes[-1]['at_utc'], True
            elif adset['created_at'] >= account.activity_since:
                since, exact = adset['created_at'], True
            else:
                since, exact = account.activity_since, False
            if mismatch:
                # The log's last value is not the field's value: something changed it unlogged.
                full = 'unknown'
            elif since <= account.yesterday_start:
                full = 'yes'
            elif exact:
                full = 'no'
            else:
                full = 'unknown'
            rows.append({'adset_key': adset['key'], 'account_key': account.key,
                         'budget': money.text(adset['budget']), 'since_local': local_text(since, account.zone),
                         'since_exact': exact, 'full_day': full, 'outside_writer': outside,
                         'log_value': money.text(changes[-1]['new']) if mismatch else None})
    return rows


def check_duplicates(accounts, policy, money):
    destination = re.compile(policy['offer_link']['destination_pattern'])
    found = []
    for account in accounts:
        live_pairs = {}
        live_budget = 0
        for adset in account.adsets:
            if adset['live']:
                live_budget += adset['budget']
                for ad in adset['active_ads']:
                    match = destination.search(ad.get('destination_url') or '')
                    pair = (match.group('offer') if match else None, ad.get('creative_fingerprint'))
                    if pair[1]:
                        live_pairs.setdefault(pair, []).append(adset['key'])
        paused, matched, added = [], set(), 0
        for adset in account.adsets:
            if adset['raw']['status'] != PAUSED:
                continue
            hits = set()
            for ad in adset['raw']['ads']:
                match = destination.search(ad.get('destination_url') or '')
                pair = (match.group('offer') if match else None, ad.get('creative_fingerprint'))
                hits.update(live_pairs.get(pair, []))
            if hits:
                paused.append(adset['key'])
                matched.update(hits)
                added += adset['budget']
        if paused:
            found.append(finding('DUPLICATE_ACTIVATION', account, account.key, paused=', '.join(paused),
                                 live=', '.join(sorted(matched)), before=money.text(live_budget),
                                 after=money.text(live_budget + added)))
    return found


# --------------------------------------------------------------------------
# write requests
# --------------------------------------------------------------------------

def last_status_change(events, object_key):
    changes = [event for event in events
               if event.get('event') == 'status_change' and event.get('object_key') == object_key]
    return changes[-1] if changes else None


def policy_minor(money, raw, label):
    """A policy money line in minor units; a value that is not a whole number of minor units is refused."""
    value = money.to_minor(raw, 'major', label)
    if value is None:
        raise AuditError(f'policy {label} must be a non-negative amount with at most {money.exponent} decimals')
    return value


def current_minor(level, obj, field, label):
    """Current value of a money field in minor units, or None when the read does not carry it."""
    if level == 'adset' and field == 'daily_budget':
        return obj['budget']
    raw = (obj if level == 'campaign' else {}).get(field + '_minor')
    return None if raw is None else minor_of(raw, label)


def judge_request(raw, index, model, events, policy, money, platform):
    """Decide allow, refuse or wait for one write request; a malformed request is refused, not fatal."""
    key = raw.get('request_key') if isinstance(raw, dict) else None
    if not isinstance(key, str) or not key:
        raise AuditError(f'write request {index} needs request_key')
    row = {'request_key': key, 'object_key': raw.get('object_key'), 'field': raw.get('field'),
           'requested': raw.get('value'), 'unit': raw.get('unit')}
    try:
        decision, code, detail = _judge(raw, key, model, events, policy, money, platform)
    except AuditError as exc:
        decision, code, detail = 'refuse', 'INVALID_REQUEST', {'problem': str(exc)}
    row.update(decision=decision, code=code, detail=detail)
    return row


def _judge(raw, key, model, events, policy, money, platform):
    as_of, accounts, adsets, campaigns, ads = model
    field = raw.get('field')
    if not isinstance(field, str) or not field:
        raise AuditError('the request names no field')
    object_key = raw.get('object_key')
    if object_key in adsets:
        level, obj = 'adset', adsets[object_key]
        account, current_raw = obj['account'], obj['raw']
    elif object_key in campaigns:
        level = 'campaign'
        account, current_raw = campaigns[object_key]
        obj = current_raw
    elif object_key in ads:
        level = 'ad'
        account, current_raw = ads[object_key]
        obj = current_raw
    else:
        return 'refuse', 'UNKNOWN_OBJECT', {}
    named = raw.get('account_key')
    if named is not None and named != account.key:
        return 'refuse', 'ACCOUNT_MISMATCH', {'named': named, 'actual': account.key}
    if not account.active:
        return 'wait', 'ACCOUNT_DISABLED', {'status': account.status}

    fields = policy['fields'][platform]
    if field in (fields.get('locked_after_create') or {}).get(level, []):
        return 'refuse', 'LOCKED_FIELD', {'field': field, 'level': level}
    if field in (fields.get('replace_whole') or {}).get(level, []):
        current = current_raw.get(field)
        value = raw.get('value')
        if not isinstance(current, dict):
            return 'refuse', 'CURRENT_UNKNOWN', {'field': field}
        if not isinstance(value, dict):
            raise AuditError(f'{field} must be sent as an object')
        missing = sorted(set(current) - set(value))
        if missing:
            return 'refuse', 'PARTIAL_REPLACE', {'field': field, 'missing': ', '.join(missing)}
        return 'allow', 'OK', {}
    if field == 'status' and str(raw.get('value')).upper() == ACTIVE:
        if str(current_raw.get('status')).upper() != PAUSED:
            return 'allow', 'NO_RULE', {}
        change = last_status_change(events, object_key)
        role = policy['writers']['own'].get(change['writer']) if change else None
        if change is None or str(change.get('new_status')).upper() != PAUSED:
            return 'wait', 'PAUSE_UNATTRIBUTED', {'writer': '—'}
        if role == 'human':
            return 'refuse', 'RESUME_HUMAN_PAUSE', {'writer': change['writer'],
                                                   'when': local_text(change['at_utc'], account.zone)}
        if role is None:
            return 'wait', 'PAUSE_UNATTRIBUTED', {'writer': change['writer']}
        return 'allow', 'NO_RULE', {}
    if field not in (fields.get('money') or []):
        return 'allow', 'NO_RULE', {}

    unit = raw.get('unit')
    if unit not in UNITS:
        return 'refuse', 'UNIT_MISSING', {}
    target = money.to_minor(raw.get('value'), unit, 'value')
    if target is None:
        return 'refuse', 'UNIT_INVALID', {'value': raw.get('value'), 'unit': unit}
    writes = policy['budget_writes']
    if field not in writes['fields']:
        return 'allow', 'NO_RULE', {}
    current = current_minor(level, obj, field, f'{object_key} {field}')
    if current is None:
        return 'refuse', 'CURRENT_UNKNOWN', {'field': field}
    ceiling = policy_minor(money, writes['ceiling_daily_budget'], 'budget_writes.ceiling_daily_budget')
    p0 = policy_minor(money, policy['budget_canary']['p0_daily_budget'], 'budget_canary.p0_daily_budget')
    limit = decimal_of(writes['max_raise_ratio'], 'budget_writes.max_raise_ratio')
    detail = {'current': money.text(current), 'target': money.text(target)}
    ratio = Decimal(target) / current if current else None
    if target > current:
        if target >= ceiling:
            return 'refuse', 'ABOVE_CEILING', {'target': detail['target'], 'ceiling': money.text(ceiling)}
        if ratio is not None and ratio > limit:
            reason = raw.get('override_reason')
            if isinstance(reason, str) and reason.strip():
                return 'allow', 'RAISE_OVERRIDE', dict(detail, ratio=ratio_text(ratio), limit=ratio_text(limit),
                                                       reason=reason.strip())
            return 'refuse', 'RAISE_TOO_LARGE', dict(detail, ratio=ratio_text(ratio), limit=ratio_text(limit))
    elif target < current:
        line = min(ceiling, p0)
        if current >= line:
            # Rolling back a runaway budget is never held for tomorrow.
            return 'allow', 'RUNAWAY_CUT', dict(detail, line=money.text(line))
        spent = obj['today_spend'] if level == 'adset' else (
            None if current_raw.get('spend_minor_today') is None else
            minor_of(current_raw['spend_minor_today'], f'{object_key} spend_minor_today'))
        if spent is None:
            return 'wait', 'SPEND_UNKNOWN', {'target': detail['target']}
        if target <= spent:
            return 'wait', 'INTRADAY_CUT', {'target': detail['target'], 'spent': money.text(spent),
                                            'when': local_text(account.tomorrow_start, account.zone)}
    return 'allow', 'BUDGET_OK', dict(detail, ratio=ratio_text(ratio) if ratio is not None else '—')


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------

def audit(snapshot, policy):
    """Audit a saved read; return findings, tiers, writers and request decisions."""
    validate_policy(policy)
    validate_snapshot(snapshot)
    platform = snapshot.get('platform')
    if not isinstance(policy['fields'].get(platform), dict):
        raise AuditError(f'policy has no field rules for platform {platform!r}; refused, not guessed')
    currency = snapshot.get('currency')
    exponents = policy['currency_exponent']
    if currency not in exponents:
        raise AuditError(f'currency {currency!r} has no minor-unit exponent in the policy; refused, not guessed')
    money = Money(currency, int(exponents[currency]))
    for label, value in (('budget_canary.p0_daily_budget', policy['budget_canary']['p0_daily_budget']),
                         ('budget_canary.p1_daily_budget', policy['budget_canary']['p1_daily_budget']),
                         ('budget_writes.ceiling_daily_budget', policy['budget_writes']['ceiling_daily_budget'])):
        policy_minor(money, value, label)
    model = build_model(snapshot)
    as_of, accounts, adsets, campaigns, ads = model
    accounts_by_key = {account.key: account for account in accounts}
    owners = {key: item['account'].key for key, item in adsets.items()}
    owners.update({key: pair[0].key for key, pair in campaigns.items()})
    owners.update({key: pair[0].key for key, pair in ads.items()})
    events = window_activity(snapshot, as_of, policy, accounts_by_key, owners)
    writers, writer_findings = writer_rows(events, policy, accounts)

    findings = (check_accounts(accounts) + check_budgets(accounts, policy, money) + check_shells(accounts, money)
                + check_offer_links(accounts, policy) + writer_findings + check_duplicates(accounts, policy, money))
    level_order = {level: index for index, level in enumerate(LEVELS)}
    account_order = {account.key: index for index, account in enumerate(accounts)}
    findings.sort(key=lambda item: (level_order[item['level']], account_order[item['account_key']],
                                    item['code'], item['object_key']))

    requests = [judge_request(raw, index, model, events, policy, money, platform)
                for index, raw in enumerate(snapshot.get('write_requests', []))]
    seen = set()
    for row in requests:
        if row['request_key'] in seen:
            raise AuditError(f"duplicate request_key {row['request_key']!r}")
        seen.add(row['request_key'])

    account_rows = []
    for account in accounts:
        live = [item for item in account.adsets if item['live']]
        active = [item for item in account.adsets if item['raw']['status'] == ACTIVE]
        account_rows.append({
            'account_key': account.key, 'status': account.status, 'timezone_name': account.zone_name,
            'local_time': account.local_now.strftime('%Y-%m-%d %H:%M (UTC%z)'),
            'live_adsets': len(live), 'active_adsets': len(active),
            'live_budget': money.text(sum(item['budget'] for item in live)),
            'full_day_cutoff': local_text(account.yesterday_start, account.zone),
            'activity_since': local_text(account.activity_since, account.zone),
        })

    counts = {level: sum(1 for item in findings if item['level'] == level) for level in LEVELS}
    decisions = {decision: sum(1 for item in requests if item['decision'] == decision) for decision in DECISIONS}
    return {
        'notice': NOTICE, 'platform': platform, 'currency': currency,
        'as_of': as_of.strftime('%Y-%m-%d %H:%M UTC'), 'policy_version': policy.get('version'),
        'window_hours': int(policy['writers']['window_hours']),
        'counts': counts, 'decisions': decisions, 'accounts': account_rows, 'findings': findings,
        'writers': writers, 'tiers': tiers(accounts, events, policy, money), 'requests': requests,
        'native_platform_calls': 0,
    }


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def cell(value):
    return '`' + str(value).replace('|', '\\|') + '`'


def requested_text(row):
    value = row['requested']
    if isinstance(value, (dict, list)):
        text = canonical(value)
    else:
        text = str(value)
    if row.get('unit'):
        text += f" ({row['unit']})"
    return cell(text)


def render_report(result, lang='en', snapshot_name='snapshot.json', policy_name='policy.json'):
    if lang not in TEXT:
        raise AuditError(f'language must be one of {list(LANGUAGES)}')
    text = TEXT[lang]
    platform = {'meta': 'Meta', 'tiktok': 'TikTok'}.get(result['platform'], result['platform'])
    counts, decisions = result['counts'], result['decisions']
    lines = [
        f"# {text['title']}", '',
        text['meta_line'].format(platform=platform, snapshot=snapshot_name, as_of=result['as_of'],
                                 policy=policy_name, version=result['policy_version'] or '—'),
        '', f"> {text['scope']}", '',
        '**' + text['result'].format(p0=counts['P0'], p1=counts['P1'], p2=counts['P2'], allow=decisions['allow'],
                                     refuse=decisions['refuse'], wait=decisions['wait']) + '**',
        '', f"## {text['accounts']}", '',
        '| ' + ' | '.join(text['account_columns']) + ' |',
        '|' + '---|' * len(text['account_columns']),
    ]
    for row in result['accounts']:
        lines.append(f"| {cell(row['account_key'])} | {cell(row['status'])} | {cell(row['timezone_name'])} | "
                     f"{row['local_time']} | {row['live_adsets']} / {row['active_adsets']} | {row['live_budget']} | "
                     f"{row['full_day_cutoff']} | {row['activity_since']} |")

    lines += ['', f"## {text['findings']}", '']
    if not result['findings']:
        lines.append(text['no_findings'])
    for item in result['findings']:
        detail = {}
        for key, value in item['detail'].items():
            if key == 'share' and value == UNKNOWN_SHARE:
                detail[key] = text['unknown_share']
                continue
            plain = key in ('budget', 'line', 'average', 'before', 'after', 'share', 'multiple', 'limit', 'days',
                            'changes', 'budget_changes')
            detail[key] = value if plain else cell(value)
        message = text['codes'][item['code']].format(**detail)
        lines.append(f"- **{item['level']}** · {cell(item['object_key'])} · {cell(item['code'])} — {message}")

    lines += ['', f"## {text['writers'].format(hours=result['window_hours'])}", '']
    if result['writers']:
        lines += ['| ' + ' | '.join(text['writer_columns']) + ' |', '|' + '---|' * len(text['writer_columns'])]
        for row in result['writers']:
            lines.append(f"| {cell(row['account_key'])} | {cell(row['writer'])} | {text['roles'][row['role']]} | "
                         f"{row['changes']} | {row['budget_changes']} | {row['net_change'] or '—'} |")
    else:
        lines.append(text['no_writers'])

    lines += ['', f"## {text['tiers']}", '',
              '| ' + ' | '.join(text['tier_columns']) + ' |', '|' + '---|' * len(text['tier_columns'])]
    for row in result['tiers']:
        since = row['since_local'] if row['since_exact'] else text['bounded'].format(when=row['since_local'])
        if row['log_value']:
            since += text['log_mismatch'].format(value=row['log_value'])
        lines.append(f"| {cell(row['adset_key'])} | {cell(row['account_key'])} | {row['budget']} | {since} | "
                     f"{text['full_day'][row['full_day']]} | {text['yes_no'][row['outside_writer']]} |")

    lines += ['', f"## {text['requests']}", '']
    if result['requests']:
        lines += ['| ' + ' | '.join(text['request_columns']) + ' |', '|' + '---|' * len(text['request_columns'])]
        for row in result['requests']:
            detail = dict(row['detail'])
            if 'level' in detail:
                detail['level'] = LEVEL_NAMES[lang][detail['level']]
            for key in ('field', 'missing', 'writer', 'value', 'unit', 'status', 'named', 'actual', 'problem'):
                if key in detail:
                    detail[key] = cell(detail[key])
            why = text['request_codes'][row['code']].format(**detail)
            lines.append(f"| {cell(row['request_key'])} | {cell(row['object_key'])} | {cell(row['field'])} | "
                         f"{requested_text(row)} | {text['decisions'][row['decision']]} | {why} |")
    else:
        lines.append(text['no_requests'])
    lines += ['', f"## {text['next']}", '', text['next_text'], '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--snapshot', required=True, type=Path, help='saved account read JSON')
    parser.add_argument('--policy', required=True, type=Path, help='audit policy JSON')
    parser.add_argument('--report', type=Path, help='write the Markdown report here')
    parser.add_argument('--check', type=Path,
                        help='compare the report with a committed golden file; exit 1 on difference')
    parser.add_argument('--lang', choices=LANGUAGES, default='en', help='report language (default en)')
    parser.add_argument('--json', action='store_true', help='print the audit result as JSON')
    parser.add_argument('--strict', action='store_true', help='exit 3 when there is a P0 finding')
    args = parser.parse_args(argv)

    try:
        result = audit(load(args.snapshot), load(args.policy))
        report = render_report(result, args.lang, args.snapshot.name, args.policy.name)
    except (OSError, AuditError) as exc:
        print(f'account_audit: {exc}', file=sys.stderr)
        return 2

    counts, decisions = result['counts'], result['decisions']
    summary = (f"{counts['P0']} P0 · {counts['P1']} P1 · {counts['P2']} P2 · requests "
               f"{decisions['allow']} allow / {decisions['refuse']} refuse / {decisions['wait']} wait · "
               '0 platform calls')
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding='utf-8')
    if args.check:
        try:
            expected = args.check.read_text(encoding='utf-8')
        except OSError as exc:
            print(f'account_audit: cannot read {args.check}: {exc.strerror}', file=sys.stderr)
            return 2
        if expected != report:
            sys.stderr.writelines(difflib.unified_diff(
                expected.splitlines(True), report.splitlines(True), fromfile=str(args.check), tofile='fresh report'))
            print(f'\naccount_audit: report differs from {args.check}; regenerate it with --report and review '
                  'the diff', file=sys.stderr)
            return 1
        print(f'{summary} · matches {args.check}')
        return 0
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.report:
        print(f'{summary} · report written to {args.report}')
    else:
        sys.stdout.write(report)
    return 3 if args.strict and counts['P0'] else 0


if __name__ == '__main__':
    sys.exit(main())
