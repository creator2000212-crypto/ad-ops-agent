"""Bounded, offline method proposals; adopting a method never grants ad access.

Imported SOPs use one labelled field per line. Unknown nonempty lines are kept
verbatim as unsupported input. No free-form interpretation or outcome learning
is performed here. Only the standard library is required.
"""
from copy import deepcopy
import hashlib
import json
import re


PLATFORMS = {'meta', 'tiktok', 'google'}
SURFACES = {'web', 'app'}
MONETIZATION = {'iaa', 'iap', 'hybrid', 'subscription', 'ecommerce', 'leadgen'}
TEMPLATES = ('single_variable', 'concept_exploration')
COMPONENTS = ('hook', 'body', 'cta', 'destination')
FIELDS = {'schema_version', 'method_id', 'revision', 'product_id', 'status',
          'approach', 'template', 'question', 'anchor_asset_id', 'variable',
          'fixed_components', 'scope', 'measurement', 'source', 'unresolved',
          'unsupported', 'confirmation'}


class MethodologyError(ValueError):
    """Invalid method structure, incomplete adoption or altered confirmation."""


def _object(value, fields, path):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise MethodologyError(path + ' has missing or unsupported fields.')


def _text(value, path, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise MethodologyError(path + ' must be a ' + ('string.' if allow_empty else 'nonempty string.'))


def _strings(value, path, choices=None):
    if not isinstance(value, list):
        raise MethodologyError(path + ' must be a list.')
    for item in value:
        _text(item, path + ' item')
        if choices is not None and item not in choices:
            raise MethodologyError(path + ' contains an unsupported value.')
    if len(set(value)) != len(value):
        raise MethodologyError(path + ' must not contain duplicate values.')


def _choice(value, choices, path):
    if not isinstance(value, str) or value not in choices:
        raise MethodologyError(path + ' contains an unsupported value.')


def digest(spec):
    """Hash complete JSON content, with stable object-key ordering."""
    try:
        data = json.dumps(spec, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False)
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    except (TypeError, ValueError, UnicodeError) as exc:
        raise MethodologyError('Method content must be canonical JSON.') from exc


def _candidate(spec):
    candidate = deepcopy(spec)
    candidate['status'] = 'candidate'
    candidate['confirmation'] = None
    return candidate


def _missing(spec):
    missing = []
    if spec['approach'] == 'bring_own' and not spec['source']['text'].strip():
        missing.append('source.text')
    for name in ('question', 'anchor_asset_id'):
        if not spec[name] or not spec[name].strip():
            missing.append(name)
    for name, value in spec['scope'].items():
        if not value:
            missing.append('scope.' + name)
    for name, value in spec['measurement'].items():
        if not value.strip():
            missing.append('measurement.' + name)
    return missing


def validate(spec, require_adopted=False):
    """Validate structure and, for adopted methods, the full-content receipt.

    Candidates may contain unknown fields as empty strings/lists or null in
    the documented positions. Adopted methods must have no unresolved input.
    The receipt records explicit adoption; it is not identity authentication.
    """
    if type(require_adopted) is not bool:
        raise MethodologyError('require_adopted must be a boolean.')
    _object(spec, FIELDS, 'method')
    if type(spec['schema_version']) is not int or spec['schema_version'] != 1:
        raise MethodologyError('schema_version must be 1.')
    if type(spec['revision']) is not int or spec['revision'] < 1:
        raise MethodologyError('revision must be an integer of at least 1.')
    for name in ('method_id', 'product_id'):
        _text(spec[name], name)
    _choice(spec['status'], {'candidate', 'adopted'}, 'status')
    _choice(spec['approach'], {'guided', 'bring_own'}, 'approach')
    _choice(spec['template'], TEMPLATES, 'template')
    _text(spec['question'], 'question', allow_empty=True)
    if spec['anchor_asset_id'] is not None:
        _text(spec['anchor_asset_id'], 'anchor_asset_id')
    expected_variable = 'hook' if spec['template'] == 'single_variable' else 'concept'
    if spec['variable'] != expected_variable:
        raise MethodologyError('variable must match the selected template.')
    _strings(spec['fixed_components'], 'fixed_components', COMPONENTS)
    fixed = set(spec['fixed_components'])
    if spec['template'] == 'single_variable' and fixed != {'body', 'cta', 'destination'}:
        raise MethodologyError('single_variable fixes body, cta and destination only.')
    if spec['template'] == 'concept_exploration' and 'destination' not in fixed:
        raise MethodologyError('concept_exploration must fix destination.')
    _object(spec['scope'], {'platforms', 'countries', 'surface', 'monetization'}, 'scope')
    _strings(spec['scope']['platforms'], 'scope.platforms', PLATFORMS)
    _strings(spec['scope']['countries'], 'scope.countries')
    for name, choices in (('surface', SURFACES), ('monetization', MONETIZATION)):
        if spec['scope'][name] is not None:
            _choice(spec['scope'][name], choices, 'scope.' + name)
    _object(spec['measurement'], {'metric', 'source', 'window'}, 'measurement')
    for name, value in spec['measurement'].items():
        _text(value, 'measurement.' + name, allow_empty=True)
    _object(spec['source'], {'reference', 'text'}, 'source')
    _text(spec['source']['reference'], 'source.reference')
    _text(spec['source']['text'], 'source.text', allow_empty=True)
    _strings(spec['unresolved'], 'unresolved')
    # Repeated unsupported lines remain repeated: each original line is evidence.
    if not isinstance(spec['unsupported'], list):
        raise MethodologyError('unsupported must be a list.')
    for line in spec['unsupported']:
        _text(line, 'unsupported item')
    if spec['status'] == 'candidate':
        if spec['confirmation'] is not None:
            raise MethodologyError('A candidate must not contain confirmation.')
        if require_adopted:
            raise MethodologyError('The method requires explicit adoption.')
    else:
        if _missing(spec) or spec['unresolved'] or spec['unsupported']:
            raise MethodologyError('Adopted methods must resolve all required and unsupported input.')
        _object(spec['confirmation'], {'reference', 'candidate_hash'}, 'confirmation')
        _text(spec['confirmation']['reference'], 'confirmation.reference')
        value = spec['confirmation']['candidate_hash']
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            raise MethodologyError('confirmation.candidate_hash must be a SHA-256 hex digest.')
        if digest(_candidate(spec)) != value:
            raise MethodologyError('Method content changed after adoption; obtain a new confirmation.')
    return spec


def adopt(spec, confirmation_reference):
    """Return an adopted copy; repeating adoption preserves revision/receipt."""
    validate(spec)
    _text(confirmation_reference, 'confirmation_reference')
    if spec['status'] == 'adopted':
        return deepcopy(spec)
    missing = _missing(spec)
    if missing or spec['unresolved'] or spec['unsupported']:
        raise MethodologyError('Resolve method input before adoption: ' + ', '.join(
            missing + spec['unresolved'] + (['unsupported'] if spec['unsupported'] else [])))
    result = deepcopy(spec)
    result['status'] = 'adopted'
    result['confirmation'] = {'reference': confirmation_reference, 'candidate_hash': digest(spec)}
    return validate(result, require_adopted=True)


def _has_source(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_source(item) for item in value.values())
    return False


def _known(profile, key):
    facts = profile.get('facts', {})
    fact = facts.get(key) if isinstance(facts, dict) else None
    if (isinstance(fact, dict) and isinstance(fact.get('status'), str)
            and fact['status'] in {'confirmed', 'observed'}
            and _has_source(fact.get('source'))):
        return fact.get('value')
    return None


def _scope(profile):
    scope = {'platforms': [], 'countries': [], 'surface': None, 'monetization': None}
    for key in ('platforms', 'countries'):
        value = _known(profile, key)
        if isinstance(value, list) and value and all(isinstance(v, str) and v.strip() for v in value):
            if key != 'platforms' or set(value) <= PLATFORMS:
                scope[key] = sorted(set(value))
    for key, choices in (('surface', SURFACES), ('monetization', MONETIZATION)):
        value = _known(profile, key)
        if isinstance(value, str) and value in choices:
            scope[key] = value
    return scope


LABELS = {
    'template': 'template', '模板': 'template',
    'variable': 'variable', '变量': 'variable',
    'fixed': 'fixed_components', 'fixed_components': 'fixed_components', '固定项': 'fixed_components',
    'question': 'question', '测试问题': 'question',
    'anchor': 'anchor_asset_id', 'anchor_asset_id': 'anchor_asset_id', '锚定素材': 'anchor_asset_id',
    'metric': 'measurement.metric', '指标': 'measurement.metric',
    'source': 'measurement.source', '数据来源': 'measurement.source',
    'window': 'measurement.window', '观察窗口': 'measurement.window',
}
ENUMS = {
    'template': {'single_variable': 'single_variable', '单变量测试': 'single_variable',
                 'concept_exploration': 'concept_exploration', '概念探索': 'concept_exploration'},
    'variable': {'hook': 'hook', '钩子': 'hook', 'concept': 'concept', '概念': 'concept'},
    'fixed_components': {'hook': 'hook', '钩子': 'hook', 'body': 'body', '主体': 'body',
                         'cta': 'cta', '行动号召': 'cta', 'destination': 'destination', '落地页': 'destination'},
}


def _parse_sop(text):
    parsed, unresolved, unsupported = {}, [], []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = re.split(r'[:：]', line, maxsplit=1)
        key = LABELS.get(parts[0].strip().casefold()) if len(parts) == 2 else None
        if key is None:
            unsupported.append(line)
            continue
        value = parts[1].strip()
        if not value:
            continue
        if key == 'fixed_components':
            values = [item.strip().casefold() for item in re.split(r'[,，、]', value)]
            if any(item not in ENUMS[key] for item in values):
                unsupported.append(line)
                continue
            mapped = {ENUMS[key][item] for item in values}
            value = [item for item in COMPONENTS if item in mapped]
        elif key in ENUMS:
            value = ENUMS[key].get(value.casefold())
            if value is None:
                unsupported.append(line)
                continue
        if key in parsed and parsed[key] != value:
            unresolved.append('conflict.' + key)
        else:
            parsed[key] = value
    return parsed, unresolved, unsupported


def _request(request):
    required = {'approach', 'source', 'answers'}
    if (not isinstance(request, dict) or not required <= set(request)
            or set(request) - required - {'unresolved', 'unsupported'}):
        raise MethodologyError('request has missing or unsupported fields.')
    if 'unresolved' in request:
        _strings(request['unresolved'], 'request.unresolved')
    if 'unsupported' in request:
        if not isinstance(request['unsupported'], list):
            raise MethodologyError('request.unsupported must be a list.')
        for line in request['unsupported']:
            _text(line, 'request.unsupported item')
    _choice(request['approach'], {'guided', 'bring_own'}, 'request.approach')
    _object(request['source'], {'reference', 'text'}, 'request.source')
    _text(request['source']['reference'], 'request.source.reference')
    _text(request['source']['text'], 'request.source.text', allow_empty=True)
    answers = request['answers']
    if not isinstance(answers, dict) or set(answers) - {'question', 'anchor_asset_id', 'template', 'measurement'}:
        raise MethodologyError('request.answers contains unsupported fields.')
    for name in ('question', 'anchor_asset_id'):
        if name in answers:
            if name == 'anchor_asset_id' and answers[name] is None:
                continue
            _text(answers[name], 'request.answers.' + name, allow_empty=name == 'question')
    if 'template' in answers:
        _choice(answers['template'], TEMPLATES, 'request.answers.template')
    if 'measurement' in answers:
        _object(answers['measurement'], {'metric', 'source', 'window'}, 'request.answers.measurement')
        for key, value in answers['measurement'].items():
            _text(value, 'request.answers.measurement.' + key, allow_empty=True)


def propose(profile, request):
    """Create candidates from known scope and explicit answers or labelled SOP.

    English labels: Template, Variable, Fixed, Question, Anchor, Metric, Source,
    Window. Chinese labels: 模板、变量、固定项、测试问题、锚定素材、指标、数据来源、观察窗口.
    Labels use ':' or '：'; fixed items use commas. Enum spellings are listed in
    ENUMS. All other lines remain unsupported, including budget instructions.
    Guided source text is provenance, not semantic input. The host may provide
    explicit request.unresolved and request.unsupported lists after reviewing
    free text; both lists block adoption and are preserved in each candidate.
    """
    if not isinstance(profile, dict):
        raise MethodologyError('profile must be an object.')
    _text(profile.get('profile_id'), 'profile.profile_id')
    _request(request)
    own = request['approach'] == 'bring_own'
    parsed, gaps, unsupported = _parse_sop(request['source']['text']) if own else ({}, [], [])
    gaps.extend(request.get('unresolved', []))
    unsupported.extend(request.get('unsupported', []))
    answers = deepcopy(request['answers'])
    explicit = {key: value for key, value in answers.items() if key != 'measurement'}
    explicit.update({'measurement.' + key: value for key, value in answers.get('measurement', {}).items()})
    for key, value in explicit.items():
        if value is None or value == '':
            continue
        if isinstance(value, str):
            value = value.strip()
        if key in parsed and parsed[key] != value:
            gaps.append('conflict.' + key)
        else:
            parsed[key] = value
    templates = [parsed['template']] if 'template' in parsed else list(TEMPLATES)
    if own:
        for key in ('template', 'variable', 'fixed_components'):
            if key not in parsed:
                gaps.append(key)
        if not request['source']['text'].strip():
            gaps.append('source.text')
    proposals = []
    for template in templates:
        variable = 'hook' if template == 'single_variable' else 'concept'
        fixed = ['body', 'cta', 'destination'] if template == 'single_variable' else ['destination']
        unresolved = list(gaps)
        if own and 'variable' in parsed and parsed['variable'] != variable:
            unresolved.append('conflict.variable')
        if own and 'fixed_components' in parsed:
            supplied = parsed['fixed_components']
            valid = (set(supplied) == set(fixed) if template == 'single_variable' else 'destination' in supplied)
            if valid:
                fixed = supplied
            else:
                unresolved.append('conflict.fixed_components')
        spec = {
            'schema_version': 1,
            'revision': 1, 'product_id': profile['profile_id'], 'status': 'candidate',
            'approach': request['approach'], 'template': template,
            'question': parsed.get('question', ''), 'anchor_asset_id': parsed.get('anchor_asset_id'),
            'variable': variable, 'fixed_components': fixed, 'scope': _scope(profile),
            'measurement': {key: parsed.get('measurement.' + key, '') for key in ('metric', 'source', 'window')},
            'source': deepcopy(request['source']), 'unresolved': [],
            'unsupported': list(unsupported), 'confirmation': None,
        }
        spec['unresolved'] = sorted(set(unresolved + _missing(spec)))
        # Candidate selection identifies this complete effective proposal, not
        # just its source document. task.py may preserve an adopted method's
        # long-lived identity across explicitly confirmed revisions.
        spec['method_id'] = 'method-' + digest(spec)[:20]
        proposals.append(validate(spec))
    return proposals


def summary(spec):
    """Stable review text for compatibility with M1 methodology text facts."""
    validate(spec)
    value = lambda item: item if item else 'unknown'
    scope = spec['scope']
    measurement = spec['measurement']
    return ('Method {method_id} revision {revision}; template={template}; '
            'question={question}; anchor={anchor}; variable={variable}; fixed={fixed}; '
            'scope={platforms}/{countries}/{surface}/{monetization}; '
            'measurement={metric}/{source}/{window}').format(
                method_id=spec['method_id'], revision=spec['revision'], template=spec['template'],
                question=value(spec['question']), anchor=value(spec['anchor_asset_id']),
                variable=spec['variable'], fixed=','.join(spec['fixed_components']),
                platforms=value(','.join(scope['platforms'])), countries=value(','.join(scope['countries'])),
                surface=value(scope['surface']), monetization=value(scope['monetization']),
                metric=value(measurement['metric']), source=value(measurement['source']), window=value(measurement['window']))


def applicability(spec, profile, targets):
    """Report incomplete scope or mismatches across the entire selected context."""
    validate(spec)
    if not isinstance(profile, dict):
        raise MethodologyError('profile must be an object.')
    issues = []
    def issue(code, path, message):
        issues.append({'code': code, 'path': path, 'message': message})
    if spec['product_id'] != profile.get('profile_id'):
        issue('scope_mismatch', 'product_id', 'Method product does not match the current profile.')
    actual = _scope(profile)
    if targets is not None:
        if not isinstance(targets, list) or not targets:
            issue('needs_input', 'targets', 'Provide the selected target accounts.')
            actual['platforms'] = []
        else:
            platforms = set()
            for index, target in enumerate(targets):
                if (not isinstance(target, dict) or not isinstance(target.get('platform'), str)
                        or target['platform'] not in PLATFORMS):
                    issue('needs_input', 'targets[' + str(index) + '].platform', 'Target platform is unknown or invalid.')
                else:
                    platforms.add(target['platform'])
            actual['platforms'] = sorted(platforms)
    for key, allowed in spec['scope'].items():
        observed = actual[key]
        if not allowed or not observed:
            issue('needs_input', 'scope.' + key, 'Both method and task need an explicit ' + key + ' scope.')
        elif isinstance(allowed, list):
            if not set(observed) <= set(allowed):
                issue('scope_mismatch', 'scope.' + key, 'Method does not cover the entire selected ' + key + ' scope.')
        elif observed != allowed:
            issue('scope_mismatch', 'scope.' + key, 'Method and task have different ' + key + ' scopes.')
    return issues
