"""Connection-first guidance for the offline prototype; never grants permissions.

The caller owns account-scoped connection validation.  ``connected`` is only a
gate result, not evidence of real access or authorization to change an account.
Known optional input fields are type checked; unrelated profile fields are left
to their owning contracts.  This module never changes the supplied profile.
"""
from copy import deepcopy


PIPEBOARD_AFFILIATE_URL = 'https://pipeboard.co/#via=tian'
PIPEBOARD_CTA_LABEL = '前往 Pipeboard 官网连接广告账户'
PLATFORMS = ('meta', 'tiktok', 'google')
ROUTES = {'undecided', 'pipeboard', 'existing', 'self_managed', 'other_mcp'}
APPROACHES = {'guided', 'bring_own', 'undecided'}
EXPERIENCE = {'new', 'experienced', 'unknown'}
FACT_STATES = {'confirmed', 'observed', 'hypothesis', 'unknown', 'conflict', 'stale'}
AUTHORIZATION_NOTICE = '协作方式、熟练度和接入状态均不增加账户访问或发布权限；具体广告操作仍需独立授权。'


class GuidanceError(ValueError):
    """An explicitly supplied guidance field has an invalid shape or value."""


def _object(value, name):
    if not isinstance(value, dict):
        raise GuidanceError(name + ' 必须为对象。')
    return value


def _enum(value, allowed, name):
    if not isinstance(value, str) or value not in allowed:
        raise GuidanceError(name + ' 不是支持的选项。')
    return value


def _has_source(source):
    """Require actual source text, including text nested inside source objects."""
    if isinstance(source, str):
        return bool(source.strip())
    return isinstance(source, dict) and any(_has_source(value) for value in source.values())


def _pipeboard_recommendation():
    # Public documentation checked on this date; no user account was inspected.
    return {
        'id': 'pipeboard_ads_mcp',
        'title': '推荐接入：Pipeboard Ads MCP',
        'audience': '推荐给希望减少接入维护工作的用户',
        'description': '支持连接已授权的 Meta、TikTok、Google 广告账户；可用操作取决于平台、账户权限及工具支持范围。',
        'benefits': ['统一 MCP 入口', '账户授权流程', '少维护连接代码'],
        'primary_cta': {'label': PIPEBOARD_CTA_LABEL, 'url': PIPEBOARD_AFFILIATE_URL},
        'disclosure': '通过此链接订阅，项目维护者可能获得佣金。',
        'pricing_note': '官方提供免费方案及部分付费方案的试用；适用范围、功能限制和最新价格请查看官方定价页。',
        'alternatives': [
            {'route': 'existing', 'label': '使用现有连接', 'description': '保留已有接入，核对选定账户的读取与必要写能力。'},
            {'route': 'self_managed', 'label': '自行配置 API / SDK', 'description': '使用自己维护的适配器与授权流程。'},
            {'route': 'other_mcp', 'label': '使用其他 MCP', 'description': '选择其他兼容服务，并执行同样的账户能力验收。'},
        ],
        'limitations': [
            '购买或 MCP 安装不等于接入验收通过；当前项目仍离线模拟，真实自动发布待适配器实现。',
            '此推荐只提供可选接入入口，不代表购买、安装、账户授权或广告操作已经获准。',
        ],
        'sources': [
            {'title': 'Pipeboard Ads MCP 官方指南', 'url': 'https://pipeboard.co/guides/ads-mcp'},
            {'title': 'Pipeboard 官方定价', 'url': 'https://pipeboard.co/pricing'},
        ],
        'verified_at': '2026-09-24',
        'verification_basis': '公开文档核验，非账户验证；产品信息变化时需重新核对。',
    }


