#!/usr/bin/env python3
"""用虚构快照跑通诊断、核对、登记、对照与交接，输出中文报告。

    python3 demo/run_demo.py              # 运行离线演示并打印报告
    python3 demo/run_demo.py --steps      # 按五个步骤说明输入、处理和产物
    python3 demo/run_demo.py --check      # 比较本次离线输出与已提交样例
    python3 demo/run_demo.py --refresh    # 用本次离线输出更新 demo/expected/

ready 只表示差异计划可供审阅，不等于获得授权。apply 只登记本地台账；
after 是预置对照快照，匹配不证明真实修改生效。没有网络调用、凭据或账户写入。
"""
import argparse
import filecmp
import json
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURES = ROOT / 'examples' / 'operating'
EXPECTED = HERE / 'expected'
# Pinned so the ledger timestamps in the demo are stable; the classifications do
# not depend on the clock at all.
DEMO_TIMESTAMP = '2026-09-24T03:58:00+00:00'

FIXTURE_ARGS = (
    ('--snapshot', FIXTURES / 'snapshot-primary.json'),
    ('--writeback', FIXTURES / 'writeback-snapshot.json'),
    ('--after', FIXTURES / 'after-snapshot.json'),
    ('--methodology', FIXTURES / 'methodology-reference.json'),
    ('--settlement', FIXTURES / 'settlement-daily.json'),
)


def run_round(out):
    out.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(ROOT / 'operating_loop.py'), 'round',
               '--out', str(out), '--at', DEMO_TIMESTAMP,
               *[part for pair in FIXTURE_ARGS for part in pair]]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError('离线汇总运行失败：\n' + result.stdout + result.stderr)
    return json.loads(result.stdout)


def sample(out):
    """The deterministic part of a run, in the shape committed to ``expected/``."""
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
    ineffective = [item['object_key'] for item in reconciliation['rows']
                   if item.get('checked') and not item['effective']]

    return {
        'notice': summary['notice'],
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
        'reconciliation': summary['reconciliation'],
        'not_effective': sorted(ineffective),
        'open_rows': summary['open_rows'],
        'native_platform_calls': 0,
    }


