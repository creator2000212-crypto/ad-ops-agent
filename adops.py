#!/usr/bin/env python3
"""Offline execution-contract prototype. No real advertising API or network code."""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import onboarding
import knowledge

PLATFORMS = {'meta', 'tiktok', 'google'}
ACTIONS = {'create_simulated_draft', 'readback_simulated_draft'}
NOTICE = 'OFFLINE SIMULATION ONLY — 不是用户真实发布批准，不会上传素材或发布广告。'


class ContractError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f, parse_constant=lambda value: (_ for _ in ()).throw(ContractError('Non-finite JSON number: ' + value)))


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(path)


def amount(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ContractError('预算必须为明确的正数，不允许缺失值。')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ContractError('预算不是合法十进制数。') from exc
    if not result.is_finite() or result <= 0:
        raise ContractError('预算必须为有限正数。')
    return result


def text_present(value):
    return isinstance(value, str) and bool(value.strip())


def string_list(value):
    return isinstance(value, list) and all(text_present(x) for x in value)


def build_plan(brief, candidates, context_path=None):
    if not isinstance(brief, dict) or not isinstance(candidates, dict):
        raise ContractError('brief 和 candidates 必须是 JSON 对象。')
    issues = []

    def issue(code, path, message):
        issues.append({'code': code, 'path': path, 'message': message})

    known_brief = {'task_id', 'mode', 'business_type', 'objective', 'target_event', 'currency', 'timezone', 'budget', 'targets', 'asset_requirements'}
    for key in sorted(set(brief) - known_brief):
        issue('unsupported', key, '此简报字段尚未实现，不能静默忽略。')
    for key in ('task_id', 'objective', 'target_event', 'currency', 'timezone'):
        if not text_present(brief.get(key)):
            issue('needs_input', key, '缺少明确的 ' + key)
    if brief.get('mode') != 'simulation':
        issue('unsupported', 'mode', '仅支持 simulation；live 永久拒绝。')
    if text_present(brief.get('currency')) and not re.fullmatch('[A-Z]{3}', brief['currency']):
        issue('needs_input', 'currency', '币种使用三个大写字母；本原型不验证平台币种支持。')
    if text_present(brief.get('timezone')):
        try:
            ZoneInfo(brief['timezone'])
        except (ZoneInfoNotFoundError, ValueError):
            issue('needs_input', 'timezone', '需要可识别的 IANA 时区。')
    budget = brief.get('budget')
    total_budget = None
    if not isinstance(budget, dict):
        issue('needs_input', 'budget', '需要 budget.amount 和 budget.period。')
    else:
        for key in sorted(set(budget) - {'amount', 'period'}):
            issue('unsupported', 'budget.' + key, '此预算约束尚未实现。')
        try:
            total_budget = amount(budget.get('amount'))
        except ContractError as exc:
            issue('needs_input', 'budget.amount', str(exc))
        if not text_present(budget.get('period')):
            issue('needs_input', 'budget.period', '必须明确预算周期。')
        elif budget['period'] != 'total':
            issue('unsupported', 'budget.period', '原型只支持本次逻辑测试总预算 total；未实现 daily 等模式。')

    targets = brief.get('targets')
    valid_targets, seen_targets = [], set()
    if not isinstance(targets, list) or not targets:
        issue('needs_input', 'targets', '至少提供一个明确的投放目标账户。')
        targets = []
    for i, target in enumerate(targets):
        path = f'targets[{i}]'
        if not isinstance(target, dict):
            issue('needs_input', path, 'target 必须是对象。')
            continue
        before = len(issues)
        for key in sorted(set(target) - {'platform', 'account_id', 'profile', 'budget_amount'}):
            issue('unsupported', path + '.' + key, '此平台配置尚未实现，不能静默忽略。')
        for key in ('platform', 'account_id', 'profile'):
            if not text_present(target.get(key)):
                issue('needs_input', path + '.' + key, '必须明确 ' + key)
        if text_present(target.get('platform')) and target['platform'] not in PLATFORMS:
            issue('unsupported', path + '.platform', '仅命名 meta/tiktok/google 三个模拟适配器。')
        if text_present(target.get('profile')) and target['profile'] != 'generic_draft':
            issue('unsupported', path + '.profile', '仅支持 generic_draft；未实现 Search/PMax 等真实广告产品。')
        target_amount = None
        try:
            target_amount = amount(target.get('budget_amount'))
        except ContractError as exc:
            issue('needs_input', path + '.budget_amount', str(exc))
        identity = (target.get('platform'), target.get('account_id'))
        if all(isinstance(x, str) for x in identity):
            if identity in seen_targets:
                issue('needs_input', path, '同一平台账户不允许重复分配预算。')
            seen_targets.add(identity)
        if before == len(issues):
            valid_targets.append({**target, 'budget_amount': str(target_amount)})
    if total_budget is not None and len(valid_targets) == len(targets):
        allocated = sum((amount(t['budget_amount']) for t in valid_targets), Decimal(0))
        if allocated > total_budget:
            issue('needs_input', 'targets', '账户分配预算之和超过任务总预算。')

    requirements = brief.get('asset_requirements')
    requirements_ok = isinstance(requirements, dict)
    if not requirements_ok:
        issue('needs_input', 'asset_requirements', '必须明确素材筛选条件。')
        requirements = {}
    for key in ('required_tags', 'excluded_tags', 'allowed_types'):
        if not string_list(requirements.get(key)) or (key == 'allowed_types' and not requirements.get(key)):
            issue('needs_input', 'asset_requirements.' + key, '需要明确的字符串数组。')
            requirements_ok = False
    if not text_present(requirements.get('language')):
        issue('needs_input', 'asset_requirements.language', '必须明确素材语言。')
        requirements_ok = False
    count = requirements.get('count')
    if type(count) is not int or count <= 0:
        issue('needs_input', 'asset_requirements.count', '必须明确正整数素材数量。')
        requirements_ok = False
    for key in ('min_width', 'min_height'):
        if key in requirements and (type(requirements[key]) is not int or requirements[key] <= 0):
            issue('needs_input', 'asset_requirements.' + key, '若设置尺寸下限，必须为正整数。')
            requirements_ok = False
    known_requirements = {'required_tags', 'excluded_tags', 'allowed_types', 'language', 'count', 'min_width', 'min_height'}
    for key in sorted(set(requirements) - known_requirements):
        issue('unsupported', 'asset_requirements.' + key, '此筛选约束尚未实现，不能静默忽略。')
        requirements_ok = False

    assets = candidates.get('assets')
    if not isinstance(assets, list):
        issue('needs_input', 'candidates.assets', '必须提供素材元数据数组。')
        assets = []
    selected, decisions, asset_ids = [], [], set()
    for i, asset in enumerate(assets):
        reasons = []
        if not isinstance(asset, dict):
            decisions.append({'candidate_index': i, 'status': 'excluded', 'reasons': ['unknown: metadata object missing']})
            continue
        aid = asset.get('asset_id')
        for key in ('asset_id', 'source_ref', 'type', 'language'):
            if not text_present(asset.get(key)):
                reasons.append('unknown: ' + key)
        if text_present(aid):
            if aid in asset_ids:
                issue('needs_input', f'candidates.assets[{i}].asset_id', '素材 ID 重复。')
                reasons.append('duplicate asset_id')
            asset_ids.add(aid)
        if not string_list(asset.get('tags')):
            reasons.append('unknown: tags')
        if requirements_ok:
            if string_list(asset.get('tags')):
                if not set(requirements['required_tags']).issubset(asset['tags']):
                    reasons.append('required tags missing')
                if set(requirements['excluded_tags']) & set(asset['tags']):
                    reasons.append('excluded tag present')
            if asset.get('type') not in requirements['allowed_types']:
                reasons.append('type does not match')
            if asset.get('language') != requirements['language']:
                reasons.append('language does not match')
            for limit, field in (('min_width', 'width'), ('min_height', 'height')):
                if limit in requirements:
                    if type(asset.get(field)) is not int or asset[field] <= 0:
                        reasons.append('unknown: ' + field)
                    elif asset[field] < requirements[limit]:
                        reasons.append(field + ' below minimum')
        else:
            reasons.append('selection blocked by invalid requirements')
        if reasons:
            status = 'excluded'
        elif len(selected) < count:
            status = 'selected'
            selected.append(asset)
            reasons = ['matches explicit metadata requirements; selected in input order']
        else:
            status = 'eligible_not_selected'
            reasons = ['matches metadata; requested count already filled']
        decisions.append({'candidate_index': i, 'asset_id': aid, 'status': status, 'reasons': reasons})
    if requirements_ok and len(selected) < count:
        issue('needs_input', 'candidates', f'符合明确元数据条件的素材不足：{len(selected)}/{count}。未知值没有当作零或合格。')

    context = None
    if context_path is None:
        issue('needs_input', 'context', '先完成 onboarding，必须引用当前业务档案 context。')
    else:
        try:
            context = onboarding.validate_context(context_path, targets=valid_targets, workflow='test_planning',
                                                  brief_budget=str(total_budget) if total_budget is not None else None,
                                                  currency=brief.get('currency'))
        except (onboarding.OnboardingError, OSError, ValueError, TypeError, KeyError) as exc:
            issue('needs_input', 'context', str(exc))
    operations = []
    if not issues:
        for target in valid_targets:
            spec = {'platform': target['platform'], 'account_id': target['account_id'],
                    'profile': 'generic_draft', 'objective_label': brief['objective'],
                    'target_event_label': brief['target_event'], 'timezone': brief['timezone'],
                    'budget': {'amount': target['budget_amount'], 'currency': brief['currency'], 'period': 'total'},
                    'assets': selected, 'native_payload': None}
            operations.append({'operation_id': digest({'task_id': brief['task_id'], 'spec': spec})[:24],
                               'action': 'create_simulated_draft', 'adapter': 'simulation',
                               'desired': spec})
    status = 'unsupported' if any(i['code'] == 'unsupported' for i in issues) else ('needs_input' if issues else 'ready')
    knowledge_reviews = []
    if context:
        saved_context = onboarding.read(context['reference'])
        profile = onboarding.read(saved_context['source_ref'])
        scoped_profile = {**profile, 'facts': {**profile['facts'], 'platforms': {
            'value': sorted({target['platform'] for target in valid_targets}),
            'status': 'confirmed', 'source': 'validated_plan_targets'}}}
        catalog = knowledge.load_catalog()
        knowledge_reviews = [knowledge.assess(scoped_profile, stage, catalog=catalog)
                             for stage in ('planning', 'creative', 'launch')]
    plan = {'schema_version': 1, 'kind': 'offline_simulation_plan', 'notice': NOTICE,
            'task_id': brief.get('task_id'), 'mode': 'simulation', 'status': status,
            'business_context': context,
            'knowledge_reviews': knowledge_reviews,
            'brief_snapshot': brief, 'candidates_metadata_hash': digest(candidates),
            'selection_basis': 'metadata_only_input_order; no file inspection, visual understanding or performance prediction',
            'asset_decisions': decisions, 'issues': issues, 'operations': operations,
            'workflow': ['validate_inputs', 'select_metadata', 'create_simulated_draft', 'readback_simulated_draft']}
    plan['plan_hash'] = digest(plan)
    return plan


def verify_plan(plan):
    if not isinstance(plan, dict):
        raise ContractError('计划必须是 JSON 对象。')
    supplied = plan.get('plan_hash')
    content = {k: v for k, v in plan.items() if k != 'plan_hash'}
    if not isinstance(supplied, str) or digest(content) != supplied:
        raise ContractError('计划 hash 不匹配：计划可能已被修改，必须重新生成与审阅。')
    if plan.get('mode') != 'simulation' or plan.get('kind') != 'offline_simulation_plan':
        raise ContractError('拒绝 live 或非本原型计划。')
    if plan.get('status') != 'ready' or plan.get('issues'):
        raise ContractError('计划尚未 ready；缺字段或 unsupported 必须先解决。')
    if not isinstance(plan.get('operations'), list) or not plan['operations']:
        raise ContractError('没有可执行的模拟操作。')
    reviews = plan.get('knowledge_reviews')
    catalog_hash = knowledge.digest(knowledge.load_catalog())
    if not isinstance(reviews, list) or len(reviews) != 3 or any(
            not isinstance(review, dict) or review.get('catalog_hash') != catalog_hash
            for review in reviews):
        raise ContractError('知识库已改版或缺少知识评审；请重新生成计划和模拟授权。')
    context = plan.get('business_context')
    if not isinstance(context, dict) or not context.get('reference') or not context.get('profile_hash'):
        raise ContractError('缺少 onboarding context；旧格式计划必须重新评估。')
    try:
        brief = plan['brief_snapshot']
        onboarding.validate_context(context['reference'], expected_hash=context['profile_hash'],
                                    targets=brief['targets'], workflow='publish',
                                    brief_budget=brief['budget']['amount'], currency=brief['currency'])
    except (onboarding.OnboardingError, OSError, ValueError, TypeError, KeyError) as exc:
        raise ContractError('业务上下文检查失败：' + str(exc)) from exc
    for operation in plan['operations']:
        spec = operation.get('desired', {})
        if operation.get('adapter') != 'simulation' or operation.get('action') != 'create_simulated_draft':
            raise ContractError('仅允许 simulation adapter 的逻辑草稿操作。')
        if spec.get('platform') not in PLATFORMS or spec.get('profile') != 'generic_draft' or spec.get('native_payload') is not None:
            raise ContractError('平台/profile 不支持，或出现禁止的 native payload。')


def authorization_for(plan):
    verify_plan(plan)
    return {'schema_version': 1, 'kind': 'simulation_authorization', 'notice': NOTICE,
            'simulation_only': True, 'task_id': plan['task_id'], 'plan_hash': plan['plan_hash'],
            'allowed_actions': sorted(ACTIONS),
            'account_scopes': [{'platform': op['desired']['platform'], 'account_id': op['desired']['account_id'],
                                'currency': op['desired']['budget']['currency'], 'period': 'total',
                                'max_amount': op['desired']['budget']['amount']} for op in plan['operations']]}


def verify_authorization(plan, authorization):
    verify_plan(plan)
    if not isinstance(authorization, dict) or authorization.get('kind') != 'simulation_authorization' or authorization.get('simulation_only') is not True:
        raise ContractError('必须提供明确标记的仅模拟授权；它不等于真实批准。')
    if authorization.get('plan_hash') != plan['plan_hash'] or authorization.get('task_id') != plan['task_id']:
        raise ContractError('模拟授权与冻结计划 hash/task_id 不匹配。')
    allowed = authorization.get('allowed_actions')
    if not string_list(allowed) or not ACTIONS.issubset(set(allowed)):
        raise ContractError('授权未覆盖模拟创建与读回动作。')
    scopes = authorization.get('account_scopes')
    if not isinstance(scopes, list):
        raise ContractError('缺少账户预算授权范围。')
    limits = {}
    for scope in scopes:
        if not isinstance(scope, dict):
            raise ContractError('授权账户范围格式错误。')
        key = (scope.get('platform'), scope.get('account_id'), scope.get('currency'), scope.get('period'))
        if not all(text_present(x) for x in key) or key in limits:
            raise ContractError('授权账户范围缺字段或重复。')
        limits[key] = amount(scope.get('max_amount'))
    totals = {}
    for op in plan['operations']:
        spec = op['desired']
        budget = spec['budget']
        key = (spec['platform'], spec['account_id'], budget['currency'], budget['period'])
        totals[key] = totals.get(key, Decimal(0)) + amount(budget['amount'])
    for key, requested in totals.items():
        if key not in limits or requested > limits[key]:
            raise ContractError('账户、币种、周期或预算超出模拟授权范围：' + str(key))


def write_review(plan, path):
    lines = ['# 离线投放草稿审阅', '', NOTICE, '', '**状态：** ' + plan['status'], '',
             '**冻结 hash：** `' + plan['plan_hash'] + '`', '',
             '仅按显式元数据筛选；没有读取媒体内容、理解画面、检查真实账户或判断平台可投放性。', '',
             '## 逻辑执行范围', '']
    if plan.get('business_context'):
        lines[8:8] = ['业务档案引用：`' + plan['business_context']['reference'] + '`', '',
                      '业务内容 hash：`' + plan['business_context']['profile_hash'] + '`', '']
    for op in plan['operations']:
        d = op['desired']
        b = d['budget']
        lines.append(f"- {d['platform']} / {d['account_id']} / generic_draft：{b['amount']} {b['currency']}（total）；素材 {', '.join(a['asset_id'] for a in d['assets'])}；只创建本地模拟草稿并读回。")
    if not plan['operations']:
        lines.append('没有可执行步骤。')
    lines += ['', '## 素材选择依据', '']
    for item in plan['asset_decisions']:
        lines.append(f"- {item.get('asset_id', 'unknown')}：{item['status']} — {'; '.join(item['reasons'])}")
    lines += ['', '## 阻断项', '']
    lines += [f"- {i['code']} / {i['path']}：{i['message']}" for i in plan['issues']] or ['无本地契约阻断项；这不表示真实广告平台已验证。']
    lines += ['', '本文件用于整批方案审阅。authorize-simulation 只创建测试用授权文件，不记录或推断用户对真实发布的批准。', '']
    for review in plan.get('knowledge_reviews', []):
        lines += [knowledge.markdown(review)]
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


def event(db, op_id, state, detail):
    db.execute('INSERT INTO events(at,operation_id,state,detail) VALUES(?,?,?,?)', (now(), op_id, state, canonical(detail)))


def execute(plan, authorization, state_dir, interrupt_after_write=0):
    verify_authorization(plan, authorization)
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(state_dir / 'simulation.sqlite3'))
    db.row_factory = sqlite3.Row
    bound_to_plan = False
    active_operation = None
    try:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY,state TEXT NOT NULL,desired TEXT NOT NULL,object_id TEXT);
        CREATE TABLE IF NOT EXISTS simulated_objects(operation_id TEXT PRIMARY KEY,object_id TEXT UNIQUE NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,operation_id TEXT NOT NULL,state TEXT NOT NULL,detail TEXT NOT NULL);
        ''')
        existing = db.execute("SELECT value FROM metadata WHERE key='plan_hash'").fetchone()
        if existing and existing['value'] != plan['plan_hash']:
            raise ContractError('此 state 目录已绑定另一个计划；每个冻结计划使用独立目录。')
        with db:
            db.execute("INSERT OR IGNORE INTO metadata VALUES('plan_hash',?)", (plan['plan_hash'],))
        bound_to_plan = True
        receipts, written = [], 0
        for op in plan['operations']:
            op_id, desired = op['operation_id'], canonical(op['desired'])
            active_operation = op_id
            current = db.execute('SELECT * FROM operations WHERE id=?', (op_id,)).fetchone()
            if current and current['desired'] != desired:
                raise ContractError('同一 operation_id 的期望配置发生漂移。')
            remote = db.execute('SELECT * FROM simulated_objects WHERE operation_id=?', (op_id,)).fetchone()
            if current:
                # Includes submitted/uncertain: reconcile first; never blindly repeat a write.
                with db:
                    event(db, op_id, 'reconcile', {'previous_state': current['state'], 'found': remote is not None})
                if remote is None:
                    raise ContractError('存在未确认操作但无法找到模拟对象；停止并核对，禁止盲重试。')
            else:
                if remote is not None:
                    raise ContractError('发现无对应操作日志的模拟对象；需要人工核对状态。')
                with db:
                    db.execute('INSERT INTO operations VALUES(?,?,?,NULL)', (op_id, 'submitted', desired))
                    event(db, op_id, 'submitted', {'adapter': 'simulation', 'action': op['action']})
                object_id = 'sim_' + op_id
                with db:
                    db.execute('INSERT INTO simulated_objects VALUES(?,?,?)', (op_id, object_id, desired))
                written += 1
                if interrupt_after_write and written == interrupt_after_write:
                    with db:
                        db.execute("UPDATE operations SET state='uncertain' WHERE id=?", (op_id,))
                        event(db, op_id, 'uncertain', {'reason': 'explicit offline interruption after simulated write'})
                    result = {'mode': 'simulation', 'notice': NOTICE, 'status': 'interrupted', 'plan_hash': plan['plan_hash'], 'operation_id': op_id, 'next': 'resume must reconcile before writing'}
                    save(state_dir / 'result.json', result)
                    return result
                remote = db.execute('SELECT * FROM simulated_objects WHERE operation_id=?', (op_id,)).fetchone()
            if remote['payload'] != desired:
                raise ContractError('模拟读回与期望配置不同；禁止覆盖或判为完成。')
            with db:
                db.execute("UPDATE operations SET state='verified',object_id=? WHERE id=?", (remote['object_id'], op_id))
                event(db, op_id, 'verified', {'object_id': remote['object_id'], 'readback_matches': True})
            receipts.append({'operation_id': op_id, 'object_id': remote['object_id'], 'state': 'verified',
                             'readback_matches': True, 'platform_status': 'simulated_draft_only',
                             'readback': json.loads(remote['payload'])})
        result = {'mode': 'simulation', 'notice': NOTICE, 'status': 'completed_simulation',
                  'plan_hash': plan['plan_hash'], 'created_this_run': written,
                  'simulated_object_count': db.execute('SELECT COUNT(*) FROM simulated_objects').fetchone()[0],
                  'receipts': receipts}
        save(state_dir / 'result.json', result)
        return result
    except ContractError as exc:
        if bound_to_plan:
            with db:
                event(db, active_operation or '__task__', 'blocked', {'reason': str(exc)})
                if active_operation:
                    db.execute("UPDATE operations SET state='blocked' WHERE id=?", (active_operation,))
            save(state_dir / 'result.json', {'mode': 'simulation', 'notice': NOTICE, 'status': 'blocked',
                                           'plan_hash': plan['plan_hash'], 'operation_id': active_operation,
                                           'error': str(exc), 'recorded_at': now()})
        raise
    finally:
        db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=NOTICE)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('plan', help='Create local plan.json and review.md from explicit metadata')
    p.add_argument('--brief', required=True)
    p.add_argument('--candidates', required=True)
    p.add_argument('--context', required=True, help='Current onboarding context.json; source is re-evaluated')
    p.add_argument('--out', required=True)
    p.add_argument('--mode', default='simulation')
    a = commands.add_parser('authorize-simulation', help='Generate a simulation-only scope token; never a real approval')
    a.add_argument('--plan', required=True)
    a.add_argument('--out', required=True)
    for name in ('execute', 'resume'):
        p = commands.add_parser(name, help='Execute/reconcile the same frozen plan using local SQLite only')
        p.add_argument('--plan', required=True)
        p.add_argument('--authorization', required=True)
        p.add_argument('--state', required=True)
        p.add_argument('--mode', default='simulation')
        p.add_argument('--interrupt-after-write', type=int, default=0, help='Offline fault injection for recovery demonstration')
    args = parser.parse_args(argv)
    try:
        if getattr(args, 'mode', 'simulation') != 'simulation':
            raise ContractError('live 已明确拒绝：此程序没有任何真实 API 或发布实现。')
        if args.command == 'plan':
            plan = build_plan(load(args.brief), load(args.candidates), context_path=args.context)
            out = Path(args.out)
            save(out / 'plan.json', plan)
            write_review(plan, out / 'review.md')
            print(json.dumps({'notice': NOTICE, 'status': plan['status'], 'plan_hash': plan['plan_hash'], 'out': str(out)}, ensure_ascii=False))
            return 0 if plan['status'] == 'ready' else 2
        plan = load(args.plan)
        if args.command == 'authorize-simulation':
            authorization = authorization_for(plan)
            save(args.out, authorization)
            print(json.dumps({'notice': NOTICE, 'status': 'simulation_authorization_created', 'plan_hash': plan['plan_hash']}, ensure_ascii=False))
            return 0
        result = execute(plan, load(args.authorization), args.state, args.interrupt_after_write)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 4 if result['status'] == 'interrupted' else 0
    except (ContractError, OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({'mode': 'simulation', 'status': 'blocked', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