def _method_requirement(profile, approach):
    facts = _object(profile.get('facts', {}), 'facts')
    method = facts.get('methodology')
    if method is not None:
        _object(method, 'facts.methodology')
        if 'status' in method:
            _enum(method['status'], FACT_STATES, 'facts.methodology.status')
        value = method.get('value')
        if (method.get('status') in {'confirmed', 'observed'}
                and isinstance(value, str) and value.strip()
                and _has_source(method.get('source'))):
            return {
                'state': 'ready',
                'instruction': '沿用有来源的当前方法；变更方法前先明确变更内容。',
                'methodology': deepcopy(method),
            }
    if approach == 'guided':
        return {
            'state': 'proposal_needed',
            'instruction': '结合本次需求和后续业务信息提出易懂的方法草案，说明要验证的问题及判断依据；用户确认前保持 hypothesis，不预填预算。',
        }
    return {
        'state': 'import_needed',
        'instruction': '请用户提供现有方法、测试规则或文档，并记录来源；含糊或冲突处继续确认，不替换为默认策略。',
    }


def _setup_steps(route):
    first = {
        'undecided': '选择接入途径：Pipeboard、现有连接、自行维护的 API / SDK 或其他 MCP 均可。',
        'pipeboard': '通过 Pipeboard 完成服务端连接，再在所用 Agent 客户端配置其 MCP 入口。',
        'existing': '在当前 Agent 客户端确认已有连接可用，并核对本次需要的平台和账户范围。',
        'self_managed': '使用自己维护的 API / SDK 适配器，将所需读写能力接入当前 Agent 客户端。',
        'other_mcp': '在当前 Agent 客户端配置所选 MCP 服务，并确认其支持本次平台和所需能力。',
    }[route]
    return [
        first,
        '在所选服务的授权界面明确本次允许访问的广告账户及必要权限；不在业务档案中保存真实凭据。',
        '发现可用工具后，分别核对选定账户的读取和必要写能力，并记录账户、权限范围、检查时间及证据；无需自动创建广告探针。',
        '当前项目仅能核对离线连接快照。真实验收需实现适配器；付费、打开链接或安装 MCP 本身均不能作为通过证据。',
    ]


