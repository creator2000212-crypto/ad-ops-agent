"""Connection-first guidance for the offline prototype; never grants permissions.

The caller owns account-scoped connection validation.  ``connected`` is only a
gate result, not evidence of real access or authorization to change an account.
Known optional input fields are type checked; unrelated profile fields are left
to their owning contracts.  This module never changes the supplied profile.

Connection guidance is vendor-neutral: an existing connection is reused, and
without one the user gets an unranked list of routes with their trade-offs and
chooses.  Links are plain provider documentation URLs (no query or fragment).
"""
from copy import deepcopy
from urllib.parse import urlsplit


PLATFORMS = ('meta', 'tiktok', 'google')
# Ways to create a connection, listed in no particular order.
CONNECTION_ROUTES = ('self_managed', 'self_hosted_mcp', 'managed_mcp')
ROUTES = {'undecided', 'existing'} | set(CONNECTION_ROUTES)
# Values accepted from older profiles and mapped to the generic route.
LEGACY_ROUTE_ALIASES = {'other_mcp': 'self_hosted_mcp'}
LANGUAGES = ('en', 'zh-CN')
APPROACHES = {'guided', 'bring_own', 'undecided'}
EXPERIENCE = {'new', 'experienced', 'unknown'}
FACT_STATES = {'confirmed', 'observed', 'hypothesis', 'unknown', 'conflict', 'stale'}
AUTHORIZATION_NOTICE = '协作方式、熟练度和接入状态均不增加账户访问或发布权限；具体广告操作仍需独立授权。'
# A link is either provider documentation or a named example of a route.
_LINK_LABELS = {'en': {'docs': 'Docs:', 'example': 'Example:'}, 'zh-CN': {'docs': '文档：', 'example': '示例：'}}
# Keys that would turn the neutral list into a ranking or a sales card.
_STEERING_KEYS = {'recommended', 'rank', 'priority', 'primary', 'primary_cta', 'default', 'featured', 'affiliate_url'}


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


_CONNECTION_OPTIONS = (
    {
        'route': 'self_managed',
        'text': {
            'en': {
                'label': 'Official platform APIs with your own adapter',
                'summary': 'Call the Meta Marketing API, TikTok API for Business or Google Ads API directly, '
                           'optionally through the official SDKs.',
                'trade_offs': [
                    'Full control of permissions, fields and API versions; no third party in the access path.',
                    'You register developer apps, run OAuth, store tokens and maintain the adapter across '
                    'API versions and rate limits.',
                ],
            },
            'zh-CN': {
                'label': '官方平台 API（自行维护适配器）',
                'summary': '直接调用 Meta Marketing API、TikTok API for Business 或 Google Ads API，可配合官方 SDK。',
                'trade_offs': [
                    '权限、字段和 API 版本完全自控；访问链路中没有第三方。',
                    '需要自行注册开发者应用、完成 OAuth、保管令牌，并随 API 版本和限流持续维护适配器。',
                ],
            },
        },
        'links': [
            {'kind': 'docs', 'title': 'Meta for Developers', 'url': 'https://developers.facebook.com/'},
            {'kind': 'docs', 'title': 'TikTok API for Business', 'url': 'https://business-api.tiktok.com/portal/docs'},
            {'kind': 'docs', 'title': 'Google Ads API client libraries',
             'url': 'https://developers.google.com/google-ads/api/docs/client-libs'},
        ],
    },
    {
        'route': 'self_hosted_mcp',
        'text': {
            'en': {
                'label': 'Self-hosted MCP server',
                'summary': 'Run an MCP server yourself (open-source or your own) on top of the official APIs '
                           'and add it to the agent client.',
                'trade_offs': [
                    'The agent gets a tool interface while credentials and hosting stay under your control; '
                    'you can restrict the tool list.',
                    'You still need the platform developer apps and tokens, and you maintain, update and '
                    'secure the server.',
                ],
            },
            'zh-CN': {
                'label': '自托管 MCP 服务器',
                'summary': '自行运行基于官方 API 的 MCP 服务器（开源或自建），再接入 Agent 客户端。',
                'trade_offs': [
                    'Agent 获得工具接口，凭据和部署仍由你掌控，可以限制开放的工具清单。',
                    '仍需平台开发者应用和令牌，并由你负责服务器的维护、升级和安全。',
                ],
            },
        },
        'links': [
            {'kind': 'docs', 'title': 'Model Context Protocol', 'url': 'https://modelcontextprotocol.io'},
        ],
    },
    {
        'route': 'managed_mcp',
        'text': {
            'en': {
                'label': 'Hosted MCP connector',
                'summary': 'A provider hosts the MCP server and the account authorization flow; you connect '
                           'the selected ad accounts and add its endpoint to the agent client.',
                'trade_offs': [
                    'Little setup or connection maintenance on your side.',
                    'Adds a third party to the account access path; tool coverage, limits, pricing and '
                    'data handling are set by the provider.',
                ],
            },
            'zh-CN': {
                'label': '托管 MCP 连接器',
                'summary': '由服务商托管 MCP 服务器和账户授权流程；你连接选定的广告账户，再把其入口加入 Agent 客户端。',
                'trade_offs': [
                    '自己需要承担的接入和连接维护较少。',
                    '账户访问链路中多了一个第三方；工具范围、限额、价格和数据处理方式由服务商决定。',
                ],
            },
        },
        'links': [
            {'kind': 'example', 'title': 'Pipeboard', 'url': 'https://pipeboard.co'},
        ],
    },
)

