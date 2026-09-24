#!/usr/bin/env python3
"""A persistent, host-driven task entry point. All operations remain offline.

The host collects user facts and confirmations; this module never infers them
from arbitrary conversation and never grants real platform permissions.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import adops
import methodology
import onboarding


class TaskError(ValueError):
    pass


WORDS = {
    'zh-CN': {
        'title': '投放任务（离线）', 'notice': '仅处理本地模拟任务；不会连接或发布真实广告。',
        'stage': '当前阶段', 'known': '已掌握', 'gaps': '待补充或确认', 'methods': '方法候选',
        'selected': '当前采用的方法', 'plan': '最近的计划', 'next': '下一步',
        'setup': '先解决所选账户的接入缺口。当前检查只接受模拟快照。',
        'intake': '补充本次任务需要的资料；已提供的信息会继续保留。',
        'propose': '通过 guided 回答或带标签的 SOP 形成候选；宿主负责把交流转成程序输入。',
        'choose': '查看候选的固定项、变量和缺项；用户明确采用后再保存对应版本。',
        'prepare': '提供本次简报和素材清单，生成符合方法约束的审阅计划。',
        'review': '查看计划与排除理由；simulate 仅生成和核对本地模拟对象。',
        'stale': '旧计划的依赖已变化，请重新生成计划。',
        'completed': '本地模拟已核对完成，可以查看回执；不代表真实广告已发布。',
        'interrupted': '模拟中断；再次运行 simulate 会先核对已有对象。',
        'reconcile': '已保存的模拟结果需要核对；查看回执和对象差异后再恢复。',
        'fixed': '固定项', 'variable': '测试变量', 'anchor': '基准素材',
        'metric': '指标', 'source': '结果来源', 'window': '观察窗口',
        'unsupported': '尚不支持', 'unresolved': '待确认',
        'allocation': '每个目标账户共享原有总预算；不承诺等量曝光或随机 A/B。',
        'single_variable': '同一概念比较开头', 'concept_exploration': '比较完整创意概念',
        'hook': '开头', 'concept': '创意概念', 'body': '正文', 'cta': '行动号召',
        'destination': '目的地', 'none': '暂无',
        'original': '用户提供的原文', 'assets': '素材选择', 'excluded': '排除',
        'eligible_not_selected': '符合条件但未选用', 'asset_selected': '选用', 'hash': '计划内容标识',
        'scope': '适用范围（平台 / 国家 / 载体 / 变现）', 'revision': '版本', 'reference': '来源记录',
    },
    'en': {
        'title': 'Ad task (offline)', 'notice': 'Local simulation only; no connection to or publishing on advertising platforms.',
        'stage': 'Current stage', 'known': 'Known information', 'gaps': 'Missing or conflicting information',
        'methods': 'Method candidates', 'selected': 'Adopted method', 'plan': 'Latest plan', 'next': 'Next step',
        'setup': 'Resolve the selected accounts connection gaps first. Current checks accept simulation snapshots only.',
        'intake': 'Supply the information required for this task; previously supplied facts are retained.',
        'propose': 'Use guided answers or a labeled SOP to prepare candidates. The host turns the conversation into program input.',
        'choose': 'Review fixed components, variables and gaps; save a revision only after the user explicitly adopts it.',
        'prepare': 'Provide this task brief and asset manifest to prepare a method-aware review.',
        'review': 'Review the plan and exclusion reasons. simulate creates and checks local objects only.',
        'stale': 'The previous plan dependencies changed; prepare a new plan.',
        'completed': 'The local simulation has been checked. Receipts do not mean real ads were published.',
        'interrupted': 'Simulation interrupted; run simulate again to reconcile existing objects first.',
        'reconcile': 'The saved simulation result needs reconciliation. Inspect receipt or object differences before resuming.',
        'fixed': 'Fixed components', 'variable': 'Test variable', 'anchor': 'Anchor asset',
        'metric': 'Metric', 'source': 'Result source', 'window': 'Observation window',
        'unsupported': 'Unsupported', 'unresolved': 'Unresolved',
        'allocation': 'Each target account shares its existing total budget; equal exposure and randomized A/B are not guaranteed.',
        'single_variable': 'Compare openings within one concept', 'concept_exploration': 'Explore complete creative concepts',
        'hook': 'Opening', 'concept': 'Concept', 'body': 'Body', 'cta': 'Call to action',
        'destination': 'Destination', 'none': 'None',
        'original': 'Original user source', 'assets': 'Asset decisions', 'excluded': 'Excluded',
        'eligible_not_selected': 'Eligible, not selected', 'asset_selected': 'Selected', 'hash': 'Plan content hash',
        'scope': 'Scope (platforms / countries / surface / monetization)', 'revision': 'Revision', 'reference': 'Source reference',
    },
}


def _time():
    return datetime.now(timezone.utc).isoformat()


def _new(path, value):
    if path.exists():
        raise TaskError('An existing task artifact cannot be overwritten.')
    adops.save(path, value)


@contextmanager
def _lock(root):
    lock = root / '.task.lock'
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise TaskError('This task has an active or unreconciled writer; inspect it before retrying.') from None
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def _load(directory):
    root = Path(directory).resolve()
    state = adops.load(root / 'task.json')
    if (state.get('schema_version') != 1 or state.get('kind') != 'offline_agent_task'
            or state.get('language') not in WORDS):
        raise TaskError('Unsupported task manifest.')
    for key in ('proposal_generation', 'method_revision', 'plan_generation'):
        if type(state.get(key)) is not int or state[key] < 0:
            raise TaskError('Invalid task generation.')
    profile = adops.load(root / 'profile.json')
    if profile.get('profile_id') != state.get('product_id') or adops.digest(profile) != state.get('profile_hash'):
        raise TaskError('Task profile changed outside an update or an interrupted write needs reconciliation.')
    return root, state, profile


def _save_state(root, state, profile, event, detail=None):
    state['profile_hash'] = adops.digest(profile)
    state['history'].append({'event': event, 'at': _time(), 'detail': detail or {}})
    adops.save(root / 'task.json', state)


def _method_path(root, state):
    return root / 'methods' / ('revision-' + str(state['method_revision']) + '.json')


def _proposal(root, state):
    proposal = adops.load(root / 'proposals' / ('generation-' + str(state['proposal_generation']) + '.json'))
    if adops.digest(proposal) != state.get('proposal_hash'):
        raise TaskError('The persisted proposal changed; reconcile it before adopting any candidate.')
    return proposal


def _plan_dir(root, state):
    return root / 'plans' / ('generation-' + str(state['plan_generation']))


def _gate(profile):
    result = onboarding.evaluate(profile)
    if result['connection_gate']['status'] != 'ready_simulation':
        raise TaskError('Connection prerequisites are not ready; resolve setup first.')
    if result['guidance']['stage'] == 'collaboration_intake':
        raise TaskError('Choose a collaboration approach and describe the current need first.')
    return result


def start(profile_path, directory, language='zh-CN'):
    if language not in WORDS:
        raise TaskError('language must be zh-CN or en.')
    profile = adops.load(profile_path)
    onboarding.evaluate(profile)  # Validate without treating missing answers as errors.
    if profile.get('methodology_ref') is not None:
        raise TaskError('Start from a business profile; adopt a structured method inside this task.')
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=False)
    adops.save(root / 'profile.json', profile)
    state = {'schema_version': 1, 'kind': 'offline_agent_task', 'mode': 'simulation',
             'language': language, 'product_id': profile['profile_id'],
             'profile_hash': adops.digest(profile), 'proposal_generation': 0,
             'method_revision': 0, 'plan_generation': 0, 'history': []}
    _save_state(root, state, profile, 'started', {'source_profile': str(Path(profile_path).resolve())})
    return status(root)


def update_profile(directory, profile_path):
    root = Path(directory).resolve()
    with _lock(root):
        root, state, current = _load(root)
        profile = adops.load(profile_path)
        if profile.get('profile_id') != state['product_id']:
            raise TaskError('A task update cannot switch products.')
        if state['method_revision']:
            expected = str(_method_path(root, state))
            if profile.get('methodology_ref', expected) != expected:
                raise TaskError('Use adopt to change the task method.')
            profile['methodology_ref'] = expected
        elif profile.get('methodology_ref') is not None:
            raise TaskError('Use propose and adopt to bind the first task method.')
        onboarding.evaluate(profile)
        history = root / 'profiles' / ('before-update-' + str(len(state['history'])) + '.json')
        _new(history, current)
        adops.save(root / 'profile.json', profile)
        _save_state(root, state, profile, 'profile_updated', {'previous': str(history.relative_to(root))})
    return status(root)


def propose(directory, request):
    root = Path(directory).resolve()
    with _lock(root):
        root, state, profile = _load(root)
        prospective = deepcopy(profile)
        if isinstance(request, dict) and request.get('approach') in {'guided', 'bring_own'}:
            prospective.setdefault('collaboration', {})['approach'] = request['approach']
        _gate(prospective)
        candidates = methodology.propose(prospective, request)
        state['proposal_generation'] += 1
        record = {'profile_hash': adops.digest(prospective), 'request': request, 'candidates': candidates}
        state['proposal_hash'] = adops.digest(record)
        _new(root / 'proposals' / ('generation-' + str(state['proposal_generation']) + '.json'), record)
        adops.save(root / 'profile.json', prospective)
        _save_state(root, state, prospective, 'proposed', {'generation': state['proposal_generation']})
    return status(root)


def adopt_method(directory, candidate_id, confirmation_reference):
    root = Path(directory).resolve()
    with _lock(root):
        root, state, profile = _load(root)
        _gate(profile)
        proposal = _proposal(root, state)
        if proposal['profile_hash'] != adops.digest(profile):
            raise TaskError('The profile changed since this proposal; prepare fresh candidates.')
        candidates = [item for item in proposal['candidates'] if item['method_id'] == candidate_id]
        if len(candidates) != 1:
            raise TaskError('Choose exactly one current candidate.')
        candidate = deepcopy(candidates[0])
        candidate['revision'] = state['method_revision'] + 1
        if state['method_revision']:
            previous = adops.load(_method_path(root, state))
            if previous['template'] == candidate['template']:
                candidate['method_id'] = previous['method_id']
        adopted = methodology.adopt(candidate, confirmation_reference)
        scope_issues = methodology.applicability(adopted, profile, profile['selected_accounts'])
        if scope_issues:
            raise TaskError('Adopted method does not cover the current business scope.')
        _new(root / 'profiles' / ('before-method-' + str(adopted['revision']) + '.json'), profile)
        state['method_revision'] = adopted['revision']
        path = _method_path(root, state)
        _new(path, adopted)
        profile['methodology_ref'] = str(path)
        profile['facts']['methodology'] = {
            'value': methodology.summary(adopted), 'status': 'confirmed',
            'source': {'kind': 'user_adopted_structured_method', 'reference': confirmation_reference,
                       'method_hash': methodology.digest(adopted)}}
        profile['profile_version'] = str(profile['profile_version']) + '.m' + str(adopted['revision'])
        adops.save(root / 'profile.json', profile)
        _save_state(root, state, profile, 'method_adopted', {'revision': adopted['revision'],
                                                         'method_hash': methodology.digest(adopted)})
    return status(root)


def prepare_plan(directory, brief, candidates):
    root = Path(directory).resolve()
    with _lock(root):
        root, state, profile = _load(root)
        _gate(profile)
        if not state['method_revision']:
            raise TaskError('Adopt a complete method before preparing this task plan.')
        next_generation = state['plan_generation'] + 1
        destination = root / 'plans' / ('generation-' + str(next_generation))
        if destination.exists():
            raise TaskError('This plan generation already exists; reconcile the interrupted preparation.')
        onboarding.build_context(root / 'profile.json', destination / 'context')
        plan = adops.build_plan(brief, candidates, context_path=destination / 'context' / 'context.json',
                               method_path=_method_path(root, state))
        adops.save(destination / 'plan.json', plan)
        adops.write_review(plan, destination / 'review.zh-CN.md')
        # A short same-language entry avoids mixing translated UI with diagnostic source text.
        (destination / 'review.md').write_text(plan_markdown(plan, state['language']), encoding='utf-8')
        state['plan_generation'] = next_generation
        _save_state(root, state, profile, 'plan_prepared', {'generation': next_generation, 'status': plan['status']})
    return status(root)


def simulate(directory, interrupt_after_write=0):
    root = Path(directory).resolve()
    with _lock(root):
        root, state, profile = _load(root)
        if not state['plan_generation']:
            raise TaskError('Prepare a plan before simulating.')
        destination = _plan_dir(root, state)
        plan = adops.load(destination / 'plan.json')
        if ((destination / 'state' / 'result.json').exists()
                and not (destination / 'state' / 'simulation.sqlite3').is_file()):
            raise TaskError('A saved result has no simulation database; reconcile the missing state first.')
        authorization_path = destination / 'simulation-authorization.json'
        if authorization_path.exists():
            authorization = adops.load(authorization_path)
        else:
            authorization = adops.authorization_for(plan)
            _new(authorization_path, authorization)
        result = adops.execute(plan, authorization, destination / 'state', interrupt_after_write)
        _save_state(root, state, profile, 'simulation_checked', {'generation': state['plan_generation'],
                                                             'status': result['status']})
    return result


def status(directory):
    root, state, profile = _load(directory)
    context = onboarding.evaluate(profile)
    method = None
    method_issues = []
    if state['method_revision']:
        method = methodology.validate(adops.load(_method_path(root, state)), require_adopted=True)
        method_issues = methodology.applicability(method, profile, profile['selected_accounts'])
        if profile['facts'].get('methodology', {}).get('value') != methodology.summary(method):
            method_issues.append({'code': 'needs_input', 'path': 'methodology',
                                  'message': 'The adopted method and current business facts disagree.'})
        method_evidence = profile['facts'].get('methodology', {}).get('source')
        if not isinstance(method_evidence, dict) or method_evidence.get('method_hash') != methodology.digest(method):
            method_issues.append({'code': 'needs_input', 'path': 'methodology.source.method_hash',
                                  'message': 'The complete adopted method differs from the business profile confirmation.'})
    candidates = []
    if state['proposal_generation']:
        proposal = _proposal(root, state)
        if proposal['profile_hash'] == adops.digest(profile):
            candidates = proposal['candidates']
    stage = 'method_proposal'
    if context['connection_gate']['status'] != 'ready_simulation':
        stage = 'connection_setup'
    elif context['guidance']['stage'] == 'collaboration_intake':
        stage = 'business_intake'
    elif candidates:
        stage = 'method_review'
    elif method is not None:
        stage = ('plan_preparation' if not method_issues and context['readiness']['test_planning']['status'] == 'ready'
                 else 'business_intake')
    plan_info = None
    if state['plan_generation']:
        destination = _plan_dir(root, state)
        plan = adops.load(destination / 'plan.json')
        plan_info = {'generation': state['plan_generation'], 'status': plan['status'],
                     'reference': str(destination / 'plan.json'), 'review': str(destination / 'review.md'),
                     'issues': plan['issues'], 'current': False}
        if plan['status'] == 'ready':
            try:
                adops.verify_plan(plan)
                plan_info['current'] = True
                if stage not in {'connection_setup', 'business_intake', 'method_review'}:
                    stage = 'plan_review'
                result_path = destination / 'state' / 'result.json'
                if result_path.exists():
                    result = adops.load(result_path)
                    if result.get('plan_hash') == plan['plan_hash']:
                        plan_info['simulation_status'] = result['status']
                        if result['status'] == 'completed_simulation':
                            try:
                                adops.verify_completed_simulation(plan, destination / 'state', result)
                            except (OSError, ValueError, TypeError, KeyError) as exc:
                                plan_info['simulation_status'] = 'needs_reconciliation'
                                plan_info['simulation_issue'] = str(exc)
                        if stage == 'plan_review':
                            stage = {'completed_simulation': 'completed_simulation', 'interrupted': 'interrupted'}.get(
                                plan_info['simulation_status'], 'simulation_review')
                    elif stage == 'plan_review':
                        plan_info['simulation_status'] = 'needs_reconciliation'
                        stage = 'simulation_review'
            except (OSError, ValueError, TypeError, KeyError):
                plan_info['status'] = 'stale'
    words = WORDS[state['language']]
    keys = {'connection_setup': 'setup', 'business_intake': 'intake', 'method_proposal': 'propose',
            'method_review': 'choose', 'plan_preparation': 'prepare', 'plan_review': 'review',
            'completed_simulation': 'completed', 'interrupted': 'interrupted', 'simulation_review': 'reconcile'}
    result = {'schema_version': 1, 'kind': 'offline_task_status', 'language': state['language'],
              'mode': 'simulation', 'notice': words['notice'], 'task': str(root), 'stage': stage,
              'next_step': words[keys[stage]], 'profile_id': state['product_id'],
              'known_facts': {key: value for key, value in context['profile_snapshot']['facts'].items()
                              if value['status'] in {'confirmed', 'observed'}},
              'connection_gate': context['connection_gate'], 'readiness': context['readiness'],
              'gaps': context['gaps'], 'method_issues': method_issues,
              'candidates': candidates, 'method': method, 'plan': plan_info,
              'history_count': len(state['history'])}
    return result


def method_markdown(method, language):
    words = WORDS[language]
    lines = ['**' + words[method['template']] + '**', '', method['question'], '',
             '- ID: `' + method['method_id'] + '`',
             '- ' + words['revision'] + ': ' + str(method['revision']),
             '- ' + words['variable'] + ': ' + words[method['variable']],
             '- ' + words['fixed'] + ': ' + ', '.join(words[item] for item in method['fixed_components']),
             '- ' + words['anchor'] + ': ' + (method['anchor_asset_id'] or words['none'])]
    for key in ('metric', 'source', 'window'):
        lines.append('- ' + words[key] + ': ' + (method['measurement'][key] or words['none']))
    scope = method['scope']
    lines.append('- ' + words['scope'] + ': ' + ' / '.join([
        ', '.join(scope['platforms']) or words['none'], ', '.join(scope['countries']) or words['none'],
        scope['surface'] or words['none'], scope['monetization'] or words['none']]))
    lines.append('- ' + words['reference'] + ': ' + method['source']['reference'])
    for key in ('unresolved', 'unsupported'):
        if method[key]:
            lines.append('- ' + words[key] + ': ' + '; '.join(method[key]))
    lines += ['', words['allocation'], '', words['original'] + ':', '']
    lines += ['> ' + line for line in method['source']['text'].splitlines()]
    lines.append('')
    return '\n'.join(lines)


def status_markdown(result):
    words = WORDS[result['language']]
    lines = ['# ' + words['title'], '', words['notice'], '',
             words['stage'] + ': `' + result['stage'] + '`', '', words['next'] + ': ' + result['next_step'], '',
             '## ' + words['known'], '']
    # Field identifiers are stable; values remain the user's original language.
    for key, fact in result['known_facts'].items():
        if key != 'methodology':
            lines.append('- ' + key + ': ' + json.dumps(fact['value'], ensure_ascii=False))
    lines += ['', '## ' + words['gaps'], '']
    for gap in result['gaps']:
        lines.append('- `' + gap['key'] + '` (' + gap['status'] + ')')
    for issue in result['method_issues']:
        lines.append('- `' + issue['path'] + '` (' + issue['code'] + ')')
    if result['candidates']:
        lines += ['', '## ' + words['methods'], '']
        lines += [method_markdown(candidate, result['language']) for candidate in result['candidates']]
    if result['method']:
        lines += ['', '## ' + words['selected'], '', method_markdown(result['method'], result['language'])]
    if result['plan']:
        plan = result['plan']
        reference = Path(plan['review']).relative_to(Path(result['task'])).as_posix()
        lines += ['', '## ' + words['plan'], '', '[' + str(plan['generation']) + '](' + reference + ')',
                  '', '`' + plan['status'] + '`']
        if plan['status'] == 'stale':
            lines += ['', words['stale']]
    return '\n'.join(lines) + '\n'


def plan_markdown(plan, language):
    words = WORDS[language]
    lines = ['# ' + words['plan'], '', words['notice'], '', '`' + plan['status'] + '`', '',
             words['hash'] + ': `' + plan['plan_hash'] + '`', '']
    if plan.get('test_plan'):
        lines += [method_markdown(plan['test_plan']['method_snapshot'], language)]
        for unit in plan['test_plan']['units']:
            lines.append('- `' + unit['unit_id'] + '`: ' + ', '.join(unit['asset_ids']) + ' / ' + unit['variable_value'])
    for operation in plan['operations']:
        desired = operation['desired']
        lines += ['', desired['platform'] + ' / ' + desired['account_id'] + ': '
                  + desired['budget']['amount'] + ' ' + desired['budget']['currency'] + ' (total)']
    lines += ['', '## ' + words['assets'], '']
    for item in plan['asset_decisions']:
        label = words['asset_selected'] if item['status'] == 'selected' else words[item['status']]
        lines.append('- ' + str(item.get('asset_id', 'unknown')) + ': ' + label)
        if language == 'en':
            lines.extend('  - ' + reason for reason in item['reasons'])
        else:
            for reason in item['reasons']:
                if 'fixed component differs' in reason:
                    field = reason.rsplit(': ', 1)[-1]
                    text = '固定项与基准不同：' + words.get(field, field)
                elif 'concept_id differs' in reason:
                    text = '单变量测试要求同一创意概念。'
                elif 'duplicate variable' in reason:
                    text = '测试变量与已选素材重复。'
                elif 'test_identity' in reason or 'unknown:' in reason:
                    text = '缺少明确、完整且有来源的素材信息。'
                elif 'anchor' in reason and item['status'] == 'selected':
                    text = '基准素材或满足已声明的固定项与独立变量。'
                elif item['status'] == 'eligible_not_selected':
                    text = '已满足本次明确要求的测试数量。'
                else:
                    text = '按明确的素材元数据与方法约束判定；完整诊断见 JSON。'
                lines.append('  - ' + text)
    lines += ['', '## ' + words['gaps'], '']
    for issue in plan['issues']:
        path = issue['path']
        if issue['code'] == 'unsupported':
            explanation = ('当前编译器不支持这项要求；必须明确修改方案后才能继续。' if language == 'zh-CN'
                           else 'This requirement is outside the current compiler support. Explicitly revise the proposal before continuing.')
        elif path == 'context':
            explanation = ('业务或接入信息尚未满足规划条件，或保存的档案已变化。请先补全或刷新档案。' if language == 'zh-CN'
                           else 'Business or connection evidence is incomplete, or the saved context changed. Complete or refresh the profile first.')
        elif path.startswith('method') or issue['code'] == 'scope_mismatch':
            explanation = ('方法版本、采用凭据或适用范围与本次任务不一致；请核对当前采用的方法。' if language == 'zh-CN'
                           else 'Method revision, adoption evidence or scope is inconsistent with this task. Review the adopted method.')
        elif path.startswith('assets') or path.startswith('test') or path.startswith('candidates'):
            explanation = ('素材信息或测试分组条件未满足；请核对基准、固定项、变量及所需数量。' if language == 'zh-CN'
                           else 'Asset evidence or test grouping requirements are unmet. Check the anchor, fixed components, variables and requested count.')
        else:
            explanation = ('此字段的输入或证据缺失、过期或不一致；原始校验详情保留在 JSON 中。' if language == 'zh-CN'
                           else 'Input or evidence at this field is missing, stale or inconsistent. Original validation details are preserved in JSON.')
        lines.append('- `' + path + '` (' + issue['code'] + '): ' + explanation)
    lines += ['', '[JSON](plan.json)', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('start')
    p.add_argument('--profile', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--language', choices=sorted(WORDS), default='zh-CN')
    for name in ('update', 'propose', 'adopt', 'plan', 'status', 'simulate'):
        p = commands.add_parser(name)
        p.add_argument('--task', required=True)
        if name == 'update':
            p.add_argument('--profile', required=True)
        if name == 'propose':
            p.add_argument('--request', required=True)
        if name == 'adopt':
            p.add_argument('--candidate', required=True)
            p.add_argument('--confirmation', required=True)
        if name == 'plan':
            p.add_argument('--brief', required=True)
            p.add_argument('--candidates', required=True)
        if name == 'simulate':
            p.add_argument('--interrupt-after-write', type=int, default=0)
    args = parser.parse_args(argv)
    try:
        if args.command == 'start':
            result = start(args.profile, args.out, args.language)
        elif args.command == 'update':
            result = update_profile(args.task, args.profile)
        elif args.command == 'propose':
            result = propose(args.task, adops.load(args.request))
        elif args.command == 'adopt':
            result = adopt_method(args.task, args.candidate, args.confirmation)
        elif args.command == 'plan':
            result = prepare_plan(args.task, adops.load(args.brief), adops.load(args.candidates))
        elif args.command == 'simulate':
            result = simulate(args.task, args.interrupt_after_write)
        else:
            result = status(args.task)
        if result.get('kind') == 'offline_task_status':
            # Presentation is derived, not the source of task truth.
            (Path(result['task']) / 'status.md').write_text(status_markdown(result), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 4 if result.get('status') == 'interrupted' else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'mode': 'simulation', 'status': 'blocked', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
