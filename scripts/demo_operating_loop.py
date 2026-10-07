#!/usr/bin/env python3
"""Run the offline operating loop and assert the behaviours that matter.

What this demonstrates, in order:

1. A settled observation window is classified without reading any media and
   without calling a platform.
2. A zero-conversion ad set below the sample gate is *not* judged, while one that
   crosses both the sample gate and the loss line is.
3. Rule precedence: an ad set that meets the promotion numbers is held when a
   creative or account problem comes first (one change per ad set per round).
4. Platform vs settlement: an account whose numbers do not reconcile with the
   settlement cannot drive a promotion; an account outside the settlement is
   reported as missing, never as zero.
5. The five-state write gate separates ready, already satisfied, conflict (a
   current value matching neither baseline nor target), unknown (state not
   read) and advisory (nothing to write).
6. A write that did not take effect is caught by the write-back reconciliation.
7. The ledger is append-only: a second round adds rows and keeps the unresolved
   ones visible instead of resetting the round.
8. The report says why CPA moved, and the decisions do not depend on the
   report language.

No network calls. All fixtures are under ``examples/operating/``.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'examples' / 'operating'


def cli(script, *arguments, expected_code=0):
    result = subprocess.run([sys.executable, str(ROOT / script), *map(str, arguments)],
                            cwd=ROOT, text=True, capture_output=True)
    if result.returncode != expected_code:
        raise RuntimeError(f'{script}: expected {expected_code}, got {result.returncode}\n'
                           + result.stdout + result.stderr)
    return json.loads(result.stdout)


def display(path):
    """Print paths relative to the repository; never a home directory."""
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).name


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    ledger = output / 'ledger.jsonl'
    fixtures = {
        '--snapshot': FIXTURES / 'snapshot-primary.json',
        '--writeback': FIXTURES / 'writeback-snapshot.json',
        '--after': FIXTURES / 'after-snapshot.json',
        '--methodology': FIXTURES / 'methodology-reference.json',
        '--settlement': FIXTURES / 'settlement-daily.json',
    }

    def round_(*, out, at, lang='en', ledger=ledger):
        return cli('operating_loop.py', 'round', '--out', out, '--ledger', ledger, '--at', at,
                   '--lang', lang, *[part for pair in fixtures.items() for part in pair])

    first = round_(out=output / 'round-1', at='2026-09-24T03:58:00+00:00')

    require(first['mode'] == 'offline_analysis_only', 'Round did not declare offline mode')
    require(first['native_platform_calls'] == 0, 'Round attempted a platform call')
    require(first['accounts'] == 4, 'Expected four fictional accounts (three Meta, one TikTok)')

    # (2) the sample gate has to split two ad sets that both show zero results.
    findings = json.loads((output / 'round-1' / 'findings.json').read_text(encoding='utf-8'))
    proposals = findings['proposals']
    by_object = {}
    for item in proposals:
        by_object.setdefault(item['object_key'], []).append(item['code'])
    require(by_object.get('fictional-adset-a2') == ['TEST_UNDERTESTED'],
            'An ad set below the sample gate must only be recorded')
    require(by_object.get('fictional-adset-a3') == ['TEST_STOP_NOCONV'],
            'An ad set past the sample gate and the loss line must stop')
    require('LADDER_PROMOTE' in (by_object.get('fictional-adset-a1') or []),
            'A healthy ad set should be proposed for promotion')

    # (3) a promotion waits behind a creative breaker and behind account P0 findings.
    for held in ('fictional-adset-a6', 'fictional-adset-b1'):
        codes = by_object.get(held) or []
        require('LADDER_HOLD' in codes and 'LADDER_PROMOTE' not in codes,
                f'{held} should be held, not promoted')

    # (4) measurement first: the TikTok account's leads look cheap on the platform,
    # but the settlement approves too few of them, so its promotion is advisory.
    settlement = {row['account_key']: row['status'] for row in findings['settlement']['rows']}
    require(settlement.get('fictional-tiktok-account-d') == 'RECON_GAP',
            'The account the settlement does not confirm should be a gap')
    require(settlement.get('fictional-meta-account-c') == 'RECON_SCOPE',
            'The account outside the settlement should be reported as out of scope')
    held = [item for item in proposals if item.get('downgraded')]
    require([(item['object_key'], item['code']) for item in held]
            == [('fictional-adgroup-d1', 'LADDER_PROMOTE')],
            'Only the unreconciled promotion should be held as advisory')
    require('target' not in held[0], 'An unreconciled promotion must not carry a write intent')

    # (5) all five gate states must be present.
    gate = json.loads((output / 'round-1' / 'gate.json').read_text(encoding='utf-8'))
    summary = gate['summary']
    for state in ('ready', 'satisfied', 'conflict', 'unknown', 'advisory'):
        require(summary[state] >= 1, f'Gate never produced a {state} row')
    conflict = next(v for v in gate['verdicts'] if v['gate'] == 'conflict')
    require('check where the difference came from' in ' '.join(conflict['gate_detail']),
            'Conflict row did not explain how to handle the unexplained difference')
    require(conflict['conflict_fields'] == ['daily_budget'],
            'Conflict row did not name the field that differs')
    require(conflict['writable_fields'] == [],
            'A conflicting row must not expose writable fields')

    # Only the ready rows may be written, and never more than there are proposals.
    require(first['planned_writes'] == summary['ready'], 'Write plan does not match the ready rows')
    require(first['planned_writes'] < first['proposals'], 'The gate wrote everything, so it gated nothing')

    # (6) a write that silently did not take effect must be visible, not assumed.
    require(first['reconciliation']['ineffective'] == 1,
            'The ineffective write was not detected')
    reconciliation = json.loads((output / 'round-1' / 'reconciliation.json').read_text(encoding='utf-8'))
    missed = [row['object_key'] for row in reconciliation['rows'] if row['checked'] and not row['effective']]
    require(missed == ['fictional-adset-a10'], 'The write that did not take should be a10')
    report = (output / 'round-1' / 'report.md').read_text(encoding='utf-8')
    require('| `fictional-adset-a10` | LADDER_PROMOTE | **No** |' in report,
            'Report did not flag the ineffective write')
    require('OFFLINE ANALYSIS ONLY' in report, 'Report did not carry the offline notice')

    # (7) the ledger grows and unresolved rows stay open across rounds.
    events_after_first = len(ledger.read_text(encoding='utf-8').strip().splitlines())
    open_first = cli('operating_loop.py', 'open', '--ledger', ledger)['open']
    require(open_first >= 1, 'The ineffective write should remain an open row')

    second = round_(out=output / 'round-2', at='2026-09-24T15:58:00+00:00')
    events_after_second = len(ledger.read_text(encoding='utf-8').strip().splitlines())
    require(events_after_second > events_after_first, 'Second round did not append to the ledger')
    require(second['snapshot_hash'] == first['snapshot_hash'],
            'The same snapshot must hash identically across rounds')
    open_second = cli('operating_loop.py', 'open', '--ledger', ledger)['open']
    require(open_second >= open_first, 'Open rows were silently dropped between rounds')

    # (8) the report explains the CPA movement it can compute, and the same
    # round in Chinese reaches the same decisions.
    require('## Why CPA moved' in report, 'Report did not decompose the CPA change')
    drivers = {entry['adset_key']: entry for entry in findings['cpa_drivers']}
    require(drivers['fictional-adset-a4']['driver'] == 'cvr',
            "a4's CPA rise should be driven by CVR")
    require(not drivers['fictional-adset-a10']['complete'],
            'A prior window without CVR must stay visibly undecomposed')
    chinese = round_(out=output / 'round-zh', at='2026-09-24T03:58:00+00:00', lang='zh-CN',
                     ledger=output / 'ledger-zh.jsonl')
    for key in ('proposals', 'gate', 'planned_writes', 'reconciliation', 'settlement'):
        require(chinese[key] == first[key], f'The Chinese round differs from the English one on {key}')
    report_zh = (output / 'round-zh' / 'report.md').read_text(encoding='utf-8')
    require('不连接任何广告平台' in report_zh, 'Chinese report did not carry the offline notice')

    return {
        'mode': 'offline_analysis_only',
        'result': 'passed',
        'out': display(output),
        'rounds': 2,
        'ledger_events': events_after_second,
        'proposals': first['proposals'],
        'planned_writes': first['planned_writes'],
        'gate': summary,
        'reconciliation': first['reconciliation'],
        'settlement': first['settlement'],
        'measurement_unreconciled': first['measurement_unreconciled'],
        'open_rows_after_round_1': open_first,
        'open_rows_after_round_2': open_second,
        'fixtures': sorted(p.name for p in FIXTURES.glob('*.json')),
        'native_platform_calls': 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path,
                        help='New output directory; an existing directory is never overwritten')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = (args.out or ROOT / 'runs' / f'demo-operating-{stamp}-{uuid4().hex[:6]}').resolve()
    try:
        summary = run(output)
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
