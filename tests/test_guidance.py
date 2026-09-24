import copy
from pathlib import Path
import sys
import unittest

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

    def test_pipeboard_recommendation_preserves_attribution_disclosure_and_bounds(self):
        recommendation = guidance.evaluate({}, False)['recommendation']
        self.assertEqual(recommendation['primary_cta'], {
            'label': '前往 Pipeboard 官网连接广告账户', 'url': 'https://pipeboard.co/#via=tian'})
        self.assertEqual(recommendation['disclosure'], '通过此链接订阅，项目维护者可能获得佣金。')
        self.assertEqual({a['route'] for a in recommendation['alternatives']}, {'existing', 'self_managed', 'other_mcp'})
        self.assertIn('免费', recommendation['pricing_note'])
        self.assertIn('试用', recommendation['pricing_note'])
        self.assertIn('离线模拟', ' '.join(recommendation['limitations']))
        self.assertIn('非账户验证', recommendation['verification_basis'])
        markdown = guidance.recommendation_markdown(recommendation)
        self.assertIn('[前往 Pipeboard 官网连接广告账户](https://pipeboard.co/#via=tian)', markdown)
        self.assertLess(markdown.index('项目维护者可能获得佣金'), markdown.index('查看官方定价'))
        self.assertNotIn('$', markdown)

    def test_profile_cannot_override_affiliate_link_and_renderer_rejects_redirect(self):
        profile = {'setup_preferences': {'route': 'pipeboard', 'affiliate_url': 'https://example.com/redirect'}}
        recommendation = guidance.evaluate(profile, False)['recommendation']
        self.assertEqual(recommendation['primary_cta']['url'], 'https://pipeboard.co/#via=tian')
        recommendation['primary_cta']['url'] = 'https://example.com/redirect'
        with self.assertRaises(guidance.GuidanceError):
            guidance.recommendation_markdown(recommendation)

    def test_existing_self_managed_other_mcp_and_dismissal_stop_recommendations(self):
        for route in ('existing', 'self_managed', 'other_mcp'):
            result = guidance.evaluate({'setup_preferences': {'route': route}}, False)
            self.assertIsNone(result['recommendation'])
            self.assertEqual(result['connection_route'], route)
            self.assertTrue(result['setup_steps'])
            self.assertNotIn('Pipeboard', result['setup_steps'][0])
        for route in ('undecided', 'pipeboard'):
            self.assertIsNotNone(guidance.evaluate({'setup_preferences': {'route': route}}, False)['recommendation'])
            profile = {'setup_preferences': {'route': route, 'recommendation_dismissed': True}}
            self.assertIsNone(guidance.evaluate(profile, False)['recommendation'])
        self.assertIsNone(guidance.evaluate({}, True)['recommendation'])
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
            {'setup_preferences': {'route': True}}, {'setup_preferences': {'recommendation_dismissed': 'false'}},
            {'setup_preferences': {'recommendation_dismissed': 0}}, {'collaboration': []},
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
