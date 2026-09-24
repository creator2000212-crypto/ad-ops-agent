"""Compile adopted test methods from declared component identities, offline only."""
from copy import deepcopy

import methodology


class PlanningError(ValueError):
    pass


COMPONENTS = {'hook', 'body', 'cta', 'destination'}
IDENTITY_FIELDS = {'concept_id', 'components', 'source'}
ALLOCATION = {
    'mode': 'shared_target_budget',
    'notice': ('Each target owns one shared budget; units do not receive separate budgets. '
               'This is an offline test design, not a randomized A/B experiment, a promise '
               'of equal exposure, or a native platform execution configuration.'),
}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _identity(asset):
    """Return explicit identity evidence or the precise missing/invalid fields."""
    identity = asset.get('test_identity')
    if not isinstance(identity, dict) or set(identity) != IDENTITY_FIELDS:
        return None, ['test_identity requires exactly concept_id, components and source']
    errors = []
    if not _text(identity['concept_id']):
        errors.append('test_identity.concept_id must be an explicit nonempty string')
    components = identity['components']
    if not isinstance(components, dict) or set(components) != COMPONENTS:
        errors.append('test_identity.components requires exactly hook, body, cta and destination')
    else:
        errors += ['test_identity.components.' + key + ' must be an explicit nonempty string'
                   for key in sorted(COMPONENTS) if not _text(components[key])]
    source = identity['source']
    if (not isinstance(source, dict) or set(source) != {'kind', 'reference'}
            or source.get('kind') not in ('user_confirmation', 'production_manifest')
            or not _text(source.get('reference'))):
        errors.append('test_identity.source requires user_confirmation or production_manifest and a reference')
    return (None, errors) if errors else (identity, [])


def _support_errors(method):
    errors = []
    template = method.get('template')
    if template not in ('single_variable', 'concept_exploration'):
        errors.append('Only single_variable and concept_exploration templates are implemented.')
        return errors
    variable = 'hook' if template == 'single_variable' else 'concept'
    if method.get('variable') != variable:
        errors.append(template + ' requires variable=' + variable + '.')
    fixed = method.get('fixed_components')
    if not isinstance(fixed, list) or any(not isinstance(value, str) for value in fixed):
        errors.append('fixed_components must be an explicit component list.')
    elif template == 'single_variable' and set(fixed) != {'body', 'cta', 'destination'}:
        errors.append('single_variable supports hook changes with body, cta and destination fixed.')
    elif template == 'concept_exploration' and ('destination' not in fixed or not set(fixed) <= COMPONENTS):
        errors.append('concept_exploration must fix destination and may also fix hook, body or cta.')
    return errors