def refresh(out):
    EXPECTED.mkdir(parents=True, exist_ok=True)
    (EXPECTED / 'report.md').write_bytes((out / 'report.md').read_bytes())
    (EXPECTED / 'summary.json').write_text(
        json.dumps(sample(out), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'已用本次离线演示输出更新 {EXPECTED.relative_to(ROOT)}/；没有平台调用。')


def check(out):
    problems = []
    for name in ('report.md', 'summary.json'):
        committed = EXPECTED / name
        fresh = out / name
        if not committed.exists():
            problems.append(f'{name}：缺少已提交的样例')
            continue
        if name == 'summary.json':
            fresh.write_text(json.dumps(sample(out), ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
        if not filecmp.cmp(committed, fresh, shallow=False):
            problems.append(f'{name}：已提交样例与本次离线输出不一致')
    if problems:
        print('样例与当前程序的离线输出出现差异：', file=sys.stderr)
        for problem in problems:
            print('  - ' + problem, file=sys.stderr)
        print('\n请用 --refresh 重新生成样例，并在提交前审阅差异。', file=sys.stderr)
        return 1
    print('样例检查通过：demo/expected/ 与本次离线输出逐字节一致。')
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=HERE / 'out',
                        help='产物目录，默认 demo/out（已被 Git 忽略）')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--steps', action='store_true',
                       help='逐步展示离线诊断、核对、登记、对照与交接')
    group.add_argument('--refresh', action='store_true',
                       help='用本次离线输出更新 demo/expected/')
    group.add_argument('--check', action='store_true',
                       help='与 demo/expected/ 比较，存在差异时返回失败')
    args = parser.parse_args()

    out = args.out.resolve()
    if args.steps:
        try:
            return run_steps(out)
        except (OSError, ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

    try:
        run_round(out)
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.refresh:
        refresh(out)
        return 0
    if args.check:
        return check(out)

    report = (out / 'report.md').read_text(encoding='utf-8')
    summary = sample(out)
    gate = summary['gate']
    print('=' * 78)
    print(f"离线演示：{summary['accounts']} 个账户 / {summary['proposals']} 条发现（发现数不等于对象数）")
    print(f"  闸门：待审差异计划 {gate['ready']}｜已满足 {gate['satisfied']}｜"
          f"冲突隔离 {gate['conflict']}｜未知 {gate['unknown']}｜仅建议 {gate['advisory']}")
    fields = sum(len(row['patch']) for row in summary['write_plan_targets'])
    print(f"  apply 只登记 {summary['planned_writes']} 条差异计划 / {fields} 个拟改字段；ready 不等于授权，没有账户写入。")
    print(f"  与预置 after 快照对照：{summary['reconciliation']['effective']} 条匹配、"
          f"{summary['reconciliation']['ineffective']} 条不匹配；不证明真实生效。")
    print(f"  闸门待确认 {len(summary['needs_human'])} 条：{', '.join(summary['needs_human']) or '无'}")
    print(f"  对照不匹配 {len(summary['not_effective'])} 条：{', '.join(summary['not_effective']) or '无'}")
    print(f"  open 只列台账未闭合的 {summary['open_rows']} 条，不包含闸门冲突/缺失；两部分需要一起交接。")
    print(f"  平台调用次数：{summary['native_platform_calls']}")
    print('=' * 78)
    print()
    print(report)
    print('=' * 78)
    print(f'全部产出：{out}')
    print(f'对照样例   ：{EXPECTED}（--check 会核对它与新跑结果是否一致）')
    print('提示：想看逐步展开的过程，用 --steps')
    return 0


# --------------------------------------------------------------------------
# --steps: one ledger for the five stages; a separate fixture round for the report
# --------------------------------------------------------------------------

LEDGER_IN_STEPS = 'ledger.jsonl'


def _cli(out, *arguments):
    """Run one CLI stage and return its parsed JSON result."""
    result = subprocess.run([sys.executable, str(ROOT / 'operating_loop.py'), *map(str, arguments)],
                            cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError('离线步骤运行失败：\n' + result.stdout + result.stderr)
    out.mkdir(parents=True, exist_ok=True)
    return json.loads(result.stdout)


def run_steps(out):
    """Print the loop as a sequence, so the order of decisions is visible.

    Five stages share steps/ledger.jsonl. The report at the end is independently
    regenerated from the same fixtures in full/, using its own ledger.
    """
    steps = out / 'steps'
    ledger = steps / LEDGER_IN_STEPS
    banner = '─' * 78

    def head(number, title, inputs, action, outputs):
        print()
        print(banner)
        print(f'第 {number} 步 · {title}')
        print(f'  输入：{inputs}')
        print(f'  做什么：{action}')
        print(f'  输出：{outputs}')
        print(banner)

    def cmd_text(*arguments):
        shown = shlex.join([sys.executable, str(ROOT / 'operating_loop.py'), *map(str, arguments)])
        print('$ ' + shown)

    # ---- step 1: classify every ad set -------------------------------------
    head(1, '诊断',
         '虚构观察快照 snapshot-primary.json 与声明的方法论阈值。',
         '推导指标并按规则生成发现；发现是待审建议，同一对象可触发多条规则。',
         str(steps / '1-diagnose' / 'findings.json') + '，以及账户信号与诊断明细。')
    cmd_text('diagnose', '--snapshot', FIXTURES / 'snapshot-primary.json',
             '--methodology', FIXTURES / 'methodology-reference.json',
             '--out', steps / '1-diagnose')
    findings = _cli(steps / '1-diagnose', 'diagnose',
                    '--snapshot', FIXTURES / 'snapshot-primary.json',
                    '--methodology', FIXTURES / 'methodology-reference.json',
                    '--out', steps / '1-diagnose')
    print(f"  账户 {findings['accounts']} 个；发现 {findings['proposals']} 条；结构警告 {findings['structure_findings']} 条。")
    codes = {}
    for proposal in json.loads((steps / '1-diagnose' / 'findings.json').read_text(encoding='utf-8'))['proposals']:
        codes[proposal['code']] = codes.get(proposal['code'], 0) + 1
    print(f'→ {findings["proposals"]} 条发现，覆盖 {len(codes)} 类判据：'
          + '、'.join(f'{k}x{v}' for k, v in sorted(codes.items())))

    # ---- step 2: gate before touching anything -----------------------------
    head(2, '核对',
         '上一步的发现与预置 writeback-snapshot.json。',
         '比较基线、目标与快照现值；ready 仅表示待审差异计划，不授予执行权限。',
         str(steps / '2-gate' / 'gate.json') + '，含差异计划、冲突和缺失状态。')
    cmd_text('gate', '--findings', steps / '1-diagnose' / 'findings.json',
             '--writeback', FIXTURES / 'writeback-snapshot.json',
             '--out', steps / '2-gate')
    _cli(steps / '2-gate', 'gate',
         '--findings', steps / '1-diagnose' / 'findings.json',
         '--writeback', FIXTURES / 'writeback-snapshot.json',
         '--out', steps / '2-gate')
    # The CLI prints counts; the detail sits in the artifact, which is what a
    # person would open next.
    gate_artifact = json.loads((steps / '2-gate' / 'gate.json').read_text(encoding='utf-8'))
    counts = gate_artifact['summary']
    print(f"  待审差异计划 {counts['ready']}｜已满足 {counts['satisfied']}｜"
          f"冲突 {counts['conflict']}｜缺失 {counts['unknown']}｜仅建议 {counts['advisory']}")
    for verdict in gate_artifact['verdicts']:
        if verdict['gate'] in ('conflict', 'unknown'):
            print(f"  ⚠ {verdict['object_key']} · {verdict['code']} · {verdict['gate_label']}"
                  f" — {' '.join(verdict['gate_detail'])}")
    print('→ 冲突行暂缓修改并核对变更来源；缺失状态先补充证据。其余行按各自核对结果处理。')

    # ---- step 3: record, do not write --------------------------------------
    head(3, '登记',
         '上一步的 gate.json。',
         'apply 只把拟改字段和跳过原因登记到本地台账；不调用接口、不向广告账户写入。',
         str(steps / '3-apply' / 'application.json') + ' 与 ' + str(ledger) + '。')
    cmd_text('apply', '--gate', steps / '2-gate' / 'gate.json',
             '--ledger', ledger,
             '--out', steps / '3-apply', '--at', DEMO_TIMESTAMP)
    _cli(steps / '3-apply', 'apply',
         '--gate', steps / '2-gate' / 'gate.json',
         '--ledger', ledger, '--out', steps / '3-apply', '--at', DEMO_TIMESTAMP)
    application = json.loads((steps / '3-apply' / 'application.json').read_text(encoding='utf-8'))
    fields = sum(len(row['patch']) for row in application['write_plan'])
    print(f"  登记 {application['planned_writes']} 条差异计划 / {fields} 个拟改字段；"
          f"追加 {application['recorded_events']} 个台账事件；没有平台写入。")
    for row in application['write_plan']:
        print(f"  → {row['object_key']}  {row['code']}  拟改字段 {row['patch']}")

    # ---- step 4: reconcile -------------------------------------------------
    head(4, '对照',
         '差异计划与预置 after-snapshot.json；该快照不是本程序操作账户后的返回值。',
         '逐字段比较目标与快照，并记录匹配或不匹配；不把匹配解释为真实操作生效。',
         str(steps / '4-verify' / 'reconciliation.json') + '，并向同一份步骤台账追加对照事件。')
    cmd_text('verify', '--gate', steps / '2-gate' / 'gate.json',
             '--after', FIXTURES / 'after-snapshot.json',
             '--ledger', ledger,
             '--out', steps / '4-verify', '--at', '2026-09-24T04:05:00+00:00')
    _cli(steps / '4-verify', 'verify',
         '--gate', steps / '2-gate' / 'gate.json',
         '--after', FIXTURES / 'after-snapshot.json',
         '--ledger', ledger, '--out', steps / '4-verify',
         '--at', '2026-09-24T04:05:00+00:00')
    reconciliation = json.loads((steps / '4-verify' / 'reconciliation.json').read_text(encoding='utf-8'))
    print(f"  对照 {reconciliation['checked']} 条；预置快照匹配 {reconciliation['effective']} 条、"
          f"不匹配 {reconciliation['ineffective']} 条。")
    for row in reconciliation['rows']:
        if row['checked'] and not row['effective']:
            print(f"  ✗ {row['object_key']} 不匹配 — 原始判据：{row['detail']}")
    print('→ 原始判据中的“生效/未生效”只描述本次快照对照结果。真实 API 接入、授权、提交与平台回读需后续独立实现。')

    # ---- step 5: what stays open ------------------------------------------
    head(5, '交接',
         '本次步骤台账，以及第 2 步 gate.json 的冲突、缺失记录。',
         'open 列出台账中待对照或不匹配的行；合并闸门待确认记录一起交接，避免漏项。',
         '终端列出 open 行；完整待办仍需同时查看 gate.json 与 reconciliation.json。')
    cmd_text('open', '--ledger', ledger)
    opened = _cli(steps / '5-open', 'open', '--ledger', ledger)
    print(f"  open 共 {opened['open']} 条：")
    for row in opened['rows']:
        print(f"  → {row['object_key']} · {row['status']} · 拟改字段 {row.get('patch') or '—'}")
    flagged = [row for row in gate_artifact['verdicts'] if row['gate'] in ('conflict', 'unknown')]
    print(f"  另有闸门待确认 {len(flagged)} 条，不在 open 中："
          + ('、'.join(f"{row['object_key']}({row['gate']})" for row in flagged) or '无'))
    print('→ 本例 open 只含快照不匹配行；它不是全部待办，也不代表其余发现已经解决。')

    # ---- the assembled report ---------------------------------------------
    print()
    print('=' * 78)
    print('接下来用同一套虚构输入独立运行 round，生成完整汇总报告。')
    print(f'  五步台账：{ledger}')
    print(f'  汇总台账：{out / "full" / "ledger.jsonl"}（独立台账，不是继续执行上面的五步）')
    print(f'  {EXPECTED.relative_to(ROOT)}/report.md   ← 已在仓库里，不用跑就能看')
    print(f'  {out}/report.md                  ← 独立汇总报告的副本')
    print('=' * 78)
    run_round(out / 'full')
    (out / 'report.md').write_bytes((out / 'full' / 'report.md').read_bytes())
    print()
    print((out / 'report.md').read_text(encoding='utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
