import copy
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adops
import knowledge
import onboarding

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 9, 24)


def fact(value, status='confirmed', source='fictional_test_evidence'):
    return {'value': value, 'status': status, 'source': source}


def catalog_fixture():
    """Small fictional corpus: tests should not depend on editorial knowledge IDs."""
    return {
        'schema_version': 1,
        'version': 'test-1',
        'sources': [{
            'id': 'official-test', 'title': 'Fictional official source',
            'url': 'https://example.invalid/official-test', 'kind': 'official',
            'checked_on': AS_OF.isoformat(), 'review_after_days': 30,
            'note': 'Test fixture; does not represent any real platform policy.',
        }],
        'entries': [{
            'id': 'TEST-001', 'title': 'Rejected creative investigation',
            'summary': 'Gather the observed rejection evidence before choosing a response.',
            'kind': 'platform_fact', 'stages': ['diagnosis'],
            'platforms': ['meta'], 'surfaces': ['all'], 'monetization': ['all'],
            'keywords': ['rejection', 'Creative'], 'required_facts': ['rejection_reason'],
            'triggers': [{'key': 'creative_rejected', 'equals': True}],
            'questions': [{'key': 'rejection_reason', 'question': 'What was the recorded reason?'}],
            'checks': ['Check the recorded reason.'],
            'actions': ['Prepare an evidence-backed review.'],
            'avoid': ['Do not infer permission or perform a write.'],
            'source_ids': ['official-test'], 'priority': 1,
        }],
    }


class KnowledgeRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.catalog = catalog_fixture()
        self.profile = {'facts': {'platforms': fact(['meta'])}}
        self.observations = {
            'creative_rejected': fact(True, status='observed'),
            'rejection_reason': fact('fictional review issue', status='observed'),
        }

    def assess(self, **kwargs):
        args = dict(profile=self.profile, stage='diagnosis', observations=self.observations,
                    catalog=self.catalog, as_of=AS_OF)
        args.update(kwargs)
        return knowledge.assess(**args)

    def test_matching_evidence_returns_source_backed_advice_without_mutating_inputs(self):
        before = copy.deepcopy((self.catalog, self.profile, self.observations))
        result = self.assess()
        self.assertTrue(result['advisory_only'])
        self.assertEqual(result['knowledge_version'], 'test-1')
        item = result['items'][0]
        self.assertEqual(item['status'], 'applicable')
        self.assertEqual(item['missing_facts'], [])
        self.assertEqual(item['scope_missing'], [])
        self.assertEqual(item['matched_triggers'][0]['key'], 'creative_rejected')
        self.assertEqual(item['sources'][0]['freshness'], 'current')
        self.assertEqual((self.catalog, self.profile, self.observations), before)

    def test_explicit_platform_surface_or_monetization_mismatch_is_excluded(self):
        cases = [
            ('platforms', ['meta'], 'platforms', ['google']),
            ('surfaces', ['app'], 'surface', 'web'),
            ('monetization', ['iap'], 'monetization', 'iaa'),
        ]
        for scope, allowed, key, value in cases:
            with self.subTest(scope=scope):
                corpus = catalog_fixture()
                corpus['entries'][0][scope] = allowed
                profile = copy.deepcopy(self.profile)
                profile['facts'][key] = fact(value)
                result = self.assess(profile=profile, catalog=corpus)
                self.assertEqual(result['items'], [])
                self.assertEqual(result['total_matches'], 0)

    def test_unknown_scope_remains_a_context_question_instead_of_an_applicable_rule(self):
        for value in (None, [], 'unrecognized-platform'):
            with self.subTest(value=value):
                result = self.assess(profile={'facts': {'platforms': fact(value)}})
                self.assertEqual(result['items'][0]['status'], 'needs_context')
                self.assertIn('platforms', result['items'][0]['scope_missing'])

    def test_explicit_false_and_numeric_zero_do_not_trigger_boolean_true_rule(self):
        for value in (False, 0, 1, 'true'):
            with self.subTest(value=value):
                observations = {**self.observations, 'creative_rejected': fact(value)}
                self.assertEqual(self.assess(observations=observations)['items'], [])
        self.catalog['entries'][0]['triggers'][0]['equals'] = False
        observations = {**self.observations, 'creative_rejected': fact(False)}
        self.assertEqual(self.assess(observations=observations)['items'][0]['status'], 'applicable')
        observations['creative_rejected'] = fact(0)
        self.assertEqual(self.assess(observations=observations)['items'], [])

    def test_unknown_trigger_is_missing_evidence_not_a_confirmed_match(self):
        observations = {'rejection_reason': self.observations['rejection_reason']}
        item = self.assess(observations=observations)['items'][0]
        self.assertEqual(item['status'], 'needs_evidence')
        self.assertIn('creative_rejected', item['missing_facts'])
        self.assertEqual(item['matched_triggers'], [])

    def test_hypotheses_stale_conflicting_and_unsourced_facts_do_not_satisfy_requirements(self):
        untrusted = [fact('reason', status=s) for s in ('hypothesis', 'unknown', 'conflict', 'stale')]
        untrusted += [fact('reason', source=s) for s in ('', '  ', {}, {'ref': ''})]
        untrusted += [fact(value) for value in (None, '', '  ', [], {})]
        for evidence in untrusted:
            with self.subTest(evidence=evidence):
                observations = {**self.observations, 'rejection_reason': evidence}
                item = self.assess(observations=observations)['items'][0]
                self.assertEqual(item['status'], 'needs_evidence')
                self.assertIn('rejection_reason', item['missing_facts'])

    def test_multiple_triggers_require_all_conditions(self):
        self.catalog['entries'][0]['triggers'].append({'key': 'review_completed', 'equals': True})
        observations = {**self.observations, 'review_completed': fact(False)}
        self.assertEqual(self.assess(observations=observations)['items'], [])
        item = self.assess()['items'][0]
        self.assertEqual(item['status'], 'needs_evidence')
        self.assertIn('review_completed', item['missing_facts'])

    def test_observation_cannot_silently_override_business_scope(self):
        observations = {**self.observations, 'platforms': fact(['google'])}
        with self.assertRaises(knowledge.KnowledgeError):
            self.assess(observations=observations)

    def test_expired_or_future_source_requires_review_even_with_complete_user_evidence(self):
        for checked_on, freshness in (('2026-08-01', 'review_due'), ('2026-09-25', 'future_date')):
            with self.subTest(checked_on=checked_on):
                self.catalog['sources'][0]['checked_on'] = checked_on
                item = self.assess()['items'][0]
                self.assertEqual(item['status'], 'needs_source_review')
                self.assertEqual(item['sources'][0]['freshness'], freshness)
                self.assertEqual(item['missing_facts'], [])

    def test_query_and_stage_filters_do_not_fall_back_to_unrelated_knowledge(self):
        self.assertEqual(self.assess(query='nonexistent-knowledge-term')['items'], [])
        self.assertEqual(self.assess(stage='launch')['items'], [])
        self.assertEqual(len(self.assess(query='CREATIVE absent-term')['items']), 1)

    def test_stable_limits_expose_omitted_matches(self):
        for number in (3, 2):
            entry = copy.deepcopy(self.catalog['entries'][0])
            entry['id'] = 'TEST-00' + str(number)
            self.catalog['entries'].append(entry)
        first = self.assess(limit=2)
        second = self.assess(limit=2)
        self.assertEqual(first, second)
        self.assertEqual(len(first['items']), 2)
        self.assertEqual(first['total_matches'], 3)
        self.assertTrue(first['truncated'])
        self.assertFalse(self.assess(limit=3)['truncated'])
        for limit in (0, -1, True, '2'):
            with self.subTest(limit=limit), self.assertRaises(knowledge.KnowledgeError):
                self.assess(limit=limit)

    def test_content_change_changes_catalog_hash_without_version_bump(self):
        original = self.assess()
        self.catalog['entries'][0]['summary'] += ' Updated evidence requirement.'
        revised = self.assess()
        self.assertEqual(original['knowledge_version'], revised['knowledge_version'])
        self.assertNotEqual(original['catalog_hash'], revised['catalog_hash'])

    def test_invalid_catalog_references_and_types_fail_closed(self):
        mutations = [
            lambda c: c['entries'].append(copy.deepcopy(c['entries'][0])),
            lambda c: c['sources'].append(copy.deepcopy(c['sources'][0])),
            lambda c: c['entries'][0].update(source_ids=['missing-source']),
            lambda c: c['sources'][0].update(kind='project'),
            lambda c: c['sources'][0].update(checked_on='2026-02-30'),
            lambda c: c['sources'][0].update(review_after_days=True),
            lambda c: c['sources'][0].update(review_after_days=0),
            lambda c: c['sources'][0].update(url='http://example.invalid/insecure'),
            lambda c: c['entries'][0].update(platforms=['all', 'meta']),
            lambda c: c['entries'][0].update(platforms=['unknown']),
            lambda c: c['entries'][0].update(stages=['auto_publish']),
            lambda c: c['entries'][0].update(triggers=[{'key': 'foo', 'equals': []}]),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                corpus = catalog_fixture()
                mutate(corpus)
                with self.assertRaises(knowledge.KnowledgeError):
                    self.assess(catalog=corpus)

    def test_loading_from_disk_enforces_same_catalog_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalog.json'
            path.write_text(json.dumps(self.catalog), encoding='utf-8')
            self.assertEqual(knowledge.load_catalog(path), self.catalog)
            self.catalog['entries'][0]['source_ids'] = ['missing-source']
            path.write_text(json.dumps(self.catalog), encoding='utf-8')
            with self.assertRaises(knowledge.KnowledgeError):
                knowledge.load_catalog(path)

    def test_bundled_catalog_is_loadable_and_each_entry_has_checkable_sources(self):
        corpus = knowledge.load_catalog()
        sources = {source['id'] for source in corpus['sources']}
        self.assertTrue(corpus['entries'])
        for entry in corpus['entries']:
            self.assertTrue(entry['source_ids'])
            self.assertTrue(set(entry['source_ids']) <= sources)


class KnowledgeRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.profile = onboarding.read(ROOT / 'examples' / 'onboarding-learning.json')
        for check in self.profile['connections']['checks']:
            for permission in ('read', 'write'):
                check[permission]['checked_at'] = datetime.now(timezone.utc).isoformat()
        self.profile_path = self.directory / 'profile.json'
        self.context_path = self.directory / 'context' / 'context.json'
        self.brief = adops.load(ROOT / 'examples' / 'brief.json')
        self.candidates = adops.load(ROOT / 'examples' / 'candidates.json')
        self.catalog = catalog_fixture()
        self.catalog['sources'][0]['checked_on'] = datetime.now(timezone.utc).date().isoformat()
        entry = self.catalog['entries'][0]
        entry.update(platforms=['all'], stages=['discovery', 'planning', 'creative', 'launch'],
                     triggers=[], required_facts=['optional_diagnostic_evidence'])

    def build(self):
        onboarding.write(self.profile_path, self.profile)
        context = onboarding.build_context(self.profile_path, self.context_path.parent)
        plan = adops.build_plan(self.brief, self.candidates, context_path=self.context_path)
        return context, plan

    def test_advisories_reach_onboarding_and_plan_without_changing_execution_decisions(self):
        with patch.object(knowledge, 'load_catalog', return_value=self.catalog):
            context, plan = self.build()
            self.assertEqual(plan['status'], 'ready')
            self.assertEqual(context['readiness']['test_planning']['status'], 'ready')
            self.assertEqual(context['knowledge_review']['items'][0]['status'], 'needs_evidence')
            self.assertEqual({r['stage'] for r in plan['knowledge_reviews']}, {'planning', 'creative', 'launch'})
            self.assertEqual(len(plan['operations']), len(self.brief['targets']))
            self.assertEqual(plan['brief_snapshot']['budget'], self.brief['budget'])
            auth = adops.authorization_for(plan)
            changed_catalog = copy.deepcopy(self.catalog)
            changed_catalog['entries'][0]['summary'] = 'A changed editorial recommendation.'
            with patch.object(knowledge, 'load_catalog', return_value=changed_catalog):
                _, revised = self.build()
            self.assertEqual(revised['operations'], plan['operations'])
            self.assertNotEqual(revised['plan_hash'], plan['plan_hash'])
            self.assertEqual(auth['plan_hash'], plan['plan_hash'])

    def test_catalog_revision_invalidates_previous_plan_and_authorization_before_execution(self):
        with patch.object(knowledge, 'load_catalog', return_value=self.catalog):
            _, plan = self.build()
            auth = adops.authorization_for(plan)
        revised = copy.deepcopy(self.catalog)
        revised['version'] = 'test-2'
        state = self.directory / 'state'
        with patch.object(knowledge, 'load_catalog', return_value=revised):
            with self.assertRaisesRegex(adops.ContractError, '知识库'):
                adops.execute(plan, auth, state)
        self.assertFalse(state.exists())

    def test_knowledge_cannot_bypass_missing_write_authorization(self):
        self.profile['connections']['checks'][0]['write']['status'] = 'unknown'
        with patch.object(knowledge, 'load_catalog', return_value=self.catalog):
            context, plan = self.build()
            self.assertEqual(plan['status'], 'needs_input')
            self.assertEqual(context['knowledge_review']['items'], [])
            self.assertEqual(plan['operations'], [])
            with self.assertRaises(adops.ContractError):
                adops.authorization_for(plan)

    def test_onboarding_question_explains_related_knowledge_without_claiming_the_fact(self):
        self.profile['facts']['product_name'] = fact(None, status='unknown')
        self.catalog['entries'][0]['required_facts'] = ['product_name']
        with patch.object(knowledge, 'load_catalog', return_value=self.catalog):
            result = onboarding.evaluate(self.profile)
        question = next(q for q in result['next_questions'] if q['key'] == 'product_name')
        self.assertIn('TEST-001', question['knowledge_refs'])
        self.assertIn(self.catalog['entries'][0]['summary'], question['why_it_matters'])
        self.assertEqual(result['profile_snapshot']['facts']['product_name']['status'], 'unknown')

    def test_plan_knowledge_is_scoped_to_selected_plan_targets(self):
        self.catalog['entries'][0]['platforms'] = ['google']
        self.brief['targets'] = [target for target in self.brief['targets'] if target['platform'] == 'meta']
        with patch.object(knowledge, 'load_catalog', return_value=self.catalog):
            context, plan = self.build()
        # The onboarding profile knows three platforms; this plan only chooses Meta.
        self.assertTrue(context['knowledge_review']['items'])
        self.assertEqual(plan['status'], 'ready')
        self.assertTrue(all(not review['items'] for review in plan['knowledge_reviews']))

    def test_review_tampering_is_detected_by_plan_hash_before_execution(self):
        with patch.object(knowledge, 'load_catalog', return_value=self.catalog):
            _, plan = self.build()
            auth = adops.authorization_for(plan)
            plan['knowledge_reviews'][0]['items'][0]['summary'] = 'Tampered advice'
            state = self.directory / 'state'
            with self.assertRaisesRegex(adops.ContractError, 'hash'):
                adops.execute(plan, auth, state)
            self.assertFalse(state.exists())


if __name__ == '__main__':
    unittest.main()
