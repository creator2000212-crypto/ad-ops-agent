"""Executable method selection uses declared identities, never inferred media content."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import methodology
import planning


def asset(asset_id, concept='concept-a', hook='hook-a', body='body-a',
          cta='cta-a', destination='destination-a'):
    return {
        'asset_id': asset_id, 'source_ref': 'virtual://' + asset_id,
        'type': 'video', 'language': 'en', 'tags': ['fictional-approved'],
        'test_identity': {
            'concept_id': concept,
            'components': {'hook': hook, 'body': body, 'cta': cta, 'destination': destination},
            'source': {'kind': 'production_manifest', 'reference': 'fictional-manifest-' + asset_id},
        },
    }


class TestPlanCompilationTests(unittest.TestCase):
    def setUp(self):
        def fact(value):
            return {'value': value, 'status': 'confirmed', 'source': 'fictional-profile'}
        self.profile = {
            'profile_id': 'fictional-method-product',
            'facts': {'platforms': fact(['meta']), 'countries': fact(['US']),
                      'surface': fact('web'), 'monetization': fact('leadgen')},
        }
        self.brief = {
            'asset_requirements': {'count': 2},
            'budget': {'amount': '90.00', 'period': 'total'},
            'targets': [{'platform': 'meta', 'account_id': 'fictional-account', 'budget_amount': '90.00'}],
        }
        self.assets = [asset('anchor'), asset('hook-b', hook='hook-b'),
                       asset('concept-b', concept='concept-b', hook='hook-c', body='body-b')]

    def method(self, template='single_variable', **overrides):
        candidate = next(method for method in methodology.propose(self.profile, {
            'approach': 'guided',
            'source': {'reference': 'fictional-method-request', 'text': 'Fictional explicit test choices.'},
            'answers': {'template': template, 'question': 'Which declared variant merits further study?',
                        'anchor_asset_id': 'anchor',
                        'measurement': {'metric': 'CTR', 'source': 'fictional-report', 'window': '7 days'}},
        }) if method['template'] == template)
        candidate.update(overrides)
        return methodology.adopt(candidate, 'fictional explicit method confirmation')

    def compile(self, method=None, assets=None, brief=None):
        return planning.compile_test_plan(
            self.method() if method is None else method,
            self.assets if assets is None else assets,
            self.brief if brief is None else brief)

    def decisions(self, result):
        return {row['asset_id']: row for row in result['asset_decisions']}

    def test_two_methods_change_selected_assets_and_units(self):
        single = self.compile()
        exploration = self.compile(method=self.method('concept_exploration'))
        self.assertEqual(single['status'], 'ready')
        self.assertEqual(exploration['status'], 'ready')
        self.assertEqual([unit['asset_ids'] for unit in single['units']], [['anchor'], ['hook-b']])
        self.assertEqual([unit['variable_value'] for unit in single['units']], ['hook-a', 'hook-b'])
        self.assertEqual([unit['asset_ids'] for unit in exploration['units']], [['anchor'], ['concept-b']])
        self.assertEqual([unit['variable_value'] for unit in exploration['units']], ['concept-a', 'concept-b'])
        self.assertNotEqual(single['method_hash'], exploration['method_hash'])
        self.assertNotEqual(single['units'][0]['unit_id'], exploration['units'][0]['unit_id'])
        self.assertIn('concept_id', ' '.join(self.decisions(single)['concept-b']['reasons']))
        self.assertIn('duplicate variable', ' '.join(self.decisions(exploration)['hook-b']['reasons']))

    def test_anchor_is_first_even_when_later_in_input_and_ids_are_stable(self):
        method = self.method()
        first = self.compile(method=method)
        reordered = self.compile(method=method, assets=[self.assets[1], self.assets[2], self.assets[0]])
        self.assertEqual(first['units'], reordered['units'])
        self.assertEqual(first['method_hash'], methodology.digest(method))
        self.assertEqual(first['method_snapshot'], method)
        self.assertEqual(len({unit['unit_id'] for unit in first['units']}), 2)

    def test_each_fixed_component_mismatch_is_excluded_and_explained(self):
        for component in ('body', 'cta', 'destination'):
            with self.subTest(component=component):
                pool = copy.deepcopy(self.assets[:2])
                pool[1]['test_identity']['components'][component] = 'changed-' + component
                result = self.compile(assets=pool)
                self.assertEqual(result['status'], 'needs_input')
                self.assertEqual(len(result['units']), 1)
                decision = self.decisions(result)['hook-b']
                self.assertEqual(decision['status'], 'excluded')
                self.assertIn('fixed component differs from the anchor: ' + component, decision['reasons'])

    def test_concept_exploration_preserves_destination_and_optional_fixed_components(self):
        method = self.method('concept_exploration', fixed_components=['destination', 'cta'])
        pool = [asset('anchor'), asset('wrong-destination', concept='b', destination='destination-b'),
                asset('wrong-cta', concept='c', cta='cta-b'),
                asset('valid-concept', concept='d', hook='hook-d', body='body-d')]
        result = self.compile(method=method, assets=pool)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual([unit['asset_ids'] for unit in result['units']], [['anchor'], ['valid-concept']])
        for asset_id, component in [('wrong-destination', 'destination'), ('wrong-cta', 'cta')]:
            self.assertIn('fixed component differs from the anchor: ' + component,
                          self.decisions(result)[asset_id]['reasons'])

    def test_duplicate_variable_never_counts_as_independent_unit(self):
        self.brief['asset_requirements']['count'] = 3
        result = self.compile(assets=[asset('anchor'), asset('same-as-anchor'),
                                     asset('hook-b', hook='hook-b'), asset('duplicate-b', hook='hook-b')])
        self.assertEqual(result['status'], 'needs_input')
        self.assertEqual(len(result['units']), 2)
        self.assertEqual({unit['variable_value'] for unit in result['units']}, {'hook-a', 'hook-b'})
        for duplicate in ('same-as-anchor', 'duplicate-b'):
            decision = self.decisions(result)[duplicate]
            self.assertEqual(decision['status'], 'excluded')
            self.assertIn('duplicate variable value: hook', decision['reasons'])

    def test_missing_or_invalid_identity_is_excluded_without_assuming_media_similarity(self):
        mutations = [
            lambda row: row.pop('test_identity'),
            lambda row: row['test_identity']['components'].pop('body'),
            lambda row: row['test_identity']['components'].update(hook=''),
            lambda row: row['test_identity'].update(concept_id=None),
            lambda row: row['test_identity'].update(inferred_similarity=True),
            lambda row: row['test_identity']['source'].update(kind='model_guess'),
            lambda row: row['test_identity']['source'].update(reference=''),
            lambda row: row['test_identity']['source'].update(externally_verified=True),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                pool = copy.deepcopy(self.assets[:2])
                mutate(pool[1])
                result = self.compile(assets=pool)
                self.assertEqual(result['status'], 'needs_input')
                self.assertEqual([unit['asset_ids'] for unit in result['units']], [['anchor']])
                self.assertEqual(self.decisions(result)['hook-b']['status'], 'excluded')
                self.assertTrue(self.decisions(result)['hook-b']['reasons'])

    def test_explicit_user_confirmed_component_identity_is_accepted(self):
        for row in self.assets:
            row['test_identity']['source']['kind'] = 'user_confirmation'
        self.assertEqual(self.compile()['status'], 'ready')

    def test_anchor_must_exist_be_eligible_unique_and_have_complete_identity(self):
        invalid_pools = [self.assets[1:],
                         [{'asset_id': 'anchor'}, self.assets[1]],
                         [self.assets[0], copy.deepcopy(self.assets[0]), self.assets[1]]]
        for pool in invalid_pools:
            with self.subTest(pool=pool):
                result = self.compile(assets=pool)
                self.assertEqual(result['status'], 'needs_input')
                self.assertEqual(result['units'], [])
                self.assertEqual(result['selected_assets'], [])
                self.assertTrue(any(issue['path'] == 'method.anchor_asset_id' for issue in result['issues']))
        result = self.compile(method=self.method(anchor_asset_id='not-in-eligible-pool'))
        self.assertEqual(result['status'], 'needs_input')
        self.assertEqual(result['units'], [])

    def test_comparison_count_must_be_at_least_two(self):
        for count in (None, 0, 1, -1, True, '2', 2.0):
            with self.subTest(count=count):
                self.brief['asset_requirements']['count'] = count
                result = self.compile()
                self.assertEqual(result['status'], 'needs_input')
                self.assertEqual(result['units'], [])
        self.brief.pop('asset_requirements')
        self.assertEqual(self.compile()['status'], 'needs_input')

    def test_excess_matching_assets_are_not_selected_and_input_order_is_preserved(self):
        pool = [asset('hook-c', hook='hook-c'), asset('anchor'), asset('hook-b', hook='hook-b')]
        result = self.compile(assets=pool)
        self.assertEqual([row['asset_id'] for row in result['asset_decisions']], ['hook-c', 'anchor', 'hook-b'])
        self.assertEqual([unit['asset_ids'] for unit in result['units']], [['anchor'], ['hook-c']])
        self.assertEqual(self.decisions(result)['hook-b']['status'], 'eligible_not_selected')

    def test_candidate_method_and_changed_adopted_method_cannot_compile(self):
        candidate = copy.deepcopy(self.method())
        candidate.update(status='candidate', confirmation=None)
        result = self.compile(method=candidate)
        self.assertEqual(result['status'], 'needs_input')
        self.assertEqual(result['units'], [])
        changed = self.method()
        changed['question'] = 'Changed question without renewed confirmation.'
        result = self.compile(method=changed)
        self.assertEqual(result['status'], 'needs_input')
        self.assertEqual(result['units'], [])

    def test_unimplemented_templates_or_variables_do_not_downgrade_silently(self):
        mutations = [lambda method: method.update(template='budget_split'),
                     lambda method: method.update(variable='body'),
                     lambda method: method.update(fixed_components=['destination']),
                     lambda method: method.update(unsupported=['per-unit fixed budgets'])]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                method = self.method()
                mutate(method)
                result = self.compile(method=method)
                self.assertEqual(result['status'], 'unsupported')
                self.assertEqual(result['units'], [])

    def test_inputs_and_budgets_are_unchanged_and_selected_assets_are_detached(self):
        method = self.method()
        before = copy.deepcopy((method, self.assets, self.brief))
        result = self.compile(method=method)
        self.assertEqual((method, self.assets, self.brief), before)
        self.assertEqual(result['allocation']['mode'], 'shared_target_budget')
        self.assertIn('equal exposure', result['allocation']['notice'])
        self.assertIn('randomized A/B', result['allocation']['notice'])
        self.assertEqual(result['evidence_basis'], 'declared_component_identity_only')
        for unit in result['units']:
            self.assertEqual(set(unit), {'unit_id', 'label', 'asset_ids', 'variable_value'})
            self.assertEqual(len(unit['asset_ids']), 1)
        result['selected_assets'][0]['test_identity']['components']['hook'] = 'changed-output-only'
        result['method_snapshot']['question'] = 'changed-output-question'
        self.assertEqual((method, self.assets, self.brief), before)

    def test_recompilation_verifies_all_fields_and_rejects_nonready_results(self):
        method = self.method()
        result = self.compile(method=method)
        self.assertEqual(planning.validate_compilation(result, method, self.assets, self.brief), result)
        mutations = [lambda output: output['units'][0].update(variable_value='invented'),
                     lambda output: output['allocation'].update(mode='fixed_per_unit_budget'),
                     lambda output: output['selected_assets'][0]['test_identity']['source'].update(reference='invented'),
                     lambda output: output.update(extra='unsupported field')]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                changed = copy.deepcopy(result)
                mutate(changed)
                with self.assertRaises(planning.PlanningError):
                    planning.validate_compilation(changed, method, self.assets, self.brief)
        incomplete = self.compile(method=method, assets=self.assets[:1])
        with self.assertRaises(planning.PlanningError):
            planning.validate_compilation(incomplete, method, self.assets[:1], self.brief)


if __name__ == '__main__':
    unittest.main()
