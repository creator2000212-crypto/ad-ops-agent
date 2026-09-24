#!/usr/bin/env python3
"""Runnable reference implementation of a recurring paid-media operating loop.

Offline only. No network, no platform SDK, no credentials, no account writes.
Everything here reads declared JSON, applies the rules in ``operating_rules.py``,
and writes reviewable artifacts plus an append-only ledger of proposals.

The loop is the one an operator actually runs, not an abstraction of it:

  0  re-verify what the previous round proposed          -> kept in the ledger
  1  collect one settled observation window               -> ``*snapshot*.json``
  2  classify every ad set against the declared ladder    -> ``diagnose`` / ``decide``
  3  turn findings into proposals with evidence           -> ``proposals.json``
  4  pass the write gate before touching anything         -> ``gate``
  5  record the round in an append-only ledger            -> ``apply``
  6  reconcile what was actually written, then report     -> ``verify`` / ``report``

Steps 2 to 6 exist because the interesting failures are not arithmetic mistakes.
They are: acting on a sample too small to judge, treating a failed write as a
successful one, and overwriting a change a human made while the round was being
prepared. Each of those has an explicit guard below.

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
import hashlib
import json
from pathlib import Path
import sys

import operating_rules as rules

NOTICE = ('OFFLINE ANALYSIS ONLY — 不连接任何广告平台、不写任何账户、不上传素材。'
          '输出的动作清单是给人审阅的建议，不是已执行的指令。')
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
            raise LoopError(f'不是合法 JSON：{path}（{exc}）') from exc


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
        raise LoopError("快照的 kind 必须是 operating_snapshot。")
    if not snapshot.get('as_of'):
        raise LoopError('快照缺少 as_of —— 不知道数据截止时间，就无法谈成熟度。')
    accounts = snapshot.get('accounts')
    if not isinstance(accounts, list) or not accounts:
        raise LoopError('快照必须包含至少一个账户。')
    seen = set()
    for account in accounts:
        for key in ('account_key', 'platform'):
            if not account.get(key):
                raise LoopError(f'账户缺少 {key}：{account}')
        if account['platform'] not in PLATFORMS:
            raise LoopError(f"平台必须是 {sorted(PLATFORMS)} 之一：{account['platform']}")
        if account['account_key'] in seen:
            raise LoopError(f"账户 key 重复：{account['account_key']}")
        seen.add(account['account_key'])
        offer = account.get('offer') or {}
        if not offer.get('offer_key'):
            raise LoopError(f"账户 {account['account_key']} 缺少 offer.offer_key。")
        if offer.get('unit_price') is None:
            # Without a unit price there is no T, and without T none of the cost
            # rules are meaningful. Refuse rather than invent a default.
            raise LoopError(f"账户 {account['account_key']} 缺少 offer.unit_price —— 没有 T 就无法判定成本。")
    return snapshot


def observation_of(document):
    """Accept either an ``operating_snapshot`` or a ``writeback_snapshot``."""
    kind = (document or {}).get('kind')
    if kind not in ('operating_snapshot', 'writeback_snapshot'):
        raise LoopError(f'期望 operating_snapshot 或 writeback_snapshot，实际为 {kind!r}。')
    return document


def collect_findings(snapshot, methodology):
    """Step 2. Every account is classified; nothing is decided yet."""
    validate_snapshot(snapshot)
    accounts, all_proposals, all_diagnostics, structure = [], [], [], []
    for account in snapshot['accounts']:
        proposals, diagnostics = rules.decide_account(account, methodology)
        accounts.append(account['account_key'])
        all_proposals.extend(proposals)
        all_diagnostics.extend(diagnostics)
        structure.extend([{'account_key': account['account_key'], **item}
                          for item in rules.structure_findings(account, methodology)])
    return {
        'schema_version': 1,
        'kind': 'operating_findings',
        'notice': NOTICE,
        'as_of': snapshot['as_of'],
        'round_id': snapshot.get('round_id'),
        'observation': snapshot.get('observation'),
        'snapshot_hash': digest(snapshot),
        'methodology': {'methodology_id': methodology['methodology_id'], 'version': methodology['version']},
        'methodology_hash': digest(methodology),
        'accounts': accounts,
        'diagnostics': all_diagnostics,
        'proposals': all_proposals,
        'structure_findings': structure,
    }


def account_signals(snapshot, methodology):
    """Account-level facts worth stating before any per-adset action."""
    signals = []
    for account in snapshot['accounts']:
        adsets = account.get('adsets') or []
        # Two different questions: is it configured to run, and is it actually
        # able to serve. Collapsing them hides rejection and billing problems.
        configured_live = [a for a in adsets if a.get('configured_status') == 'ACTIVE']
        effective_live = [a for a in configured_live if a.get('effective_status') == 'ACTIVE']
        signals.append({
            'account_key': account['account_key'],
            'offer_key': (account.get('offer') or {}).get('offer_key'),
            'reward_code': (account.get('offer') or {}).get('unit_price'),
            'account_timezone': account.get('account_timezone'),
            'report_timezone': account.get('report_timezone'),
            'adsets_total': len(adsets),
            'adsets_configured_live': len(configured_live),
            'adsets_effective_live': len(effective_live),
            'today_spend': account.get('today_spend'),
            'balance': account.get('balance'),
            'spend_cap': account.get('spend_cap'),
            'capability_gaps': (['spend_cap 读回为 null，余量预警不可用']
                                if account.get('spend_cap') is None else []),
            'timezone_warning': (account.get('account_timezone') != account.get('report_timezone')),
        })
    return signals


# --------------------------------------------------------------------------
# step 4: the write gate
# --------------------------------------------------------------------------

def run_gate(findings, writeback):
    observation_of(writeback)
    verdicts = rules.gate(findings['proposals'], writeback)
    return {
        'schema_version': 1,
        'kind': 'operating_gate',
        'notice': NOTICE,
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

def append_events(ledger, events):
    if not events:
        return
    path = Path(ledger)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False) + '\n')


def read_events(ledger):
    path = Path(ledger)
    if not path.exists():
        return []
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


def apply_gate(ledger, gate_document, at):
    """Step 5. Record every gated row. Only ``ready`` rows produce a write plan."""
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
                           'reason': '已满足：目标值已就位，写了等于一次无意义的 significant edit。', 'at': at})
        elif verdict['gate'] == rules.CONFLICT:
            events.append({'type': 'skipped', 'id': row_id, 'code': verdict['code'],
                           'object_key': verdict['object_key'],
                           'reason': '冲突隔离：现值既非基线也非目标，交给人确认，不覆盖。', 'at': at})
        elif verdict['gate'] == rules.UNKNOWN:
            # Recorded, not forgotten: an unread state is an open item that must
            # come back next round, not a row that quietly disappears.
            events.append({'type': 'skipped', 'id': row_id, 'code': verdict['code'],
                           'object_key': verdict['object_key'],
                           'reason': '未知：没读到写前状态或字段缺失，先复拉再判。', 'at': at})
    append_events(ledger, events)
    return {
        'schema_version': 1,
        'kind': 'operating_application',
        'notice': NOTICE,
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


def reconcile_and_record(ledger, gate_document, after, at):
    observation_of(after)
    report = rules.reconcile(gate_document['verdicts'], after.get('objects') or {})
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
        'notice': NOTICE,
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

def render_report(findings, gate_document, application, reconciliation, settlement, signal_rows):
    summary = gate_document['summary']
    flagged = [item for item in gate_document['verdicts'] if item['gate'] in rules.NEEDS_HUMAN]
    unmatched = [item for item in reconciliation['rows'] if item.get('checked') and not item['effective']]
    planned_fields = sum(len(row['patch']) for row in application['write_plan'])

    def display(value):
        return '—' if value is None else str(value)

    lines = []
    add = lines.append
    add(f"# 快循环回执 · {findings.get('round_id')}")
    add('')
    add(f"> {NOTICE}")
    add('')
    add(f"**数据截止：** {findings.get('as_of')}　|　"
        f"**口径：** {findings['methodology']['methodology_id']} "
        f"v{findings['methodology']['version']}　|　"
        f"**快照指纹：** `{findings['snapshot_hash'][:12]}`")
    observation = findings.get('observation') or {}
    if observation:
        add('')
        add(f"**观察窗口：** {observation.get('date', '未声明')}"
            f"（{observation.get('kind', '')}，覆盖完整投放日："
            f"{('是' if observation['complete_delivery_day'] else '否') if isinstance(observation.get('complete_delivery_day'), bool) else '—'}）"
            f"{' — ' + observation['note'] if observation.get('note') else ''}")
    add('')
    add('## 本轮结果')
    add('')
    add(f"- 诊断产生 **{summary['total']} 条发现**，不代表 {summary['total']} 个不同对象。"
        f"发现覆盖账户、广告组和素材；同一对象可以触发多条规则，下方列出全部 {len(findings['diagnostics'])} 个广告组的诊断。")
    add(f"- `ready` **{summary[rules.READY]} 条**表示差异计划通过当前快照核对、可供审阅，**不表示已获操作授权**。")
    add(f"- `apply` 仅向本地台账登记 **{application['planned_writes']} 条差异计划 / {planned_fields} 个拟改字段**；没有调用平台或写入广告账户。")
    add(f"- 对照输入的 `after` 快照：**{reconciliation['effective']} 条匹配、{reconciliation['ineffective']} 条不匹配**。"
        '演示使用预置快照，这些结果不证明真实修改已经生效。')
    add('')
    add('## 先处理这些待办')
    add('')
    add(f"**闸门待确认 {len(flagged)} 条**（见 `gate.json`）：")
    add('')
    if flagged:
        for item in flagged:
            add(f"- `{item['object_key']}` · {item['code']} · **{item['gate_label']}** — "
                + ' '.join(item['gate_detail']))
    else:
        add('没有冲突或状态缺失的闸门行。')
    add('')
    add(f"**快照对照不匹配 {len(unmatched)} 条**（见 `reconciliation.json`）：")
    add('')
    if unmatched:
        for item in unmatched:
            add(f"- `{item['object_key']}` · {item['code']} — {item['detail']}")
    else:
        add('本次已对照的行没有发现不匹配。')
    add('')
    add('`open` 只列台账中待对照或已对照但不匹配的行；**不包含被闸门隔离的冲突、缺失行，不能视为完整待办**。'
        '交接时应合并查看以上两组待办。规则原文中的“生效/未生效”仅指本次快照值是否匹配。')
    add('')
    add('## 账户信号')
    add('')
    add('| 账户 | offer | 单价 | configured 在投 | effective 可投 | 总组 | 今日消耗 | 余额 | 额度 | 备注 |')
    add('|---|---|---|---|---|---|---|---|---|---|')
    for signal in signal_rows:
        notes = []
        if signal['capability_gaps']:
            notes.append('；'.join(signal['capability_gaps']))
        if signal['timezone_warning']:
            notes.append(f"账户时区 {signal['account_timezone']} != 报表时区 {signal['report_timezone']}，跨户加总前先对齐")
        if signal['adsets_configured_live'] > signal['adsets_effective_live']:
            notes.append(f"{signal['adsets_configured_live'] - signal['adsets_effective_live']} 个组配置为在投但实际不可投")
        add(f"| `{signal['account_key']}` | {signal['offer_key']} | {signal['reward_code']} | "
            f"{signal['adsets_configured_live']} | {signal['adsets_effective_live']} | "
            f"{signal['adsets_total']} | {signal['today_spend']} | "
            f"{display(signal['balance'])} | {display(signal['spend_cap'])} | {'；'.join(notes) or '—'} |")
    add('')
    add('## 判定明细（按 ad set）')
    add('')
    add('| ad set | 阶段 | 花费 | 展示 | 转化 | CPA | T | 止损线 | 利用率 | 判据 |')
    add('|---|---|---|---|---|---|---|---|---|---|')
    by_object = {}
    for proposal in findings['proposals']:
        by_object.setdefault(proposal.get('object_key'), []).append(proposal)
        # A creative-level finding still belongs to its ad set row, otherwise the
        # report silently drops it from the table it logically belongs in.
        if proposal.get('parent_key') and proposal['parent_key'] != proposal.get('object_key'):
            by_object.setdefault(proposal['parent_key'], []).append(proposal)
    for values in findings['diagnostics']:
        key = values.get('adset_key')
        codes = by_object.get(key) or []
        verdict = '；'.join(f"{item['code']}({item['level']})" for item in codes) or '保持观察'
        if values.get('blocked'):
            verdict = '无法判定：' + values['blocked']
        add(f"| `{display(key)}` | {display(values.get('stage'))} | {display(values.get('spend'))} | {display(values.get('impressions'))} | "
            f"{display(values.get('results'))} | {display(values.get('cpa'))} | {display(values.get('T_display'))} | "
            f"{display(values.get('stop_loss_line'))} | {display(values.get('utilisation'))} | {verdict} |")
    if not findings['diagnostics']:
        add('| — | — | — | — | — | — | — | — | — | 本次没有可判定的广告组 |')
    add('')
    add('## 闸门结果与已登记的差异计划')
    add('')
    add('| 结果 | 条数 | 含义 |')
    add('|---|---|---|')
    add(f"| 待审差异计划（ready） | {summary[rules.READY]} | 现值与基线一致；只列差异字段，尚未获得执行授权 |")
    add(f"| 已满足 | {summary[rules.SATISFIED]} | 目标值已就位，跳过不写 |")
    add(f"| 冲突隔离 | {summary[rules.CONFLICT]} | 检测到状态不一致，无法判定修改者；隔离并确认 |")
    add(f"| 未知 | {summary[rules.UNKNOWN]} | 没读到写前状态或字段缺失，先复拉 |")
    add(f"| 仅建议 | {summary[rules.ADVISORY]} | 该发现不涉及写入字段，不过闸门 |")
    add('')
    add('下表是 `apply` 登记的拟改字段，不是已经提交的操作：')
    add('')
    add('| 对象 | 规则 | 拟改字段 |')
    add('|---|---|---|')
    for item in application['write_plan']:
        patch = '；'.join(f"`{key}` → {display(value)}" for key, value in item['patch'].items())
        add(f"| `{item['object_key']}` | {item['code']} | {patch or '—'} |")
    if not application['write_plan']:
        add('| — | — | 本轮没有待登记的差异字段 |')
    add('')
    advisory = [item for item in gate_document['verdicts'] if item['gate'] == rules.ADVISORY]
    if advisory:
        add(f'仅建议（{len(advisory)} 条，不涉及写入，不需要过闸门）：'
            + '、'.join(f"`{item['object_key']}`·{item['code']}" for item in advisory))
        add('')
    add('## 与 after 快照逐条对照')
    add('')
    add('这里对比目标值与输入快照，不执行平台写入。说明列保留原始判据，其中“生效”不代表真实操作已完成。')
    add('')
    if reconciliation['checked']:
        add('| 对象 | 规则 | 快照是否匹配 | 原始判据 |')
        add('|---|---|---|---|')
        for item in reconciliation['rows']:
            if not item['checked']:
                continue
            add(f"| `{item['object_key']}` | {item['code']} | "
                f"{'匹配' if item['effective'] else '**不匹配**'} | {item['detail']} |")
    else:
        add('本轮没有需对照的差异计划。')
    unchecked = [item for item in reconciliation['rows'] if not item['checked']]
    if unchecked:
        add('')
        add(f"**本轮未对照 {len(unchecked)} 条，完整列出如下：**")
        add('')
        for item in unchecked:
            add(f"- `{item['object_key']}` · {item.get('code', '—')} — {item['reason']}")
    add('')
    if settlement:
        add('## 结算口径对账')
        add('')
        basis = settlement.get('cost_basis') or {}
        add(f"日期 {settlement.get('date')}　|　目标 ROAS {basis.get('target_roas')}　|　"
            f"混量成本 {basis.get('mixed_traffic_cost_per_result')}/转化")
        add('')
        add('| 平台 | 账户 | 单价 | 花费 | 转化 | 收入 | 盘面 CPA | 目标 CPA(T) | ROAS |')
        add('|---|---|---|---|---|---|---|---|---|')
        for row in settlement.get('rows', []):
            unit = rules.dec(row.get('unit_price'), 'unit_price')
            spend = rules.dec(row.get('spend'), 'spend')
            results = rules.integer(row.get('results'), 'results')
            value = rules.dec(row.get('value'), 'value')
            target = (rules.target_cost(unit, {'target_roas': basis.get('target_roas') or '0.85'})
                      if unit else None)
            cpa = rules.ratio(spend, rules.Decimal(results)) if results else None
            roas = rules.ratio(value, spend) if spend else None
            add(f"| {row.get('platform')} | `{row.get('account_key')}` | {row.get('unit_price')} | "
                f"{row.get('spend')} | {row.get('results')} | {row.get('value')} | "
                f"{rules.num2(cpa) or '—'} | {rules.num2(rules.money(target)) if target else '—'} | "
                f"{rules.num(roas, '0.0001') or '—'} |")
        add('')
        for rule in settlement.get('reconciliation_rules', []):
            add(f"- {rule}")
        add('')
    if findings['structure_findings']:
        add('## 结构警告（不产生动作，但会影响判定可信度）')
        add('')
        for item in findings['structure_findings']:
            add(f"- `{item['object_key']}` — {item['detail']}")
        add('')
    add('## 交接边界')
    add('')
    add('- 本轮只生成建议、登记本地台账并对照快照；真实 API 接入、操作授权、提交和平台回读仍需后续独立实现。')
    add('- 「已满足」不产生差异计划；「冲突」隔离并确认原因，不推断修改者。')
    add('- 样本不足（展示未达判死门槛）不判素材好坏，只记录。')
    add('- 能力缺口如实说明（如额度字段读回为 null），不用推断填空。')
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

    p = commands.add_parser('diagnose', help='Classify every ad set in one settled snapshot')
    p.add_argument('--snapshot', required=True)
    p.add_argument('--methodology', required=True)
    p.add_argument('--out', required=True)

    p = commands.add_parser('gate', help='Four-way write gate against a fresh writeback snapshot')
    p.add_argument('--findings', required=True)
    p.add_argument('--writeback', required=True)
    p.add_argument('--out', required=True)

    p = commands.add_parser('apply', help='Record the gated rows into an append-only ledger')
    p.add_argument('--gate', required=True)
    p.add_argument('--ledger', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--at', default='')

    p = commands.add_parser('verify', help='Reconcile the state read after writing')
    p.add_argument('--gate', required=True)
    p.add_argument('--after', required=True)
    p.add_argument('--ledger', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--at', default='')

    p = commands.add_parser('open', help='Show rows still awaiting or failing verification')
    p.add_argument('--ledger', required=True)

    p = commands.add_parser('round', help='Run the whole loop end to end in one command')
    p.add_argument('--snapshot', required=True)
    p.add_argument('--writeback', required=True)
    p.add_argument('--after', required=True)
    p.add_argument('--methodology', required=True)
    p.add_argument('--settlement', default='')
    p.add_argument('--ledger', default='')
    p.add_argument('--out', required=True)
    p.add_argument('--at', default='')
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == 'round':
            return _command_round(args)
        if args.command == 'diagnose':
            methodology = rules.load_methodology(args.methodology)
            snapshot = load(args.snapshot)
            findings = collect_findings(snapshot, methodology)
            signals = account_signals(snapshot, methodology)
            write_findings(args.out, findings, signals)
            print(json.dumps({'notice': NOTICE, 'kind': findings['kind'],
                              'accounts': len(findings['accounts']),
                              'proposals': len(findings['proposals']),
                              'structure_findings': len(findings['structure_findings']),
                              'out': str(args.out)}, ensure_ascii=False))
            return 0
        if args.command == 'gate':
            findings = load(args.findings)
            gate_document = run_gate(findings, load(args.writeback))
            save(Path(args.out) / 'gate.json', gate_document)
            print(json.dumps({'notice': NOTICE, 'summary': gate_document['summary'],
                              'write_plan': len(gate_document['write_plan'])}, ensure_ascii=False))
            return 0
        if args.command == 'apply':
            gate_document = load(args.gate)
            application = apply_gate(args.ledger, gate_document, timestamp(args.at))
            save(Path(args.out) / 'application.json', application)
            print(json.dumps({'notice': NOTICE, 'planned_writes': application['planned_writes'],
                              'not_written': len(application['not_written'])}, ensure_ascii=False))
            return 0
        if args.command == 'verify':
            gate_document = load(args.gate)
            result = reconcile_and_record(args.ledger, gate_document, load(args.after), timestamp(args.at))
            save(Path(args.out) / 'reconciliation.json', result)
            print(json.dumps({'notice': NOTICE, 'checked': result['checked'],
                              'effective': result['effective'],
                              'ineffective': result['ineffective']}, ensure_ascii=False))
            return 0
        if args.command == 'open':
            rows = open_rows(args.ledger)
            print(json.dumps({'notice': NOTICE, 'open': len(rows), 'rows': rows},
                             ensure_ascii=False, indent=2))
            return 0
        raise LoopError(f'未知命令：{args.command}')
    except (rules.RuleError, LoopError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


def _command_round(args):
    at = timestamp(args.at)
    out = Path(args.out)
    methodology = rules.load_methodology(args.methodology)
    snapshot = load(args.snapshot)
    writeback = load(args.writeback)
    after = load(args.after)
    settlement = load(args.settlement) if args.settlement else None
    ledger = args.ledger or str(out / 'ledger.jsonl')

    findings = collect_findings(snapshot, methodology)
    signals = account_signals(snapshot, methodology)
    write_findings(out, findings, signals)

    gate_document = run_gate(findings, writeback)
    save(out / 'gate.json', gate_document)

    application = apply_gate(ledger, gate_document, at)
    save(out / 'application.json', application)

    reconciliation = reconcile_and_record(ledger, gate_document, after, at)
    save(out / 'reconciliation.json', reconciliation)

    report = render_report(findings, gate_document, application, reconciliation, settlement, signals)
    (out / 'report.md').write_text(report, encoding='utf-8')

    still_open = open_rows(ledger)
    summary = {
        'notice': NOTICE,
        'mode': 'offline_analysis_only',
        'round_id': findings.get('round_id'),
        'snapshot_hash': findings['snapshot_hash'],
        'accounts': len(findings['accounts']),
        'proposals': len(findings['proposals']),
        'gate': gate_document['summary'],
        'planned_writes': application['planned_writes'],
        'reconciliation': {'checked': reconciliation['checked'],
                           'effective': reconciliation['effective'],
                           'ineffective': reconciliation['ineffective']},
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
