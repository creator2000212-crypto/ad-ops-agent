import copy
from pathlib import Path
import sys
import unittest
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import guidance


class GuidanceTests(unittest.TestCase):
    def profile(self, approach='guided', current_need='先了解当前账户，再准备一次素材测试。'):
        return {'collaboration': {'approach': approach, 'current_need': current_need}}

    def test_connection_precedes_all_intake_even_with_existing_collaboration(self):
        for profile in ({}, self.profile(), self.profile('bring_own')):
            with self.subTest(profile=profile):
                result = guidance.evaluate(profile, connected=False)
                self.assertEqual(result['stage'], 'connection_setup')
                self.assertEqual(result['questions'], [])
                self.assertEqual(result['collaboration_summary'], {'status': 'deferred'})
                self.assertEqual(result['method_requirement']['state'], 'needs_choice')
                self.assertIsNone(result['familiarity_question'])
                self.assertTrue(result['setup_steps'])
                self.assertTrue(all(isinstance(step, str) and step.strip() for step in result['setup_steps']))

    def test_unconnected_undecided_user_gets_every_route_unranked(self):
        options = guidance.evaluate({}, False)['connection_options']
        self.assertEqual(options['ordering'], 'unranked')
        self.assertEqual(sorted(item['route'] for item in options['routes']),
                         sorted(guidance.CONNECTION_ROUTES))
        self.assertEqual(set(guidance.CONNECTION_ROUTES), {'self_managed', 'self_hosted_mcp', 'managed_mcp'})
        for item in options['routes']:
            with self.subTest(route=item['route']):
                for lang in guidance.LANGUAGES:
                    text = item['text'][lang]
                    self.assertTrue(text['label'].strip() and text['summary'].strip())
                    self.assertGreaterEqual(len(text['trade_offs']), 2)
                self.assertTrue(item['links'])

    def test_no_option_is_flagged_first_or_recommended(self):
        options = guidance.evaluate({}, False)['connection_options']
        steering = {'recommended', 'rank', 'priority', 'primary', 'primary_cta', 'default', 'featured'}
        self.assertFalse(steering & set(options))
        for item in options['routes']:
            self.assertFalse(steering & set(item))
        for lang in guidance.LANGUAGES:
            markdown = guidance.connection_options_markdown(options, lang)
            for word in ('recommend', 'Recommended', '推荐', '优先', 'first', 'best'):
                self.assertNotIn(word, markdown)

    def test_option_links_are_plain_urls_without_query_or_fragment(self):
        options = guidance.evaluate({}, False)['connection_options']
        urls = [link['url'] for item in options['routes'] for link in item['links']]
        self.assertIn('https://pipeboard.co', urls)
        example = [link for item in options['routes'] for link in item['links'] if link['kind'] == 'example']
        self.assertEqual([(link['title'], link['url']) for link in example], [('Pipeboard', 'https://pipeboard.co')])
        for url in urls:
            with self.subTest(url=url):
                parts = urlsplit(url)
                self.assertEqual(parts.scheme, 'https')
                self.assertEqual((parts.query, parts.fragment), ('', ''))
                self.assertNotIn('#', url)
                self.assertNotIn('?', url)
        for lang in guidance.LANGUAGES:
            markdown = guidance.connection_options_markdown(options, lang)
            self.assertNotIn('#', markdown.replace('**', ''))
            self.assertNotIn('via=', markdown)

    def test_renderer_rejects_tracking_links_ranking_and_missing_routes(self):
        options = guidance.evaluate({}, False)['connection_options']
        tampered = []
        for url in ('https://example.com/#ref=x', 'https://example.com/?ref=x', 'http://example.com/', 'example.com'):
            changed = copy.deepcopy(options)
            changed['routes'][0]['links'][0]['url'] = url
            tampered.append(changed)
        ranked = copy.deepcopy(options)
        ranked['routes'][2]['recommended'] = True
        tampered.append(ranked)
        cta = copy.deepcopy(options)
        cta['primary_cta'] = {'label': 'Sign up', 'url': 'https://example.com/'}
        tampered.append(cta)
        missing = copy.deepcopy(options)
        missing['routes'].pop()
        tampered.append(missing)
        unnamed = copy.deepcopy(options)
        unnamed['routes'][0].pop('route')
        tampered.append(unnamed)
        untranslated = copy.deepcopy(options)
        untranslated['routes'][1]['text'].pop('en')
        tampered.append(untranslated)
        unlabeled = copy.deepcopy(options)
        unlabeled['routes'][2]['links'][0]['kind'] = 'partner'
        tampered.append(unlabeled)
        duplicated = copy.deepcopy(options)
        duplicated['routes'][1] = copy.deepcopy(duplicated['routes'][2])
        tampered.append(duplicated)
        ordered = copy.deepcopy(options)
        ordered['ordering'] = 'ranked'
        tampered.append(ordered)
        for index, changed in enumerate(tampered):
            with self.subTest(case=index), self.assertRaises(guidance.GuidanceError):
                guidance.connection_options_markdown(changed)
        with self.assertRaises(guidance.GuidanceError):
            guidance.connection_options_markdown(options, 'fr')

    def test_profile_cannot_inject_a_link_into_the_options(self):
        profile = {'setup_preferences': {'route': 'undecided', 'affiliate_url': 'https://example.com/redirect'}}
        options = guidance.evaluate(profile, False)['connection_options']
        urls = [link['url'] for item in options['routes'] for link in item['links']]
        self.assertNotIn('https://example.com/redirect', urls)

    def test_legacy_catch_all_route_maps_to_a_generic_route(self):
        for legacy, canonical in (('other_mcp', 'self_hosted_mcp'),):
            with self.subTest(route=legacy):
                result = guidance.evaluate({'setup_preferences': {'route': legacy}}, False)
                self.assertEqual(result['connection_route'], canonical)
                self.assertIsNone(result['connection_options'])
                self.assertNotIn('Pipeboard', ' '.join(result['setup_steps']))

    def test_vendor_name_is_not_a_route(self):
        with self.assertRaises(guidance.GuidanceError):
            guidance.evaluate({'setup_preferences': {'route': 'pipeboard'}}, False)

    def test_chosen_route_existing_connection_and_dismissal_hide_the_options(self):
        for route in ('existing', 'self_managed', 'self_hosted_mcp', 'managed_mcp'):
            result = guidance.evaluate({'setup_preferences': {'route': route}}, False)
            self.assertIsNone(result['connection_options'])
            self.assertNotIn('recommendation', result)
            self.assertEqual(result['connection_route'], route)
            self.assertTrue(result['setup_steps'])
            self.assertNotIn('Pipeboard', ' '.join(result['setup_steps']))
        undecided = guidance.evaluate({'setup_preferences': {'route': 'undecided'}}, False)
        self.assertIsNotNone(undecided['connection_options'])
        # The list is only ever exposed as neutral connection options.
        self.assertNotIn('recommendation', undecided)
        for key in ('options_dismissed', 'recommendation_dismissed'):
            profile = {'setup_preferences': {'route': 'undecided', key: True}}
            self.assertIsNone(guidance.evaluate(profile, False)['connection_options'])
        self.assertIsNone(guidance.evaluate({}, True)['connection_options'])
        self.assertEqual(guidance.evaluate({}, True)['setup_steps'], [])

    def test_connected_unknown_experience_does_not_default_to_new_or_select_approach(self):
        result = guidance.evaluate({}, True)
        self.assertEqual(result['stage'], 'collaboration_intake')
        self.assertEqual(result['collaboration_summary']['experience_by_platform'], {
            'meta': 'unknown', 'tiktok': 'unknown', 'google': 'unknown'})
        self.assertEqual(result['collaboration_summary']['approach'], 'undecided')
        self.assertEqual(result['familiarity_question']['key'], 'collaboration.experience_by_platform')
        self.assertTrue(result['familiarity_question']['optional'])
        self.assertEqual({q['key'] for q in result['questions']}, {
            'collaboration.approach', 'collaboration.current_need'})
        self.assertLessEqual(len(result['questions']), 3)

    def test_familiarity_only_asks_selected_platforms_and_accepts_explicit_unknown(self):
        profile = {'selected_accounts': [{'platform': 'meta', 'account_id': 'fictional_meta'}]}
        result = guidance.evaluate(profile, True)
        self.assertEqual(result['familiarity_question']['platforms'], ['meta'])
        profile['collaboration'] = {'experience_by_platform': {'meta': 'unknown'}}
        self.assertIsNone(guidance.evaluate(profile, True)['familiarity_question'])

    def test_only_missing_collaboration_fields_are_asked_before_method(self):
        for profile, key in (({'collaboration': {'approach': 'guided'}}, 'collaboration.current_need'),
                             ({'collaboration': {'current_need': '排查账户数据'}}, 'collaboration.approach')):
            result = guidance.evaluate(profile, True)
            self.assertEqual([q['key'] for q in result['questions']], [key])
            self.assertEqual(result['method_requirement']['state'], 'needs_choice')
        self.assertEqual(guidance.evaluate(self.profile(current_need='   '), True)['stage'], 'collaboration_intake')

    def test_guided_and_bring_own_have_distinct_method_requirements_without_default_budget(self):
        for approach, state, phrase in (('guided', 'proposal_needed', '草案'), ('bring_own', 'import_needed', '已有')):
            with self.subTest(approach=approach):
                profile = self.profile(approach)
                before = copy.deepcopy(profile)
                result = guidance.evaluate(profile, True)
                self.assertEqual(result['stage'], 'business_intake')
                self.assertEqual(result['method_requirement']['state'], state)
                self.assertEqual([q['key'] for q in result['questions']], ['methodology'])
                self.assertIn(phrase, result['questions'][0]['question'])
                self.assertNotIn('learning_budget', result)
                self.assertNotIn('facts', profile)
                self.assertEqual(profile, before)

    def test_experience_is_optional_and_does_not_override_explicit_approach(self):
        profile = self.profile('bring_own')
        profile['collaboration']['experience_by_platform'] = {'meta': 'experienced', 'tiktok': 'new'}
        profile['collaboration']['explanation'] = 'detailed'
        result = guidance.evaluate(profile, True)
        self.assertEqual(result['method_requirement']['state'], 'import_needed')
        self.assertEqual(result['collaboration_summary']['experience_by_platform']['google'], 'unknown')
        self.assertEqual(result['collaboration_summary']['explanation'], 'detailed')
        self.assertEqual([q['key'] for q in result['questions']], ['methodology'])
        profile['collaboration']['experience_by_platform']['google'] = 'experienced'
        self.assertIsNone(guidance.evaluate(profile, True)['familiarity_question'])

    def test_method_requires_current_evidence_and_actual_text(self):
        profile = self.profile()
        for status in ('unknown', 'hypothesis', 'stale', 'conflict'):
            profile['facts'] = {'methodology': {'status': status, 'value': '控制变量测试', 'source': 'user'}}
            self.assertEqual(guidance.evaluate(profile, True)['method_requirement']['state'], 'proposal_needed')
        for value in (False, 0, {}, [], None, '', '  '):
            profile['facts'] = {'methodology': {'status': 'confirmed', 'value': value, 'source': 'user'}}
            self.assertEqual(guidance.evaluate(profile, True)['method_requirement']['state'], 'proposal_needed')
        for source in (False, True, 0, {}, {'ref': False}, {'nested': {'ref': ''}}, '', '   '):
            profile['facts'] = {'methodology': {'status': 'confirmed', 'value': '控制变量测试', 'source': source}}
            self.assertEqual(guidance.evaluate(profile, True)['method_requirement']['state'], 'proposal_needed')

    def test_confirmed_or_observed_method_with_nested_source_is_ready_for_either_route(self):
        for approach in ('guided', 'bring_own'):
            for status in ('confirmed', 'observed'):
                profile = self.profile(approach)
                profile['facts'] = {'methodology': {
                    'status': status, 'value': '控制变量测试', 'source': {'nested': {'ref': 'user supplied method'}}}}
                result = guidance.evaluate(profile, True)
                self.assertEqual(result['method_requirement']['state'], 'ready')
                self.assertEqual(result['questions'], [])
                result['method_requirement']['methodology']['source']['nested']['ref'] = 'changed result'
                self.assertEqual(profile['facts']['methodology']['source']['nested']['ref'], 'user supplied method')

    def test_connected_guidance_does_not_grant_or_mutate_ad_permissions(self):
        profile = self.profile()
        profile['connections'] = {'mode': 'simulation', 'checks': [{'write': {'status': 'unknown'}}]}
        profile['authorization'] = {'publish': False}
        before = copy.deepcopy(profile)
        result = guidance.evaluate(profile, True)
        self.assertEqual(profile, before)
        self.assertIn('不增加账户访问或发布权限', result['authorization_notice'])
        self.assertNotIn('authorization', result)
        self.assertNotIn('permissions', result)
        self.assertNotIn('readiness', result)

    def test_invalid_guidance_shapes_enums_and_boolean_values_are_rejected(self):
        invalid = [
            [], {'setup_preferences': []}, {'setup_preferences': {'route': 'auto_buy'}},
            {'setup_preferences': {'route': True}}, {'setup_preferences': {'route': ['managed_mcp']}},
            {'setup_preferences': {'recommendation_dismissed': 'false'}},
            {'setup_preferences': {'recommendation_dismissed': 0}}, {'setup_preferences': {'options_dismissed': 1}},
            {'collaboration': []},
            {'collaboration': {'approach': 'expert'}}, {'collaboration': {'current_need': False}},
            {'collaboration': {'current_need': None}}, {'collaboration': {'explanation': 'automatic'}},
            {'collaboration': {'explanation': None}}, {'collaboration': {'experience_by_platform': []}},
            {'collaboration': {'experience_by_platform': {'meta': True}}},
            {'collaboration': {'experience_by_platform': {'meta': 'beginner'}}},
            {'collaboration': {'experience_by_platform': {'unsupported': 'new'}}},
        ]
        for profile in invalid:
            with self.subTest(profile=profile), self.assertRaises(guidance.GuidanceError):
                guidance.evaluate(profile, True)
        for connected in (1, 0, None, 'false'):
            with self.subTest(connected=connected), self.assertRaises(guidance.GuidanceError):
                guidance.evaluate({}, connected)
        for facts in ([], {'methodology': []}, {'methodology': {'status': 'ready'}}):
            profile = self.profile()
            profile['facts'] = facts
            with self.subTest(facts=facts), self.assertRaises(guidance.GuidanceError):
                guidance.evaluate(profile, True)


if __name__ == '__main__':
    unittest.main()
