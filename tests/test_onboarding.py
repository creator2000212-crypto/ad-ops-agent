import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adops
import onboarding

ROOT = Path(__file__).resolve().parents[1]


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.as_of = datetime.now(timezone.utc)
        self.profile = onboarding.read(ROOT / 'examples' / 'onboarding-learning.json')
        for check in self.profile['connections']['checks']:
            for permission in ('read', 'write'):
                check[permission]['checked_at'] = self.as_of.isoformat()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source.json'
        self.output = Path(self.temp.name) / 'context'

    def fact(self, key, value, status='confirmed'):
        self.profile['facts'][key] = {'value': value, 'status': status, 'source': 'fictional_test_source'}

    def evaluate(self):
        return onboarding.evaluate(self.profile, as_of=self.as_of)

    def persist(self):
        onboarding.write(self.source, self.profile)
        onboarding.build_context(self.source, self.output)
        return self.output / 'context.json'

    def test_unknown_ltv_stays_unknown_without_blocking_learning(self):
        result = self.evaluate()
        self.assertIsNone(result['profile_snapshot']['facts']['ltv']['value'])
        self.assertEqual(result['profile_snapshot']['facts']['ltv']['status'], 'unknown')
        for state in result['readiness'].values():
            self.assertEqual(state['status'], 'ready')
        self.assertTrue(any(g['key'] == 'ltv' and not g['required_by'] for g in result['gaps']))
        self.assertEqual(result['next_questions'], [])

    def test_app_only_branch_allows_firebase_without_commercial_mmp(self):
        web = self.evaluate()
        self.assertFalse({'os', 'store', 'measurement_stack'} & {g['key'] for g in web['gaps']})
        self.fact('surface', 'app')
        app = self.evaluate()
        self.assertEqual(app['readiness']['material_selection']['status'], 'ready')
        self.assertIn('measurement_stack', app['readiness']['test_planning']['gaps'])
        for key, value in {'os': ['android'], 'store': 'virtual://fictional-store', 'measurement_stack': 'Firebase'}.items():
            self.fact(key, value)
        self.assertEqual(self.evaluate()['readiness']['publish']['status'], 'ready')

    def test_iaa_iap_hybrid_revenue_dependencies_are_conditional(self):
        models = {'iaa': {'ad_revenue_event', 'ad_revenue_window'},
                  'iap': {'purchase_revenue_event', 'refund_policy'},
                  'hybrid': {'ad_revenue_event', 'ad_revenue_window', 'purchase_revenue_event', 'refund_policy'},
                  'subscription': {'subscription_revenue_event', 'refund_policy'},
                  'ecommerce': {'purchase_revenue_event', 'refund_policy'}}
        for model, expected in models.items():
            with self.subTest(model=model):
                self.fact('monetization', model)
                self.fact('goal_type', 'learning')
                learning = self.evaluate()
                self.assertEqual(learning['readiness']['publish']['status'], 'ready')
                self.fact('goal_type', 'revenue')
                revenue = self.evaluate()
                self.assertTrue(expected.issubset(set(revenue['readiness']['publish']['gaps'])))
                self.assertEqual(revenue['readiness']['material_selection']['status'], 'ready')
        self.fact('monetization', 'leadgen')
        self.fact('goal_type', 'conversion')
        self.assertTrue({'lead_event', 'lead_qualification'}.issubset(self.evaluate()['readiness']['publish']['gaps']))

    def test_conflict_or_stale_blocks_only_dependent_workflows(self):
        for status in ('conflict', 'stale'):
            self.fact('countries', ['US'], status)
            result = self.evaluate()
            self.assertEqual(result['readiness']['publish']['status'], 'blocked')
            self.assertEqual(result['readiness']['discovery']['status'], 'ready')
        self.fact('countries', ['US'])
        self.fact('ltv', None, 'stale')
        self.assertEqual(self.evaluate()['readiness']['publish']['status'], 'ready')

    def test_discovered_connection_is_not_write_verification(self):
        self.profile['connections']['checks'][0]['write'] = {'status': 'unknown', 'scopes': []}
        result = self.evaluate()
        self.assertEqual(result['readiness']['test_planning']['status'], 'ready')
        self.assertEqual(result['readiness']['publish']['status'], 'needs_input')
        context = self.persist()
        saved = onboarding.read(context)
        saved['readiness']['publish'] = {'status': 'ready', 'gaps': []}
        onboarding.write(context, saved)
        with self.assertRaisesRegex(onboarding.OnboardingError, '未就绪'):
            onboarding.validate_context(context)

    def test_connection_freshness_future_and_scope_are_enforced(self):
        record = self.profile['connections']['checks'][0]['write']
        record['checked_at'] = (self.as_of - timedelta(hours=25)).isoformat()
        self.assertEqual(self.evaluate()['readiness']['publish']['status'], 'blocked')
        record['checked_at'] = (self.as_of + timedelta(seconds=1)).isoformat()
        future = self.evaluate()
        self.assertEqual(future['readiness']['publish']['status'], 'blocked')
        self.assertTrue(any('未来' in gap['reason'] for gap in future['gaps']))
        record['checked_at'] = self.as_of.isoformat()
        record['scopes'] = []
        self.assertEqual(self.evaluate()['readiness']['publish']['status'], 'needs_input')

    def test_questions_are_bounded_nonrepeating_and_do_not_change_business_hash(self):
        self.fact('surface', 'app')
        self.fact('audience', 'conflicting claims', 'conflict')
        first = self.evaluate()
        self.assertLessEqual(len(first['next_questions']), 3)
        self.assertEqual(first['next_questions'][0]['key'], 'audience')
        asked = first['question_progress']['asked_questions']
        second = onboarding.evaluate(self.profile, asked_questions=asked, as_of=self.as_of)
        self.assertFalse({q['key'] for q in first['next_questions']} & {q['key'] for q in second['next_questions']})
        self.assertTrue(set(asked).issubset(second['question_progress']['unresolved']))
        self.assertEqual(first['profile_hash'], second['profile_hash'])
        self.profile['asked_questions'] = asked
        self.assertEqual(first['profile_hash'], self.evaluate()['profile_hash'])

    def test_both_surface_is_explicitly_unsupported(self):
        self.fact('surface', 'both')
        result = self.evaluate()
        self.assertEqual(result['readiness']['publish']['status'], 'blocked')
        self.assertTrue(any(g['key'] == 'surface' and g['status'] == 'unsupported' for g in result['gaps']))

    def test_profile_change_invalidates_old_plan_even_without_rebuilding_context(self):
        context = self.persist()
        brief = adops.load(ROOT / 'examples' / 'brief.json')
        assets = adops.load(ROOT / 'examples' / 'candidates.json')
        plan = adops.build_plan(brief, assets, context_path=context)
        auth = adops.authorization_for(plan)
        self.profile['profile_version'] = '2'
        self.fact('creative_direction', 'a changed direction requiring review')
        onboarding.write(self.source, self.profile)
        with self.assertRaisesRegex(adops.ContractError, '改版'):
            adops.execute(plan, auth, Path(self.temp.name) / 'state')
        onboarding.build_context(self.source, self.output)
        with self.assertRaisesRegex(adops.ContractError, '改版'):
            adops.execute(plan, auth, Path(self.temp.name) / 'state')

    def test_brief_account_must_belong_to_context_and_old_plan_without_context_fails(self):
        context = self.persist()
        brief = adops.load(ROOT / 'examples' / 'brief.json')
        assets = adops.load(ROOT / 'examples' / 'candidates.json')
        self.assertEqual(adops.build_plan(brief, assets)['status'], 'needs_input')
        brief['targets'][0]['account_id'] = 'not_selected'
        plan = adops.build_plan(brief, assets, context_path=context)
        self.assertEqual(plan['status'], 'needs_input')
        self.assertTrue(any('选定范围' in issue['message'] for issue in plan['issues']))

    def test_current_workflow_ignores_unselected_accounts_write_problem(self):
        self.profile['connections']['checks'][2]['write'] = {'status': 'unknown'}
        context = self.persist()
        one_target = [self.profile['selected_accounts'][0]]
        binding = onboarding.validate_context(context, targets=one_target)
        self.assertEqual(binding['profile_hash'], self.evaluate()['profile_hash'])
        with self.assertRaises(onboarding.OnboardingError):
            onboarding.validate_context(context)

    def test_source_is_required_and_new_questions_persist_separately(self):
        self.fact('surface', 'app')
        context = self.persist()
        first = onboarding.read(self.output / 'questions.json')
        onboarding.build_context(self.source, self.output)
        second = onboarding.read(self.output / 'questions.json')
        self.assertFalse({q['key'] for q in first['next_questions']} & {q['key'] for q in second['next_questions']})
        self.source.unlink()
        with self.assertRaisesRegex(onboarding.OnboardingError, '来源无法读取'):
            onboarding.validate_context(context)

    def test_questions_follow_current_workflow_and_connection_gaps_are_machine_actions(self):
        self.fact('ltv', None, 'stale')
        self.fact('countries', None, 'unknown')
        self.fact('methodology', None, 'unknown')
        result = onboarding.evaluate(self.profile, as_of=self.as_of, workflow='material_selection')
        self.assertEqual([q['key'] for q in result['next_questions']], ['countries'])
        self.fact('countries', ['US'])
        self.fact('methodology', 'explicit testing method')
        self.profile['connections']['checks'][0]['write'] = {'status': 'unknown'}
        result = onboarding.evaluate(self.profile, as_of=self.as_of, workflow='publish')
        self.assertEqual(result['next_questions'], [])
        self.assertEqual(len(result['machine_actions']), 1)
        self.assertTrue(result['machine_actions'][0]['key'].endswith('.write'))
        self.assertTrue(any(g['key'] == 'ltv' for g in result['gaps']))

    def test_false_zero_empty_objects_and_invalid_sources_are_not_known_text(self):
        for value in (False, 0, {}, [], '', '  '):
            with self.subTest(value=value):
                self.fact('product_name', value)
                self.assertIn('product_name', self.evaluate()['readiness']['material_selection']['gaps'])
        self.fact('product_name', 'Fictional product')
        for source in (False, 0, {}, {'ref': ''}, ''):
            self.profile['facts']['product_name']['source'] = source
            self.assertIn('product_name', self.evaluate()['readiness']['material_selection']['gaps'])
        self.profile['facts']['product_name']['source'] = {'kind': 'fixture', 'ref': 'fictional-user-statement'}
        self.assertEqual(self.evaluate()['readiness']['material_selection']['status'], 'ready')

    def test_value_goal_can_use_observed_amounts_without_ltv_prediction(self):
        self.fact('goal_type', 'value')
        self.fact('monetization', 'iaa')
        self.fact('ad_revenue_event', 'fictional_ad_revenue')
        self.fact('ad_revenue_window', 'observed 7 days')
        self.fact('value_basis', 'Observed ad revenue amounts per recorded event; no LTV prediction')
        self.fact('value_window', 'observed 7-day value window')
        result = self.evaluate()
        self.assertIsNone(result['profile_snapshot']['facts']['ltv']['value'])
        self.assertEqual(result['readiness']['publish']['status'], 'ready')
        self.assertEqual(result['next_questions'], [])

    def test_refresh_only_copies_explicit_fixtures_and_does_not_grant_unknown_permissions(self):
        self.profile['connections']['checks'][0]['read']['checked_at'] = (self.as_of - timedelta(days=2)).isoformat()
        self.profile['connections']['checks'][0]['write'] = {'status': 'unknown', 'scopes': []}
        onboarding.write(self.source, self.profile)
        before = self.source.read_bytes()
        destination = Path(self.temp.name) / 'refreshed.json'
        result = onboarding.refresh_simulation_fixture(self.source, destination, as_of=self.as_of)
        self.assertEqual(result['mode'], 'simulation')
        self.assertEqual(self.source.read_bytes(), before)
        refreshed = onboarding.read(destination)
        self.assertEqual(refreshed['connections']['checks'][0]['read']['checked_at'], self.as_of.isoformat())
        self.assertEqual(refreshed['connections']['checks'][0]['write']['status'], 'unknown')
        with self.assertRaises(onboarding.OnboardingError):
            onboarding.refresh_simulation_fixture(self.source, self.source)
        self.profile['fixture_only'] = False
        onboarding.write(self.source, self.profile)
        with self.assertRaises(onboarding.OnboardingError):
            onboarding.refresh_simulation_fixture(self.source, destination)


if __name__ == '__main__':
    unittest.main()
