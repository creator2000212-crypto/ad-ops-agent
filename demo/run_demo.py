#!/usr/bin/env python3
"""Replay one round of the 12-hour check on fictional data and print the report.

    python3 demo/run_demo.py                 # run the round, print the English report
    python3 demo/run_demo.py --lang zh-CN    # the same round in Chinese
    python3 demo/run_demo.py --steps         # the five steps one at a time
    python3 demo/run_demo.py --check         # compare both languages with demo/expected/
    python3 demo/run_demo.py --refresh       # rewrite demo/expected/ from this run

`ready` means a change passed the state check; it is not approval. `apply` only
records a local ledger, and the after snapshot is a prepared file. No network
call, no credentials, no account write.
"""
import argparse
import difflib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURES = ROOT / 'examples' / 'operating'
EXPECTED = HERE / 'expected'
LANGUAGES = ('en', 'zh-CN')
REPORT_NAMES = {'en': 'report.md', 'zh-CN': 'report.zh-CN.md'}
# Pinned so the ledger timestamps in the demo are stable; the classifications do
# not depend on the clock at all.
DEMO_TIMESTAMP = '2026-09-24T03:58:00+00:00'
VERIFY_TIMESTAMP = '2026-09-24T04:05:00+00:00'

FIXTURE_ARGS = (
    ('--snapshot', FIXTURES / 'snapshot-primary.json'),
    ('--writeback', FIXTURES / 'writeback-snapshot.json'),
    ('--after', FIXTURES / 'after-snapshot.json'),
    ('--methodology', FIXTURES / 'methodology-reference.json'),
    ('--settlement', FIXTURES / 'settlement-daily.json'),
)

