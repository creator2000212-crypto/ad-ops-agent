"""Integration contracts for connection-first, then collaboration onboarding."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import onboarding

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ('discovery', 'material_selection', 'test_planning', 'publish')


class SetupFlowTests(unittest.TestCase):
    def setUp(self):
        self.as_of = datetime.now(timezone.utc)
        self.profile = onboarding.read(ROOT / 'examples' / 'onboarding-learning.json')
        for check in self.profile['connections']['checks']:
            for permission in ('read', 'write'):
                check[permission]['checked_at'] = self.as_of.isoformat()
        self.profile['setup_preferences'] = {'route': 'existing'}
        self.profile['collaboration'] = {
            'approach': 'bring_own',
            'current_need': 'Prepare the fictional creative test using my existing method',
            'experience_by_platform': {'meta': 'experienced', 'tiktok': 'unknown', 'google': 'unknown'},
        }
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'profile.json'
        self.output = Path(self.temp.name) / 'context'

    def evaluate(self, **kwargs):
        return onboarding.evaluate(self.profile, as_of=self.as_of, **kwargs)

    def unknown_fact(self, key):
        self.profile['facts'][key] = {'value': None, 'status': 'unknown', 'source': 'fictional_fixture_only'}

    def run_cli(self):
        onboarding.write(self.source, self.profile)
        return subprocess.run(
            [sys.executable, str(ROOT / 'onboarding.py'), '--input', str(self.source), '--out', str(self.output)],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )

    def assert_setup_artifacts(self):
        for name in ('setup.json', 'setup.md', 'questions.json', 'context.json'):
            with self.subTest(artifact=name):
                self.assertTrue((self.output / name).is_file())
        context = onboarding.read(self.output / 'context.json')
        setup = onboarding.read(self.output / 'setup.json')
        self.assertEqual(setup['connection_gate'], context['connection_gate'])
        self.assertEqual(setup['guidance'], context['guidance'])
        return context

    def test_read_and_write_are_prerequisites_for_every_workflow(self):
        original = copy.deepcopy(self.profile)
        for permission in ('read', 'write'):
            for fault in ('absent', 'unknown', 'expired'):
                for workflow in WORKFLOWS:
                    with self.subTest(permission=permission, fault=fault, workflow=workflow):
                        self.profile = copy.deepcopy(original)
                        self.profile.pop('collaboration')
                        self.unknown_fact('product_name')
                        check = self.profile['connections']['checks'][0]
                        if fault == 'absent':
                            check.pop(permission)
                        elif fault == 'unknown':
                            check[permission] = {'status': 'unknown', 'scopes': []}
                        else:
                            check[permission]['checked_at'] = (self.as_of - timedelta(hours=25)).isoformat()
                        result = self.evaluate(workflow=workflow)
                        expected = 'blocked' if fault == 'expired' else 'needs_input'
                        key = f"connections.{check['platform']}.{check['account_id']}.{permission}"
                        self.assertEqual(result['connection_gate']['status'], expected)
                        self.assertIn(key, result['connection_gate']['gaps'])
                        self.assertEqual(result['connection_gate']['mode'], 'simulation')
                        self.assertEqual(result['guidance']['stage'], 'connection_setup')
                        self.assertEqual(result['next_questions'], [])
                        self.assertEqual(result['knowledge_review']['items'], [])
                        self.assertIn(key, {action['key'] for action in result['machine_actions']})
                        for state in result['readiness'].values():
                            self.assertEqual(state['status'], expected)
                            self.assertIn(key, state['gaps'])

    def test_no_selected_accounts_defers_the_interview(self):
        self.profile['selected_accounts'] = []
        self.profile.pop('collaboration')
        result = self.evaluate()
        self.assertEqual(result['connection_gate']['status'], 'needs_input')
        self.assertEqual(result['connection_gate']['selected_accounts'], [])
        self.assertIn('selected_accounts', result['connection_gate']['gaps'])
        self.assertEqual(result['guidance']['stage'], 'connection_setup')
        self.assertEqual(result['next_questions'], [])
        self.assertEqual(result['knowledge_review']['items'], [])
        self.assertIn('resolve_selected_accounts', {action['action'] for action in result['machine_actions']})
        self.assertTrue(all(state['status'] != 'ready' for state in result['readiness'].values()))

    def test_valid_connection_does_not_need_business_facts_first(self):
        self.profile['facts'] = {}
        self.profile.pop('collaboration')
        result = self.evaluate()
        self.assertEqual(result['connection_gate']['status'], 'ready_simulation')
        self.assertEqual(result['connection_gate']['selected_accounts'], self.profile['selected_accounts'])
        self.assertEqual(result['guidance']['stage'], 'collaboration_intake')
        self.assertEqual(
            {question['key'] for question in result['next_questions']},
            {'collaboration.approach', 'collaboration.current_need', 'collaboration.experience_by_platform'},
        )
        self.assertEqual(result['machine_actions'], [])
        self.assertEqual(result['knowledge_review']['items'], [])
        self.assertTrue(all(state['status'] == 'needs_input' for state in result['readiness'].values()))

    def test_collaboration_questions_precede_business_questions_for_every_workflow(self):
        self.profile.pop('collaboration')
        self.unknown_fact('product_name')
        self.unknown_fact('methodology')
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow):
                result = self.evaluate(workflow=workflow)
                keys = {question['key'] for question in result['next_questions']}
                self.assertEqual(keys, {'collaboration.approach', 'collaboration.current_need', 'collaboration.experience_by_platform'})
                self.assertLessEqual(len(result['next_questions']), 3)
                self.assertEqual(result['knowledge_review']['items'], [])
                self.assertTrue(all(state['status'] == 'needs_input' for state in result['readiness'].values()))
                self.assertEqual(result['guidance']['stage'], 'collaboration_intake')

    def test_answered_collaboration_fields_are_not_asked_again(self):
        self.profile['collaboration'] = {'approach': 'guided'}
        self.unknown_fact('product_name')
        first = self.evaluate()
        self.assertEqual([question['key'] for question in first['next_questions']],
                         ['collaboration.current_need', 'collaboration.experience_by_platform'])
        second = self.evaluate(asked_questions=first['question_progress']['asked_questions'])
        self.assertEqual(second['next_questions'], [])
        self.assertIn('collaboration.current_need', second['question_progress']['unresolved'])
        self.assertEqual(second['guidance']['stage'], 'collaboration_intake')
        self.assertTrue(all(state['status'] == 'needs_input' for state in second['readiness'].values()))
        self.assertEqual(first['profile_hash'], second['profile_hash'])

    def test_business_intake_resumes_workflow_specific_dependencies(self):
        self.unknown_fact('countries')
        self.unknown_fact('methodology')
        result = self.evaluate(workflow='material_selection')
        self.assertEqual(result['connection_gate']['status'], 'ready_simulation')
        self.assertEqual(result['guidance']['stage'], 'business_intake')
        self.assertEqual(result['readiness']['discovery']['status'], 'ready')
        self.assertEqual(result['readiness']['material_selection']['status'], 'needs_input')
        self.assertEqual([question['key'] for question in result['next_questions']], ['countries'])
        self.assertEqual(result['machine_actions'], [])

    def test_optional_familiarity_does_not_block_progress_after_core_intake(self):
        self.profile['collaboration'] = {'approach': 'guided', 'current_need': 'Prepare a fictional test'}
        result = self.evaluate()
        self.assertEqual(result['guidance']['stage'], 'business_intake')
        self.assertTrue(all(state['status'] == 'ready' for state in result['readiness'].values()))
        self.assertEqual(result['next_questions'], [])

    def test_guided_intake_requests_a_method_without_confirming_one(self):
        self.profile['collaboration']['approach'] = 'guided'
        self.unknown_fact('methodology')
        before = copy.deepcopy(self.profile)
        result = self.evaluate(workflow='test_planning')
        self.assertEqual(result['connection_gate']['status'], 'ready_simulation')
        self.assertEqual(result['guidance']['stage'], 'business_intake')
        self.assertEqual(result['readiness']['test_planning']['status'], 'needs_input')
        self.assertEqual(result['guidance']['method_requirement']['state'], 'proposal_needed')
        question = next(item for item in result['next_questions'] if item['key'] == 'methodology')
        guided_question = next(item for item in result['guidance']['questions'] if item['key'] == 'methodology')
        self.assertEqual(question['question'], guided_question['question'])
        self.assertNotEqual(question['question'], onboarding.QUESTIONS['methodology'])
        self.assertEqual(self.profile, before)
        self.assertEqual(result['profile_snapshot']['facts']['methodology']['status'], 'unknown')
        self.assertIsNone(result['profile_snapshot']['facts']['methodology']['value'])

    def test_bring_own_method_is_requested_without_a_default(self):
        self.unknown_fact('methodology')
        result = self.evaluate(workflow='test_planning')
        self.assertEqual(result['readiness']['test_planning']['status'], 'needs_input')
        self.assertEqual(result['guidance']['method_requirement']['state'], 'import_needed')
        question = next(item for item in result['next_questions'] if item['key'] == 'methodology')
        own_question = next(item for item in result['guidance']['questions'] if item['key'] == 'methodology')
        self.assertEqual(question['question'], own_question['question'])
        self.assertRegex(question['question'], '资料|文档|方法|链接')
        self.assertIsNone(result['profile_snapshot']['facts']['methodology']['value'])

    def test_commercial_preferences_do_not_grant_account_capabilities(self):
        self.profile['connections']['checks'][0]['write'] = {'status': 'unknown', 'scopes': []}
        before = self.evaluate()
        self.profile['setup_preferences'] = {
            'route': 'pipeboard',
            'visited_url': 'https://example.invalid/fictional-affiliate-link',
            'purchased': True,
        }
        self.profile['collaboration']['approach'] = 'guided'
        self.profile['collaboration']['experience_by_platform']['meta'] = 'new'
        after = self.evaluate()
        self.assertEqual(after['connection_gate'], before['connection_gate'])
        self.assertEqual(after['connection_results'], before['connection_results'])
        self.assertEqual(after['readiness'], before['readiness'])
        self.assertEqual(after['guidance']['stage'], 'connection_setup')
        self.assertEqual(after['next_questions'], [])
        self.assertEqual(after['profile_snapshot']['connections']['checks'][0]['write']['status'], 'unknown')

    def test_valid_existing_route_is_not_promoted_again(self):
        result = self.evaluate()
        self.assertEqual(result['connection_gate']['status'], 'ready_simulation')
        self.assertIsNone(result['guidance']['recommendation'])
        self.assertTrue(all(state['status'] == 'ready' for state in result['readiness'].values()))

    def test_unselected_account_failure_does_not_block_the_scoped_workflow(self):
        bad_check = self.profile['connections']['checks'][2]
        bad_check['read'] = {'status': 'unknown', 'scopes': []}
        bad_check['write'] = {'status': 'unknown', 'scopes': []}
        self.assertEqual(self.evaluate()['connection_gate']['status'], 'needs_input')
        scope = [self.profile['selected_accounts'][0]]
        scoped = self.evaluate(account_scope=scope)
        self.assertEqual(scoped['connection_gate']['status'], 'ready_simulation')
        self.assertEqual(scoped['connection_gate']['selected_accounts'], scope)
        self.assertTrue(all(state['status'] == 'ready' for state in scoped['readiness'].values()))
        self.assertIsNone(scoped['guidance']['recommendation'])
        onboarding.write(self.source, self.profile)
        onboarding.build_context(self.source, self.output, as_of=self.as_of)
        binding = onboarding.validate_context(self.output / 'context.json', targets=scope, as_of=self.as_of)
        self.assertEqual(binding['profile_hash'], scoped['profile_hash'])

    def test_blocked_setup_cli_still_writes_reviewable_guidance(self):
        self.profile['connections']['checks'] = []
        self.profile.pop('collaboration')
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(completed.stderr, '')
        output = json.loads(completed.stdout)
        self.assertEqual(output['guidance']['stage'], 'connection_setup')
        context = self.assert_setup_artifacts()
        self.assertEqual(context['connection_gate']['status'], 'needs_input')
        questions = onboarding.read(self.output / 'questions.json')
        self.assertEqual(questions['next_questions'], [])
        self.assertTrue(questions['machine_actions'])
        self.assertIn('connection_setup', (self.output / 'setup.md').read_text(encoding='utf-8'))

    def test_connected_business_intake_cli_succeeds_with_unresolved_facts(self):
        self.unknown_fact('product_name')
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertEqual(output['connection_gate']['status'], 'ready_simulation')
        self.assertEqual(output['guidance']['stage'], 'business_intake')
        self.assertEqual(output['readiness']['test_planning']['status'], 'needs_input')
        context = self.assert_setup_artifacts()
        self.assertIn('product_name', {question['key'] for question in context['next_questions']})

    def test_connected_collaboration_intake_cli_remains_incomplete(self):
        self.profile.pop('collaboration')
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 2, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertEqual(output['connection_gate']['status'], 'ready_simulation')
        self.assertEqual(output['guidance']['stage'], 'collaboration_intake')
        self.assert_setup_artifacts()


if __name__ == '__main__':
    unittest.main()