_OPTIONS_NOTICE = {
    'en': {
        'title': 'Connection options',
        'intro': 'No connection is available yet. These routes are listed in no particular order; choose by the '
                 'trade-offs. An existing connection you already use stays valid.',
        'requirements': [
            'Whatever the route, verify reading (and, only when the task needs it, writing and readback) on the '
            'selected accounts before relying on it.',
            'Do not paste tokens or passwords into the conversation; keep credentials in the client\'s or '
            'provider\'s secure configuration.',
            'Choosing, paying for or installing a connection does not verify access and does not authorize '
            'any ad account change.',
        ],
        'sources_note': 'Links go to each provider\'s own documentation. Capabilities, plans and terms change; '
                        'check them when you choose.',
    },
    'zh-CN': {
        'title': '连接选项',
        'intro': '当前没有可用连接。以下路线不分先后，请按取舍自行选择；已在使用的连接继续有效。',
        'requirements': [
            '无论选择哪条路线，都要先在选定账户上核验读取能力；仅在任务需要时再核验写入与读回。',
            '不要在对话中粘贴令牌或密码；凭据放在客户端或服务商的安全配置中。',
            '选择、付费或安装某个连接，都不代表接入已验收，也不授权任何广告账户变更。',
        ],
        'sources_note': '链接指向各服务商自己的文档；能力、套餐与条款可能变化，选择时请以当前页面为准。',
    },
}


def connection_options():
    """Return the unranked, vendor-neutral list of ways to create a connection."""
    return {
        'id': 'connection_options',
        'ordering': 'unranked',
        'routes': deepcopy(list(_CONNECTION_OPTIONS)),
        'text': deepcopy(_OPTIONS_NOTICE),
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
        'undecided': '使用已有连接；尚无连接时，从连接选项（官方平台 API、自托管 MCP 服务器、托管 MCP 连接器）中按取舍自行选择，选项不分先后。',
        'existing': '在当前 Agent 客户端确认已有连接可用，并核对本次需要的平台和账户范围。',
        'self_managed': '使用自己维护的适配器调用官方平台 API / SDK，将所需读写能力接入当前 Agent 客户端。',
        'self_hosted_mcp': '自行运行 MCP 服务器并使用自己的平台开发者应用，在当前 Agent 客户端添加该服务器，并确认其支持本次平台和所需能力。',
        'managed_mcp': '在所选托管 MCP 连接器的授权流程中只连接本次选定的账户，再在当前 Agent 客户端配置其入口，并确认其支持本次平台和所需能力。',
    }[route]
    return [
        first,
        '在所选服务的授权界面明确本次允许访问的广告账户及必要权限；不在对话或业务档案中提供真实凭据或令牌。',
        '发现可用工具后，分别核对选定账户的读取和必要写能力，并记录账户、权限范围、检查时间及证据；无需自动创建广告探针。',
        '当前项目仅能核对离线连接快照。真实验收需实现适配器；付费、打开链接或安装 MCP 本身均不能作为通过证据。',
    ]


def _route(setup):
    """Return the canonical route; older vendor-specific values map to generic routes."""
    value = setup.get('route', 'undecided')
    if isinstance(value, str) and value in LEGACY_ROUTE_ALIASES:
        return LEGACY_ROUTE_ALIASES[value]
    return _enum(value, ROUTES, 'setup_preferences.route')


