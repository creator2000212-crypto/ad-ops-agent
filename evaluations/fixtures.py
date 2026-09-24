"""Six fictional offline cases; guided answers model host extraction, not NLP tests."""
from datetime import datetime, timezone
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = tuple((business, approach) for business in ('app', 'ecommerce', 'leadgen')
              for approach in ('guided', 'bring_own'))
CASE_NAMES = tuple(business + '_' + approach for business, approach in CASES)


def _load(name):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


def build_case(business, approach, template=None):
    """Return fresh, explicit simulation input without touching files or accounts."""
    if (business, approach) not in CASES:
        raise ValueError('Choose app/ecommerce/leadgen and guided/bring_own.')
    template = template or ('single_variable' if approach == 'guided' else 'concept_exploration')
    if template not in ('single_variable', 'concept_exploration'):
        raise ValueError('Unsupported fictional method template.')
    case = business + '_' + approach
    profile = _load('onboarding-learning.json')
    profile['profile_id'] = 'fictional-m2-' + case
    profile['profile_version'] = '1'
    profile['fixture_only'] = True
    profile['collaboration'].update(approach=approach,
                                    current_need='Prepare a fictional ' + business + ' method-aware asset comparison.')
    profile['fixture_note'] = ('Fictional offline inputs only. Guided structured answers below simulate '
                               'host extraction from explicit user choices; this is not an NLP or host-client test.')

    def fact(name, value, status='confirmed'):
        profile['facts'][name] = {'value': value, 'status': status, 'source': 'fictional-m2-fixture-' + case}

    fact('product_name', 'Fictional M2 ' + case)
    fact('methodology', None, 'unknown')
    fact('audience', 'Fictional adult audience for offline planning; no real targeting settings.')
    fact('creative_direction', 'Compare declared components from fictional approved asset manifests.')
    checked_at = datetime.now(timezone.utc).isoformat()
    for account, check in zip(profile['selected_accounts'], profile['connections']['checks']):
        account['account_id'] = 'fictional_' + case + '_' + account['platform']
        check['account_id'] = account['account_id']
        for permission in ('read', 'write'):
            check[permission]['checked_at'] = checked_at
            check[permission]['evidence'] = 'Fictional offline fixture only; no real platform check.'
    if business == 'app':
        facts = {'surface': 'app', 'monetization': 'hybrid', 'goal_type': 'revenue',
                 'os': ['android'], 'store': 'virtual://fictional-app-store',
                 'measurement_stack': 'Fictional Firebase and server event fixture',
                 'ad_revenue_event': 'fictional_ad_revenue', 'ad_revenue_window': 'observed 7-day cohort',
                 'purchase_revenue_event': 'fictional_purchase',
                 'refund_policy': 'Fictional observed purchase amounts net of recorded refunds',
                 'success_metric': 'Observed combined ad and purchase revenue in the declared window'}
        metric = 'observed_combined_revenue'
    elif business == 'ecommerce':
        facts = {'surface': 'web', 'monetization': 'ecommerce', 'goal_type': 'value',
                 'purchase_revenue_event': 'fictional_purchase',
                 'refund_policy': 'Subtract recorded refunds from observed purchase amounts',
                 'value_basis': 'Observed transaction revenue only; neither profit nor predicted LTV',
                 'value_window': 'observed 7-day transaction window',
                 'success_metric': 'Observed purchase value in the declared transaction window'}
        metric = 'observed_purchase_value'
    else:
        facts = {'surface': 'web', 'monetization': 'leadgen', 'goal_type': 'conversion',
                 'lead_event': 'fictional_qualified_lead',
                 'lead_qualification': 'Fictional deduplicated lead explicitly marked qualified by the CRM fixture',
                 'success_metric': 'Observed qualified leads, distinct from raw form submissions'}
        metric = 'qualified_leads'
    for name, value in facts.items():
        fact(name, value)
    question = 'Which declared ' + ('opening' if template == 'single_variable' else 'concept') + ' should receive another test?'
    measurement = {'metric': metric, 'source': 'fictional-' + business + '-result-report', 'window': 'observed 7 days'}
    variable = 'hook' if template == 'single_variable' else 'concept'
    fixed = 'body, cta, destination' if template == 'single_variable' else 'destination'
    if approach == 'guided':
        request = {'approach': approach,
                   'source': {'reference': 'fictional-host-extracted-user-choices-' + case,
                              'text': ('Fictional user: start from anchor, keep the declared fixed components, '
                                       'and compare ' + variable + '. Use ' + metric + ' from the named report over 7 days.')},
                   'answers': {'template': template, 'question': question,
                               'anchor_asset_id': 'anchor', 'measurement': measurement}}
    else:
        sop = '\n'.join(['Template: ' + template, 'Variable: ' + variable, 'Fixed: ' + fixed,
                         'Question: ' + question, 'Anchor: anchor', 'Metric: ' + metric,
                         'Source: ' + measurement['source'], 'Window: ' + measurement['window']])
        request = {'approach': approach,
                   'source': {'reference': 'fictional-labelled-sop-' + case, 'text': sop}, 'answers': {}}
    brief = _load('brief.json')
    brief.update(task_id='fictional-m2-task-' + case, business_type=business,
                 objective='fictional_' + facts['goal_type'], target_event=metric)
    for target, account in zip(brief['targets'], profile['selected_accounts']):
        target['account_id'] = account['account_id']

    def asset(asset_id, concept='concept-a', hook='hook-a', body='body-a', destination='destination-a'):
        return {'asset_id': asset_id, 'source_ref': 'virtual://fictional-m2-' + asset_id,
                'type': 'image', 'language': 'en', 'width': 1080, 'height': 1080,
                'tags': ['example_approved', 'generic_test'],
                'test_identity': {'concept_id': concept,
                                  'components': {'hook': hook, 'body': body, 'cta': 'cta-a', 'destination': destination},
                                  'source': {'kind': 'production_manifest', 'reference': 'fictional-manifest-' + asset_id}}}
    wrong_destination = asset('wrong-destination', concept='concept-c', hook='hook-c', destination='destination-c')
    unknown = asset('unknown-identity')
    unknown.pop('test_identity')
    pool = [wrong_destination, unknown,
            asset('concept-b', concept='concept-b', hook='hook-b', body='body-b'),
            asset('anchor'), asset('hook-b', hook='hook-b')]
    return {'profile': profile, 'request': request, 'brief': brief,
            'candidates': {'notice': 'Fictional declared metadata and identities; no media inspection.', 'assets': pool}}
