#!/usr/bin/env python3
"""Run the fictional CLI workflow and verify local recovery. No network calls."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def cli(script, *arguments, expected_code=0):
    result = subprocess.run([sys.executable, str(ROOT / script), *map(str, arguments)],
                            cwd=ROOT, text=True, capture_output=True)
    if result.returncode != expected_code:
        raise RuntimeError(f'{script}: expected {expected_code}, got {result.returncode}\n'
                           + result.stdout + result.stderr)
    return json.loads(result.stdout)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    profile, context = output / 'profile.json', output / 'context'
    plan, auth = output / 'plan', output / 'simulation-authorization.json'
    cli('onboarding.py', '--input', ROOT / 'examples/onboarding-learning.json',
        '--out', profile, '--refresh-simulation-fixture')
    cli('onboarding.py', '--input', profile, '--out', context)
    planned = cli('adops.py', 'plan', '--brief', ROOT / 'examples/brief.json',
                  '--candidates', ROOT / 'examples/candidates.json',
                  '--context', context / 'context.json', '--out', plan)
    require(planned['status'] == 'ready', 'Fictional plan was not ready')
    cli('adops.py', 'authorize-simulation', '--plan', plan / 'plan.json', '--out', auth)

    def execute(command, state, *extra, expected_code=0):
        return cli('adops.py', command, '--plan', plan / 'plan.json',
                   '--authorization', auth, '--state', output / state,
                   *extra, expected_code=expected_code)

    first = execute('execute', 'normal-state')
    second = execute('resume', 'normal-state')
    interrupted = execute('execute', 'interrupted-state', '--interrupt-after-write', '1', expected_code=4)
    recovered = execute('resume', 'interrupted-state')
    require(first['status'] == second['status'] == recovered['status'] == 'completed_simulation', 'Unexpected execution status')
    require(first['created_this_run'] == first['simulated_object_count'] == 3, 'Expected three simulated objects')
    require(second['created_this_run'] == 0 and second['simulated_object_count'] == 3, 'Resume duplicated objects')
    require(interrupted['status'] == 'interrupted', 'Fault injection did not interrupt')
    require(recovered['created_this_run'] == 2 and recovered['simulated_object_count'] == 3, 'Uncertain write was not reconciled')
    summary = {
        'mode': 'offline_simulation_only', 'result': 'passed',
        'output': str(output), 'review': str(plan / 'review.md'),
        'initial_created': 3, 'resume_created': 0,
        'recovery_created': 2, 'recovery_total': 3,
        'native_platform_calls': 0
    }
    (output / 'demo-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='New output directory; an existing directory is never overwritten')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = (args.out or ROOT / 'runs' / f'demo-{stamp}-{uuid4().hex[:6]}').resolve()
    try:
        print(json.dumps(run(output), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