def compile_test_plan(method, eligible_assets, brief):
    """Compile a deterministic advisory test design; never allocate or mutate budgets.

    eligible_assets is the complete metadata-filtered pool, before the requested
    count is applied. Explicit anchor and declared component identities govern
    selection. These declarations do not prove media content or performance.
    """
    if not isinstance(method, dict) or not isinstance(brief, dict):
        raise PlanningError('method and brief must be objects.')
    if not isinstance(eligible_assets, list) or any(not isinstance(asset, dict) for asset in eligible_assets):
        raise PlanningError('eligible_assets must be a list of asset objects.')
    # Canonical serialization also rejects non-JSON values and nonfinite numbers.
    try:
        method_hash = methodology.digest(method)
        methodology.digest(eligible_assets)
        methodology.digest(brief)
    except (ValueError, TypeError) as exc:
        raise PlanningError('Test compilation requires finite JSON inputs.') from exc
    snapshot = deepcopy(method)
    decisions = [{'asset_id': asset.get('asset_id'), 'status': 'excluded', 'reasons': []}
                 for asset in eligible_assets]
    issues = []
    units, selected_assets = [], []

    def issue(code, path, message):
        issues.append({'code': code, 'path': path, 'message': message})

    def result():
        status = ('unsupported' if any(item['code'] == 'unsupported' for item in issues)
                  else 'needs_input' if issues else 'ready')
        return {
            'schema_version': 1, 'kind': 'offline_test_plan', 'status': status,
            'method_hash': method_hash, 'method_snapshot': snapshot,
            'issues': issues, 'units': units, 'asset_decisions': decisions,
            'allocation': deepcopy(ALLOCATION),
            'evidence_basis': 'declared_component_identity_only',
            'selected_assets': selected_assets,
        }

    unsupported = _support_errors(method)
    if method.get('unsupported'):
        unsupported.append('The method declares unsupported requirements; they cannot be silently dropped.')
    for message in unsupported:
        issue('unsupported', 'method', message)
    try:
        methodology.validate(method, require_adopted=True)
    except ValueError as exc:
        issue('needs_input', 'method', str(exc))
    requirements = brief.get('asset_requirements')
    count = requirements.get('count') if isinstance(requirements, dict) else None
    if type(count) is not int or count < 2:
        issue('needs_input', 'asset_requirements.count', 'A comparison requires an explicit integer count of at least two.')
    if issues:
        for decision in decisions:
            decision['reasons'] = ['selection blocked until the method and comparison count are valid']
        return result()

    identities = {}
    ids = {}
    for index, asset in enumerate(eligible_assets):
        asset_id = asset.get('asset_id')
        if not _text(asset_id):
            decisions[index]['reasons'] = ['asset_id must be an explicit nonempty string']
            continue
        ids.setdefault(asset_id, []).append(index)
        identity, errors = _identity(asset)
        if errors:
            decisions[index]['reasons'] = errors
        else:
            identities[index] = identity
    duplicates = {asset_id for asset_id, indices in ids.items() if len(indices) > 1}
    for asset_id in sorted(duplicates):
        issue('needs_input', 'eligible_assets', 'Duplicate asset_id cannot identify a unique test asset: ' + asset_id)
        for index in ids[asset_id]:
            identities.pop(index, None)
            decisions[index]['reasons'].append('duplicate asset_id')

    anchor_id = method.get('anchor_asset_id')
    anchor_indices = ids.get(anchor_id, [])
    anchor_index = anchor_indices[0] if len(anchor_indices) == 1 else None
    if anchor_index is None or anchor_index not in identities:
        issue('needs_input', 'method.anchor_asset_id',
              'The explicit anchor must be a unique eligible asset with complete declared component identity.')
        for decision in decisions:
            if not decision['reasons']:
                decision['reasons'] = ['selection blocked because the anchor is missing or its identity is invalid']
        return result()

    anchor = identities[anchor_index]
    variable = method['variable']
    fixed = method['fixed_components']

    def variable_value(identity):
        return identity['components']['hook'] if variable == 'hook' else identity['concept_id']

    def add_unit(index, anchor_unit=False):
        asset = eligible_assets[index]
        value = variable_value(identities[index])
        unit_id = methodology.digest({'method_hash': method_hash, 'asset_id': asset['asset_id'],
                                      'variable': variable, 'value': value})[:24]
        units.append({'unit_id': unit_id,
                      'label': ('Anchor' if anchor_unit else 'Variant') + ': ' + asset['asset_id'],
                      'asset_ids': [asset['asset_id']], 'variable_value': value})
        selected_assets.append(deepcopy(asset))
        decisions[index].update(status='selected', reasons=[
            'explicit anchor; declared identities only' if anchor_unit
            else 'distinct ' + variable + '; all declared fixed components match the anchor'])

    add_unit(anchor_index, anchor_unit=True)
    seen_variables = {variable_value(anchor)}
    for index, asset in enumerate(eligible_assets):
        if index == anchor_index or index not in identities:
            continue
        identity = identities[index]
        reasons = []
        if variable == 'hook' and identity['concept_id'] != anchor['concept_id']:
            reasons.append('concept_id differs from the anchor in a single-variable test')
        for key in fixed:
            if identity['components'][key] != anchor['components'][key]:
                reasons.append('fixed component differs from the anchor: ' + key)
        value = variable_value(identity)
        if value in seen_variables:
            reasons.append('duplicate variable value: ' + variable)
        if reasons:
            decisions[index]['reasons'] = reasons
            continue
        seen_variables.add(value)
        if len(units) < count:
            add_unit(index)
        else:
            decisions[index].update(status='eligible_not_selected', reasons=[
                'all declared method conditions match; requested unit count already filled'])
    if len(units) < count:
        issue('needs_input', 'eligible_assets',
              'Insufficient distinct assets matching the declared method: ' + str(len(units)) + '/' + str(count) + '.')
    return result()


def validate_compilation(compilation, method, eligible_assets, brief):
    """Recompile and compare all fields, including presentation and evidence metadata."""
    if not isinstance(compilation, dict):
        raise PlanningError('compilation must be an object.')
    expected = compile_test_plan(method, eligible_assets, brief)
    try:
        matches = methodology.digest(compilation) == methodology.digest(expected)
    except (ValueError, TypeError) as exc:
        raise PlanningError('Compilation contains invalid JSON values.') from exc
    if not matches:
        raise PlanningError('Test compilation differs from its adopted method and declared asset evidence.')
    if expected['status'] != 'ready':
        raise PlanningError('Test compilation is not ready.')
    return expected
