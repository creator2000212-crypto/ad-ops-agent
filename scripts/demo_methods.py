#!/usr/bin/env python3
"""Exercise six fictional M2 tasks across independent CLI processes, offline only."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluations.fixtures import CASES, build_case


def cli(script, *arguments, expected_code=0):
    result = subprocess.run([sys.executable, str(ROOT / script), *map(str, arguments)],
                            cwd=ROOT, text=True, capture_output=True)
    if result.returncode != expected_code:
        raise RuntimeError(f'{script}: expected {expected_code}, got {result.returncode}\n'
                           + result.stdout + result.stderr)
    return json.loads(result.stdout or result.stderr)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for index, (business, approach) in enumerate(CASES):
        name = business + '_' + approach
        directory = output / name
        directory.mkdir()
        case = build_case(business, approach)
        for key, value in case.items():
            save(directory / (key + '.json'), value)
        source = directory / 'profile.json'
        original = source.read_bytes()
        task = directory / 'task'
        language = 'en' if index % 2 else 'zh-CN'
        started = cli('task.py', 'start', '--profile', source, '--out', task, '--language', language)
        require(started['stage'] == 'method_proposal', name + ': expected method proposal')

        def command(name, *args, **kwargs):
            return cli('task.py', name, '--task', task, *args, **kwargs)

        proposed = command('propose', '--request', directory / 'request.json')
        candidate = proposed['candidates'][0]
        adopted = command('adopt', '--candidate', candidate['method_id'],
                          '--confirmation', 'fictional user adopts initial method: ' + name)
        require(adopted['stage'] == 'plan_preparation', name + ': method not ready')
        prepared = command('plan', '--brief', directory / 'brief.json',
                           '--candidates', directory / 'candidates.json')
        require(prepared['plan']['status'] == 'ready', name + ': plan not ready')
        old_plan = Path(prepared['plan']['reference'])
        before = json.loads(old_plan.read_text(encoding='utf-8'))
        old_auth = old_plan.parent / 'simulation-authorization.json'
        selected = [item['asset_id'] for item in before['test_plan']['selected_assets']]
        require(selected == ['anchor', 'hook-b' if approach == 'guided' else 'concept-b'],
                name + ': selection ignored method constraints')
        require(all(op['desired']['native_payload'] is None for op in before['operations']),
                name + ': unexpected native payload')
        interrupted = command('simulate', '--interrupt-after-write', '1', expected_code=4)
        require(interrupted['status'] == command('status')['stage'] == 'interrupted', name + ': interruption not retained')
        resumed = command('simulate')
        again = command('simulate')
        require(resumed['created_this_run'] == 2 and resumed['simulated_object_count'] == 3,
                name + ': failed to reconcile uncertain first write')
        require(again['created_this_run'] == 0 and command('status')['stage'] == 'completed_simulation',
                name + ': repeat created duplicates or completion was not verified')

        template = 'concept_exploration' if candidate['template'] == 'single_variable' else 'single_variable'
        correction = build_case(business, approach, template)['request']
        save(directory / 'correction.json', correction)
        proposed = command('propose', '--request', directory / 'correction.json')
        changed = command('adopt', '--candidate', proposed['candidates'][0]['method_id'],
                          '--confirmation', 'fictional user adopts revised method: ' + name)
        require(changed['method']['revision'] == 2 and not changed['plan']['current'],
                name + ': previous plan stayed current after method revision')
        blocked_state = directory / 'blocked-old-plan'
        cli('adops.py', 'execute', '--plan', old_plan, '--authorization', old_auth,
            '--state', blocked_state, expected_code=2)
        require(not blocked_state.exists(), name + ': rejected old plan created execution state')
        corrected = command('plan', '--brief', directory / 'brief.json',
                            '--candidates', directory / 'candidates.json')
        require(corrected['plan']['status'] == 'ready', name + ': corrected plan not ready')
        after = json.loads(Path(corrected['plan']['reference']).read_text(encoding='utf-8'))
        revised_assets = [item['asset_id'] for item in after['test_plan']['selected_assets']]
        require(revised_assets == ['anchor', 'hook-b' if template == 'single_variable' else 'concept-b'],
                name + ': revised method did not change selection')
        require(before['operations'][0]['desired']['test_design'] != after['operations'][0]['desired']['test_design'],
                name + ': revised method did not change operations')
        require(source.read_bytes() == original, name + ': source profile was modified')
        require(json.loads(old_plan.read_text(encoding='utf-8')) == before, name + ': previous plan was overwritten')
        results.append({'case': name, 'language': language, 'result': 'passed',
                        'initial_template': candidate['template'], 'initial_assets': selected,
                        'revised_template': template, 'revised_assets': revised_assets,
                        'recovery_created': resumed['created_this_run'], 'recovery_total': 3,
                        'repeat_created': 0, 'old_plan_rejected_before_state_creation': True,
                        'original_profile_unchanged': True, 'review': corrected['plan']['review']})
    summary = {'mode': 'offline_simulation_only', 'result': 'passed', 'output': str(output),
               'case_count': len(results), 'cases': results, 'native_platform_calls': 0,
               'limitations': 'Fictional complete profiles and host-extracted guided answers; labeled SOP parser only. '
                              'Does not validate live platforms, arbitrary conversation extraction, media content or external-user usability.'}
    save(output / 'demo-summary.json', summary)
    lines = ['# M2 offline methods demonstration', '', summary['limitations'], '',
             '| Case | Initial assets | Revised assets | Recovery |', '|---|---|---|---|']
    for row in results:
        review = Path(row['review']).relative_to(output).as_posix()
        lines.append('| [' + row['case'] + '](' + review + ') | ' + ', '.join(row['initial_assets'])
                     + ' | ' + ', '.join(row['revised_assets']) + ' | 3 objects, 0 repeat creations |')
    (output / 'review.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='New output directory; existing directories are never overwritten')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = (args.out or ROOT / 'runs' / f'methods-{stamp}-{uuid4().hex[:6]}').resolve()
    try:
        print(json.dumps(run(output), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
