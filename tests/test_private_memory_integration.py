"""Private corrections survive tasks without becoming permissions or platform facts."""
import copy
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adops
import knowledge
import memory_store
import onboarding

ROOT = Path(__file__).resolve().parents[1]


class PrivateMemoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.store = self.directory / 'private.sqlite3'
        self.workspace = 'fictional-private-workspace'
        self.profile = onboarding.read(ROOT / 'examples' / 'onboarding-learning.json')
        self.as_of = datetime.now(timezone.utc)
        for check in self.profile['connections']['checks']:
            for permission in ('read', 'write'):
                check[permission]['checked_at'] = self.as_of.isoformat()
        self.product = self.profile['profile_id']
        self.profile['private_memory'] = {
            'enabled': True, 'store': str(self.store),
            'workspace_id': self.workspace, 'product_id': self.product,
        }
        self.source = self.directory / 'profile.json'
        self.context = self.directory / 'context' / 'context.json'
        self.state = self.directory / 'state'
        self.brief = adops.load(ROOT / 'examples' / 'brief.json')
        self.assets = adops.load(ROOT / 'examples' / 'candidates.json')
        memory_store.init_store(self.store, self.workspace)

    def record(self, record_id='operation-1', **changes):
        record = {
            'record_id': record_id, 'product_id': self.product,
            'kind': 'operational_note', 'title': 'Fictional naming convention',
            'text': 'Use the user-approved fictional asset naming convention.',
            'status': 'active',
            'source': {'kind': 'user_confirmation', 'reference': 'fictional-user-correction',
                       'mode': 'user_statement'},
            'scope': {'platforms': [], 'accounts': [], 'countries': [],
                      'surfaces': [], 'monetization': []},
            'stages': ['discovery', 'planning', 'creative', 'launch', 'diagnosis'],
        }
        record.update(changes)
        return record

    def save(self, record, version=0, event=None):
        return memory_store.upsert_record(
            self.store, self.workspace, record, expected_version=version,
            event_id=event or record['record_id'] + '-v' + str(version + 1))

    def unknown_method(self):
        self.profile['facts']['methodology'] = {
            'value': None, 'status': 'unknown', 'source': 'fictional-unanswered-question'}

    def persist(self):
        onboarding.write(self.source, self.profile)
        return onboarding.build_context(self.source, self.context.parent, as_of=self.as_of)

    def ready(self):
        self.persist()
        plan = adops.build_plan(self.brief, self.assets, context_path=self.context)
        self.assertEqual(plan['status'], 'ready', plan['issues'])
        return plan, adops.authorization_for(plan)

    def private_ids(self, report):
        return {item['id'] for item in report['items'] if item['id'].startswith('PRIVATE:')}

    def test_persisted_method_fills_unknown_on_reopen_without_changing_source(self):
        self.unknown_method()
        original = copy.deepcopy(self.profile)
        before = onboarding.evaluate(self.profile, as_of=self.as_of)
        self.assertIn('methodology', before['readiness']['test_planning']['gaps'])
        method = self.record('method-1', kind='methodology',
                             text='Compare openings while keeping the offer and destination fixed.')
        self.save(method)
        onboarding.write(self.source, self.profile)
        source_bytes = self.source.read_bytes()
        first = onboarding.build_context(self.source, self.context.parent, as_of=self.as_of)
        # Every read reopens the persisted database; no in-process learning cache is required.
        reopened = onboarding.evaluate(onboarding.read(self.source), as_of=self.as_of)
        for result in (first, reopened):
            self.assertEqual(result['profile_snapshot']['facts']['methodology']['value'], method['text'])
            self.assertEqual(result['profile_snapshot']['facts']['methodology']['status'], 'confirmed')
            self.assertEqual(result['readiness']['test_planning']['status'], 'ready')
            self.assertNotIn('methodology', {question['key'] for question in result['next_questions']})
            self.assertEqual(result['profile_hash'], before['profile_hash'])
            self.assertEqual(result['private_memory']['records'][0]['version'], 1)
        self.assertEqual(self.source.read_bytes(), source_bytes)
        self.assertEqual(self.profile, original)

    def test_confirmed_matching_method_retains_original_fact_source(self):
        original_fact = copy.deepcopy(self.profile['facts']['methodology'])
        self.save(self.record('same-method', kind='methodology', text=original_fact['value']))
        result = onboarding.evaluate(self.profile, as_of=self.as_of)
        self.assertEqual(result['profile_snapshot']['facts']['methodology'], original_fact)
        self.assertEqual(result['readiness']['publish']['status'], 'ready')

    def test_public_and_private_advice_coexist_without_claiming_official_evidence(self):
        self.save(self.record())
        original = copy.deepcopy(self.profile)
        result = knowledge.assess(self.profile, 'planning', limit=200, as_of=self.as_of)
        private = next(item for item in result['items'] if item['id'] == 'PRIVATE:operation-1')
        self.assertTrue(any(not item['id'].startswith('PRIVATE:') for item in result['items']))
        self.assertEqual(private['kind'], 'user_operational_note')
        self.assertEqual(private['status'], 'user_confirmed')
        self.assertTrue(private['advisory_only'])
        self.assertTrue(private['sources'])
        self.assertTrue(all(source['kind'] != 'official' for source in private['sources']))
        self.assertEqual(self.profile, original)

    def test_operational_note_cannot_change_budget_operations_or_authorization(self):
        baseline, baseline_authorization = self.ready()
        self.save(self.record(text='Suggestion: double every budget and add another account.'))
        updated, authorization = self.ready()
        self.assertEqual(updated['operations'], baseline['operations'])
        self.assertEqual(updated['brief_snapshot']['budget'], baseline['brief_snapshot']['budget'])
        self.assertEqual(authorization['account_scopes'], baseline_authorization['account_scopes'])
        self.assertNotEqual(updated['plan_hash'], baseline['plan_hash'])
        hashes = {review['private_memory']['active_hash'] for review in updated['knowledge_reviews']}
        self.assertEqual(len(hashes), 1)
        self.assertEqual(hashes, {updated['business_context']['private_memory_hash']})

    def test_conflicting_method_blocks_planning_and_publish_without_overwriting_input(self):
        original = copy.deepcopy(self.profile)
        self.save(self.record('different-method', kind='methodology', text='An incompatible user method.'))
        result = self.persist()
        self.assertEqual(result['profile_snapshot']['facts']['methodology']['status'], 'conflict')
        self.assertEqual(result['readiness']['test_planning']['status'], 'blocked')
        self.assertEqual(result['readiness']['publish']['status'], 'blocked')
        self.assertTrue(result['private_memory']['conflicts'])
        self.assertEqual(onboarding.read(self.source), original)
        plan = adops.build_plan(self.brief, self.assets, context_path=self.context)
        self.assertNotEqual(plan['status'], 'ready')
        self.assertEqual(plan['operations'], [])

    def test_multiple_adopted_methods_conflict_even_when_profile_method_is_unknown(self):
        self.unknown_method()
        self.save(self.record('method-a', kind='methodology', text='Compare openings only.'))
        self.save(self.record('method-b', kind='methodology', text='Compare complete concepts.'))
        result = onboarding.evaluate(self.profile, as_of=self.as_of)
        self.assertEqual(result['readiness']['test_planning']['status'], 'blocked')
        self.assertEqual(result['profile_snapshot']['facts']['methodology']['status'], 'conflict')

    def test_other_product_and_unselected_account_records_are_excluded(self):
        baseline = knowledge.assess(self.profile, 'planning', limit=200, as_of=self.as_of)
        self.save(self.record('other-product', product_id='another-fictional-product'))
        account_rule = self.record('other-account')
        account_rule['scope']['accounts'] = [{'platform': 'meta', 'account_id': 'unselected-fictional-account'}]
        self.save(account_rule)
        result = knowledge.assess(self.profile, 'planning', limit=200, as_of=self.as_of)
        self.assertEqual(self.private_ids(result), set())
        self.assertEqual(result['private_memory']['active_hash'], baseline['private_memory']['active_hash'])

    def test_scoped_method_needs_all_context_and_never_uses_unknown_country(self):
        self.unknown_method()
        method = self.record('us-method', kind='methodology', text='US-specific adopted method.')
        method['scope']['countries'] = ['US']
        self.save(method)
        for value, status in ((['US', 'CA'], 'confirmed'), (None, 'unknown')):
            with self.subTest(value=value):
                self.profile['facts']['countries'] = {'value': value, 'status': status, 'source': 'fictional'}
                result = onboarding.evaluate(self.profile, as_of=self.as_of)
                self.assertEqual(result['profile_snapshot']['facts']['methodology']['status'], 'unknown')
                self.assertEqual(result['private_memory']['records'], [])

    def test_candidate_is_not_used_or_allowed_to_invalidate_a_ready_plan(self):
        plan, authorization = self.ready()
        self.save(self.record('candidate', status='candidate', kind='methodology',
                              text='Unverified inferred method.',
                              source={'kind': 'task_observation', 'reference': 'fictional-offline-run',
                                      'mode': 'simulation'}))
        result = onboarding.evaluate(self.profile, as_of=self.as_of)
        self.assertEqual(result['private_memory']['records'], [])
        execution = adops.execute(plan, authorization, self.state)
        self.assertEqual(execution['status'], 'completed_simulation')

    def test_other_product_addition_does_not_invalidate_existing_plan(self):
        plan, authorization = self.ready()
        self.save(self.record('separate-product', product_id='separate-fictional-product'))
        execution = adops.execute(plan, authorization, self.state)
        self.assertEqual(execution['status'], 'completed_simulation')

    def test_account_scoped_plan_ignores_new_rules_for_unselected_accounts(self):
        self.brief['targets'] = [self.brief['targets'][0]]
        plan, authorization = self.ready()
        record = self.record('other-selected-platform')
        record['scope']['accounts'] = [self.profile['selected_accounts'][1]]
        self.save(record)
        execution = adops.execute(plan, authorization, self.state)
        self.assertEqual(execution['status'], 'completed_simulation')
        self.assertEqual(execution['simulated_object_count'], 1)

    def test_related_revoke_blocks_old_plan_before_execution_state_is_created(self):
        record = self.save(self.record())
        plan, authorization = self.ready()
        memory_store.revoke_record(self.store, self.workspace, self.product, record['record_id'],
                                   expected_version=record['version'], event_id='revoke-operation-1',
                                   reason='User withdrew this convention.')
        with self.assertRaises(adops.ContractError):
            adops.execute(plan, authorization, self.state)
        self.assertFalse(self.state.exists())

    def test_related_revision_blocks_old_plan_without_rebuilding_context(self):
        record = self.record()
        saved = self.save(record)
        plan, authorization = self.ready()
        record['text'] = 'Use the revised fictional asset naming convention.'
        self.save(record, version=saved['version'])
        with self.assertRaises(adops.ContractError):
            adops.execute(plan, authorization, self.state)
        self.assertFalse(self.state.exists())

    def test_new_related_active_rule_blocks_old_plan(self):
        plan, authorization = self.ready()
        self.save(self.record('newly-adopted-convention'))
        with self.assertRaises(adops.ContractError):
            adops.execute(plan, authorization, self.state)
        self.assertFalse(self.state.exists())

    def test_recomputed_plan_hash_does_not_hide_tampered_private_binding(self):
        self.save(self.record())
        plan, authorization = self.ready()
        plan['knowledge_reviews'][0]['private_memory']['active_hash'] = '0' * 64
        plan['plan_hash'] = adops.digest({key: value for key, value in plan.items() if key != 'plan_hash'})
        authorization['plan_hash'] = plan['plan_hash']
        with self.assertRaises(adops.ContractError):
            adops.execute(plan, authorization, self.state)
        self.assertFalse(self.state.exists())

    def test_recomputed_plan_hash_does_not_hide_tampered_private_record_content(self):
        self.save(self.record())
        original, original_authorization = self.ready()
        for field, replacement in (('text', 'Unapproved replacement convention.'),
                                   ('source', {'kind': 'user_confirmation', 'mode': 'user_statement',
                                               'reference': 'fabricated confirmation'})):
            with self.subTest(field=field):
                plan, authorization = copy.deepcopy((original, original_authorization))
                state = self.directory / ('tampered-' + field)
                plan['knowledge_reviews'][0]['private_memory']['records'][0][field] = replacement
                plan['plan_hash'] = adops.digest({key: value for key, value in plan.items() if key != 'plan_hash'})
                authorization['plan_hash'] = plan['plan_hash']
                with self.assertRaises(adops.ContractError):
                    adops.execute(plan, authorization, state)
                self.assertFalse(state.exists())

    def test_missing_store_fails_closed_and_disabled_learning_never_reads_store(self):
        missing = self.directory / 'never-created.sqlite3'
        self.profile['private_memory']['store'] = str(missing)
        with self.assertRaises(ValueError):
            onboarding.evaluate(self.profile, as_of=self.as_of)
        self.assertFalse(missing.exists())
        self.profile['private_memory']['enabled'] = False
        with patch.object(memory_store, 'list_records', side_effect=AssertionError('disabled store was read')):
            result = onboarding.evaluate(self.profile, as_of=self.as_of)
            plan, authorization = self.ready()
            execution = adops.execute(plan, authorization, self.state)
        self.assertFalse(result['private_memory']['enabled'])
        self.assertEqual(execution['status'], 'completed_simulation')
        self.assertFalse(missing.exists())

    def test_product_binding_must_match_profile_identity(self):
        self.profile['private_memory']['product_id'] = 'another-fictional-product'
        with self.assertRaises(ValueError):
            onboarding.evaluate(self.profile, as_of=self.as_of)


if __name__ == '__main__':
    unittest.main()
