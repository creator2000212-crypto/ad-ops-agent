"""Read scoped, explicitly adopted private methods without mutating profiles."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import memory_store


class PersonalizationError(ValueError):
    pass


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def _has_source(value):
    return (isinstance(value, str) and bool(value.strip())
            or isinstance(value, dict) and any(_has_source(v) for v in value.values()))


def _known(fact):
    if not isinstance(fact, dict) or fact.get('status') not in {'confirmed', 'observed'}:
        return False
    return _has_source(fact.get('source')) and fact.get('value') not in (None, '', [], {})


def _accounts(profile, account_scope):
    rows = profile.get('selected_accounts', []) if account_scope is None else account_scope
    if not isinstance(rows, list):
        raise PersonalizationError('私有知识账户范围需要列表。')
    identities = set()
    for row in rows:
        if (not isinstance(row, dict) or row.get('platform') not in {'meta', 'tiktok', 'google'}
                or not isinstance(row.get('account_id'), str) or not row['account_id'].strip()):
            raise PersonalizationError('私有知识账户范围需要明确平台与账户 ID。')
        identities.add((row['platform'], row['account_id']))
    return identities


def _scope(record, facts, accounts):
    """A rule must cover the entire selected context, not merely intersect it."""
    scope, missing = record['scope'], []
    if scope['accounts']:
        allowed = {(a['platform'], a['account_id']) for a in scope['accounts']}
        if not accounts:
            missing.append('selected_accounts')
        elif not accounts <= allowed:
            return False, []
    for key, fact_key in (('platforms', 'platforms'), ('countries', 'countries'),
                          ('surfaces', 'surface'), ('monetization', 'monetization')):
        allowed = scope[key]
        if not allowed:
            continue
        if key == 'platforms' and accounts:
            values = {platform for platform, _ in accounts}
        else:
            fact = facts.get(fact_key)
            if not _known(fact):
                missing.append(fact_key)
                continue
            value = fact['value']
            values = value if isinstance(value, list) else [value]
            if not values or any(not isinstance(v, str) or not v.strip() for v in values):
                missing.append(fact_key)
                continue
            values = set(values)
        if not values <= set(allowed):
            return False, []
    return not missing, missing


def resolve(profile, account_scope=None):
    """Return an effective copy and an immutable-by-convention private snapshot.

    Only an unknown/missing methodology is filled. Explicit conflicting facts
    remain visible as conflicts. Private text never becomes budget or tool args.
    Scope IDs select local data; they do not authenticate a remote tenant.
    """
    if not isinstance(profile, dict):
        raise PersonalizationError('业务档案必须是对象。')
    effective = deepcopy(profile)
    snapshot = {'enabled': False, 'active_hash': None, 'records': [],
                'applied_fields': [], 'conflicts': [], 'pending_scopes': []}
    if 'private_memory' not in profile:
        return effective, snapshot
    config = profile['private_memory']
    if not isinstance(config, dict) or type(config.get('enabled')) is not bool:
        raise PersonalizationError('private_memory 需要明确的 enabled 布尔值。')
    if set(config) - {'enabled', 'store', 'workspace_id', 'product_id'}:
        raise PersonalizationError('private_memory 包含不支持的配置字段。')
    if not config['enabled']:
        return effective, snapshot
    for key in ('store', 'workspace_id', 'product_id'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise PersonalizationError('private_memory 缺少明确的 ' + key)
    path = Path(config['store'])
    if not path.is_absolute():
        raise PersonalizationError('private_memory.store 必须为明确的绝对路径。')
    if config['product_id'] != profile.get('profile_id'):
        raise PersonalizationError('private_memory.product_id 必须与 profile_id 一致。')
    facts = effective.get('facts')
    if not isinstance(facts, dict):
        raise PersonalizationError('私有知识解析需要 facts 对象。')
    accounts = _accounts(profile, account_scope)
    records = memory_store.list_records(path, config['workspace_id'], config['product_id'])
    matched, pending = [], []
    for record in records:
        applies, missing = _scope(record, facts, accounts)
        if applies:
            matched.append(record)
        elif missing:
            # Unknown scope never reveals the rule's content or enables it.
            pending.append({'record_id': record['record_id'], 'missing': missing})
    binding = {'workspace_id': config['workspace_id'], 'product_id': config['product_id']}
    material = [{k: v for k, v in record.items() if k != 'updated_at'} for record in matched]
    snapshot.update(enabled=True, **binding, records=matched, pending_scopes=pending,
                    active_hash=digest({'binding': binding, 'records': material}))
    methods = [record for record in matched if record['kind'] == 'methodology']
    if not methods:
        return effective, snapshot
    values = {record['text'] for record in methods}
    current = facts.get('methodology')
    refs = [{'record_id': record['record_id'], 'version': record['version'],
             'source': deepcopy(record['source'])} for record in methods]
    source = {'kind': 'private_user_confirmation', **binding, 'records': refs,
              'basis': 'User-adopted method; not empirical performance validation.'}
    if len(values) == 1 and (current is None or isinstance(current, dict) and current.get('status') == 'unknown'):
        facts['methodology'] = {'value': next(iter(values)), 'status': 'confirmed', 'source': source}
        snapshot['applied_fields'].append('methodology')
    elif len(values) == 1 and _known(current) and current['value'] == next(iter(values)):
        pass  # Retain the explicit profile source instead of relabeling it.
    else:
        snapshot['conflicts'].append({'field': 'methodology', 'records': refs,
                                      'reason': '私有方法彼此不一致，或与当前档案的方法不同；请明确采用哪一版。'})
        facts['methodology'] = {'value': deepcopy(current.get('value')) if isinstance(current, dict) else None,
                               'status': 'conflict',
                               'source': {'profile': deepcopy(current), 'private': source}}
    return effective, snapshot


def knowledge_items(snapshot, stage, query=''):
    """Adapt user methods to advisory report items, not to public platform facts."""
    result = []
    for record in snapshot['records']:
        if stage not in record['stages']:
            continue
        haystack = ' '.join((record['record_id'], record['title'], record['text'])).casefold()
        score = sum(term in haystack for term in query.casefold().split())
        if query.strip() and not score:
            continue
        conflicting = record['kind'] == 'methodology' and bool(snapshot['conflicts'])
        source = record['source']
        result.append({
            'id': 'PRIVATE:' + record['record_id'], 'title': record['title'],
            'summary': record['text'], 'kind': 'user_' + record['kind'],
            'status': 'conflict' if conflicting else 'user_confirmed',
            'advisory_only': True, 'origin': 'private', 'version': record['version'],
            'workspace_id': snapshot['workspace_id'], 'product_id': snapshot['product_id'],
            'scope': deepcopy(record['scope']), 'stages': record['stages'],
            'scope_missing': [], 'missing_facts': ['methodology'] if conflicting else [],
            'required_facts': ['methodology'] if record['kind'] == 'methodology' else [],
            'matched_triggers': [], 'query_score': score, 'priority': 1,
            'checks': ['核对本轮是否仍沿用该用户方法或操作约定。'],
            'actions': ['先解决方法冲突，再准备方案。'] if conflicting else ['在已确认范围内作为准备与审阅依据。'],
            'avoid': ['用户确认采用不证明经营效果，不改变预算、账户范围或操作授权。'],
            'questions': [],
            'sources': [{'id': 'PRIVATE:' + record['record_id'], 'title': source['reference'],
                         'kind': source['kind'], 'reference': source['reference'], 'mode': source['mode'],
                         'checked_on': record['updated_at'][:10], 'freshness': 'user_confirmed_not_platform_verified'}],
            'reason': '按工作空间、产品与全部所选范围匹配；用户确认采用，未验证效果。',
        })
    return result