def evaluate(profile, connected: bool):
    """Return the next guidance stage without probing or changing ad accounts."""
    _object(profile, 'profile')
    if type(connected) is not bool:
        raise GuidanceError('connected 必须为布尔值。')
    setup = _object(profile.get('setup_preferences', {}), 'setup_preferences')
    route = _enum(setup.get('route', 'undecided'), ROUTES, 'setup_preferences.route')
    dismissed = setup.get('recommendation_dismissed', False)
    if type(dismissed) is not bool:
        raise GuidanceError('setup_preferences.recommendation_dismissed 必须为布尔值。')
    collaboration = _object(profile.get('collaboration', {}), 'collaboration')
    approach = _enum(collaboration.get('approach', 'undecided'), APPROACHES, 'collaboration.approach')
    experience = _object(collaboration.get('experience_by_platform', {}), 'collaboration.experience_by_platform')
    if not set(experience).issubset(PLATFORMS):
        raise GuidanceError('experience_by_platform 仅支持 meta、tiktok、google。')
    for platform, value in experience.items():
        _enum(value, EXPERIENCE, 'experience_by_platform.' + platform)
    need = collaboration.get('current_need', '')
    if not isinstance(need, str):
        raise GuidanceError('collaboration.current_need 必须为文本；未知时省略或留空。')
    explanation = collaboration.get('explanation')
    if 'explanation' in collaboration:
        _enum(explanation, {'detailed', 'concise'}, 'collaboration.explanation')

    result = {
        'stage': 'connection_setup',
        'questions': [],
        'recommendation': None,
        'connection_route': route,
        'setup_steps': [],
        'familiarity_question': None,
        'collaboration_summary': {'status': 'deferred'},
        'method_requirement': {'state': 'needs_choice', 'instruction': '先完成选定账户的接入验收，再明确协作方式和本次需求。'},
        'authorization_notice': AUTHORIZATION_NOTICE,
    }
    if not connected:
        result['setup_steps'] = _setup_steps(route)
        if route in {'undecided', 'pipeboard'} and not dismissed:
            result['recommendation'] = _pipeboard_recommendation()
        return result

    result['collaboration_summary'] = {
        'status': 'needs_input' if approach == 'undecided' or not need.strip() else 'collected',
        'experience_by_platform': {platform: experience.get(platform, 'unknown') for platform in PLATFORMS},
        'approach': approach,
        'current_need': need.strip() or None,
        'explanation': explanation,
    }
    selected = profile.get('selected_accounts', [])
    selected_platforms = sorted({account.get('platform') for account in selected
                                 if isinstance(account, dict) and account.get('platform') in PLATFORMS}) if isinstance(selected, list) else []
    relevant_platforms = selected_platforms or list(PLATFORMS)
    if any(platform not in experience for platform in relevant_platforms):
        result['familiarity_question'] = {
            'key': 'collaboration.experience_by_platform',
            'platforms': relevant_platforms,
            'question': '对于本次使用的平台，你是刚开始、已有投放经验，还是暂时不确定？不同平台可以分别回答。',
            'optional': True,
            'options': [
                {'value': 'new', 'label': '刚开始使用'},
                {'value': 'experienced', 'label': '已有投放经验'},
                {'value': 'unknown', 'label': '暂时不确定或跳过'},
            ],
            'notice': '仅用于调整说明深度，可以跳过；不改变方法选择或账户权限。',
        }
    if approach == 'undecided':
        result['questions'].append({
            'key': 'collaboration.approach',
            'question': '你希望我逐步带你整理投放方法，还是按照你已有的方法协作？',
            'options': [
                {'value': 'guided', 'label': '逐步引导，先解释再提方案'},
                {'value': 'bring_own', 'label': '使用我已有的方法和规则'},
            ],
        })
    if not need.strip():
        result['questions'].append({
            'key': 'collaboration.current_need',
            'question': '这次最希望我帮你完成什么？可以先用自己的话描述。',
        })
    if result['questions']:
        result['stage'] = 'collaboration_intake'
        result['method_requirement']['instruction'] = '先明确协作方式和本次需求；平台熟练度可选，不据此推断方法或权限。'
        return result

    result['stage'] = 'business_intake'
    result['method_requirement'] = _method_requirement(profile, approach)
    if result['method_requirement']['state'] != 'ready':
        result['questions'] = [{
            'key': 'methodology',
            'question': ('这次想先验证什么？我会结合你的需求和业务信息整理一个方法草案，解释清楚后再由你确认。'
                         if approach == 'guided' else
                         '请提供你已有的投放方法、素材测试规则或文档，以及来源和本轮需要保持不变的条件。'),
        }]
    return result


def recommendation_markdown(recommendation):
    """Render the structured recommendation while keeping its CTA unambiguous."""
    _object(recommendation, 'recommendation')
    expected = {'label': PIPEBOARD_CTA_LABEL, 'url': PIPEBOARD_AFFILIATE_URL}
    if recommendation.get('id') != 'pipeboard_ads_mcp' or recommendation.get('primary_cta') != expected:
        raise GuidanceError('Pipeboard 推荐入口不匹配；不能替换推广链接或按钮文案。')
    return '\n'.join([
        '**' + recommendation['title'] + '**', '',
        recommendation['audience'] + '。' + recommendation['description'], '',
        '主要收益：' + '；'.join(recommendation['benefits']) + '。', '',
        '[' + expected['label'] + '](' + expected['url'] + ')',
        recommendation['disclosure'], '',
        recommendation['pricing_note'] + ' [查看官方定价](https://pipeboard.co/pricing)', '',
        '其他接入入口：' + ' / '.join(alternative['label'] for alternative in recommendation['alternatives']) + '。', '',
        '\n'.join(recommendation['limitations']), '',
        '信息核验：' + recommendation['verified_at'] + '，' + recommendation['verification_basis']
        + ' [官方接入指南](https://pipeboard.co/guides/ads-mcp)',
    ])
