#!/usr/bin/env python3
"""Offline onboarding contracts; connection records are fixtures, never live probes."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import sys
import knowledge
import personalization
import guidance

STATES = {'confirmed', 'observed', 'hypothesis', 'unknown', 'conflict', 'stale'}
PLATFORMS = {'meta', 'tiktok', 'google'}
MONETIZATION = {'iaa', 'iap', 'hybrid', 'subscription', 'ecommerce', 'leadgen'}
BASE = ['product_name', 'surface', 'monetization', 'countries', 'platforms', 'methodology', 'audience', 'creative_direction', 'goal_type', 'success_metric', 'learning_budget']
QUESTIONS = {
    'product_name': '产品是什么，核心用途和要解决的问题是什么？',
    'surface': '这次工作流针对 Web 还是 App？',
    'monetization': '产品通过 IAA、IAP、混合、订阅、电商还是线索收费？',
    'countries': '本轮先覆盖哪些国家或地区？',
    'platforms': '本轮要准备 Meta、TikTok、Google 中的哪些平台？',
    'methodology': '采用什么投放和素材测试方法，哪些变量保持不变？',
    'audience': '目前的人群认识是什么，哪些已确认、哪些只是待验证假设？',
    'creative_direction': '本轮希望验证哪些创意方向，有哪些素材限制？',
    'goal_type': '本轮是学习测试、转化测试，还是收入/价值优化？',
    'success_metric': '本轮用什么指标和观察口径回答问题？',
    'learning_budget': '本轮明确的学习预算和币种是多少？',
    'os': 'App 先覆盖哪个操作系统？',
    'store': '对应的应用商店页面或分发地址是什么？',
    'measurement_stack': 'App 用 Firebase、MMP、自建或其他什么测量方案？',
    'ad_revenue_event': 'IAA 广告收入记录在哪个事件或数据源？',
    'ad_revenue_window': 'IAA 收入采用哪个统计/回收窗口？',
    'purchase_revenue_event': '付费或购买收入用哪个事件与金额口径？',
    'refund_policy': '退款、撤销和净收入如何处理？',
    'subscription_revenue_event': '订阅收入如何记录首次支付和续订？',
    'lead_event': '什么事件才算有效提交的线索？',
    'lead_qualification': '线索有效性或结算通过的标准是什么？',
    'value_basis': '本轮价值如何计算，使用哪些已观测交易或广告收入金额？不要求 LTV 预测。',
    'value_window': '本轮价值使用哪个明确的观察或归因窗口？',
}


class OnboardingError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def semantic_profile(profile):
    """Conversation progress does not change the business-content hash."""
    if not isinstance(profile, dict):
        raise OnboardingError('业务档案必须是对象。')
    return {k: v for k, v in profile.items() if k != 'asked_questions'}


def timestamp(value):
    if not isinstance(value, str):
        raise OnboardingError('缺少带时区的 checked_at。')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise OnboardingError('checked_at 不是有效日期。') from exc
    if result.tzinfo is None:
        raise OnboardingError('checked_at 必须包含时区。')
    return result.astimezone(timezone.utc)


def evaluate(profile, asked_questions=None, as_of=None, account_scope=None, workflow='test_planning'):
    data = semantic_profile(profile)
    source_profile_hash = digest(data)
    try:
        data, private_snapshot = personalization.resolve(data, account_scope=account_scope)
    except ValueError as exc:
        raise OnboardingError('私有知识无法解析：' + str(exc)) from exc
    if data.get('mode') != 'simulation':
        raise OnboardingError('onboarding 仅接受 simulation；没有真实连接检查实现。')
    if not isinstance(data.get('profile_id'), str) or not data['profile_id'].strip() or not isinstance(data.get('profile_version'), str) or not data['profile_version'].strip():
        raise OnboardingError('必须明确 profile_id 和字符串 profile_version。')
    facts = data.get('facts')
    if not isinstance(facts, dict):
        raise OnboardingError('facts 必须为字段到 value/status/source 的映射。')
    for key, fact in facts.items():
        if not isinstance(fact, dict) or fact.get('status') not in STATES or 'value' not in fact:
            raise OnboardingError('事实字段格式不合法：' + key)
    current = as_of or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise OnboardingError('as_of 必须带时区。')
    current = current.astimezone(timezone.utc)
    gaps = {}

    def has_source(source):
        if isinstance(source, str):
            return bool(source.strip())
        return isinstance(source, dict) and bool(source) and any(has_source(v) for v in source.values())

    def missing(key, status, reason):
        gaps.setdefault(key, {'key': key, 'status': status, 'reason': reason, 'required_by': []})

    def usable(key):
        fact = facts.get(key, {'value': None, 'status': 'unknown'})
        status, value = fact['status'], fact['value']
        if status not in {'confirmed', 'observed'}:
            missing(key, status, '尚未取得当前可依赖的事实；值保留原样，不以 0 替代。')
            return False
        if value is None or value == '' or value == [] or not has_source(fact.get('source')):
            missing(key, 'unknown', '缺少明确值或来源。')
            return False
        text_fields = {'product_name', 'methodology', 'audience', 'creative_direction', 'success_metric',
                       'store', 'measurement_stack', 'ad_revenue_event', 'ad_revenue_window',
                       'purchase_revenue_event', 'refund_policy', 'subscription_revenue_event',
                       'lead_event', 'lead_qualification', 'value_basis', 'value_window'}
        if key in text_fields and (not isinstance(value, str) or not value.strip()):
            missing(key, 'unknown', '该字段需要明确的非空文本，false、0、空对象不能视为已掌握。')
            return False
        if key == 'os' and not ((isinstance(value, str) and value.strip()) or (isinstance(value, list) and value and all(isinstance(v, str) and v.strip() for v in value))):
            missing(key, 'unknown', 'OS 需要非空名称或名称列表。')
            return False
        enums = {'surface': {'web', 'app'}, 'monetization': MONETIZATION,
                 'goal_type': {'learning', 'conversion', 'revenue', 'value'}}
        if key in enums and (not isinstance(value, str) or value not in enums[key]):
            missing(key, 'unsupported', '当前字段选项不支持；surface 仅 web/app，不支持 both。')
            return False
        if key in {'countries', 'platforms'}:
            if not isinstance(value, list) or not value or not all(isinstance(v, str) and v.strip() for v in value):
                missing(key, 'unknown', '需要非空字符串列表。')
                return False
            if key == 'platforms' and not set(value).issubset(PLATFORMS):
                missing(key, 'unsupported', '存在未实现的平台。')
                return False
        if key == 'learning_budget':
            try:
                value_amount = Decimal(str(value.get('amount'))) if isinstance(value, dict) else Decimal('NaN')
                valid = value_amount.is_finite() and value_amount > 0 and isinstance(value.get('currency'), str) and len(value['currency']) == 3 and value['currency'].isalpha() and value['currency'].isupper()
            except (InvalidOperation, AttributeError):
                valid = False
            if not valid:
                missing(key, 'unknown', '需要明确的正数学习预算及三字母币种。')
                return False
        return True

    def value(key):
        return facts[key]['value'] if usable(key) else None

    for key in BASE:
        usable(key)
    surface, monetization, goal = value('surface'), value('monetization'), value('goal_type')
    app_fields = ['os', 'store', 'measurement_stack'] if surface == 'app' else []
    model_fields = []
    if monetization in {'iaa', 'hybrid'}:
        model_fields += ['ad_revenue_event', 'ad_revenue_window']
    if monetization in {'iap', 'hybrid', 'ecommerce'}:
        model_fields += ['purchase_revenue_event', 'refund_policy']
    if monetization == 'subscription':
        model_fields += ['subscription_revenue_event', 'refund_policy']
    if monetization == 'leadgen':
        model_fields += ['lead_event', 'lead_qualification']
    for key in app_fields + model_fields:
        usable(key)
    # Retain user-declared uncertainties even when they are not dependencies of this task.
    for key, fact in facts.items():
        if fact['status'] in {'unknown', 'hypothesis', 'conflict', 'stale'}:
            usable(key)

    selected = data.get('selected_accounts', [])
    if not isinstance(selected, list):
        raise OnboardingError('selected_accounts 必须是列表。')
    selected_keys = []
    for account in selected:
        if not isinstance(account, dict) or account.get('platform') not in PLATFORMS or not isinstance(account.get('account_id'), str) or not account['account_id'].strip():
            raise OnboardingError('选定账户需要明确 platform/account_id。')
        pair = (account['platform'], account['account_id'])
        if pair in selected_keys:
            raise OnboardingError('选定账户重复。')
        selected_keys.append(pair)
    if account_scope is not None:
        requested = {(a.get('platform'), a.get('account_id')) for a in account_scope}
        if not requested.issubset(set(selected_keys)):
            raise OnboardingError('brief 的平台/账户超出业务档案选定范围。')
        selected_keys = [pair for pair in selected_keys if pair in requested]
    snapshot = data.get('connections', {})
    if not isinstance(snapshot, dict) or snapshot.get('mode') != 'simulation':
        raise OnboardingError('connections 必须明确 mode=simulation，不得假称真实检查。')
    checks = snapshot.get('checks', [])
    if not isinstance(checks, list):
        raise OnboardingError('connections.checks 必须是列表。')
    indexed = {}
    for check in checks:
        if not isinstance(check, dict) or check.get('platform') not in PLATFORMS or not isinstance(check.get('account_id'), str):
            raise OnboardingError('连接条目缺少平台/账户。')
        pair = (check['platform'], check['account_id'])
        if pair in indexed:
            raise OnboardingError('连接 snapshot 的平台/账户重复。')
        indexed[pair] = check
    ttl = snapshot.get('max_age_hours', 24)
    if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or not math.isfinite(ttl) or ttl <= 0 or ttl > 24 * 30:
        raise OnboardingError('max_age_hours 必须为 0 至 720 之间的正数。')
    connection_results = []
    connection_requirements = {'read': [], 'write': []}
    selected_platforms = value('platforms')
    if not selected_keys:
        missing('selected_accounts', 'unknown', '尚未明确本档案选定的平台账户。')
    for platform, account in selected_keys:
        check = indexed.get((platform, account), {})
        for permission, required_scope in (('read', 'read_objects'), ('write', 'create_simulated_draft')):
            key = f'connections.{platform}.{account}.{permission}'
            connection_requirements[permission].append(key)
            record = check.get(permission, {})
            status, reason = 'unknown', '连接被发现不等于读/写能力已经验证。'
            if selected_platforms is not None and platform not in selected_platforms:
                status, reason = 'conflict', '选定账户的平台不在 facts.platforms 范围。'
            elif isinstance(record, dict) and record.get('status') == 'verified' and check.get('discovered') is True:
                scopes = record.get('scopes', [])
                try:
                    checked_at = timestamp(record.get('checked_at'))
                    age = (current - checked_at).total_seconds() / 3600
                    if age < 0:
                        status, reason = 'conflict', 'checked_at 位于未来，不能视作已验证。'
                    elif age > ttl:
                        status, reason = 'stale', '模拟验证时间已超过新鲜度窗口。'
                    elif not isinstance(scopes, list) or required_scope not in scopes:
                        status, reason = 'unknown', '验证 scope 不覆盖本原型所需动作。'
                    else:
                        status, reason = 'verified_simulation', '仅为离线 fixture 验证，不代表真实账户权限。'
                except OnboardingError as exc:
                    reason = str(exc)
            elif isinstance(record, dict) and record.get('status') in {'stale', 'failed'}:
                status, reason = 'stale' if record['status'] == 'stale' else 'unknown', '连接检查未通过或已过期。'
            if status != 'verified_simulation':
                missing(key, status, reason)
            connection_results.append({'platform': platform, 'account_id': account, 'permission': permission, 'status': status, 'reason': reason})

    connection_fields = connection_requirements['read'] + connection_requirements['write'] or ['selected_accounts']
    gate_gaps = [key for key in connection_fields if key in gaps]
    hard_gate = any(gaps[key]['status'] in {'conflict', 'stale', 'unsupported'} for key in gate_gaps)
    connection_gate = {
        'status': ('blocked' if hard_gate else 'needs_input') if gate_gaps else 'ready_simulation',
        'mode': 'simulation', 'gaps': gate_gaps,
        'selected_accounts': [{'platform': platform, 'account_id': account} for platform, account in selected_keys],
        'required_capabilities': ['read_objects', 'create_simulated_draft'],
        'notice': '先验收本次选定账户的读取与必要写能力，再进入访谈；当前只核对离线快照，不证明真实接入或授权发布。'}
    guided = guidance.evaluate({**data, 'selected_accounts': connection_gate['selected_accounts']}, connected=not gate_gaps)
    collaboration_fields = []
    if not gate_gaps and guided['stage'] == 'collaboration_intake':
        for question in guided['questions']:
            key = question['key']
            collaboration_fields.append(key)
            missing(key, 'unknown', '接入已就绪；先明确希望如何协作及本次需求。')

    material_fields = ['product_name', 'surface', 'countries', 'creative_direction']
    planning_fields = material_fields + ['platforms', 'methodology', 'audience', 'goal_type', 'success_metric', 'learning_budget'] + app_fields
    if goal in {'revenue', 'value'}:
        planning_fields += ['monetization'] + model_fields
    if goal == 'value':
        planning_fields += ['value_basis', 'value_window']
    if goal == 'conversion' and monetization == 'leadgen':
        planning_fields += ['lead_event', 'lead_qualification']
    readiness = {}

    def readiness_for(workflow, fields, connection_fields):
        required = list(dict.fromkeys(fields))
        for key in required:
            usable(key)
        required += connection_fields + collaboration_fields
        if connection_fields and not selected_keys:
            required.append('selected_accounts')
        missing_keys = [key for key in dict.fromkeys(required) if key in gaps]
        for key in missing_keys:
            gaps[key]['required_by'].append(workflow)
        hard = any(gaps[key]['status'] in {'conflict', 'stale', 'unsupported'} for key in missing_keys)
        readiness[workflow] = {'status': ('blocked' if hard else 'needs_input') if missing_keys else 'ready',
                               'gaps': missing_keys, 'mode': 'simulation'}

    readiness_for('discovery', [], connection_fields)
    readiness_for('material_selection', material_fields, connection_fields)
    readiness_for('test_planning', planning_fields, connection_fields)
    readiness_for('publish', planning_fields, connection_fields)
    if workflow not in readiness:
        raise OnboardingError('不支持的当前 workflow。')
    asked = asked_questions if asked_questions is not None else profile.get('asked_questions', [])
    if not isinstance(asked, list) or not all(isinstance(q, str) for q in asked):
        raise OnboardingError('asked_questions 需要字符串列表。')
    asked = list(dict.fromkeys(asked))
    relevant = [gap for gap in gaps.values() if workflow in gap['required_by']]
    machine_gaps = [gap for gap in relevant if gap['key'].startswith('connections.') or gap['key'] == 'selected_accounts']
    human_gaps = [gap for gap in relevant if gap not in machine_gaps]
    ordered = sorted(human_gaps, key=lambda gap: (0 if gap['status'] in {'conflict', 'stale'} else 1, list(gaps).index(gap['key'])))
    next_questions = [{'key': gap['key'], 'question': QUESTIONS.get(gap['key'], '请补充或核对 ' + gap['key'] + ' 的信息、来源和当前状态。'),
                       'reason': gap['reason'], 'status': gap['status']} for gap in ordered if gap['key'] not in asked][:3]
    if gate_gaps:
        next_questions = []
    elif guided['stage'] == 'collaboration_intake':
        next_questions = [{**question, 'status': 'unknown', 'reason': '先确定协作方式和本次需求。'}
                          for question in guided['questions'] if question['key'] not in asked][:3]
        familiarity = guided.get('familiarity_question')
        if familiarity:
            missing(familiarity['key'], 'unknown', '可选的平台熟悉度；允许暂时不确定，不阻断业务工作流。')
            if len(next_questions) < 3 and familiarity['key'] not in asked:
                next_questions.append({**familiarity, 'status': 'unknown', 'reason': '帮助选择合适的说明方式，可跳过。'})
    else:
        method_question = next((question for question in guided['questions'] if question['key'] == 'methodology'), None)
        for question in next_questions:
            if question['key'] == 'methodology' and method_question:
                question['question'] = method_question['question']
            elif data.get('collaboration', {}).get('approach') == 'guided':
                plain_questions = {
                    'audience': '哪些人最可能需要这个产品？不知道也可以，先说说他们遇到的问题。',
                    'creative_direction': '有哪些图片、视频或产品演示可用？你希望用户首先明白什么？',
                    'goal_type': '这次最想得到订单、咨询、注册，还是先验证有没有人感兴趣？',
                    'success_metric': '看到什么结果，你会认为这轮尝试有价值？我可以帮你整理可选指标。',
                    'learning_budget': '这一轮最多愿意投入多少广告费，使用哪种货币？'}
                question['question'] = plain_questions.get(question['key'], question['question'])
    knowledge_stage = {'discovery': 'discovery', 'material_selection': 'creative',
                       'test_planning': 'planning', 'publish': 'launch'}[workflow]
    knowledge_profile = data
    if account_scope is not None:
        knowledge_profile = {**data, 'facts': {**facts, 'platforms': {
            'value': sorted({platform for platform, _ in selected_keys}),
            'status': 'confirmed', 'source': 'validated_selected_account_scope'}}}
    knowledge_review = knowledge.assess(knowledge_profile, knowledge_stage, as_of=current,
                                        private_snapshot=private_snapshot)
    if gate_gaps or guided['stage'] == 'collaboration_intake':
        knowledge_review.update(items=[], total_matches=0, truncated=False,
                                deferred=True, notice='先完成接入验收与协作需求确认，投放知识评估暂不呈现。')
    for question in next_questions:
        supporting = [item for item in knowledge_review['items'] if question['key'] in item['required_facts']]
        question['knowledge_refs'] = [item['id'] for item in supporting]
        question['why_it_matters'] = [item['summary'] for item in supporting]
    return {'schema_version': 1, 'kind': 'offline_onboarding_context', 'mode': 'simulation',
            'notice': '仅模拟连接 snapshot；没有真实 API/MCP/auth/provider 检查或变更。',
            'profile_id': data['profile_id'], 'profile_version': data['profile_version'],
            'profile_hash': source_profile_hash, 'profile_snapshot': data, 'readiness': readiness,
            'private_memory': private_snapshot,
            'current_workflow': workflow,
            'connection_gate': connection_gate, 'guidance': guided,
            'knowledge_review': knowledge_review,
            'connection_results': connection_results, 'gaps': list(gaps.values()), 'next_questions': next_questions,
            'machine_actions': [{'key': gap['key'], 'status': gap['status'], 'reason': gap['reason'],
                                 'action': 'resolve_selected_accounts' if gap['key'] == 'selected_accounts' else 'refresh_connection_snapshot',
                                 'mode': 'simulation', 'note': '连接器应检查和回报；此原型只读取离线 fixture，不要求用户手填验证成功。'} for gap in machine_gaps],
            'question_progress': {'profile_id': data['profile_id'], 'asked_questions': asked + [q['key'] for q in next_questions],
                                  'unresolved': [gap['key'] for gap in gaps.values() if gap['key'] in asked]}}


def build_context(input_path, output_dir, as_of=None, workflow='test_planning'):
    source = Path(input_path).resolve()
    output = Path(output_dir)
    progress_path = output / 'question_progress.json'
    profile = read(source)
    progress = read(progress_path) if progress_path.exists() else {}
    asked = progress.get('asked_questions', []) if progress.get('profile_id') == profile.get('profile_id') else None
    result = evaluate(profile, asked_questions=asked, as_of=as_of, workflow=workflow)
    result['source_ref'] = str(source)
    write(output / 'context.json', result)
    write(output / 'setup.json', {'connection_gate': result['connection_gate'], 'guidance': result['guidance']})
    (output / 'setup.md').write_text(setup_markdown(result), encoding='utf-8')
    write(output / 'knowledge-review.json', result['knowledge_review'])
    write(output / 'gaps.json', {'profile_hash': result['profile_hash'], 'readiness': result['readiness'], 'gaps': result['gaps']})
    write(output / 'questions.json', {'workflow': workflow, 'next_questions': result['next_questions'], 'unresolved': result['question_progress']['unresolved'], 'machine_actions': result['machine_actions']})
    write(progress_path, result['question_progress'])
    lines = ['# 业务档案摘要（离线模拟）', '', result['notice'], '',
             f"档案：{result['profile_id']} / 版本 {result['profile_version']}", '', f"业务内容 hash：`{result['profile_hash']}`", '', '## 事实与来源', '']
    for key, fact in result['profile_snapshot']['facts'].items():
        lines.append(f"- {key}：{json.dumps(fact['value'], ensure_ascii=False)}；状态={fact['status']}；来源={fact.get('source', '未提供')}")
    lines += ['', '## 工作流准备度', '']
    for workflow, state in result['readiness'].items():
        lines.append(f"- {workflow}：{state['status']}；缺口={', '.join(state['gaps']) or '无相关缺口'}")
    lines += ['', '## 本轮最多三个问题', '']
    lines += [f"- {q['question']}（{q['status']}）" for q in result['next_questions']] or ['没有新问题；已问未答仍在 unresolved 和 gaps 中，不代表信息已补齐。']
    lines += ['', '## 连接检查待办（机器动作，不是访谈问题）', '']
    lines += [f"- {action['key']}：{action['action']}；{action['reason']}" for action in result['machine_actions']] or ['当前工作流没有连接检查待办。']
    lines += ['', '先完成连接验收与协作方式确认；之后收入/LTV 等信息只影响依赖它们的目标。', '']
    lines += [knowledge.markdown(result['knowledge_review'])]
    (output / 'summary.md').write_text('\n'.join(lines), encoding='utf-8')
    return result


def setup_markdown(result):
    gate, route = result['connection_gate'], result['guidance']
    lines = ['# 首次接入与协作引导', '', gate['notice'], '',
             '接入状态：' + gate['status'], '', '当前阶段：' + route['stage'], '']
    recommendation = route.get('recommendation')
    if recommendation:
        # Structured content only; no installation, checkout, auth or ad writes occur here.
        lines += [guidance.recommendation_markdown(recommendation), '']
    lines += ['## 当前待办', '']
    lines += [f"- {step}" for step in route.get('setup_steps', [])]
    lines += [f"- {action['key']}：{action['reason']}" for action in result['machine_actions']]
    lines += [f"- {question['question']}" for question in result['next_questions']]
    if not result['machine_actions'] and not result['next_questions']:
        lines += ['没有新问题；请结合 context.json 中仍未解决的缺口判断下一步。']
    lines += ['', '协作方式与平台熟练度不会增加账户访问或发布权限。', '']
    return '\n'.join(lines)


def validate_context(path, expected_hash=None, targets=None, workflow='publish', as_of=None, brief_budget=None, currency=None):
    path = Path(path).resolve()
    saved = read(path)
    if saved.get('kind') != 'offline_onboarding_context' or saved.get('mode') != 'simulation':
        raise OnboardingError('context 不是有效的离线 onboarding 结果。')
    source = saved.get('source_ref')
    if not isinstance(source, str) or not Path(source).is_file():
        raise OnboardingError('当前业务档案来源无法读取，不能使用孤立旧快照。')
    current = evaluate(read(source), as_of=as_of, account_scope=targets, workflow=workflow)
    if saved.get('profile_hash') != current['profile_hash'] or (expected_hash is not None and expected_hash != current['profile_hash']):
        raise OnboardingError('业务档案已改版或 hash 不符；旧计划必须重新评估。')
    if current['readiness'][workflow]['status'] != 'ready':
        raise OnboardingError(f"{workflow} 未就绪：" + ', '.join(current['readiness'][workflow]['gaps']))
    scope = {(a['platform'], a['account_id']) for a in current['profile_snapshot']['selected_accounts']}
    for target in targets or []:
        if (target.get('platform'), target.get('account_id')) not in scope:
            raise OnboardingError('brief 的平台/账户超出业务档案选定范围。')
    if brief_budget is not None:
        learning_budget = current['profile_snapshot']['facts']['learning_budget']['value']
        if currency != learning_budget['currency'] or Decimal(str(brief_budget)) > Decimal(str(learning_budget['amount'])):
            raise OnboardingError('brief 预算/币种超出业务档案已确认的学习预算。')
    return {'reference': str(path), 'profile_id': current['profile_id'], 'profile_version': current['profile_version'],
            'profile_hash': current['profile_hash'], 'private_memory_hash': current['private_memory']['active_hash'],
            'mode': 'simulation'}


def refresh_simulation_fixture(input_path, output_path, as_of=None):
    source, destination = Path(input_path).resolve(), Path(output_path).resolve()
    if source == destination:
        raise OnboardingError('模拟刷新必须生成新副本，禁止就地覆盖来源示例。')
    profile = read(source)
    if profile.get('mode') != 'simulation' or profile.get('fixture_only') is not True or profile.get('connections', {}).get('mode') != 'simulation':
        raise OnboardingError('只能刷新明确标记 fixture_only=true 的纯模拟输入。')
    current = as_of or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise OnboardingError('模拟刷新时间必须带时区。')
    checked = current.astimezone(timezone.utc).isoformat()
    for connection in profile['connections'].get('checks', []):
        for permission in ('read', 'write'):
            record = connection.get(permission)
            if isinstance(record, dict) and record.get('status') == 'verified':
                record['checked_at'] = checked
                record['evidence'] = 'fictional fixture timestamp reset; NO real verification performed'
    profile['fixture_refreshed_at'] = checked
    write(destination, profile)
    return {'mode': 'simulation', 'notice': '仅更新新副本的虚拟时间；unknown/failed 不改成 verified，未检查任何真实连接。',
            'output': str(destination), 'next': '重建 context 和 plan；使用新的 state 目录。'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline onboarding: connection fixtures, sourced facts and workflow readiness')
    parser.add_argument('--input', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--workflow', choices=['discovery', 'material_selection', 'test_planning', 'publish'], default='test_planning')
    parser.add_argument('--refresh-simulation-fixture', action='store_true', help='Write a NEW fixture-only input copy with fresh fictional timestamps; no real checks')
    args = parser.parse_args(argv)
    try:
        if args.refresh_simulation_fixture:
            print(json.dumps(refresh_simulation_fixture(args.input, args.out), ensure_ascii=False, indent=2))
            return 0
        result = build_context(args.input, args.out, workflow=args.workflow)
        print(json.dumps({'mode': 'simulation', 'profile_hash': result['profile_hash'], 'connection_gate': result['connection_gate'],
                          'guidance': result['guidance'], 'readiness': result['readiness'], 'next_questions': result['next_questions'],
                          'machine_actions': result['machine_actions']}, ensure_ascii=False, indent=2))
        return 2 if result['connection_gate']['status'] != 'ready_simulation' or result['guidance']['stage'] == 'collaboration_intake' else 0
    except (OnboardingError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