TEXT = {
    'en': {
        'round_failed': 'The offline round failed:\n',
        'step_failed': 'An offline step failed:\n',
        'refreshed': 'Updated {path}/ from this offline run (both languages); no platform call.',
        'differs': '{name}: the committed sample differs from this offline run',
        'missing': '{name}: no committed sample',
        'languages_differ': 'summary.json: the English and Chinese runs reached different decisions',
        'check_failed': 'The committed sample no longer matches the program output:',
        'check_hint': 'Regenerate with --refresh and review the diff before committing.',
        'check_ok': 'Sample check passed: {path}/ matches this offline run byte for byte, in both languages.',
        'banner': ('Offline replay: {accounts} accounts / {proposals} findings (findings are not objects; '
                   'one object can trigger several rules)'),
        'gate': ('  Gate: ready {ready} | satisfied {satisfied} | conflict {conflict} | unknown {unknown} | '
                 'advisory {advisory}'),
        'apply': ('  apply only records {planned} planned changes / {fields} fields; ready is not approval, '
                  'and nothing is written to an account.'),
        'after': '  Against the prepared after snapshot: {effective} matched, {ineffective} did not.',
        'settlement': '  Platform vs settlement: {counts}; held as advisory (measurement unreconciled): {held}',
        'human': '  Gate rows needing a human: {n}: {rows}',
        'mismatch': '  After-snapshot mismatches: {n}: {rows}',
        'open': ('  open lists the {n} unclosed ledger row(s) only, not gate conflicts or missing state; '
                 'hand over both.'),
        'calls': '  Platform calls: {n}',
        'none': 'none',
        'all_output': 'All output: {path}',
        'sample': 'Committed sample: {path} (--check compares it with a fresh run)',
        'hint': 'Tip: --steps walks through the same round one step at a time',
        'step': 'Step {n} · {title}',
        'inputs': '  Inputs:  ',
        'does': '  Does:    ',
        'outputs': '  Outputs: ',
        's1': ('Diagnose',
               'fictional snapshot-primary.json, the declared methodology and settlement-daily.json.',
               'derive metrics, apply the rules and check each account against the settlement; findings '
               'are proposals for review.',
               '{path}, plus account signals.'),
        's1_counts': ('  Accounts {accounts}; findings {proposals}; structure warnings {structure}; '
                      'settlement {settlement}; measurement unreconciled {held}.'),
        's1_codes': '→ {n} findings across {kinds} rules: {codes}',
        's2': ('Gate',
               'the findings from step 1 and the prepared writeback-snapshot.json.',
               'compare baseline, target and current value; ready only marks a change ready for review.',
               '{path}, with the difference plan, conflicts and missing state.'),
        's2_counts': ('  ready {ready} | satisfied {satisfied} | conflict {conflict} | unknown {unknown} | '
                      'advisory {advisory}'),
        's2_next': ('→ Hold conflicting rows and check where the difference came from; supply evidence for '
                    'missing state. Every other row stands on its own result.'),
        's3': ('Record',
               'gate.json from step 2.',
               'apply records planned fields and skip reasons in the local ledger; no API call, no account '
               'write.',
               '{path} and {ledger}.'),
        's3_counts': '  Recorded {planned} planned changes / {fields} fields; appended {events} ledger events.',
        's3_row': '  → {key}  {code}  planned {patch}',
        's4': ('Compare',
               'the difference plan and the prepared after-snapshot.json, which is not a platform readback.',
               'compare each target with the snapshot and record match or mismatch.',
               '{path}, and comparison events in the same step ledger.'),
        's4_counts': '  Compared {checked}; matched {effective}; did not match {ineffective}.',
        's4_row': '  ✗ {key} did not match — {detail}',
        's5': ('Hand over',
               'the step ledger, plus the conflict and missing-state rows from gate.json.',
               'open lists ledger rows awaiting comparison or failing it; add the gate rows so nothing is '
               'dropped.',
               'the open rows in the terminal; the full to-do list also needs gate.json and '
               'reconciliation.json.'),
        's5_counts': '  open: {n} row(s):',
        's5_row': '  → {key} · {status} · planned {patch}',
        's5_gate': '  Also needing a human, not in open: {n}: {rows}',
        's5_next': '→ Here open holds only the after-snapshot mismatch; it is not the whole to-do list.',
        'assembled': 'Next, round runs independently on the same fictional inputs and writes the full report.',
        'step_ledger': '  Step ledger:   {path}',
        'round_ledger': '  Round ledger:  {path} (a separate ledger, not a continuation of the steps)',
        'committed': '  {path}   ← committed in the repository',
        'copy': '  {path}   ← this run\'s copy',
    },
    'zh-CN': {
        'round_failed': '离线汇总运行失败：\n',
        'step_failed': '离线步骤运行失败：\n',
        'refreshed': '已用本次离线输出更新 {path}/（两种语言）；没有平台调用。',
        'differs': '{name}：已提交样例与本次离线输出不一致',
        'missing': '{name}：缺少已提交的样例',
        'languages_differ': 'summary.json：英文与中文运行得出的判定不一致',
        'check_failed': '样例与当前程序的离线输出出现差异：',
        'check_hint': '请用 --refresh 重新生成样例，并在提交前审阅差异。',
        'check_ok': '样例检查通过：{path}/ 与本次离线输出逐字节一致（两种语言）。',
        'banner': '离线演示：{accounts} 个账户 / {proposals} 条发现（发现数不等于对象数）',
        'gate': '  闸门：待审差异计划 {ready}｜已满足 {satisfied}｜冲突隔离 {conflict}｜未知 {unknown}｜仅建议 {advisory}',
        'apply': '  apply 只登记 {planned} 条差异计划 / {fields} 个拟改字段；ready 不等于授权，没有账户写入。',
        'after': '  与预置 after 快照对照：{effective} 条匹配、{ineffective} 条不匹配。',
        'settlement': '  平台与结算对账：{counts}；口径未对齐、降为仅建议：{held}',
        'human': '  闸门待确认 {n} 条：{rows}',
        'mismatch': '  对照不匹配 {n} 条：{rows}',
        'open': '  open 只列台账未闭合的 {n} 条，不包含闸门冲突/缺失；两部分需要一起交接。',
        'calls': '  平台调用次数：{n}',
        'none': '无',
        'all_output': '全部产出：{path}',
        'sample': '对照样例：{path}（--check 会核对它与新跑结果是否一致）',
        'hint': '提示：想看逐步展开的过程，用 --steps',
        'step': '第 {n} 步 · {title}',
        'inputs': '  输入：',
        'does': '  做什么：',
        'outputs': '  输出：',
        's1': ('诊断',
               '虚构观察快照 snapshot-primary.json、声明的方法论与 settlement-daily.json。',
               '推导指标、按规则生成发现，并逐账户与结算对账；发现是待审建议。',
               '{path}，以及账户信号。'),
        's1_counts': '  账户 {accounts} 个；发现 {proposals} 条；结构警告 {structure} 条；结算 {settlement}；口径未对齐 {held} 条。',
        's1_codes': '→ {n} 条发现，覆盖 {kinds} 类判据：{codes}',
        's2': ('核对',
               '上一步的发现与预置 writeback-snapshot.json。',
               '比较基线、目标与快照现值；ready 仅表示待审差异计划，不授予执行权限。',
               '{path}，含差异计划、冲突和缺失状态。'),
        's2_counts': '  待审差异计划 {ready}｜已满足 {satisfied}｜冲突 {conflict}｜缺失 {unknown}｜仅建议 {advisory}',
        's2_next': '→ 冲突行暂缓修改并核对变更来源；缺失状态先补充证据。其余行按各自核对结果处理。',
        's3': ('登记',
               '上一步的 gate.json。',
               'apply 只把拟改字段和跳过原因登记到本地台账；不调用接口、不向广告账户写入。',
               '{path} 与 {ledger}。'),
        's3_counts': '  登记 {planned} 条差异计划 / {fields} 个拟改字段；追加 {events} 个台账事件。',
        's3_row': '  → {key}  {code}  拟改字段 {patch}',
        's4': ('对照',
               '差异计划与预置 after-snapshot.json；该快照不是平台回读。',
               '逐字段比较目标与快照，并记录匹配或不匹配。',
               '{path}，并向同一份步骤台账追加对照事件。'),
        's4_counts': '  对照 {checked} 条；匹配 {effective} 条、不匹配 {ineffective} 条。',
        's4_row': '  ✗ {key} 不匹配 — {detail}',
        's5': ('交接',
               '本次步骤台账，以及 gate.json 中的冲突、缺失记录。',
               'open 列出台账中待对照或不匹配的行；合并闸门待确认记录一起交接，避免漏项。',
               '终端列出 open 行；完整待办仍需同时查看 gate.json 与 reconciliation.json。'),
        's5_counts': '  open 共 {n} 条：',
        's5_row': '  → {key} · {status} · 拟改字段 {patch}',
        's5_gate': '  另有闸门待确认 {n} 条，不在 open 中：{rows}',
        's5_next': '→ 本例 open 只含快照不匹配行；它不是全部待办。',
        'assembled': '接下来用同一套虚构输入独立运行 round，生成完整汇总报告。',
        'step_ledger': '  五步台账：{path}',
        'round_ledger': '  汇总台账：{path}（独立台账，不是继续执行上面的五步）',
        'committed': '  {path}   ← 已在仓库里，不用跑就能看',
        'copy': '  {path}   ← 本次独立汇总报告的副本',
    },
}


