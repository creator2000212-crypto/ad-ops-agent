#!/usr/bin/env python3
"""One command to see what the operating loop actually produces.

Run it and you get, without any platform connection:

* a classified action list for every ad set in one settled observation window,
* a write-gate verdict per row (what may be written, what must not be),
* a write-back reconciliation (including a write that silently did not take effect),
* a one-page report.

    python3 demo/run_demo.py              # run it and print the report
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
    group.add_argument('--refresh', action='store_true',
                       help='Regenerate demo/expected/ from this run')
    group.add_argument('--check', action='store_true',
                       help='Compare a fresh run against demo/expected/ and fail on drift')
    args = parser.parse_args()

    out = args.out.resolve()
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
    return 0


if __name__ == '__main__':
    sys.exit(main())
