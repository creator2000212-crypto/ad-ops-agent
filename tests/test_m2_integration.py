"""Six fictional businesses exercise the persistent method-to-plan workflow."""
import copy
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adops
from evaluations.fixtures import CASES, CASE_NAMES, build_case
import methodology
import onboarding
import task


class M2TaskIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def started(self, business='leadgen', approach='guided', name='test', language='en', template=None):
        case = build_case(business, approach, template)
        source = self.directory / (name + '-source.json')
        adops.save(source, case['profile'])
        root = self.directory / name
        result = task.start(source, root, language=language)
        return case, source, root, result

    def adopted(self, business='leadgen', approach='guided', name='test', language='en', template=None):
        case, source, root, _ = self.started(business, approach, name, language, template)
        proposal = task.propose(root, case['request'])
        candidate = proposal['candidates'][0]
        result = task.adopt_method(root, candidate['method_id'], 'fictional-user-adoption-' + name)
        self.assertEqual(result['method']['status'], 'adopted')
        return case, source, root, result

    def prepared(self, **kwargs):
        case, source, root, _ = self.adopted(**kwargs)
        result = task.prepare_plan(root, case['brief'], case['candidates'])
        self.assertEqual(result['plan']['status'], 'ready', result['plan']['issues'])
        plan = adops.load(result['plan']['reference'])
        return case, source, root, result, plan

    def test_six_fictional_cases_complete_adopt_prepare_interrupt_resume_without_changing_source(self):
        self.assertEqual(len(CASES), 6)
        self.assertEqual(len(set(CASE_NAMES)), 6)
        for index, (business, approach) in enumerate(CASES):
            with self.subTest(business=business, approach=approach):
                name = business + '_' + approach
                case, source, root, initial = self.started(business, approach, name,
                                                          language='zh-CN' if index % 2 == 0 else 'en')
                original = source.read_bytes()
                self.assertEqual(initial['stage'], 'method_proposal')
                self.assertNotIn('methodology', initial['known_facts'])
                proposal = task.propose(root, case['request'])
                self.assertEqual(proposal['stage'], 'method_review')
                self.assertEqual(proposal['candidates'][0]['status'], 'candidate')
                adopted = task.adopt_method(root, proposal['candidates'][0]['method_id'], 'fictional explicit approval')
                self.assertEqual(adopted['stage'], 'plan_preparation')
                result = task.prepare_plan(root, case['brief'], case['candidates'])
                self.assertEqual(result['plan']['status'], 'ready', result['plan']['issues'])
                plan = adops.load(result['plan']['reference'])
                expected = ['anchor', 'hook-b'] if approach == 'guided' else ['anchor', 'concept-b']
                self.assertEqual([asset['asset_id'] for asset in plan['test_plan']['selected_assets']], expected)
                self.assertEqual(plan['test_plan']['allocation']['mode'], 'shared_target_budget')
                self.assertEqual(len(plan['operations']), 3)
                for operation in plan['operations']:
                    self.assertEqual(operation['adapter'], 'simulation')
                    self.assertIsNone(operation['desired']['native_payload'])
                    self.assertEqual(operation['desired']['budget']['amount'], '30.00')
                    self.assertEqual(len(operation['desired']['test_design']['units']), 2)
                interrupted = task.simulate(root, interrupt_after_write=1)
                self.assertEqual(interrupted['status'], 'interrupted')
                self.assertEqual(task.status(root)['stage'], 'interrupted')
                resumed = task.simulate(root)
                self.assertEqual(resumed['status'], 'completed_simulation')
                self.assertEqual(resumed['created_this_run'], 2)
                self.assertEqual(resumed['simulated_object_count'], 3)
                again = task.simulate(root)
                self.assertEqual(again['created_this_run'], 0)
                self.assertEqual(task.status(root)['stage'], 'completed_simulation')
                database = Path(result['plan']['reference']).parent / 'state' / 'simulation.sqlite3'
                with sqlite3.connect(database) as connection:
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM events WHERE state='submitted'").fetchone()[0], 3)
                self.assertEqual(source.read_bytes(), original)
                self.assertEqual(onboarding.read(source)['facts']['methodology']['status'], 'unknown')

    def test_business_fixtures_have_distinct_products_and_required_measurement_dependencies(self):
        cases = [build_case(*identity) for identity in CASES]
        self.assertEqual(len({case['profile']['profile_id'] for case in cases}), 6)
        for case in cases:
            with self.subTest(product=case['profile']['profile_id']):
                result = onboarding.evaluate(case['profile'])
                self.assertEqual(result['connection_gate']['status'], 'ready_simulation')
                self.assertEqual(result['readiness']['publish']['gaps'], ['methodology'])
                self.assertEqual(case['profile']['facts']['ltv']['status'], 'unknown')
                self.assertTrue(case['profile']['fixture_only'])

    def test_fixed_conflicts_and_missing_identity_are_explained_after_full_pool_filtering(self):
        _, _, _, _, plan = self.prepared()
        decisions = {item['asset_id']: item for item in plan['asset_decisions']}
        self.assertEqual(decisions['wrong-destination']['status'], 'excluded')
        self.assertIn('destination', ' '.join(decisions['wrong-destination']['reasons']))
        self.assertEqual(decisions['unknown-identity']['status'], 'excluded')
        self.assertIn('test_identity', ' '.join(decisions['unknown-identity']['reasons']))
        self.assertEqual(decisions['anchor']['status'], 'selected')
        self.assertEqual(decisions['hook-b']['status'], 'selected')
        # These two valid selections occur beyond the old input-order count cutoff.
        self.assertEqual([item['asset_id'] for item in plan['operations'][0]['desired']['assets']], ['anchor', 'hook-b'])

    def test_method_correction_changes_selection_and_blocks_previous_plan(self):
        case, _, root, before, old_plan = self.prepared()
        old_authorization = adops.authorization_for(old_plan)
        corrected = build_case('leadgen', 'guided', template='concept_exploration')['request']
        proposal = task.propose(root, corrected)
        adopted = task.adopt_method(root, proposal['candidates'][0]['method_id'], 'fictional method correction')
        self.assertEqual(adopted['method']['revision'], 2)
        with self.assertRaises(adops.ContractError):
            adops.execute(old_plan, old_authorization, self.directory / 'old-state')
        self.assertFalse((self.directory / 'old-state').exists())
        self.assertFalse(task.status(root)['plan']['current'])
        result = task.prepare_plan(root, case['brief'], case['candidates'])
        plan = adops.load(result['plan']['reference'])
        self.assertEqual(plan['status'], 'ready')
        self.assertEqual([item['asset_id'] for item in plan['operations'][0]['desired']['assets']], ['anchor', 'concept-b'])
        self.assertNotEqual(plan['operations'][0]['desired']['test_design'], old_plan['operations'][0]['desired']['test_design'])
        self.assertNotEqual(result['plan']['reference'], before['plan']['reference'])
        self.assertEqual(adops.load(before['plan']['reference']), old_plan)

    def test_sop_unknown_rule_remains_visible_and_cannot_be_adopted(self):
        case, _, root, _ = self.started(approach='bring_own')
        unsupported = 'Budget: assign a guaranteed fixed budget to every unit'
        case['request']['source']['text'] += '\n' + unsupported
        result = task.propose(root, case['request'])
        candidate = result['candidates'][0]
        self.assertIn(unsupported, candidate['unsupported'])
        with self.assertRaises(ValueError):
            task.adopt_method(root, candidate['method_id'], 'fictional confirmation cannot erase unsupported rules')
        self.assertEqual(adops.load(root / 'task.json')['method_revision'], 0)
        self.assertFalse((root / 'methods').exists())

    def test_disconnected_profile_cannot_propose_a_method(self):
        case = build_case('app', 'guided')
        case['profile']['connections']['checks'][0]['write']['status'] = 'unknown'
        source = self.directory / 'disconnected.json'
        adops.save(source, case['profile'])
        root = self.directory / 'disconnected'
        self.assertEqual(task.start(source, root)['stage'], 'connection_setup')
        with self.assertRaises(task.TaskError):
            task.propose(root, case['request'])
        self.assertEqual(adops.load(root / 'task.json')['proposal_generation'], 0)
        self.assertFalse((root / 'proposals').exists())

    def test_profile_update_invalidates_existing_candidates(self):
        case, _, root, _ = self.started()
        proposed = task.propose(root, case['request'])
        changed = adops.load(root / 'profile.json')
        changed['facts']['countries']['value'] = ['CA']
        path = self.directory / 'changed-profile.json'
        adops.save(path, changed)
        result = task.update_profile(root, path)
        self.assertEqual(result['candidates'], [])
        with self.assertRaises(task.TaskError):
            task.adopt_method(root, proposed['candidates'][0]['method_id'], 'stale candidate approval')
        self.assertEqual(adops.load(root / 'task.json')['method_revision'], 0)

    def test_changed_candidate_content_cannot_reuse_previous_candidate_identity(self):
        case, _, root, _ = self.started()
        proposed = task.propose(root, case['request'])
        proposal_path = root / 'proposals' / 'generation-1.json'
        changed = adops.load(proposal_path)
        changed['candidates'][0]['question'] = 'A substituted question not in the recorded user request.'
        adops.save(proposal_path, changed)
        with self.assertRaises(ValueError):
            task.adopt_method(root, proposed['candidates'][0]['method_id'], 'original candidate confirmation')
        self.assertEqual(adops.load(root / 'task.json')['method_revision'], 0)

    def test_reproposal_with_changed_answers_cannot_accept_previous_candidate_id(self):
        case, _, root, _ = self.started()
        previous = task.propose(root, case['request'])['candidates'][0]
        request = copy.deepcopy(case['request'])
        request['answers']['question'] = 'Which opening should be reviewed in a different explicit comparison?'
        current = task.propose(root, request)['candidates'][0]
        self.assertEqual(current['source'], previous['source'])
        self.assertNotEqual(current['method_id'], previous['method_id'])
        with self.assertRaises(task.TaskError):
            task.adopt_method(root, previous['method_id'], 'confirmation referring to the previous candidate')
        self.assertEqual(adops.load(root / 'task.json')['method_revision'], 0)
        self.assertEqual(task.adopt_method(root, current['method_id'], 'current fictional confirmation')['method']['question'],
                         request['answers']['question'])

    def test_missing_business_fact_after_adoption_returns_to_intake(self):
        _, _, root, _ = self.adopted()
        changed = adops.load(root / 'profile.json')
        changed['facts']['audience'] = {'value': None, 'status': 'unknown', 'source': 'fictional unanswered audience'}
        path = self.directory / 'missing-business-fact.json'
        adops.save(path, changed)
        result = task.update_profile(root, path)
        self.assertEqual(result['method']['status'], 'adopted')
        self.assertIn('audience', result['readiness']['test_planning']['gaps'])
        self.assertEqual(result['stage'], 'business_intake')
        self.assertEqual(task.status(root)['stage'], 'business_intake')

    def test_profile_method_confirmation_hash_must_match_adopted_content(self):
        case, _, root, _ = self.adopted()
        profile = adops.load(root / 'profile.json')
        method_path = Path(profile['methodology_ref'])
        revised = adops.load(method_path)
        revised.update(status='candidate', confirmation=None)
        revised['question'] = 'A changed but separately confirmed fictional question.'
        revised = methodology.adopt(revised, 'a new explicit fictional method confirmation')
        adops.save(method_path, revised)
        original_hash = profile['facts']['methodology']['source']['method_hash']
        profile['facts']['methodology']['value'] = methodology.summary(revised)
        self.assertNotEqual(original_hash, methodology.digest(revised))
        # A fresh context avoids relying on the old profile hash to catch this mismatch.
        source = self.directory / 'stale-method-confirmation-profile.json'
        adops.save(source, profile)
        context_dir = self.directory / 'stale-method-confirmation-context'
        onboarding.build_context(source, context_dir)
        plan = adops.build_plan(case['brief'], case['candidates'], context_path=context_dir / 'context.json')
        self.assertNotEqual(plan['status'], 'ready')
        self.assertEqual(plan['operations'], [])
        with self.assertRaises(adops.ContractError):
            adops.verify_plan(plan)

    def test_string_method_source_reports_missing_binding_without_crashing(self):
        case, _, root, _ = self.adopted()
        changed = adops.load(root / 'profile.json')
        changed['facts']['methodology']['source'] = 'fictional user statement without structured method hash'
        path = self.directory / 'string-method-source.json'
        adops.save(path, changed)
        result = task.update_profile(root, path)
        self.assertEqual(result['stage'], 'business_intake')
        self.assertTrue(any('method_hash' in issue['path'] for issue in result['method_issues']))
        prepared = task.prepare_plan(root, case['brief'], case['candidates'])
        self.assertEqual(prepared['plan']['status'], 'needs_input')
        plan = adops.load(prepared['plan']['reference'])
        self.assertEqual(plan['operations'], [])
        self.assertTrue(any('method_hash' in issue['path'] for issue in plan['issues']))

    def test_completion_requires_receipts_and_current_simulated_object_evidence(self):
        for corruption in ('missing_receipts', 'empty_receipts', 'missing_database', 'object_drift'):
            with self.subTest(corruption=corruption):
                _, _, root, prepared, _ = self.prepared(name=corruption)
                self.assertEqual(task.simulate(root)['status'], 'completed_simulation')
                state = Path(prepared['plan']['reference']).parent / 'state'
                result_path = state / 'result.json'
                database = state / 'simulation.sqlite3'
                if corruption in ('missing_receipts', 'empty_receipts'):
                    result = adops.load(result_path)
                    if corruption == 'missing_receipts':
                        result.pop('receipts')
                    else:
                        result['receipts'] = []
                    adops.save(result_path, result)
                elif corruption == 'missing_database':
                    database.unlink()
                else:
                    with sqlite3.connect(database) as connection:
                        connection.execute("UPDATE simulated_objects SET payload='{}'")
                before = result_path.read_bytes()
                result = task.status(root)
                self.assertNotEqual(result['stage'], 'completed_simulation')
                self.assertNotEqual(result['plan'].get('simulation_status'), 'completed_simulation')
                self.assertEqual(result_path.read_bytes(), before)
                if corruption == 'missing_database':
                    self.assertFalse(database.exists(), 'Status must not recreate missing execution evidence.')

    def test_scope_update_blocks_old_plan_and_repreparation_with_old_method(self):
        case, _, root, _, old_plan = self.prepared(business='ecommerce')
        old_authorization = adops.authorization_for(old_plan)
        changed = adops.load(root / 'profile.json')
        changed['facts']['countries']['value'] = ['CA']
        path = self.directory / 'scope-update.json'
        adops.save(path, changed)
        result = task.update_profile(root, path)
        self.assertTrue(any(issue['code'] == 'scope_mismatch' for issue in result['method_issues']))
        with self.assertRaises(adops.ContractError):
            adops.execute(old_plan, old_authorization, self.directory / 'old-scope-state')
        prepared = task.prepare_plan(root, case['brief'], case['candidates'])
        plan = adops.load(prepared['plan']['reference'])
        self.assertNotEqual(plan['status'], 'ready')
        self.assertEqual(plan['operations'], [])
        self.assertTrue(any(issue['code'] == 'scope_mismatch' for issue in plan['issues']))

    def test_profile_bound_method_loads_without_flag_and_missing_file_does_not_downgrade(self):
        case, _, _, result, original = self.prepared()
        context = original['business_context']['reference']
        rebuilt = adops.build_plan(case['brief'], case['candidates'], context_path=context)
        self.assertEqual(rebuilt['status'], 'ready')
        self.assertEqual(rebuilt['test_plan'], original['test_plan'])
        Path(original['method_reference']['path']).unlink()
        missing = adops.build_plan(case['brief'], case['candidates'], context_path=context)
        self.assertNotEqual(missing['status'], 'ready')
        self.assertEqual(missing['operations'], [])
        with self.assertRaises(adops.ContractError):
            adops.verify_plan(original)

    def test_removing_method_fields_does_not_bypass_current_profile_binding(self):
        _, _, _, _, original = self.prepared()
        plan = copy.deepcopy(original)
        for key in ('test_plan', 'method_reference', 'candidates_snapshot'):
            plan.pop(key)
        for operation in plan['operations']:
            operation['desired'].pop('test_design')
        plan['plan_hash'] = adops.digest({key: value for key, value in plan.items() if key != 'plan_hash'})
        with self.assertRaises(adops.ContractError):
            adops.verify_plan(plan)

    def test_candidate_method_file_cannot_replace_adopted_binding(self):
        _, _, _, _, original = self.prepared()
        path = Path(original['method_reference']['path'])
        candidate = adops.load(path)
        candidate.update(status='candidate', confirmation=None)
        adops.save(path, candidate)
        with self.assertRaises(adops.ContractError):
            adops.verify_plan(original)

    def test_test_units_and_operations_are_recomputed_even_after_plan_hash_changes(self):
        _, _, _, _, original = self.prepared()
        mutations = [
            lambda plan: plan['test_plan']['units'][0].update(variable_value='invented-hook'),
            lambda plan: plan['operations'][0]['desired']['test_design']['units'][0].update(asset_ids=['unknown-identity']),
            lambda plan: plan['operations'][0]['desired']['assets'].reverse(),
            lambda plan: plan['operations'][0]['desired']['budget'].update(amount='1.00'),
            lambda plan: plan['test_plan']['allocation'].update(mode='fixed_per_unit_budget'),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                plan = copy.deepcopy(original)
                mutate(plan)
                plan['plan_hash'] = adops.digest({key: value for key, value in plan.items() if key != 'plan_hash'})
                with self.assertRaises(adops.ContractError):
                    adops.verify_plan(plan)


if __name__ == '__main__':
    unittest.main()