def _options_dismissed(setup):
    """``options_dismissed`` hides the list; ``recommendation_dismissed`` is its older name."""
    dismissed = False
    for key in ('options_dismissed', 'recommendation_dismissed'):
        value = setup.get(key, False)
        if type(value) is not bool:
            raise GuidanceError('setup_preferences.' + key + ' 必须为布尔值。')
        dismissed = dismissed or value
    return dismissed


def evaluate(profile, connected: bool):
    """Return the next guidance stage without probing or changing ad accounts."""
    _object(profile, 'profile')
    if type(connected) is not bool:
        raise GuidanceError('connected 必须为布尔值。')
    setup = _object(profile.get('setup_preferences', {}), 'setup_preferences')
    route = _route(setup)
    dismissed = _options_dismissed(setup)
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
        'connection_options': None,
        'connection_route': route,
        'setup_steps': [],
        'familiarity_question': None,
        'collaboration_summary': {'status': 'deferred'},
        'method_requirement': {'state': 'needs_choice', 'instruction': '先完成选定账户的接入验收，再明确协作方式和本次需求。'},
        'authorization_notice': AUTHORIZATION_NOTICE,
    }
    if not connected:
        result['setup_steps'] = _setup_steps(route)
        if route == 'undecided' and not dismissed:
            result['connection_options'] = connection_options()
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


def _check_neutral(options):
    """Reject a list that ranks routes, drops one, or carries tracking in a link."""
    _object(options, 'connection_options')
    if options.get('id') != 'connection_options' or options.get('ordering') != 'unranked':
        raise GuidanceError('connection_options 必须是不分先后的连接选项列表。')
    routes = options.get('routes')
    if not isinstance(routes, list) or not all(isinstance(item, dict) for item in routes):
        raise GuidanceError('connection_options.routes 必须为对象列表。')
    listed = [item.get('route') for item in routes]
    if len(listed) != len(CONNECTION_ROUTES) or set(listed) != set(CONNECTION_ROUTES):
        raise GuidanceError('connection_options 必须完整列出每条连接路线，且每条只出现一次。')
    texts = [options.get('text')] + [item.get('text') for item in routes]
    if not all(isinstance(text, dict) and all(isinstance(text.get(lang), dict) for lang in LANGUAGES)
               for text in texts):
        raise GuidanceError('connection_options 需要 en 与 zh-CN 两种文本。')
    if _STEERING_KEYS & set(options):
        raise GuidanceError('connection_options 不能包含推荐、排序或推广字段。')
    for item in routes:
        if _STEERING_KEYS & set(item):
            raise GuidanceError('连接选项不能包含推荐、排序或推广字段。')
        links = item.get('links')
        if not isinstance(links, list) or not links:
            raise GuidanceError('每个连接选项都需要至少一个文档链接。')
        for link in links:
            if _object(link, 'link').get('kind') not in _LINK_LABELS['en']:
                raise GuidanceError('连接选项链接需要标明 docs 或 example。')
            url = link.get('url')
            parts = urlsplit(url) if isinstance(url, str) else None
            if parts is None or parts.scheme != 'https' or not parts.netloc or parts.query or parts.fragment \
                    or '#' in url or '?' in url:
                raise GuidanceError('连接选项链接必须是不带查询参数或片段的 https 地址。')
    return routes


def connection_options_markdown(options, lang='en'):
    """Render the neutral connection options in one language."""
    if lang not in LANGUAGES:
        raise GuidanceError('lang 仅支持 en 或 zh-CN。')
    routes = _check_neutral(options)
    notice = options['text'][lang]
    trade_off_label = 'Trade-offs: ' if lang == 'en' else '取舍：'
    lines = ['**' + notice['title'] + '**', '', notice['intro'], '']
    for item in routes:
        text = item['text'][lang]
        groups = []
        for kind, label in _LINK_LABELS[lang].items():
            links = ['[' + link['title'] + '](' + link['url'] + ')' for link in item['links'] if link['kind'] == kind]
            if links:
                groups.append(label + ('' if lang == 'zh-CN' else ' ') + ' · '.join(links))
        lines.append('- **' + text['label'] + '** — ' + text['summary'] + ' ' + ' '.join(groups))
        lines.append('  ' + trade_off_label + ' / '.join(text['trade_offs']))
    lines += [''] + ['- ' + line for line in notice['requirements']] + ['', notice['sources_note']]
    return '\n'.join(lines)
