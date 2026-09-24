import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import methodology


class MethodologyTests(unittest.TestCase):
    def profile(self):
        values = {'platforms': ['meta', 'tiktok'], 'countries': ['US', 'CA'],
                  'surface': 'web', 'monetization': 'leadgen'}
        return {'profile_id': 'fictional-method-product', 'facts': {
            key: {'value': value, 'status': 'confirmed', 'source': 'fictional_fixture_only'}
            for key, value in values.items()}}

    def request(self, template='single_variable'):
        answers = {'question': 'Which hook should be tested next?', 'anchor_asset_id': 'fictional-anchor',
                   'measurement': {'metric': 'qualified CPL', 'source': 'fictional imported report',
                                   'window': 'explicit fictional seven-day observation'}}
        if template is not None:
            answers['template'] = template
        return {'approach': 'guided', 'source': {'reference': 'fictional user brief', 'text': 'Prepare a comparison.'},
                'answers': answers}

    def candidate(self, template='single_variable'):
        return methodology.propose(self.profile(), self.request(template))[0]

    def own_request(self):
        return {'approach': 'bring_own', 'source': {'reference': 'fictional SOP v1', 'text': '\n'.join([
            'Template: single_variable', 'Variable: hook', 'Fixed: body, cta, destination',
            'Question: Which hook should be tested next?', 'Anchor: fictional-anchor',
            'Metric: qualified CPL', 'Source: fictional report', 'Window: seven days'])}, 'answers': {}}

    def test_guided_offers_two_complete_candidates_without_inventing_choices(self):
        profile, request = self.profile(), self.request(None)
        before = copy.deepcopy((profile, request))
        choices = methodology.propose(profile, request)
        self.assertEqual({spec['template'] for spec in choices}, set(methodology.TEMPLATES))
        self.assertEqual(before, (profile, request))
        for spec in choices:
            self.assertEqual(spec['status'], 'candidate')
            self.assertEqual(spec['unresolved'], [])
            self.assertEqual(spec['measurement'], request['answers']['measurement'])
            self.assertNotIn('budget', spec)
            self.assertEqual(methodology.adopt(spec, 'explicit fixture adoption')['status'], 'adopted')

    def test_missing_inputs_stay_unknown_and_do_not_inherit_hypotheses(self):
        profile = self.profile()
        profile['facts']['platforms']['status'] = 'hypothesis'
        profile['facts']['countries']['source'] = ''
        profile['facts']['surface']['status'] = 'conflict'
        profile['facts']['monetization']['value'] = 'made_up'
        request = self.request(None)
        request['answers'] = {}
        for spec in methodology.propose(profile, request):
            self.assertEqual(spec['scope'], {'platforms': [], 'countries': [], 'surface': None, 'monetization': None})
            self.assertEqual(spec['measurement'], {'metric': '', 'source': '', 'window': ''})
            self.assertIsNone(spec['anchor_asset_id'])
            self.assertIn('question', spec['unresolved'])
            self.assertIn('measurement.window', spec['unresolved'])
            with self.assertRaises(methodology.MethodologyError):
                methodology.adopt(spec, 'not enough input')

    def test_adoption_is_copy_idempotent_and_binds_complete_candidate(self):
        candidate = self.candidate()
        original = copy.deepcopy(candidate)
        adopted = methodology.adopt(candidate, 'explicit fictional user confirmation')
        self.assertEqual(candidate, original)
        self.assertEqual(adopted['confirmation']['candidate_hash'], methodology.digest(candidate))
        self.assertEqual(methodology.adopt(adopted, 'repeated explicit confirmation'), adopted)
        self.assertEqual(adopted['revision'], 1)
        self.assertIs(methodology.validate(adopted, require_adopted=True), adopted)
        for key, value in (('question', 'Changed question'), ('revision', 2), ('product_id', 'other-product')):
            tampered = copy.deepcopy(adopted)
            tampered[key] = value
            with self.subTest(field=key), self.assertRaises(methodology.MethodologyError):
                methodology.validate(tampered, require_adopted=True)
        with self.assertRaises(methodology.MethodologyError):
            methodology.validate(candidate, require_adopted=True)

    def test_clearing_unresolved_does_not_make_missing_measurement_adoptable(self):
        spec = self.candidate('concept_exploration')
        spec['measurement']['window'] = ''
        spec['unresolved'] = []
        with self.assertRaises(methodology.MethodologyError):
            methodology.adopt(spec, 'fictional confirmation')
        spec = self.candidate()
        spec['approach'] = 'bring_own'
        spec['source']['text'] = ''
        with self.assertRaises(methodology.MethodologyError):
            methodology.adopt(spec, 'fictional confirmation')
        spec = self.candidate('concept_exploration')
        spec['anchor_asset_id'] = None
        with self.assertRaises(methodology.MethodologyError):
            methodology.adopt(spec, 'fictional confirmation')

    def test_sop_parses_only_explicit_labels_and_preserves_original_source(self):
        request = self.own_request()
        spec = methodology.propose(self.profile(), request)[0]
        self.assertEqual(spec['source'], request['source'])
        self.assertEqual(spec['unsupported'], [])
        self.assertEqual(spec['unresolved'], [])
        self.assertEqual(spec['variable'], 'hook')
        self.assertEqual(methodology.adopt(spec, 'fixture adoption')['status'], 'adopted')
        request['source']['text'] += '\n  每天提高预算 30%\nBudget: split equally\nBudget: split equally'
        spec = methodology.propose(self.profile(), request)[0]
        self.assertEqual(spec['unsupported'], ['  每天提高预算 30%', 'Budget: split equally', 'Budget: split equally'])
        with self.assertRaises(methodology.MethodologyError):
            methodology.adopt(spec, 'fixture adoption')

    def test_chinese_sop_and_fullwidth_delimiters_support_same_finite_contract(self):
        request = {'approach': 'bring_own', 'source': {'reference': '虚构方法', 'text': '\n'.join([
            '模板：概念探索', '变量：概念', '固定项：主体，行动号召，落地页',
            '测试问题：哪个素材概念值得继续验证？', '锚定素材：fictional-anchor',
            '指标：有效线索成本', '数据来源：虚构报表', '观察窗口：用户指定的一周'])}, 'answers': {}}
        spec = methodology.propose(self.profile(), request)[0]
        self.assertEqual(spec['template'], 'concept_exploration')
        self.assertEqual(spec['fixed_components'], ['body', 'cta', 'destination'])
        self.assertEqual(spec['unresolved'], [])

    def test_answers_fill_missing_values_but_sop_conflicts_are_not_overwritten(self):
        request = self.own_request()
        request['source']['text'] = request['source']['text'].replace('Window: seven days', '')
        request['answers'] = {'question': 'Different question', 'measurement': {
            'metric': 'qualified CPL', 'source': 'fictional report', 'window': 'fourteen days'}}
        spec = methodology.propose(self.profile(), request)[0]
        self.assertEqual(spec['question'], 'Which hook should be tested next?')
        self.assertEqual(spec['measurement']['window'], 'fourteen days')
        self.assertEqual(spec['unresolved'], ['conflict.question'])
        with self.assertRaises(methodology.MethodologyError):
            methodology.adopt(spec, 'fixture adoption')

    def test_missing_or_conflicting_sop_controls_never_become_inferred_method(self):
        request = self.own_request()
        request['source']['text'] = 'Question: Test something\n1n1\nFixed: destination'
        specs = methodology.propose(self.profile(), request)
        self.assertEqual(len(specs), 2)
        for spec in specs:
            self.assertIn('template', spec['unresolved'])
            self.assertIn('variable', spec['unresolved'])
            self.assertEqual(spec['unsupported'], ['1n1'])
        request = self.own_request()
        request['source']['text'] += '\nVariable: concept'
        spec = methodology.propose(self.profile(), request)[0]
        self.assertIn('conflict.variable', spec['unresolved'])

    def test_applicability_requires_full_country_and_platform_coverage(self):
        spec = self.candidate()
        targets = [{'platform': 'meta', 'account_id': 'fictional'}]
        self.assertEqual(methodology.applicability(spec, self.profile(), targets), [])
        targets.append({'platform': 'google', 'account_id': 'fictional-google'})
        issues = methodology.applicability(spec, self.profile(), targets)
        self.assertIn('scope.platforms', {i['path'] for i in issues})
        profile = self.profile()
        profile['facts']['countries']['value'].append('GB')
        profile['facts']['surface']['value'] = 'app'
        profile['profile_id'] = 'another-product'
        issues = methodology.applicability(spec, profile, targets[:1])
        self.assertEqual({i['path'] for i in issues}, {'scope.countries', 'scope.surface', 'product_id'})
        profile['facts']['countries']['status'] = 'stale'
        issues = methodology.applicability(spec, profile, [])
        self.assertTrue(any(i['code'] == 'needs_input' and i['path'] == 'scope.countries' for i in issues))

    def test_exact_fields_and_boolean_integer_confusion_are_rejected(self):
        modifications = [lambda s: s.update(extra='unknown'), lambda s: s.update(revision=True),
                         lambda s: s.update(schema_version=True), lambda s: s.update(variable='concept'),
                         lambda s: s['scope'].update(accounts=[]),
                         lambda s: s['fixed_components'].append('hook'),
                         lambda s: s.update(confirmation={'reference': 'premature'})]
        for modify in modifications:
            spec = self.candidate()
            modify(spec)
            with self.subTest(modify=modify), self.assertRaises(methodology.MethodologyError):
                methodology.validate(spec)
        request = self.request()
        request['answers']['budget'] = 30
        with self.assertRaises(methodology.MethodologyError):
            methodology.propose(self.profile(), request)

    def test_summary_and_identity_are_stable_without_status_changing_method_text(self):
        spec = self.candidate()
        repeat = self.candidate()
        self.assertEqual(spec, repeat)
        self.assertEqual(methodology.summary(spec), methodology.summary(methodology.adopt(spec, 'fixture adoption')))
        self.assertIn('template=single_variable', methodology.summary(spec))
        changed = copy.deepcopy(spec)
        changed['question'] += ' Changed.'
        self.assertNotEqual(methodology.summary(spec), methodology.summary(changed))
        self.assertNotEqual(methodology.digest(spec), methodology.digest(changed))
        self.assertEqual(methodology.digest(spec), methodology.digest(dict(reversed(list(spec.items())))))

    def test_candidate_identity_changes_with_effective_answers_scope_and_unresolved_input(self):
        baseline = self.candidate()['method_id']
        changes = [
            lambda p, r: r['answers'].update(question='Which opening improves qualified visits?'),
            lambda p, r: r['answers'].update(anchor_asset_id='another-fictional-anchor'),
            lambda p, r: r['answers']['measurement'].update(window='fourteen days'),
            lambda p, r: p['facts']['countries'].update(value=['GB']),
            lambda p, r: p['facts']['surface'].update(value='app'),
            lambda p, r: r['source'].update(text='A corrected source brief.'),
            lambda p, r: r.update(unresolved=['Confirm the comparison definition.']),
            lambda p, r: r.update(unsupported=['Use separate asset budgets.']),
        ]
        for change in changes:
            profile, request = self.profile(), self.request()
            change(profile, request)
            changed = methodology.propose(profile, request)[0]
            with self.subTest(change=change):
                self.assertNotEqual(changed['method_id'], baseline)
                self.assertEqual(changed, methodology.propose(copy.deepcopy(profile), copy.deepcopy(request))[0])
        incomplete_request = self.request()
        incomplete_request['answers'].pop('question')
        incomplete = methodology.propose(self.profile(), incomplete_request)[0]
        self.assertNotEqual(incomplete['method_id'], baseline)
        self.assertIn('question', incomplete['unresolved'])

    def test_explicit_uninterpreted_guided_requirements_block_every_candidate(self):
        request = self.request(None)
        request['source']['text'] = 'A free-form brief with additional conditions.'
        request['unresolved'] = ['Confirm the meaning of the observation window.']
        request['unsupported'] = ['Assign a separate equal budget to every asset.']
        before = copy.deepcopy(request)
        for spec in methodology.propose(self.profile(), request):
            self.assertEqual(spec['unresolved'], request['unresolved'])
            self.assertEqual(spec['unsupported'], request['unsupported'])
            self.assertEqual(spec['source']['text'], request['source']['text'])
            with self.assertRaises(methodology.MethodologyError):
                methodology.adopt(spec, 'complete fields do not resolve extra requirements')
        self.assertEqual(request, before)

    def test_imported_and_explicit_unknown_requirements_are_combined(self):
        request = self.own_request()
        request['source']['text'] += '\nBudget: split equally'
        request['unsupported'] = ['Pending native placement mapping.']
        request['unresolved'] = ['Need final measurement definition.']
        spec = methodology.propose(self.profile(), request)[0]
        self.assertEqual(spec['unsupported'], ['Budget: split equally', 'Pending native placement mapping.'])
        self.assertIn('Need final measurement definition.', spec['unresolved'])

    def test_schema_is_executable_structure_and_declares_runtime_hash_check(self):
        schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas/methodology.schema.json').read_text())
        self.assertEqual(set(schema['required']), methodology.FIELDS)
        self.assertFalse(schema['additionalProperties'])
        self.assertIn('methodology.validate', schema['$comment'])
        self.assertIn('allOf', schema)


if __name__ == '__main__':
    unittest.main()
