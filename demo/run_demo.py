#!/usr/bin/env python3
"""One command to see what the operating loop actually produces.

Run it and you get, without any platform connection:

* a classified action list for every ad set in one settled observation window,
* a write-gate verdict per row (what may be written, what must not be),
* a write-back reconciliation (including a write that silently did not take effect),
* a one-page report.

    python3 demo/run_demo.py              # run one round and print the report
    python3 demo/run_demo.py --steps      # the same loop, one stage at a time
    python3 demo/run_demo.py --check      # CI: fail if the committed sample drifted
    python3 demo/run_demo.py --refresh    # regenerate demo/expected/ from a real run

``demo/expected/`` holds a committed sample so a reader can see the output without
running anything. ``--check`` keeps that sample honest: it re-runs the loop and
compares byte for byte, so a committed sample can never quietly go stale.

No network. No credentials. No account is written.
"""
import argparse
import filecmp
import json
from pathlib import Path
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
        raise RuntimeError('round failed:\n' + result.stdout + result.stderr)
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
    print(f'refreshed {EXPECTED.relative_to(ROOT)}/ from a real run')


def check(out):
    problems = []
    for name in ('report.md', 'summary.json'):
        committed = EXPECTED / name
        fresh = out / name
        if not committed.exists():
            problems.append(f'{name}: committed sample is missing')
            continue
        if name == 'summary.json':
            fresh.write_text(json.dumps(sample(out), ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
        if not filecmp.cmp(committed, fresh, shallow=False):
            problems.append(f'{name}: committed sample no longer matches a fresh run')
    if problems:
        print('The committed sample has drifted from the loop:', file=sys.stderr)
        for problem in problems:
            print('  - ' + problem, file=sys.stderr)
        print('\nA sample that says more than the code does is worse than no sample.\n'
              'Re-run with --refresh and review the diff before committing.', file=sys.stderr)
        return 1
    print('sample check passed: demo/expected/ matches a fresh run')
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=HERE / 'out',
                        help='Where the run writes; defaults to demo/out (ignored by git)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--steps', action='store_true',
                       help='Walk the loop one step at a time, the way a round actually runs')
    group.add_argument('--refresh', action='store_true',
                       help='Regenerate demo/expected/ from this run')
    group.add_argument('--check', action='store_true',
                       help='Compare a fresh run against demo/expected/ and fail on drift')
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
    print(f"跑完一轮：{summary['accounts']} 个账户 / {summary['proposals']} 条发现")
    print(f"  闸门：可执行 {gate['ready']}｜已满足 {gate['satisfied']}｜"
          f"冲突隔离 {gate['conflict']}｜未知 {gate['unknown']}｜仅建议 {gate['advisory']}")
    print(f"  模拟写入 {summary['planned_writes']} 个对象，"
          f"写后核对 {summary['reconciliation']['checked']} 条，"
          f"{summary['reconciliation']['ineffective']} 条未真正生效")
    print(f"  需要人处理：{', '.join(summary['needs_human']) or '无'}")
    print(f"  未生效：{', '.join(summary['not_effective']) or '无'}")
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
# --steps: the same loop, one stage at a time, in the order it really runs
# --------------------------------------------------------------------------

LEDGER_IN_STEPS = 'ledger.jsonl'


def _cli(out, *arguments):
    """Run one CLI stage and return its parsed JSON result."""
    result = subprocess.run([sys.executable, str(ROOT / 'operating_loop.py'), *map(str, arguments)],
                            cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError('stage failed:\n' + result.stdout + result.stderr)
    out.mkdir(parents=True, exist_ok=True)
    return json.loads(result.stdout)


def run_steps(out):
    """Print the loop as a sequence, so the order of decisions is visible.

    Each stage states what was on hand, what ran, what came out, and why that
    stage exists at all. The report at the end is the same one a full ``round``
    produces; nothing here is a special demo path.
    """
    steps = out / 'steps'
    ledger = steps / LEDGER_IN_STEPS
    banner = '─' * 78

    def head(number, title, why):
        print()
        print(banner)
        print(f'第 {number} 步 · {title}')
        print(f'  why：{why}')
        print(banner)

    def cmd_text(*arguments):
        shown = ' '.join(str(a).replace(str(ROOT) + '/', '') for a in arguments)
        print(f'$ python3 operating_loop.py {shown}')

    # ---- step 1: classify every ad set -------------------------------------
    head(1, '定性 —— 逐个广告组算指标、按固定顺序套规则',
         '先把「谁该动」判出来。判定顺序本身就是判据：样本关不过，后面一律不谈。')
    cmd_text('diagnose', '--snapshot', FIXTURES / 'snapshot-primary.json',
             '--methodology', FIXTURES / 'methodology-reference.json',
             '--out', steps / '1-diagnose')
    findings = _cli(steps / '1-diagnose', 'diagnose',
                    '--snapshot', FIXTURES / 'snapshot-primary.json',
                    '--methodology', FIXTURES / 'methodology-reference.json',
                    '--out', steps / '1-diagnose')
    print(json.dumps({'kind': findings['kind'], 'accounts': findings['accounts'],
                      'proposals': findings['proposals'],
                      'structure_findings': findings['structure_findings']},
                     ensure_ascii=False))
    codes = {}
    for proposal in json.loads((steps / '1-diagnose' / 'findings.json').read_text(encoding='utf-8'))['proposals']:
        codes[proposal['code']] = codes.get(proposal['code'], 0) + 1
    print(f'→ {findings["proposals"]} 条发现，覆盖 {len(codes)} 类判据：'
          + '、'.join(f'{k}x{v}' for k, v in sorted(codes.items())))

    # ---- step 2: gate before touching anything -----------------------------
    head(2, '写前闸门 —— 动手之前，先确认脚下没被改过',
         '取数和写回之间有几分钟。这几分钟里可能有人已经改过。不比对就直接写，会覆盖人工改动。')
    cmd_text('gate', '--findings', 'demo/out/steps/1-diagnose/findings.json',
             '--writeback', FIXTURES / 'writeback-snapshot.json',
             '--out', steps / '2-gate')
    _cli(steps / '2-gate', 'gate',
         '--findings', steps / '1-diagnose' / 'findings.json',
         '--writeback', FIXTURES / 'writeback-snapshot.json',
         '--out', steps / '2-gate')
    # The CLI prints counts; the detail sits in the artifact, which is what a
    # person would open next.
    gate_artifact = json.loads((steps / '2-gate' / 'gate.json').read_text(encoding='utf-8'))
    print(json.dumps({'summary': gate_artifact['summary'],
                      'write_plan': len(gate_artifact['write_plan'])}, ensure_ascii=False))
    for verdict in gate_artifact['verdicts']:
        if verdict['gate'] in ('conflict', 'unknown'):
            print(f"  ⚠ {verdict['object_key']} · {verdict['code']} · {verdict['gate_label']}"
                  f" — {verdict['gate_detail'][0]}")
    print(f"→ {gate_artifact['summary']['total']} 条里只有 "
          f"{len(gate_artifact['write_plan'])} 条可写；其余是「不涉及写入」"
          f"「已经是目标值」或「人工改过」")

    # ---- step 3: record, do not write --------------------------------------
    head(3, '执行 —— 只发差异字段，并把本轮记进只追加台账',
         '这一步只记录「决定要写什么」。真实环境里这里换成连接器调用，其余逻辑不变。')
    cmd_text('apply', '--gate', 'demo/out/steps/2-gate/gate.json',
             '--ledger', 'demo/out/steps/ledger.jsonl',
             '--out', steps / '3-apply', '--at', DEMO_TIMESTAMP)
    _cli(steps / '3-apply', 'apply',
         '--gate', steps / '2-gate' / 'gate.json',
         '--ledger', ledger, '--out', steps / '3-apply', '--at', DEMO_TIMESTAMP)
    application = json.loads((steps / '3-apply' / 'application.json').read_text(encoding='utf-8'))
    print(json.dumps({'planned_writes': application['planned_writes'],
                      'recorded_events': application['recorded_events'],
                      'not_written': len(application['not_written'])}, ensure_ascii=False))
    for row in application['write_plan']:
        print(f"  → {row['object_key']}  {row['code']}  只发 {row['patch']}")

    # ---- step 4: reconcile -------------------------------------------------
    head(4, '写后核对 —— 确认「发出去的」真的变成了「发生了的」',
         '写入返回成功不等于字段变了。回读一次再比对，不一致就当作未生效。')
    cmd_text('verify', '--gate', 'demo/out/steps/2-gate/gate.json',
             '--after', FIXTURES / 'after-snapshot.json',
             '--ledger', 'demo/out/steps/ledger.jsonl',
             '--out', steps / '4-verify', '--at', '2026-09-24T04:05:00+00:00')
    _cli(steps / '4-verify', 'verify',
         '--gate', steps / '2-gate' / 'gate.json',
         '--after', FIXTURES / 'after-snapshot.json',
         '--ledger', ledger, '--out', steps / '4-verify',
         '--at', '2026-09-24T04:05:00+00:00')
    reconciliation = json.loads((steps / '4-verify' / 'reconciliation.json').read_text(encoding='utf-8'))
    print(json.dumps({k: reconciliation[k] for k in ('checked', 'effective', 'ineffective')},
                     ensure_ascii=False))
    for row in reconciliation['rows']:
        if row['checked'] and not row['effective']:
            print(f"  ✗ {row['object_key']} 未生效 — {row['detail']}")

    # ---- step 5: what stays open ------------------------------------------
    head(5, '闭环 —— 下一轮开头，先回验这一轮没做完的（回到第 1 步）',
         '闭环发生在轮与轮之间：没生效的行继续挂着，而不是悄悄算完成。')
    cmd_text('open', '--ledger', 'demo/out/steps/ledger.jsonl')
    opened = _cli(steps / '5-open', 'open', '--ledger', ledger)
    print(json.dumps({'open': opened['open'],
                      'rows': [{'object_key': r['object_key'], 'status': r['status'],
                                'patch': r.get('patch')} for r in opened['rows']]},
                     ensure_ascii=False, indent=2))
    print('→ 这条行会带着进下一轮；这就是「系统」与「零散优化」的分界')

    # ---- the assembled report ---------------------------------------------
    print()
    print('=' * 78)
    print('把上述五步合起来跑（`operating_loop.py round`）就是一份可直接发出去的回执：')
    print(f'  {EXPECTED.relative_to(ROOT)}/report.md   ← 已在仓库里，不用跑就能看')
    print(f'  {out}/report.md                  ← 本次 --steps 也会在末尾生成一份')
    print('=' * 78)
    run_round(out / 'full')
    (out / 'report.md').write_bytes((out / 'full' / 'report.md').read_bytes())
    print()
    print((out / 'report.md').read_text(encoding='utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
