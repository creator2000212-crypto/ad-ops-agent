#!/usr/bin/env python3
"""Source-backed, deterministic advertising knowledge retrieval. No network or mutations."""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import personalization

DEFAULT_CATALOG = Path(__file__).resolve().parent / 'knowledge' / 'catalog.json'
STAGES = {'discovery', 'planning', 'creative', 'launch', 'measurement', 'diagnosis'}
KINDS = {'platform_fact', 'operational_principle', 'strategy_template', 'diagnostic_hypothesis'}
STATES = {'confirmed', 'observed', 'hypothesis', 'unknown', 'conflict', 'stale'}
SCOPES = {'platforms': {'meta', 'tiktok', 'google'}, 'surfaces': {'web', 'app'},
          'monetization': {'iaa', 'iap', 'hybrid', 'subscription', 'ecommerce', 'leadgen'}}


class KnowledgeError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      parse_constant=lambda value: (_ for _ in ()).throw(KnowledgeError('非有限 JSON 值：' + value)))


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value, allow_empty=True):
    return isinstance(value, list) and (allow_empty or bool(value)) and all(nonempty(v) for v in value)


def day(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise KnowledgeError('as_of datetime 必须包含时区。')
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
            if parsed.isoformat() == value:
                return parsed
        except ValueError:
            pass
    raise KnowledgeError('日期必须为 YYYY-MM-DD。')


def validate_catalog(catalog):
    if not isinstance(catalog, dict) or type(catalog.get('schema_version')) is not int or catalog['schema_version'] != 1 or not nonempty(catalog.get('version')):
        raise KnowledgeError('知识库需要 schema_version=1 和明确 version。')
    if not isinstance(catalog.get('sources'), list) or not isinstance(catalog.get('entries'), list) or not catalog['entries']:
        raise KnowledgeError('知识库需要 sources 列表与非空 entries。')
    source_ids, entry_ids = {}, set()
    for source in catalog['sources']:
        if not isinstance(source, dict) or not all(nonempty(source.get(k)) for k in ('id', 'title', 'url', 'note')):
            raise KnowledgeError('来源需要 id/title/url/note。')
        if source['id'] in source_ids or source.get('kind') not in {'official', 'project'}:
            raise KnowledgeError('来源 id 重复或 kind 无效。')
        if not source['url'].startswith('https://'):
            raise KnowledgeError('公开来源需要 https URL。')
        day(source.get('checked_on'))
        ttl = source.get('review_after_days')
        if type(ttl) is not int or not 1 <= ttl <= 3660:
            raise KnowledgeError('review_after_days 需要 1..3660 整数。')
        source_ids[source['id']] = source
    for entry in catalog['entries']:
        if not isinstance(entry, dict) or not all(nonempty(entry.get(k)) for k in ('id', 'title', 'summary')):
            raise KnowledgeError('条目需要 id/title/summary。')
        if entry['id'] in entry_ids:
            raise KnowledgeError('知识条目 id 重复：' + entry['id'])
        entry_ids.add(entry['id'])
        if entry.get('kind') not in KINDS:
            raise KnowledgeError('未知知识分类：' + entry['id'])
        if not strings(entry.get('stages'), False) or not set(entry['stages']) <= STAGES:
            raise KnowledgeError('未知工作阶段：' + entry['id'])
        for field, choices in SCOPES.items():
            values = entry.get(field)
            if not strings(values, False) or not set(values) <= choices | {'all'} or ('all' in values and len(values) != 1):
                raise KnowledgeError('适用范围无效：' + field)
        for field in ('keywords', 'required_facts', 'checks', 'actions', 'avoid', 'source_ids'):
            if not strings(entry.get(field), field in {'keywords', 'required_facts'}):
                raise KnowledgeError('条目列表无效：' + field)
        if not set(entry['source_ids']) <= source_ids.keys():
            raise KnowledgeError('条目引用不存在的 source。')
        if entry['kind'] == 'platform_fact' and not any(source_ids[s]['kind'] == 'official' for s in entry['source_ids']):
            raise KnowledgeError('平台事实必须引用官方来源。')
        if type(entry.get('priority')) is not int or entry['priority'] not in {1, 2, 3}:
            raise KnowledgeError('priority 需要 1、2 或 3。')
        if not isinstance(entry.get('triggers'), list) or not isinstance(entry.get('questions'), list):
            raise KnowledgeError('triggers/questions 需要列表。')
        for trigger in entry['triggers']:
            if not isinstance(trigger, dict) or set(trigger) != {'key', 'equals'} or not nonempty(trigger['key']) or type(trigger['equals']) not in {bool, str, int, float}:
                raise KnowledgeError('触发器只支持明确 key/equals 标量。')
        for question in entry['questions']:
            if not isinstance(question, dict) or not nonempty(question.get('key')) or not nonempty(question.get('question')):
                raise KnowledgeError('知识问题需要 key/question。')
    canonical(catalog)  # Reject NaN even in programmatic inputs.
    return catalog


def load_catalog(path=None):
    return validate_catalog(read(path or DEFAULT_CATALOG))


def has_source(value):
    if nonempty(value):
        return True
    return isinstance(value, dict) and any(has_source(v) for v in value.values())


def usable(fact):
    if not isinstance(fact, dict) or fact.get('status') not in {'confirmed', 'observed'} or not has_source(fact.get('source')):
        return False
    value = fact.get('value')
    return value is not None and value != '' and value != [] and value != {} and (not isinstance(value, str) or bool(value.strip()))


def validate_facts(facts):
    if not isinstance(facts, dict):
        raise KnowledgeError('facts 必须是 value/status/source 映射。')
    for key, fact in facts.items():
        if not nonempty(key) or not isinstance(fact, dict) or fact.get('status') not in STATES or 'value' not in fact:
            raise KnowledgeError('事实格式无效：' + str(key))
    canonical(facts)


def assess(profile, stage, observations=None, query='', limit=12, as_of=None, catalog=None, private_snapshot=None):
    """Return advisory candidates with explicit missing evidence; never create execution actions."""
    catalog = load_catalog() if catalog is None else validate_catalog(catalog)
    if stage not in STAGES or type(limit) is not int or not 1 <= limit <= 200 or not isinstance(query, str):
        raise KnowledgeError('需要合法 stage、query 与 1..200 的 limit。')
    if not isinstance(profile, dict):
        raise KnowledgeError('profile 必须为对象。')
    if private_snapshot is None:
        profile, private_snapshot = personalization.resolve(profile)
    facts = profile.get('facts', {})
    validate_facts(facts)
    observations = {} if observations is None else observations
    validate_facts(observations)
    if facts.keys() & observations.keys():
        raise KnowledgeError('observations 不能覆盖 profile 的业务事实；请显式更新档案。')
    facts = {**facts, **observations}
    current = day(as_of) if as_of is not None else datetime.now(timezone.utc).date()
    sources = {s['id']: s for s in catalog['sources']}
    matches = []
    for entry in catalog['entries']:
        if stage not in entry['stages']:
            continue
        scope_missing, excluded = [], False
        for field, fact_key in (('platforms', 'platforms'), ('surfaces', 'surface'), ('monetization', 'monetization')):
            if entry[field] == ['all']:
                continue
            fact = facts.get(fact_key)
            if not usable(fact):
                scope_missing.append(fact_key)
                continue
            value = fact['value']
            values = value if isinstance(value, list) else [value]
            if not values or not all(isinstance(v, str) and v in SCOPES[field] for v in values):
                scope_missing.append(fact_key)
            elif not set(values) & set(entry[field]):
                excluded = True
        if excluded:
            continue
        haystack = ' '.join([entry['id'], entry['title'], entry['summary'], *entry['keywords']]).casefold()
        score = sum(term in haystack for term in query.casefold().split())
        if query.strip() and not score:
            continue
        missing = [key for key in entry['required_facts'] if not usable(facts.get(key))]
        matched = []
        for trigger in entry['triggers']:
            fact = facts.get(trigger['key'])
            if not usable(fact):
                missing.append(trigger['key'])
            elif type(fact['value']) is not type(trigger['equals']) or fact['value'] != trigger['equals']:
                excluded = True
            else:
                matched.append({'key': trigger['key'], 'value': fact['value'], 'source': fact['source']})
        if excluded:
            continue
        evidence = []
        for source_id in entry['source_ids']:
            source = sources[source_id]
            age = (current - day(source['checked_on'])).days
            freshness = 'future_date' if age < 0 else 'review_due' if age > source['review_after_days'] else 'current'
            evidence.append({**source, 'freshness': freshness})
        missing = list(dict.fromkeys(missing))
        stale = any(s['freshness'] != 'current' for s in evidence)
        status = 'needs_source_review' if stale else 'needs_context' if scope_missing else 'needs_evidence' if missing else 'applicable'
        matches.append({**entry, 'status': status, 'advisory_only': True,
                        'scope_missing': scope_missing, 'missing_facts': missing,
                        'matched_triggers': matched, 'sources': evidence, 'query_score': score,
                        'reason': '按声明的范围和条件匹配；未独立验证用户提供的事实，未完成平台检查或因果判断。'})
    # Explicit user methods share the report but never masquerade as platform facts.
    matches.extend(personalization.knowledge_items(private_snapshot, stage, query))
    # Evidence-backed triggers lead generic guidance. Uncertain scope is never presented as a match.
    matches.sort(key=lambda item: (bool(item['scope_missing']), -item['query_score'],
                                  -len(item['matched_triggers']), item['priority'],
                                  0 if item.get('origin') == 'private' else 1, item['id']))
    return {'schema_version': 1, 'kind': 'knowledge_review', 'advisory_only': True,
            'retrieval': 'deterministic_scope_and_keyword_rules', 'knowledge_version': catalog['version'],
            'catalog_hash': digest(catalog), 'facts_hash': digest(facts), 'as_of': current.isoformat(),
            'private_memory': private_snapshot,
            'stage': stage, 'query': query, 'total_matches': len(matches), 'truncated': len(matches) > limit,
            'items': matches[:limit],
            'notice': '知识提供检查和建议，不证明已完成，不授予操作权限；诊断假设不等于已确认根因。'}


def markdown(report):
    lines = ['## 投放知识建议', '', report['notice'], '',
             f"知识版本：{report['knowledge_version']}；阶段：{report['stage']}；匹配 {report['total_matches']} 条，展示 {len(report['items'])} 条。", '']
    for item in report['items']:
        lines += [f"### {item['id']} · {item['title']}", '', f"状态：{item['status']}；类型：{item['kind']}", '', item['summary'], '']
        if item['scope_missing']:
            lines += ['适用范围待确认：' + '、'.join(item['scope_missing']), '']
        if item['missing_facts']:
            lines += ['缺少证据：' + '、'.join(item['missing_facts']), '']
        for label, field in (('需核对', 'checks'), ('建议步骤', 'actions'), ('不应推断', 'avoid')):
            lines += [f"- {label}：{text}" for text in item[field]]
        lines += [f"- 补充问题：{question['question']}" for question in item['questions']
                  if question['key'] in item['missing_facts'] + item['scope_missing']]
        for source in item['sources']:
            if 'url' in source:
                lines += [f"- 来源：[{source['title']}]({source['url']})；复核 {source['checked_on']}；{source['freshness']}"]
            else:
                lines += [f"- 私有来源：{source['reference']}；类型={source['kind']}；{source['freshness']}"]
        lines.append('')
    private = report.get('private_memory', {})
    if private.get('enabled'):
        lines += ['私有知识仅代表用户明确采用的约定；不证明经营效果，不增加执行权限。',
                  '私有知识快照：`' + private['active_hash'] + '`', '']
        for conflict in private.get('conflicts', []):
            lines += ['- 私有方法冲突：' + conflict['reason']]
        for pending in private.get('pending_scopes', []):
            lines += ['- 私有条目适用范围待确认：' + pending['record_id'] + '；缺少 ' + '、'.join(pending['missing'])]
    if not report['items']:
        lines += ['没有匹配条目；不能据此判断不存在风险或问题。', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('search', 'assess'):
        sub = commands.add_parser(command)
        sub.add_argument('--catalog')
        sub.add_argument('--stage', choices=sorted(STAGES), default='diagnosis')
        sub.add_argument('--query', default='')
        sub.add_argument('--limit', type=int, default=12)
        sub.add_argument('--out', type=Path)
        if command == 'search':
            sub.add_argument('--platform', choices=sorted(SCOPES['platforms']))
            sub.add_argument('--surface', choices=sorted(SCOPES['surfaces']))
            sub.add_argument('--monetization', choices=sorted(SCOPES['monetization']))
        else:
            sub.add_argument('--profile', required=True)
            sub.add_argument('--observations')
    args = parser.parse_args(argv)
    try:
        profile, observations = {'facts': {}}, {}
        if args.command == 'assess':
            profile = read(args.profile)
            if args.observations:
                document = read(args.observations)
                if not isinstance(document, dict) or document.get('schema_version') != 1 or 'facts' not in document:
                    raise KnowledgeError('观测文件需要 schema_version=1 和 facts。')
                observations = document['facts']
        else:
            for flag, key in (('platform', 'platforms'), ('surface', 'surface'), ('monetization', 'monetization')):
                value = getattr(args, flag)
                if value:
                    profile['facts'][key] = {'value': [value] if flag == 'platform' else value,
                                             'status': 'confirmed', 'source': 'explicit_search_filter'}
        report = assess(profile, args.stage, observations, args.query, args.limit, catalog=load_catalog(args.catalog))
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            (args.out / 'review.md').write_text(markdown(report), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