def shown(path):
    """A path for printing: relative to the repository, never a home directory."""
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return os.path.relpath(path)


def arg(path):
    """A path for the subprocess, which runs with the repository as its cwd."""
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def fresh_ledger(path):
    """Each demo run starts its own ledger, so earlier runs cannot leak open rows
    into the committed sample. Only the demo's own ledger file is removed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        path.unlink()
    return path


def run_round(out, lang='en'):
    out.mkdir(parents=True, exist_ok=True)
    ledger = fresh_ledger(out / 'ledger.jsonl')
    command = [sys.executable, 'operating_loop.py', 'round',
               '--out', arg(out), '--ledger', arg(ledger), '--at', DEMO_TIMESTAMP, '--lang', lang,
               *[part for name, path in FIXTURE_ARGS for part in (name, arg(path))]]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(TEXT[lang]['round_failed'] + result.stdout + result.stderr)
    return json.loads(result.stdout)


def sample(out):
    """The deterministic, language-neutral part of a run, as committed to ``expected/``."""
    gate = json.loads((out / 'gate.json').read_text(encoding='utf-8'))
    findings = json.loads((out / 'findings.json').read_text(encoding='utf-8'))
    reconciliation = json.loads((out / 'reconciliation.json').read_text(encoding='utf-8'))
    summary = json.loads((out / 'round-summary.json').read_text(encoding='utf-8'))

    by_code = {}
    for proposal in findings['proposals']:
        by_code[proposal['code']] = by_code.get(proposal['code'], 0) + 1
    human = sorted(f"{item['object_key']}({item['gate']})" for item in gate['verdicts']
                   if item['gate'] in ('conflict', 'unknown'))
    promote = [item['object_key'] for item in findings['proposals']
               if item['code'] == 'LADDER_PROMOTE']
    hold = [item['object_key'] for item in findings['proposals']
            if item['code'] == 'LADDER_HOLD']
    held = [f"{item['object_key']}({item['code']})" for item in findings['proposals']
            if item.get('downgraded')]
    ineffective = [item['object_key'] for item in reconciliation['rows']
                   if item.get('checked') and not item['effective']]
    settlement = findings.get('settlement') or {'rows': []}

    return {
        'notice': 'OFFLINE ANALYSIS ONLY — fictional fixtures; 0 platform calls.',
        'mode': summary['mode'],
        'round_id': summary['round_id'],
        'snapshot_hash': summary['snapshot_hash'],
        'methodology': findings['methodology'],
        'accounts': summary['accounts'],
        'proposals': summary['proposals'],
        'findings_by_code': dict(sorted(by_code.items())),
        'gate': gate['summary'],
        'planned_writes': summary['planned_writes'],
        'write_plan_targets': [{'object_key': row['object_key'], 'patch': row['patch']}
                               for row in gate['write_plan']],
        'needs_human': human,
        'promotion_candidates': sorted(promote),
        'promotion_holds': sorted(hold),
        'settlement': {row['account_key']: row['status'] for row in settlement['rows']},
        'measurement_unreconciled': sorted(held),
        'cpa_drivers': {entry['adset_key']: entry['driver'] or 'not decomposed'
                        for entry in findings.get('cpa_drivers') or []},
        'reconciliation': summary['reconciliation'],
        'not_effective': sorted(ineffective),
        'open_rows': summary['open_rows'],
        'native_platform_calls': 0,
    }


def sample_text(out):
    return json.dumps(sample(out), ensure_ascii=False, indent=2) + '\n'


def run_both(out):
    runs = {}
    for lang in LANGUAGES:
        runs[lang] = out / lang
        run_round(runs[lang], lang)
    return runs


def refresh(out):
    runs = run_both(out)
    EXPECTED.mkdir(parents=True, exist_ok=True)
    for lang, name in REPORT_NAMES.items():
        (EXPECTED / name).write_bytes((runs[lang] / 'report.md').read_bytes())
    (EXPECTED / 'summary.json').write_text(sample_text(runs['en']), encoding='utf-8')
    print(TEXT['en']['refreshed'].format(path=shown(EXPECTED)))
    return 0


def check(out, lang='en'):
    text = TEXT[lang]
    runs = run_both(out)
    fresh = {name: (runs[code] / 'report.md').read_text(encoding='utf-8')
             for code, name in REPORT_NAMES.items()}
    fresh['summary.json'] = sample_text(runs['en'])
    problems, diffs = [], []
    for name, content in fresh.items():
        committed = EXPECTED / name
        if not committed.is_file():
            problems.append(text['missing'].format(name=name))
            continue
        expected = committed.read_text(encoding='utf-8')
        if expected != content:
            problems.append(text['differs'].format(name=name))
            diffs.extend(difflib.unified_diff(
                expected.splitlines(True), content.splitlines(True),
                fromfile=shown(committed), tofile=f'fresh {name}'))
    if sample_text(runs['en']) != sample_text(runs['zh-CN']):
        problems.append(text['languages_differ'])
    if problems:
        sys.stderr.writelines(diffs)
        print(('\n' if diffs else '') + text['check_failed'], file=sys.stderr)
        for problem in problems:
            print('  - ' + problem, file=sys.stderr)
        print('\n' + text['check_hint'], file=sys.stderr)
        return 1
    print(text['check_ok'].format(path=shown(EXPECTED)))
    return 0


def counts_text(settlement_summary):
    return ' · '.join(f'{code} {count}' for code, count in (settlement_summary or {}).items() if count) or '—'


def print_summary(out, lang):
    text = TEXT[lang]
    report = (out / 'report.md').read_text(encoding='utf-8')
    summary = sample(out)
    gate = summary['gate']
    fields = sum(len(row['patch']) for row in summary['write_plan_targets'])
    settlement = {}
    for status in summary['settlement'].values():
        settlement[status] = settlement.get(status, 0) + 1
    print('=' * 78)
    print(text['banner'].format(accounts=summary['accounts'], proposals=summary['proposals']))
    print(text['gate'].format(**gate))
    print(text['apply'].format(planned=summary['planned_writes'], fields=fields))
    print(text['after'].format(**summary['reconciliation']))
    print(text['settlement'].format(counts=counts_text(settlement),
                                    held=', '.join(summary['measurement_unreconciled']) or text['none']))
    print(text['human'].format(n=len(summary['needs_human']),
                               rows=', '.join(summary['needs_human']) or text['none']))
    print(text['mismatch'].format(n=len(summary['not_effective']),
                                  rows=', '.join(summary['not_effective']) or text['none']))
    print(text['open'].format(n=summary['open_rows']))
    print(text['calls'].format(n=summary['native_platform_calls']))
    print('=' * 78)
    print()
    print(report)
    print('=' * 78)
    print(text['all_output'].format(path=shown(out)))
    print(text['sample'].format(path=shown(EXPECTED / REPORT_NAMES[lang])))
    print(text['hint'])


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=HERE / 'out',
                        help='output directory, default demo/out (ignored by Git)')
    parser.add_argument('--lang', choices=LANGUAGES, default='en',
                        help='language of the report and terminal output (default en)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--steps', action='store_true',
                       help='walk through diagnose, gate, apply, verify and open one step at a time')
    group.add_argument('--refresh', action='store_true',
                       help='rewrite demo/expected/ from this run, in both languages')
    group.add_argument('--check', action='store_true',
                       help='compare both languages with demo/expected/; exit 1 and print a diff on change')
    args = parser.parse_args(argv)

    out = args.out.resolve()
    try:
        if args.steps:
            return run_steps(out, args.lang)
        if args.refresh:
            return refresh(out / 'expected-run')
        if args.check:
            return check(out / 'check-run', args.lang)
        run_round(out, args.lang)
        print_summary(out, args.lang)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


# --------------------------------------------------------------------------
# --steps: one ledger for the five stages; a separate fixture round for the report
# --------------------------------------------------------------------------

def _cli(lang, *arguments):
    """Run one CLI stage and return its parsed JSON result."""
    result = subprocess.run([sys.executable, 'operating_loop.py', *map(str, arguments), '--lang', lang],
                            cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(TEXT[lang]['step_failed'] + result.stdout + result.stderr)
    return json.loads(result.stdout)


def run_steps(out, lang='en'):
    """Print the loop as a sequence, so the order of decisions is visible.

    Five stages share steps/ledger.jsonl. The report at the end is independently
    regenerated from the same fixtures in full/, using its own ledger.
    """
    text = TEXT[lang]
    steps = out / 'steps'
    ledger = fresh_ledger(steps / 'ledger.jsonl')
    fixtures = {name: path for name, path in FIXTURE_ARGS}
    banner = '─' * 78

    def head(number, key, **paths):
        title, inputs, action, outputs = text[key]
        print()
        print(banner)
        print(text['step'].format(n=number, title=title))
        print(text['inputs'] + inputs)
        print(text['does'] + action)
        print(text['outputs'] + outputs.format(**paths))
        print(banner)

    def run(*arguments):
        parts = ['python3', 'operating_loop.py'] + [shown(part) if isinstance(part, Path) else str(part)
                                                    for part in arguments] + ['--lang', lang]
        print('$ ' + ' '.join(shlex.quote(part) for part in parts))
        return _cli(lang, *[arg(part) if isinstance(part, Path) else part for part in arguments])

    def load(path):
        return json.loads(path.read_text(encoding='utf-8'))

    # ---- step 1: classify every ad set and check the settlement ------------
    head(1, 's1', path=shown(steps / '1-diagnose' / 'findings.json'))
    result = run('diagnose', '--snapshot', fixtures['--snapshot'],
                 '--methodology', fixtures['--methodology'],
                 '--settlement', fixtures['--settlement'], '--out', steps / '1-diagnose')
    print(text['s1_counts'].format(accounts=result['accounts'], proposals=result['proposals'],
                                   structure=result['structure_findings'],
                                   settlement=counts_text(result['settlement']),
                                   held=result['measurement_unreconciled']))
    codes = {}
    for proposal in load(steps / '1-diagnose' / 'findings.json')['proposals']:
        codes[proposal['code']] = codes.get(proposal['code'], 0) + 1
    print(text['s1_codes'].format(n=result['proposals'], kinds=len(codes),
                                  codes=', '.join(f'{k}x{v}' for k, v in sorted(codes.items()))))

    # ---- step 2: gate before touching anything -----------------------------
    head(2, 's2', path=shown(steps / '2-gate' / 'gate.json'))
    run('gate', '--findings', steps / '1-diagnose' / 'findings.json',
        '--writeback', fixtures['--writeback'], '--out', steps / '2-gate')
    gate_artifact = load(steps / '2-gate' / 'gate.json')
    print(text['s2_counts'].format(**gate_artifact['summary']))
    for verdict in gate_artifact['verdicts']:
        if verdict['gate'] in ('conflict', 'unknown'):
            print(f"  ⚠ {verdict['object_key']} · {verdict['code']} · {verdict['gate_label']}"
                  f" — {' '.join(verdict['gate_detail'])}")
    print(text['s2_next'])

    # ---- step 3: record, do not write --------------------------------------
    head(3, 's3', path=shown(steps / '3-apply' / 'application.json'), ledger=shown(ledger))
    run('apply', '--gate', steps / '2-gate' / 'gate.json', '--ledger', ledger,
        '--out', steps / '3-apply', '--at', DEMO_TIMESTAMP)
    application = load(steps / '3-apply' / 'application.json')
    fields = sum(len(row['patch']) for row in application['write_plan'])
    print(text['s3_counts'].format(planned=application['planned_writes'], fields=fields,
                                   events=application['recorded_events']))
    for row in application['write_plan']:
        print(text['s3_row'].format(key=row['object_key'], code=row['code'], patch=row['patch']))

    # ---- step 4: reconcile -------------------------------------------------
    head(4, 's4', path=shown(steps / '4-verify' / 'reconciliation.json'))
    run('verify', '--gate', steps / '2-gate' / 'gate.json', '--after', fixtures['--after'],
        '--ledger', ledger, '--out', steps / '4-verify', '--at', VERIFY_TIMESTAMP)
    reconciliation = load(steps / '4-verify' / 'reconciliation.json')
    print(text['s4_counts'].format(**{key: reconciliation[key]
                                      for key in ('checked', 'effective', 'ineffective')}))
    for row in reconciliation['rows']:
        if row['checked'] and not row['effective']:
            print(text['s4_row'].format(key=row['object_key'], detail=row['detail']))

    # ---- step 5: what stays open ------------------------------------------
    head(5, 's5')
    opened = run('open', '--ledger', ledger)
    print(text['s5_counts'].format(n=opened['open']))
    for row in opened['rows']:
        print(text['s5_row'].format(key=row['object_key'], status=row['status'],
                                    patch=row.get('patch') or '—'))
    flagged = [row for row in gate_artifact['verdicts'] if row['gate'] in ('conflict', 'unknown')]
    print(text['s5_gate'].format(n=len(flagged), rows=', '.join(
        f"{row['object_key']}({row['gate']})" for row in flagged) or text['none']))
    print(text['s5_next'])

    # ---- the assembled report ---------------------------------------------
    print()
    print('=' * 78)
    print(text['assembled'])
    print(text['step_ledger'].format(path=shown(ledger)))
    print(text['round_ledger'].format(path=shown(out / 'full' / 'ledger.jsonl')))
    print(text['committed'].format(path=shown(EXPECTED / REPORT_NAMES[lang])))
    print(text['copy'].format(path=shown(out / 'report.md')))
    print('=' * 78)
    run_round(out / 'full', lang)
    (out / 'report.md').write_bytes((out / 'full' / 'report.md').read_bytes())
    print()
    print((out / 'report.md').read_text(encoding='utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
