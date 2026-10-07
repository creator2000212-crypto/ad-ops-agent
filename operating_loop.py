#!/usr/bin/env python3
"""Runnable reference implementation of a recurring paid-media operating loop.

Offline only. No network, no platform SDK, no credentials, no account writes.
Everything here reads declared JSON, applies the rules in ``operating_rules.py``,
and writes reviewable artifacts plus an append-only ledger of proposals.

The loop is the one an operator actually runs, not an abstraction of it:

  0  re-verify what the previous round proposed          -> kept in the ledger
  1  collect one settled observation window               -> ``*snapshot*.json``
  2  classify every ad set, check platform vs settlement  -> ``diagnose``
  3  turn findings into proposals with evidence           -> ``findings.json``
  4  pass the write gate before touching anything         -> ``gate``
  5  record the round in an append-only ledger            -> ``apply``
  6  reconcile what was actually written, then report     -> ``verify`` / ``report``

Steps 2 to 6 exist because the interesting failures are not arithmetic mistakes.
They are: acting on a sample too small to judge, acting on platform numbers the
settlement does not confirm, treating a failed write as a successful one, and
overwriting a change a human made while the round was being prepared. Each of
those has an explicit guard below.

Every command takes ``--lang en|zh-CN`` (default ``en``) for the report, gate
labels, evidence and ledger reasons. Codes and gate states do not change with
the language.

Usage (see ``scripts/demo_operating_loop.py`` for a runnable end-to-end example):

    python3 operating_loop.py round \\
        --snapshot examples/operating/snapshot-primary.json \\
        --writeback examples/operating/writeback-snapshot.json \\
        --after examples/operating/after-snapshot.json \\
        --methodology examples/operating/methodology-reference.json \\
        --settlement examples/operating/settlement-daily.json \\
        --out runs/operating-demo
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

import operating_rules as rules

NOTICES = {
    'en': ('OFFLINE ANALYSIS ONLY — no ad platform is contacted, no account is written and no media '
           'is uploaded. The action list is a proposal for human review, not an executed instruction.'),
    'zh-CN': ('OFFLINE ANALYSIS ONLY — 不连接任何广告平台、不写任何账户、不上传素材。'
              '输出的动作清单是给人审阅的建议，不是已执行的指令。'),
}
NOTICE = NOTICES['en']
PLATFORMS = {'meta', 'tiktok', 'google'}
ROUND_MODES = ('dry_run', 'simulate_apply')


class LoopError(ValueError):
    pass


# --------------------------------------------------------------------------
# io helpers
# --------------------------------------------------------------------------

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def load(path):
    with open(path, encoding='utf-8') as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError as exc:
            raise LoopError(f'Not valid JSON: {path} ({exc})') from exc


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(path)


def timestamp(explicit=None):
    if explicit:
        return explicit
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


# --------------------------------------------------------------------------
# step 1 / 2: validate the snapshot, then classify
# --------------------------------------------------------------------------

def validate_snapshot(snapshot):
    if snapshot.get('kind') != 'operating_snapshot':
        raise LoopError('Snapshot kind must be operating_snapshot.')
    if not snapshot.get('as_of'):
        raise LoopError('Snapshot has no as_of: without the data cut-off time, maturity cannot be judged.')
    accounts = snapshot.get('accounts')
    if not isinstance(accounts, list) or not accounts:
        raise LoopError('Snapshot must contain at least one account.')
    seen = set()
    for account in accounts:
        for key in ('account_key', 'platform'):
            if not account.get(key):
                raise LoopError(f'Account is missing {key}: {account}')
        if account['platform'] not in PLATFORMS:
            raise LoopError(f"Platform must be one of {sorted(PLATFORMS)}: {account['platform']}")
        if account['account_key'] in seen:
            raise LoopError(f"Duplicate account key: {account['account_key']}")
        seen.add(account['account_key'])
        offer = account.get('offer') or {}
        if not offer.get('offer_key'):
            raise LoopError(f"Account {account['account_key']} is missing offer.offer_key.")
        if offer.get('unit_price') is None:
            # Without a unit price there is no T, and without T none of the cost
            # rules are meaningful. Refuse rather than invent a default.
            raise LoopError(f"Account {account['account_key']} is missing offer.unit_price: "
                            'without T, cost cannot be judged.')
    return snapshot


def observation_of(document):
    """Accept either an ``operating_snapshot`` or a ``writeback_snapshot``."""
    kind = (document or {}).get('kind')
    if kind not in ('operating_snapshot', 'writeback_snapshot'):
        raise LoopError(f'Expected operating_snapshot or writeback_snapshot, got {kind!r}.')
    return document


def collect_findings(snapshot, methodology, settlement=None, lang='en'):
    """Step 2. Every account is classified and, when a settlement is supplied,
    checked against it; nothing is decided yet."""
    rules.check_lang(lang)
    validate_snapshot(snapshot)
    accounts, all_proposals, all_diagnostics, structure, drivers = [], [], [], [], []
    for account in snapshot['accounts']:
        proposals, diagnostics = rules.decide_account(account, methodology, lang)
        accounts.append(account['account_key'])
        all_proposals.extend(proposals)
        all_diagnostics.extend(diagnostics)
        structure.extend([{'account_key': account['account_key'], **item}
                          for item in rules.structure_findings(account, methodology, lang)])
        drivers.extend(rules.cpa_drivers(account, methodology))
    settlement_result = None
    if settlement is not None:
        settlement_result = rules.reconcile_settlement(snapshot, settlement, methodology, lang)
        all_proposals = rules.downgrade_unreconciled(all_proposals, settlement_result, lang)
    return {
        'schema_version': 1,
        'kind': 'operating_findings',
        'notice': NOTICES[lang],
        'lang': lang,
        'as_of': snapshot['as_of'],
        'round_id': snapshot.get('round_id'),
        'observation': snapshot.get('observation'),
        'snapshot_hash': digest(snapshot),
        'settlement_hash': digest(settlement) if settlement is not None else None,
        'methodology': {'methodology_id': methodology['methodology_id'], 'version': methodology['version']},
        'methodology_hash': digest(methodology),
        'accounts': accounts,
        'diagnostics': all_diagnostics,
        'proposals': all_proposals,
        'structure_findings': structure,
        'cpa_drivers': drivers,
        'settlement': settlement_result,
    }


SIGNAL_TEXT = {
    'en': {'spend_cap_null': 'spend_cap reads back null; the headroom alert is unavailable'},
    'zh-CN': {'spend_cap_null': 'spend_cap 读回为 null，余量预警不可用'},
}


def account_signals(snapshot, methodology, lang='en'):
    """Account-level facts worth stating before any per-adset action."""
    rules.check_lang(lang)
    signals = []
    for account in snapshot['accounts']:
        adsets = account.get('adsets') or []
        # Two different questions: is it configured to run, and is it actually
        # able to serve. Collapsing them hides rejection and billing problems.
        configured_live = [a for a in adsets if a.get('configured_status') == 'ACTIVE']
        effective_live = [a for a in configured_live if a.get('effective_status') == 'ACTIVE']
        signals.append({
            'account_key': account['account_key'],
            'platform': account.get('platform'),
            'offer_key': (account.get('offer') or {}).get('offer_key'),
            'unit_price': (account.get('offer') or {}).get('unit_price'),
            'account_timezone': account.get('account_timezone'),
            'report_timezone': account.get('report_timezone'),
            'adsets_total': len(adsets),
            'adsets_configured_live': len(configured_live),
            'adsets_effective_live': len(effective_live),
            'today_spend': account.get('today_spend'),
            'balance': account.get('balance'),
            'spend_cap': account.get('spend_cap'),
            'capability_gaps': ([SIGNAL_TEXT[lang]['spend_cap_null']]
                                if account.get('spend_cap') is None else []),
            'timezone_warning': (account.get('account_timezone') != account.get('report_timezone')),
        })
    return signals


# --------------------------------------------------------------------------
# step 4: the write gate
# --------------------------------------------------------------------------

def run_gate(findings, writeback, lang='en'):
    observation_of(writeback)
    verdicts = rules.gate(findings['proposals'], writeback, lang)
    return {
        'schema_version': 1,
        'kind': 'operating_gate',
        'notice': NOTICES[lang],
        'lang': lang,
        'as_of': writeback.get('as_of'),
        'round_id': findings.get('round_id'),
        'proposals_hash': digest(findings['proposals']),
        'writeback_hash': digest(writeback),
        'summary': rules.gate_summary(verdicts),
        'verdicts': verdicts,
        'write_plan': rules.writable_rows(verdicts),
    }


# --------------------------------------------------------------------------
# step 5 / 6: ledger, apply, reconcile
# --------------------------------------------------------------------------

LEDGER_TEXT = {
    'en': {
        'satisfied': ('Satisfied: the target is already in place; writing it again would be a pointless '
                      'significant edit.'),
        'conflict': ('Conflict, isolated: the current value is neither baseline nor target; a human '
                     'confirms it and nothing is overwritten.'),
        'unknown': ("Unknown: the pre-write state or the plan's baseline evidence is missing; supply the "
                    'specific item, then check again.'),
    },
    'zh-CN': {
        'satisfied': '已满足：目标值已就位，写了等于一次无意义的 significant edit。',
        'conflict': '冲突隔离：现值既非基线也非目标，交给人确认，不覆盖。',
        'unknown': '未知：写前状态或原方案基线证据不足，按具体缺项补证后重新核对。',
    },
}


def append_events(ledger, events):
    """Append events; the ledger file exists afterwards even when nothing was added."""
    path = Path(ledger)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False) + '\n')


def require_ledger(ledger):
    """A missing ledger is missing evidence, never an empty history."""
    path = Path(ledger)
    if not path.is_file():
        raise LoopError(f'Ledger not found: {ledger}. Missing is not "nothing open"; check the path '
                        'or run apply first.')
    return path


def read_events(ledger):
    path = require_ledger(ledger)
    events = []
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # A damaged line must not silently become a missing action.
                events.append({'type': 'corrupt', 'raw': line[:120]})
    return events


def fold(ledger):
    """Collapse the append-only event stream into the current state per row."""
    rows = {}
    for event in read_events(ledger):
        key = event.get('id')
        if event.get('type') == 'proposal' and key:
            rows[key] = {'id': key, 'status': 'pending_write',
                         'round_id': event.get('round_id'),
                         'code': event.get('code'),
                         'level': event.get('level'),
                         'object_key': event.get('object_key'),
                         'patch': event.get('patch') or {},
                         'at': event.get('at')}
        elif event.get('type') == 'reconciliation' and key in rows:
            rows[key]['status'] = ('verified_effective' if event.get('effective')
                                   else 'verified_not_effective')
            rows[key]['reconciliation'] = event.get('detail', '')
            rows[key]['verified_at'] = event.get('at')
        elif event.get('type') == 'skipped' and key:
            rows[key] = {'id': key, 'status': 'skipped', 'code': event.get('code'),
                         'object_key': event.get('object_key'),
                         'reason': event.get('reason'), 'at': event.get('at')}
    return rows


def open_rows(ledger):
    return [row for row in fold(ledger).values()
            if row.get('status') in ('pending_write', 'verified_not_effective')]


def apply_gate(ledger, gate_document, at, lang='en'):
    """Step 5. Record every gated row. Only ``ready`` rows produce a write plan."""
    rules.check_lang(lang)
    text = LEDGER_TEXT[lang]
    events = []
    for verdict in gate_document['verdicts']:
        row_id = f"{gate_document['round_id']}-{verdict['code']}-{verdict['object_key']}"
        if verdict['gate'] == rules.READY:
            events.append({'type': 'proposal', 'id': row_id, 'round_id': gate_document['round_id'],
                           'code': verdict['code'], 'level': verdict['level'],
                           'object_key': verdict['object_key'],
                           'patch': {field: verdict['target'][field] for field in verdict['writable_fields']},
                           'at': at})
        elif verdict['gate'] == rules.SATISFIED:
            events.append({'type': 'skipped', 'id': row_id, 'code': verdict['code'],
                           'reason': text['satisfied'], 'at': at})
        elif verdict['gate'] == rules.CONFLICT:
            events.append({'type': 'skipped', 'id': row_id, 'code': verdict['code'],
                           'object_key': verdict['object_key'],
                           'reason': text['conflict'], 'at': at})
        elif verdict['gate'] == rules.UNKNOWN:
            # Preserve the specific evidence gap. A fresh current-state read
            # cannot establish a missing baseline from the original plan.
            events.append({'type': 'skipped', 'id': row_id, 'code': verdict['code'],
                           'object_key': verdict['object_key'],
                           'reason': text['unknown'],
                           'detail': verdict['gate_detail'], 'at': at})
    append_events(ledger, events)
    return {
        'schema_version': 1,
        'kind': 'operating_application',
        'notice': NOTICES[lang],
        'round_id': gate_document['round_id'],
        'mode': 'simulate_apply',
        'write_plan': gate_document['write_plan'],
        'planned_writes': len(gate_document['write_plan']),
        'recorded_events': len(events),
        'advisory_only': gate_document['summary'][rules.ADVISORY],
        'not_written': [
            {'code': verdict['code'], 'object_key': verdict['object_key'],
             'gate': verdict['gate_label'], 'reason': verdict['gate_detail']}
            for verdict in gate_document['verdicts'] if verdict['gate'] != rules.READY],
        'at': at,
    }


def reconcile_and_record(ledger, gate_document, after, at, lang='en'):
    observation_of(after)
    require_ledger(ledger)
    report = rules.reconcile(gate_document['verdicts'], after.get('objects') or {}, lang)
    events = []
    for item in report:
        if not item['checked']:
            continue
        row_id = f"{gate_document['round_id']}-{item['code']}-{item['object_key']}"
        events.append({'type': 'reconciliation', 'id': row_id, 'effective': item['effective'],
                       'detail': item['detail'], 'at': at})
    append_events(ledger, events)
    effective = sum(1 for item in report if item.get('effective'))
    checked = sum(1 for item in report if item['checked'])
    return {
        'schema_version': 1,
        'kind': 'operating_reconciliation',
        'notice': NOTICES[lang],
        'round_id': gate_document['round_id'],
        'after_hash': digest(after),
        'checked': checked,
        'effective': effective,
        'ineffective': checked - effective,
        'rows': report,
        'at': at,
    }


# --------------------------------------------------------------------------
# step 6: the report a human reads
# --------------------------------------------------------------------------

REPORT_TEXT = {
    'en': {
        'title': '# 12-hour check · {round_id}',
        'header': '**Data as of:** {as_of} · **Method:** {method} v{version} · **Snapshot hash:** `{hash}`',
        'window': '**Observation window:** {date} ({kind}; full delivery day: {full_day}){note}',
        'window_sep': ' — ',
        'undeclared': 'not declared',
        'yes': 'yes', 'no': 'no',
        'this_round': '## This round',
        'b_findings': ('- Diagnosis produced **{total} findings** across accounts, ad sets and creatives. '
                       'One object can trigger several rules, so this is not {total} objects; all {adsets} '
                       'ad sets are listed under "Decisions by ad set".'),
        'b_ready': ('- **{ready} rows are `ready`**: each change passed the current-state check and is '
                    'ready for review. `ready` is not approval to act.'),
        'b_apply': ('- `apply` recorded **{planned} planned changes / {fields} fields** in the local ledger; '
                    'nothing was sent to a platform.'),
        'b_after': '- Against the supplied `after` snapshot: **{effective} matched, {ineffective} did not match**.',
        'b_settlement': ('- Platform vs settlement: {counts}. Cost-based proposals held as advisory until '
                         'the numbers reconcile: **{downgraded}**.'),
        'b_no_settlement': ('- No settlement file was supplied: platform numbers are unreconciled and '
                            'nothing was downgraded.'),
        'count': '{code} {n}',
        'count_sep': ' · ',
        'handle': '## Handle these first',
        'flagged_head': '**Gate rows that need a human: {n}** (`gate.json`):',
        'flagged_none': 'No conflicting or missing-state rows.',
        'unmatched_head': '**After-snapshot mismatches: {n}** (`reconciliation.json`):',
        'unmatched_none': 'No mismatch among the rows compared.',
        'downgraded_head': '**Measurement unreconciled: {n}** (`findings.json`, see "Platform vs settlement"):',
        'downgraded_tail': ' Advisory until platform and settlement agree; no budget or status change this round.',
        'downgraded_none': 'No proposal was downgraded.',
        'open_note': ('`open` lists only ledger rows that await comparison or failed it. **Gate conflicts '
                      'and missing state are not in `open`, so it is not the whole to-do list**; hand '
                      'over every list above.'),
        'signals': '## Account signals',
        'signals_cols': ('Account', 'Platform', 'Offer', 'Value per lead', 'Configured live',
                         'Able to deliver', 'Ad sets', "Today's spend", 'Balance', 'Spend cap', 'Notes'),
        'note_tz': ('account time zone {account} ≠ report time zone {report}; align before adding across '
                    'accounts'),
        'note_blocked': '{n} ad set(s) configured live but unable to deliver',
        'note_sep': '; ',
        'settlement': '## Platform vs settlement',
        'settle_meta': ('Settlement date {date} · time zone {tz} · currency {currency} · tolerance: spend '
                        '±{spend}%, settled leads ±{results}% of platform leads × approval rate {rate} · '
                        'target ROAS {roas}'),
        'settle_cols': ('Account', 'Spend: platform → settled', 'Leads: platform → settled (expected)',
                        'CPA: platform / settled', 'T / settled target', 'Settled ROAS', 'Status'),
        'settle_explain': ('Settled CPA is spend per approved lead, so it is compared with the settled '
                           'target, T ÷ approval rate (value per lead ÷ target ROAS), not with T. A row '
                           'that exists on one side only is shown as missing, never as zero. In accounts '
                           'with {downgrade_on}, {codes} become advisory ("measurement unreconciled").'),
        'or': ' or ',
        'decisions': '## Decisions by ad set',
        'decision_cols': ('Ad set', 'Stage', 'Spend', 'Impr.', 'Leads', 'CPA', 'T', 'Stop line',
                          'Utilisation', 'Rules fired'),
        'keep_observing': 'Keep observing',
        'cannot_classify': 'Cannot classify: ',
        'unreconciled': 'advisory: measurement unreconciled',
        'no_adsets': 'No ad set to classify',
        'code_sep': '; ',
        'drivers': '## Why CPA moved',
        'drivers_intro': ('CPA = CPM ÷ (1000 × CTR × CVR), so the change in log CPA splits exactly into a CPM, '
                          'a CTR and a CVR term. Each cell is that term in log-points (100 × change in the '
                          'natural log; negative pushed CPA down) and its share of the total movement. The '
                          'residual is what the quoted prior CPA leaves unexplained (rounding). It is an '
                          'accounting identity, not a cause.'),
        'drivers_cols': ('Ad set', 'Prior window', 'CPA: prior → now', 'Δ log CPA', 'CPM', 'CTR', 'CVR',
                         'Residual', 'Main driver'),
        'drivers_guide': ('Read the largest share first: CVR points after the click (destination, form, '
                          'lead quality), CTR to the hook, CPM to the auction.'),
        'not_decomposed': 'not decomposed: {missing} missing',
        'prior': 'prior', 'current': 'current',
        'gate': '## Gate results and recorded difference plan',
        'gate_cols': ('Result', 'Rows', 'Meaning'),
        'gate_rows': (
            ('ready', 'Ready for review (`ready`)',
             'Current value equals the baseline; only differing fields are listed; not yet approved'),
            ('satisfied', 'Satisfied', 'Target already in place; skipped'),
            ('conflict', 'Conflict (isolated)',
             'State matches neither baseline nor target; the values do not say who changed it; isolate and confirm'),
            ('unknown', 'Unknown', 'Pre-write state not read, a field missing or no usable baseline; re-read first'),
            ('advisory', 'Advisory', 'No field change declared, or downgraded; nothing to gate'),
        ),
        'plan_intro': 'Fields `apply` recorded. They are planned, not submitted:',
        'plan_cols': ('Object', 'Rule', 'Planned fields'),
        'plan_none': 'No differing field to record this round',
        'advisory_line': 'Advisory ({n} rows, no field change, not gated): ',
        'list_sep': ', ',
        'after': '## After-snapshot comparison',
        'after_intro': 'Targets compared with the supplied after file; no platform write happens here.',
        'after_cols': ('Object', 'Rule', 'Matches', 'Detail'),
        'match_yes': 'Yes', 'match_no': '**No**',
        'after_none': 'No planned change to compare this round.',
        'unchecked_head': '**Not compared this round: {n} rows, listed in full:**',
        'structure': '## Structure warnings (no action, but they limit how far a verdict can be trusted)',
        'handoff': '## Handoff rules',
        'handoff_lines': (
            '- `satisfied` produces no change. A `conflict` is isolated and its cause confirmed; the values '
            'alone do not say who changed it.',
            '- An insufficient sample (impressions below the floor) is recorded, not judged.',
            '- Capability gaps are stated (for example a spend cap that reads back null), never filled by '
            'inference.',
            '- Platform numbers that do not reconcile with the settlement do not drive budget or pause '
            'changes until they do.',
            '- Approval, submission and live readback are outside this offline round.',
        ),
    },
    'zh-CN': {
        'title': '# 快循环回执 · {round_id}',
        'header': '**数据截止：** {as_of}　|　**口径：** {method} v{version}　|　**快照指纹：** `{hash}`',
        'window': '**观察窗口：** {date}（{kind}，覆盖完整投放日：{full_day}）{note}',
        'window_sep': ' — ',
        'undeclared': '未声明',
        'yes': '是', 'no': '否',
        'this_round': '## 本轮结果',
        'b_findings': ('- 诊断产生 **{total} 条发现**，覆盖账户、广告组和素材；同一对象可以触发多条规则，'
                       '所以不代表 {total} 个不同对象。全部 {adsets} 个广告组见「判定明细」。'),
        'b_ready': '- `ready` **{ready} 条**：差异计划通过当前状态核对、可供审阅；`ready` 不等于获得操作授权。',
        'b_apply': '- `apply` 仅向本地台账登记 **{planned} 条差异计划 / {fields} 个拟改字段**；没有向任何平台发送。',
        'b_after': '- 对照输入的 `after` 快照：**{effective} 条匹配、{ineffective} 条不匹配**。',
        'b_settlement': '- 平台与结算对账：{counts}。数字对齐之前降为仅建议的成本类建议：**{downgraded} 条**。',
        'b_no_settlement': '- 未提供结算文件：平台数未经对账，也没有任何建议被降级。',
        'count': '{code} {n}',
        'count_sep': '　·　',
        'handle': '## 先处理这些待办',
        'flagged_head': '**闸门待确认 {n} 条**（见 `gate.json`）：',
        'flagged_none': '没有冲突或状态缺失的闸门行。',
        'unmatched_head': '**快照对照不匹配 {n} 条**（见 `reconciliation.json`）：',
        'unmatched_none': '本次已对照的行没有发现不匹配。',
        'downgraded_head': '**口径未对齐 {n} 条**（见 `findings.json` 与「平台与结算对账」）：',
        'downgraded_tail': '平台数与结算数对齐之前仅作建议，本轮不改预算或状态。',
        'downgraded_none': '没有建议被降级。',
        'open_note': ('`open` 只列台账中待对照或已对照但不匹配的行；**不包含被闸门隔离的冲突、缺失行，'
                      '不能视为完整待办**。交接时应合并查看以上各组待办。'),
        'signals': '## 账户信号',
        'signals_cols': ('账户', '平台', 'offer', '单价', 'configured 在投', 'effective 可投', '总组',
                         '今日消耗', '余额', '额度', '备注'),
        'note_tz': '账户时区 {account} != 报表时区 {report}，跨户加总前先对齐',
        'note_blocked': '{n} 个组配置为在投但实际不可投',
        'note_sep': '；',
        'settlement': '## 平台与结算对账',
        'settle_meta': ('结算日期 {date}　|　时区 {tz}　|　币种 {currency}　|　容差：花费 ±{spend}%，'
                        '结算线索数 ±{results}%（基准 = 平台线索数 × 通过率 {rate}）　|　目标 ROAS {roas}'),
        'settle_cols': ('账户', '花费：平台 → 结算', '线索：平台 → 结算（应有）', 'CPA：平台 / 结算',
                        'T / 结算口径目标', '结算 ROAS', '状态'),
        'settle_explain': ('结算 CPA 是每条「被认可线索」的花费，所以和结算口径目标（T ÷ 通过率 = 线索价值 ÷ 目标 ROAS）'
                           '比较，而不是和 T 比较。只在一侧存在的行按缺失显示，绝不补零。状态为 {downgrade_on} 的账户，'
                           '{codes} 降为仅建议（口径未对齐）。'),
        'or': '、',
        'decisions': '## 判定明细（按 ad set）',
        'decision_cols': ('ad set', '阶段', '花费', '展示', '转化', 'CPA', 'T', '止损线', '利用率', '判据'),
        'keep_observing': '保持观察',
        'cannot_classify': '无法判定：',
        'unreconciled': '仅建议：口径未对齐',
        'no_adsets': '本次没有可判定的广告组',
        'code_sep': '；',
        'drivers': '## CPA 为什么变了',
        'drivers_intro': ('CPA = CPM ÷ (1000 × CTR × CVR)，所以 CPA 的对数变化可以精确拆成 CPM、CTR、CVR 三项。'
                          '每格是该项的对数点（100 × 自然对数变化；负数表示把 CPA 往下拉）及其在总变动中的占比。'
                          '残差是报出的上期 CPA 无法解释的部分（取整）。这是会计恒等式，不是因果结论。'),
        'drivers_cols': ('ad set', '上期窗口', 'CPA：上期 → 本期', 'Δ log CPA', 'CPM', 'CTR', 'CVR', '残差', '主因'),
        'drivers_guide': '先看占比最大的一项：CVR 指向点击之后（落地页、表单、线索质量），CTR 指向钩子，CPM 指向竞价。',
        'not_decomposed': '未拆分：缺少 {missing}',
        'prior': '上期', 'current': '本期',
        'gate': '## 闸门结果与已登记的差异计划',
        'gate_cols': ('结果', '条数', '含义'),
        'gate_rows': (
            ('ready', '待审差异计划（ready）', '现值与基线一致；只列差异字段，尚未获得执行授权'),
            ('satisfied', '已满足', '目标值已就位，跳过不写'),
            ('conflict', '冲突隔离', '现值既非基线也非目标，数值本身不能说明修改者；隔离并确认'),
            ('unknown', '未知', '没读到写前状态、字段缺失或没有可用基线，先复拉'),
            ('advisory', '仅建议', '该发现不涉及写入字段或已被降级，不过闸门'),
        ),
        'plan_intro': '下表是 `apply` 登记的拟改字段，不是已经提交的操作：',
        'plan_cols': ('对象', '规则', '拟改字段'),
        'plan_none': '本轮没有待登记的差异字段',
        'advisory_line': '仅建议（{n} 条，不涉及写入，不需要过闸门）：',
        'list_sep': '、',
        'after': '## 与 after 快照逐条对照',
        'after_intro': '这里对比目标值与输入的 after 文件，不执行平台写入。',
        'after_cols': ('对象', '规则', '快照是否匹配', '原始判据'),
        'match_yes': '匹配', 'match_no': '**不匹配**',
        'after_none': '本轮没有需对照的差异计划。',
        'unchecked_head': '**本轮未对照 {n} 条，完整列出如下：**',
        'structure': '## 结构警告（不产生动作，但会影响判定可信度）',
        'handoff': '## 交接规则',
        'handoff_lines': (
            '- 「已满足」不产生差异计划；「冲突」隔离并确认原因，数值本身不能说明是谁改的。',
            '- 样本不足（展示未达判死门槛）不判素材好坏，只记录。',
            '- 能力缺口如实说明（如额度字段读回为 null），不用推断填空。',
            '- 平台数与结算数对不上时，先修口径；对齐之前不按平台数改预算或暂停。',
            '- 审批、提交与实盘回读不在这一轮离线检查之内。',
        ),
    },
}


def _cell(value):
    text = '—' if value is None else str(value)
    return text.replace('|', '\\|')


def _signed(value, scale=1, digits='0.1'):
    """``'-0.10'`` -> ``'-0.1'``; a float log term x100 -> ``'+2.5'``."""
    if value is None:
        return None
    number = Decimal(str(value)) * Decimal(scale)
    text = rules.num(number, digits)
    if text.lstrip('-').strip('0.') == '':
        text = rules.num(abs(number), digits)
    return text if text.startswith('-') else '+' + text


def _share(value):
    return rules.num(Decimal(str(value)) * rules.HUNDRED, '1') + '%'


def _note_text(note, lang):
    if isinstance(note, dict):
        return note.get(lang) or note.get('en') or ''
    return note or ''


def render_report(findings, gate_document, application, reconciliation, signal_rows, methodology,
                  lang='en'):
    rules.check_lang(lang)
    text = REPORT_TEXT[lang]
    summary = gate_document['summary']
    flagged = [item for item in gate_document['verdicts'] if item['gate'] in rules.NEEDS_HUMAN]
    unmatched = [item for item in reconciliation['rows'] if item.get('checked') and not item['effective']]
    planned_fields = sum(len(row['patch']) for row in application['write_plan'])
    settlement = findings.get('settlement')
    downgraded = [item for item in findings['proposals'] if item.get('downgraded')]

    lines = []
    add = lines.append

    def table(columns):
        add('| ' + ' | '.join(columns) + ' |')
        add('|' + '---|' * len(columns))

    add(text['title'].format(round_id=findings.get('round_id')))
    add('')
    add(f"> {NOTICES[lang]}")
    add('')
    add(text['header'].format(as_of=findings.get('as_of'),
                              method=findings['methodology']['methodology_id'],
                              version=findings['methodology']['version'],
                              hash=findings['snapshot_hash'][:12]))
    observation = findings.get('observation') or {}
    if observation:
        complete = observation.get('complete_delivery_day')
        full_day = (text['yes'] if complete else text['no']) if isinstance(complete, bool) else '—'
        note = _note_text(observation.get('note'), lang)
        add('')
        add(text['window'].format(date=observation.get('date', text['undeclared']),
                                  kind=observation.get('kind', ''), full_day=full_day,
                                  note=(text['window_sep'] + note) if note else ''))
    add('')
    add(text['this_round'])
    add('')
    add(text['b_findings'].format(total=summary['total'], adsets=len(findings['diagnostics'])))
    add(text['b_ready'].format(ready=summary[rules.READY]))
    add(text['b_apply'].format(planned=application['planned_writes'], fields=planned_fields))
    add(text['b_after'].format(effective=reconciliation['effective'],
                               ineffective=reconciliation['ineffective']))
    if settlement:
        counts = text['count_sep'].join(text['count'].format(code=code, n=count)
                                        for code, count in settlement['summary'].items() if count)
        add(text['b_settlement'].format(counts=counts, downgraded=len(downgraded)))
    else:
        add(text['b_no_settlement'])
    add('')

    # ---- what needs a person first ---------------------------------------
    add(text['handle'])
    add('')
    add(text['flagged_head'].format(n=len(flagged)))
    add('')
    if flagged:
        for item in flagged:
            add(f"- `{item['object_key']}` · {item['code']} · **{item['gate_label']}** — "
                + ' '.join(item['gate_detail']))
    else:
        add(text['flagged_none'])
    add('')
    add(text['unmatched_head'].format(n=len(unmatched)))
    add('')
    if unmatched:
        for item in unmatched:
            add(f"- `{item['object_key']}` · {item['code']} — {item['detail']}")
    else:
        add(text['unmatched_none'])
    add('')
    if settlement:
        add(text['downgraded_head'].format(n=len(downgraded)))
        add('')
        if downgraded:
            for item in downgraded:
                add(f"- `{item['object_key']}` · {item['code']} · {item['downgraded']['status']} — "
                    + item['downgraded']['detail'] + text['downgraded_tail'])
        else:
            add(text['downgraded_none'])
        add('')
    add(text['open_note'])
    add('')

    # ---- account signals ---------------------------------------------------
    add(text['signals'])
    add('')
    table(text['signals_cols'])
    for signal in signal_rows:
        notes = list(signal['capability_gaps'])
        if signal['timezone_warning']:
            notes.append(text['note_tz'].format(account=signal['account_timezone'],
                                                report=signal['report_timezone']))
        if signal['adsets_configured_live'] > signal['adsets_effective_live']:
            notes.append(text['note_blocked'].format(
                n=signal['adsets_configured_live'] - signal['adsets_effective_live']))
        add(f"| `{signal['account_key']}` | {_cell(signal.get('platform'))} | {_cell(signal['offer_key'])} | "
            f"{_cell(signal['unit_price'])} | {signal['adsets_configured_live']} | "
            f"{signal['adsets_effective_live']} | {signal['adsets_total']} | {_cell(signal['today_spend'])} | "
            f"{_cell(signal['balance'])} | {_cell(signal['spend_cap'])} | "
            f"{_cell(text['note_sep'].join(notes) or None)} |")
    add('')

    # ---- platform vs settlement --------------------------------------------
    if settlement:
        add(text['settlement'])
        add('')
        add(text['settle_meta'].format(date=_cell(settlement.get('date')), tz=_cell(settlement.get('timezone')),
                                       currency=_cell(settlement.get('currency')),
                                       spend=settlement['tolerances']['spend_pct'],
                                       results=settlement['tolerances']['results_pct'],
                                       rate=settlement['approval_rate'], roas=settlement['target_roas']))
        add('')
        table(text['settle_cols'])
        for row in settlement['rows']:
            spend_delta = _signed(row['spend_delta_pct'])
            results_delta = _signed(row['results_delta_pct'])
            spend = f"{_cell(row['platform_spend'])} → {_cell(row['settled_spend'])}"
            if spend_delta is not None:
                spend += f' ({spend_delta}%)'
            leads = f"{_cell(row['platform_results'])} → {_cell(row['settled_results'])}"
            if row['expected_settled_results'] is not None and row['side'] == 'both':
                expected = rules.num(Decimal(row['expected_settled_results']), '0.1')
                leads += f" ({expected}" + (f', {results_delta}%' if results_delta is not None else '') + ')'
            add(f"| `{row['account_key']}` | {spend} | {leads} | "
                f"{_cell(row['platform_cpa'])} / {_cell(row['settled_cpa'])} | "
                f"{_cell(row['T'])} / {_cell(row['settled_target'])} | {_cell(row['settled_roas'])} | "
                f"**{row['status']}** |")
        add('')
        for row in settlement['rows']:
            if row['status'] != rules.RECON_OK:
                add(f"- `{row['account_key']}` · {row['status']} — " + ' '.join(row['reasons']))
        add('')
        add(text['settle_explain'].format(downgrade_on=text['or'].join(settlement['downgrade_on']),
                                          codes=text['or'].join(settlement['downgrade_codes'])))
        add('')

    # ---- decisions by ad set -----------------------------------------------
    add(text['decisions'])
    add('')
    table(text['decision_cols'])
    by_object = {}
    for proposal in findings['proposals']:
        by_object.setdefault(proposal.get('object_key'), []).append(proposal)
        # A creative-level finding still belongs to its ad set row, otherwise the
        # report silently drops it from the table it logically belongs in.
        if proposal.get('parent_key') and proposal['parent_key'] != proposal.get('object_key'):
            by_object.setdefault(proposal['parent_key'], []).append(proposal)
    for values in findings['diagnostics']:
        key = values.get('adset_key')
        labels = []
        for item in by_object.get(key) or []:
            level = item['level'] + (', ' + text['unreconciled'] if item.get('downgraded') else '')
            labels.append(f"{item['code']}({level})")
        verdict = text['code_sep'].join(labels) or text['keep_observing']
        if values.get('blocked'):
            verdict = text['cannot_classify'] + values['blocked']
        utilisation = values.get('utilisation')
        utilisation = rules.pct(Decimal(utilisation)) if utilisation is not None else None
        add(f"| `{_cell(key)}` | {_cell(values.get('stage'))} | {_cell(values.get('spend'))} | "
            f"{_cell(values.get('impressions'))} | {_cell(values.get('results'))} | {_cell(values.get('cpa'))} | "
            f"{_cell(values.get('T_display'))} | {_cell(values.get('stop_loss_line'))} | {_cell(utilisation)} | "
            f"{_cell(verdict)} |")
    if not findings['diagnostics']:
        add('| — ' * (len(text['decision_cols']) - 1) + f"| {text['no_adsets']} |")
    add('')

    # ---- why CPA moved -----------------------------------------------------
    drivers = findings.get('cpa_drivers') or []
    if drivers:
        add(text['drivers'])
        add('')
        add(text['drivers_intro'])
        add('')
        table(text['drivers_cols'])
        for entry in drivers:
            change = f"{_cell(entry['prior_cpa'])} → {_cell(entry['current_cpa'])}"
            if entry['complete']:
                cells = [f"{_signed(entry['terms'][key], 100)} ({_share(entry['shares'][key])})"
                         for key in rules.DRIVER_KEYS]
                add(f"| `{entry['adset_key']}` | {_cell(entry['prior_date'])} | {change} | "
                    f"{_signed(entry['observed_total'], 100)} | {' | '.join(cells)} | "
                    f"{_signed(entry['residual'], 100)} | **{(entry['driver'] or '—').upper()}** |")
            else:
                missing = text['list_sep'].join(
                    f"{text['prior'] if name.startswith('reference.') else text['current']} "
                    f"{name.split('.', 1)[1].upper()}" for name in entry['missing'])
                add(f"| `{entry['adset_key']}` | {_cell(entry['prior_date'])} | {change} | — | — | — | — | — | "
                    f"{text['not_decomposed'].format(missing=missing)} |")
        add('')
        add(text['drivers_guide'])
        add('')

    # ---- gate --------------------------------------------------------------
    add(text['gate'])
    add('')
    table(text['gate_cols'])
    for state, label, meaning in text['gate_rows']:
        add(f'| {label} | {summary[state]} | {meaning} |')
    add('')
    add(text['plan_intro'])
    add('')
    table(text['plan_cols'])
    for item in application['write_plan']:
        patch = text['note_sep'].join(f"`{key}` → {_cell(value)}" for key, value in item['patch'].items())
        add(f"| `{item['object_key']}` | {item['code']} | {patch or '—'} |")
    if not application['write_plan']:
        add(f"| — | — | {text['plan_none']} |")
    add('')
    advisory = [item for item in gate_document['verdicts'] if item['gate'] == rules.ADVISORY]
    if advisory:
        add(text['advisory_line'].format(n=len(advisory))
            + text['list_sep'].join(f"`{item['object_key']}`·{item['code']}" for item in advisory))
        add('')

    # ---- after snapshot ----------------------------------------------------
    add(text['after'])
    add('')
    add(text['after_intro'])
    add('')
    if reconciliation['checked']:
        table(text['after_cols'])
        for item in reconciliation['rows']:
            if not item['checked']:
                continue
            add(f"| `{item['object_key']}` | {item['code']} | "
                f"{text['match_yes'] if item['effective'] else text['match_no']} | {_cell(item['detail'])} |")
    else:
        add(text['after_none'])
    unchecked = [item for item in reconciliation['rows'] if not item['checked']]
    if unchecked:
        add('')
        add(text['unchecked_head'].format(n=len(unchecked)))
        add('')
        for item in unchecked:
            add(f"- `{item['object_key']}` · {item.get('code', '—')} — {item['reason']}")
    add('')
    if findings['structure_findings']:
        add(text['structure'])
        add('')
        for item in findings['structure_findings']:
            add(f"- `{item['object_key']}` — {item['detail']}")
        add('')
    add(text['handoff'])
    add('')
    for line in text['handoff_lines']:
        add(line)
    add('')
    return '\n'.join(lines) + '\n'


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def write_findings(out, findings, signal_rows):
    save(Path(out) / 'findings.json', findings)
    save(Path(out) / 'account-signals.json', {'kind': 'account_signals', 'rows': signal_rows})


def build_parser():
    parser = argparse.ArgumentParser(description=NOTICE)
    commands = parser.add_subparsers(dest='command', required=True)

    def lang(p):
        p.add_argument('--lang', choices=rules.LANGUAGES, default='en',
                       help='language of the report, labels and evidence (default en)')

    p = commands.add_parser('diagnose', help='Classify every ad set and check platform vs settlement')
    p.add_argument('--snapshot', required=True)
    p.add_argument('--methodology', required=True)
    p.add_argument('--settlement', default='')
    p.add_argument('--out', required=True)
    lang(p)

    p = commands.add_parser('gate', help='Five-state write gate against a fresh writeback snapshot')
    p.add_argument('--findings', required=True)
    p.add_argument('--writeback', required=True)
    p.add_argument('--out', required=True)
    lang(p)

    p = commands.add_parser('apply', help='Record the gated rows into an append-only ledger')
    p.add_argument('--gate', required=True)
    p.add_argument('--ledger', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--at', default='')
    lang(p)

    p = commands.add_parser('verify', help='Reconcile the state read after writing')
    p.add_argument('--gate', required=True)
    p.add_argument('--after', required=True)
    p.add_argument('--ledger', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--at', default='')
    lang(p)

    p = commands.add_parser('open', help='Show rows still awaiting or failing verification')
    p.add_argument('--ledger', required=True)
    lang(p)

    p = commands.add_parser('round', help='Run the whole loop end to end in one command')
    p.add_argument('--snapshot', required=True)
    p.add_argument('--writeback', required=True)
    p.add_argument('--after', required=True)
    p.add_argument('--methodology', required=True)
    p.add_argument('--settlement', default='')
    p.add_argument('--ledger', default='')
    p.add_argument('--out', required=True)
    p.add_argument('--at', default='')
    lang(p)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    notice = NOTICES[args.lang]
    try:
        if args.command == 'round':
            return _command_round(args)
        if args.command == 'diagnose':
            methodology = rules.load_methodology(args.methodology)
            snapshot = load(args.snapshot)
            settlement = load(args.settlement) if args.settlement else None
            findings = collect_findings(snapshot, methodology, settlement, args.lang)
            signals = account_signals(snapshot, methodology, args.lang)
            write_findings(args.out, findings, signals)
            print(json.dumps({'notice': notice, 'kind': findings['kind'],
                              'accounts': len(findings['accounts']),
                              'proposals': len(findings['proposals']),
                              'structure_findings': len(findings['structure_findings']),
                              'settlement': (findings['settlement'] or {}).get('summary'),
                              'measurement_unreconciled': sum(1 for p in findings['proposals']
                                                              if p.get('downgraded')),
                              'out': str(args.out)}, ensure_ascii=False))
            return 0
        if args.command == 'gate':
            findings = load(args.findings)
            gate_document = run_gate(findings, load(args.writeback), args.lang)
            save(Path(args.out) / 'gate.json', gate_document)
            print(json.dumps({'notice': notice, 'summary': gate_document['summary'],
                              'write_plan': len(gate_document['write_plan'])}, ensure_ascii=False))
            return 0
        if args.command == 'apply':
            gate_document = load(args.gate)
            application = apply_gate(args.ledger, gate_document, timestamp(args.at), args.lang)
            save(Path(args.out) / 'application.json', application)
            print(json.dumps({'notice': notice, 'planned_writes': application['planned_writes'],
                              'not_written': len(application['not_written'])}, ensure_ascii=False))
            return 0
        if args.command == 'verify':
            gate_document = load(args.gate)
            result = reconcile_and_record(args.ledger, gate_document, load(args.after), timestamp(args.at),
                                          args.lang)
            save(Path(args.out) / 'reconciliation.json', result)
            print(json.dumps({'notice': notice, 'checked': result['checked'],
                              'effective': result['effective'],
                              'ineffective': result['ineffective']}, ensure_ascii=False))
            return 0
        if args.command == 'open':
            rows = open_rows(args.ledger)
            print(json.dumps({'notice': notice, 'open': len(rows), 'rows': rows},
                             ensure_ascii=False, indent=2))
            return 0
        raise LoopError(f'Unknown command: {args.command}')
    except (rules.RuleError, LoopError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


def _command_round(args):
    at = timestamp(args.at)
    lang = args.lang
    out = Path(args.out)
    methodology = rules.load_methodology(args.methodology)
    snapshot = load(args.snapshot)
    writeback = load(args.writeback)
    after = load(args.after)
    settlement = load(args.settlement) if args.settlement else None
    ledger = args.ledger or str(out / 'ledger.jsonl')

    findings = collect_findings(snapshot, methodology, settlement, lang)
    signals = account_signals(snapshot, methodology, lang)
    write_findings(out, findings, signals)

    gate_document = run_gate(findings, writeback, lang)
    save(out / 'gate.json', gate_document)

    application = apply_gate(ledger, gate_document, at, lang)
    save(out / 'application.json', application)

    reconciliation = reconcile_and_record(ledger, gate_document, after, at, lang)
    save(out / 'reconciliation.json', reconciliation)

    report = render_report(findings, gate_document, application, reconciliation, signals, methodology, lang)
    (out / 'report.md').write_text(report, encoding='utf-8')

    still_open = open_rows(ledger)
    summary = {
        'notice': NOTICES[lang],
        'mode': 'offline_analysis_only',
        'lang': lang,
        'round_id': findings.get('round_id'),
        'snapshot_hash': findings['snapshot_hash'],
        'accounts': len(findings['accounts']),
        'proposals': len(findings['proposals']),
        'gate': gate_document['summary'],
        'planned_writes': application['planned_writes'],
        'reconciliation': {'checked': reconciliation['checked'],
                           'effective': reconciliation['effective'],
                           'ineffective': reconciliation['ineffective']},
        'settlement': (findings['settlement'] or {}).get('summary'),
        'measurement_unreconciled': sum(1 for p in findings['proposals'] if p.get('downgraded')),
        'open_rows': len(still_open),
        'ledger': ledger,
        'out': str(out),
        'artifacts': sorted(p.name for p in out.iterdir() if p.is_file()),
        'native_platform_calls': 0,
    }
    save(out / 'round-summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
