#!/usr/bin/env python3
"""Verify scoped private learning across separate CLI processes, entirely offline."""
import argparse
from copy import deepcopy
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
    return json.loads(result.stdout or result.stderr)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    profile_path, store = output / 'profile.json', output / 'private.sqlite3'
    context, plan = output / 'context-v1', output / 'plan-v1'
    auth, method_path = output / 'authorization-v1.json', output / 'method.json'
    workspace = 'fictional-team'
    cli('onboarding.py', '--input', ROOT / 'examples/onboarding-learning.json',
        '--out', profile_path, '--refresh-simulation-fixture')
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    profile['facts']['methodology'] = {
        'value': None, 'status': 'unknown', 'source': 'fictional_fixture_only'}
    profile['private_memory'] = {
        'enabled': True, 'store': str(store), 'workspace_id': workspace,
        'product_id': profile['profile_id']}
    save(profile_path, profile)
    original_bytes = profile_path.read_bytes()
    cli('memory_store.py', 'init', '--store', store, '--workspace', workspace)

    def put(record, version, event):
        save(method_path, record)
        return cli('memory_store.py', 'put', '--store', store, '--workspace', workspace,
                   '--input', method_path, '--expected-version', version, '--event-id', event)

    method = json.loads((ROOT / 'examples/private-methodology.json').read_text(encoding='utf-8'))
    first = put(method, 0, 'fictional-method-create')
    repeated = put(method, 0, 'fictional-method-create')
    require(first == repeated and first['version'] == 1, 'Idempotent creation failed')

    def intake(source, destination):
        cli('onboarding.py', '--input', source, '--out', destination)
        return json.loads((destination / 'context.json').read_text(encoding='utf-8'))

    first_intake = intake(profile_path, context)
    reopened = intake(profile_path, output / 'reopened-context')
    for evaluated in (first_intake, reopened):
        require(evaluated['profile_snapshot']['facts']['methodology']['value'] == method['text'],
                'Persisted method was not reused')
        require('methodology' not in {q['key'] for q in evaluated['next_questions']},
                'Adopted method was asked again')
    require(profile_path.read_bytes() == original_bytes, 'Source profile was mutated')
    review = cli('knowledge.py', 'assess', '--profile', profile_path,
                 '--stage', 'planning', '--out', output / 'knowledge')
    require(any(item['id'].startswith('PRIVATE:') for item in review['items']), 'Missing private review')
    require(any(not item['id'].startswith('PRIVATE:') for item in review['items']), 'Missing public review')
    planned = cli('adops.py', 'plan', '--brief', ROOT / 'examples/brief.json',
                  '--candidates', ROOT / 'examples/candidates.json',
                  '--context', context / 'context.json', '--out', plan)
    require(planned['status'] == 'ready', 'Fictional private-method plan was not ready')
    cli('adops.py', 'authorize-simulation', '--plan', plan / 'plan.json', '--out', auth)

    candidate = deepcopy(method)
    candidate.update(record_id='candidate-observation', kind='operational_note', status='candidate',
                     source={'kind': 'task_observation', 'reference': 'Fictional simulated observation',
                             'mode': 'simulation'})
    put(candidate, 0, 'fictional-candidate-create')
    other_product = deepcopy(method)
    other_product['product_id'] = 'fictional-other-product'
    put(other_product, 0, 'fictional-other-product-create')

    def execute(state, expected_code=0):
        return cli('adops.py', 'execute', '--plan', plan / 'plan.json', '--authorization', auth,
                   '--state', output / state, expected_code=expected_code)

    executed = execute('allowed-state')
    require(executed['status'] == 'completed_simulation', 'Unrelated records invalidated the plan')
    method['text'] += ' In the next batch, compare only the opening.'
    corrected = put(method, 1, 'fictional-method-correction')
    require(corrected['version'] == 2, 'Correction did not increment the version')
    execute('blocked-stale-state', expected_code=2)
    require(not (output / 'blocked-stale-state').exists(), 'Stale plan created execution state')
    corrected_intake = intake(profile_path, output / 'context-v2')
    require(corrected_intake['profile_snapshot']['facts']['methodology']['value'] == method['text'],
            'Correction was not reused')

    isolated = deepcopy(profile)
    isolated['profile_id'] = isolated['private_memory']['product_id'] = 'fictional-empty-product'
    isolated_path = output / 'isolated-profile.json'
    save(isolated_path, isolated)
    isolated_intake = intake(isolated_path, output / 'isolated-context')
    require(isolated_intake['profile_snapshot']['facts']['methodology']['status'] == 'unknown'
            and not isolated_intake['private_memory']['records'], 'Cross-product private knowledge leak')
    cli('memory_store.py', 'revoke', '--store', store, '--workspace', workspace,
        '--product', profile['profile_id'], '--record', method['record_id'],
        '--expected-version', 2, '--event-id', 'fictional-method-revoke',
        '--reason', 'Fictional user withdrawal')
    revoked = intake(profile_path, output / 'context-revoked')
    require(revoked['profile_snapshot']['facts']['methodology']['status'] == 'unknown',
            'Revoked method is still applied')
    history = cli('memory_store.py', 'history', '--store', store, '--workspace', workspace,
                  '--product', profile['profile_id'], '--record', method['record_id'])
    require([entry['version'] for entry in history] == [1, 2, 3]
            and history[-1]['status'] == 'revoked', 'Revision history is incomplete')
    summary = {
        'result': 'passed', 'mode': 'offline_simulation_only', 'output': str(output),
        'review': str(output / 'review.md'), 'reopened_method_reused': True,
        'original_profile_unchanged': profile_path.read_bytes() == original_bytes,
        'public_and_private_reviewed': True, 'candidate_and_other_product_do_not_invalidate': True,
        'related_correction_blocks_old_plan': True, 'product_isolation': True,
        'revocation_stops_reuse': True, 'revision_history': [1, 2, 3], 'native_platform_calls': 0}
    save(output / 'demo-summary.json', summary)
    (output / 'review.md').write_text(
        '# 私有方法库离线演示\n\n'
        '本次使用虚构产品，在独立 CLI 进程中验证了持久化方法复用、公共与私有知识共同审阅、'
        '重复事件幂等、产品隔离、候选隔离、修订后旧计划失效，以及撤回后停止复用。\n\n'
        '修订历史为 1 → 2 → 3，源业务档案未被改写，真实平台调用数为 0。'
        '演示结束时方法已撤回；保留的旧计划仅用于审阅，不能继续执行。\n\n'
        '结果见 [demo-summary.json](demo-summary.json)，方法修订保存在本目录的私有 SQLite 文件中。\n',
        encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='New output directory; an existing directory is never overwritten')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = (args.out or ROOT / 'runs' / f'private-memory-{stamp}-{uuid4().hex[:6]}').resolve()
    try:
        print(json.dumps(run(output), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
