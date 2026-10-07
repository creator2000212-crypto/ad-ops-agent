"""The pre-flight linter stops configuration mistakes before anything exists.

Each check has a pass, a warn (cannot tell, a person decides) and a fail
(contradiction that must be fixed) case. Platform facts such as the macro list
come from the policy file, so changing the policy changes the verdict.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import preflight

FIXTURES = ROOT / 'examples' / 'preflight'
HASH_A = 'a' * 64
HASH_B = 'b' * 64
GOOD_TAGS = 'utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}'


def policy():
    return json.loads((FIXTURES / 'policy.json').read_text(encoding='utf-8'))


def fixture():
    return json.loads((FIXTURES / 'checklist.json').read_text(encoding='utf-8'))


def ad(key='ad-1', url='https://example.com/quote', tags=GOOD_TAGS, digest=HASH_A):
    return {'ad_key': key, 'name': key, 'destination_url': url, 'url_parameters': tags,
            'creative': {'file': key + '.mp4', 'sha256': digest}}


def adset(key='as-1', name='1n1 | C1 | MAX | $20', strategy='LOWEST_COST_WITHOUT_CAP',
          bid=None, budget='20.00', attribution=None, ads=None):
    return {'adset_key': key, 'name': name, 'bid_strategy': strategy, 'bid_amount': bid,
            'daily_budget': budget,
            'attribution': attribution if attribution is not None else {'click_days': 7, 'view_days': 1},
            'ads': ads if ads is not None else [ad(key='ad-' + key)]}


def checklist(adsets=None, platform='meta', **campaign):
    base = {'campaign_key': 'cmp-1', 'name': 'LG | Test', 'offer_category': 'home_services',
            'special_ad_categories': [], 'adsets': adsets if adsets is not None else [adset()]}
    base.update(campaign)
    return {'kind': 'build_checklist', 'platform': platform, 'currency': 'USD', 'campaigns': [base]}


def cells(result, key):
    for row in result['rows']:
        if row['object_key'] == key:
            return row['cells']
    raise KeyError(key)


def codes(result, key=None):
    return [item['code'] for item in result['findings'] if key is None or item['object_key'] == key]


class CleanTests(unittest.TestCase):
    def test_clean_checklist_passes(self):
        result = preflight.lint(checklist(), policy())
        self.assertEqual(result['result'], 'pass')
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['counts'], {'pass': 7, 'warn': 0, 'fail': 0})
        self.assertEqual(result['native_platform_calls'], 0)

    def test_fixture_shows_every_kind_of_failure(self):
        result = preflight.lint(fixture(), policy())
        self.assertEqual(result['result'], 'fail')
        self.assertEqual(cells(result, 'as-h1'),
                         {'special_category': None, 'attribution': None, 'name_bid': 'pass',
                          'name_budget': 'pass', 'duplicate_creative': 'pass', 'url_https': None,
                          'url_params': None})
        self.assertEqual(cells(result, 'as-h2')['name_bid'], 'fail')
        self.assertEqual(cells(result, 'as-h3')['name_budget'], 'fail')
        self.assertEqual(cells(result, 'ad-h2')['url_params'], 'warn')
        self.assertEqual(cells(result, 'ad-h3')['url_https'], 'fail')
        self.assertEqual(cells(result, 'cmp-hire-01')['special_category'], 'fail')
        self.assertEqual(cells(result, 'cmp-hire-01')['attribution'], 'fail')
        self.assertEqual(cells(result, 'as-j2')['duplicate_creative'], 'fail')
        self.assertEqual(cells(result, 'as-j2')['name_bid'], 'warn')


class NamingTests(unittest.TestCase):
    def test_max_name_with_cost_cap_fails(self):
        result = preflight.lint(checklist([adset(strategy='COST_CAP', bid='6.50')]), policy())
        self.assertEqual(cells(result, 'as-1')['name_bid'], 'fail')
        self.assertEqual(codes(result, 'as-1'), ['bid_token_conflict'])

    def test_cap_in_name_must_equal_bid_amount(self):
        good = adset(name='1n1 | C1 | CC6.50 | $20', strategy='COST_CAP', bid='6.50')
        self.assertEqual(preflight.lint(checklist([good]), policy())['result'], 'pass')
        bad = adset(name='1n1 | C1 | CC6.50 | $20', strategy='COST_CAP', bid='7.00')
        result = preflight.lint(checklist([bad]), policy())
        self.assertEqual(codes(result, 'as-1'), ['bid_amount_conflict'])

    def test_budget_in_name_must_equal_config(self):
        result = preflight.lint(checklist([adset(budget='25.00')]), policy())
        self.assertEqual(cells(result, 'as-1')['name_budget'], 'fail')
        self.assertEqual(codes(result, 'as-1'), ['budget_conflict'])

    def test_name_outside_the_convention_warns_not_fails(self):
        result = preflight.lint(checklist([adset(name='C1 test')]), policy())
        self.assertEqual(result['result'], 'warn')
        self.assertEqual(cells(result, 'as-1')['name_bid'], 'warn')
        self.assertEqual(cells(result, 'as-1')['name_budget'], 'warn')

    def test_unknown_bid_token_warns(self):
        result = preflight.lint(checklist([adset(name='1n1 | C1 | ROAS | $20')]), policy())
        self.assertEqual(codes(result, 'as-1'), ['bid_token_unknown'])


class UrlTests(unittest.TestCase):
    def test_http_destination_fails(self):
        result = preflight.lint(checklist([adset(ads=[ad(url='http://example.com/quote')])]), policy())
        self.assertEqual(cells(result, 'ad-1')['url_https'], 'fail')

    def test_missing_required_parameter_fails(self):
        tags = 'utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}'
        result = preflight.lint(checklist([adset(ads=[ad(tags=tags)])]), policy())
        self.assertEqual(cells(result, 'ad-1')['url_params'], 'fail')
        self.assertEqual(result['findings'][0]['detail']['names'], 'utm_content')

    def test_parameters_in_the_destination_url_count(self):
        url = 'https://example.com/quote?' + GOOD_TAGS
        result = preflight.lint(checklist([adset(ads=[ad(url=url, tags='')])]), policy())
        self.assertEqual(result['result'], 'pass')

    def test_unknown_macro_fails(self):
        result = preflight.lint(checklist([adset(ads=[ad(tags=GOOD_TAGS + '&src={{adname}}')])]),
                                policy())
        self.assertEqual(codes(result, 'ad-1'), ['macro_unknown'])

    def test_macro_list_comes_from_the_policy(self):
        rules = policy()
        known = rules['destination_url']['platforms']['meta']['known_macros']
        known.remove('{{ad.name}}')
        result = preflight.lint(checklist(), rules)
        self.assertEqual(codes(result, 'ad-as-1'), ['macro_unknown'])

    def test_parameter_value_other_than_policy_warns(self):
        tags = GOOD_TAGS.replace('{{ad.name}}', 'c1')
        result = preflight.lint(checklist([adset(ads=[ad(tags=tags)])]), policy())
        self.assertEqual(cells(result, 'ad-1')['url_params'], 'warn')
        self.assertEqual(codes(result), ['param_value'])

    def test_tiktok_uses_its_own_macros(self):
        tags = 'utm_source=tiktok&utm_medium=paid&utm_campaign=__CAMPAIGN_NAME__&utm_content=__CID_NAME__'
        good = checklist([adset(strategy='BID_TYPE_NO_BID', ads=[ad(tags='', url='https://example.com/q?' + tags)])],
                         platform='tiktok')
        result = preflight.lint(good, policy())
        # TikTok has no sourced special-category map in the policy: warn, never a silent pass.
        self.assertEqual(result['result'], 'warn')
        self.assertEqual(codes(result), ['no_category_map'])
        bad = copy.deepcopy(good)
        bad['campaigns'][0]['adsets'][0]['ads'][0]['destination_url'] += '&ag=__ADGROUP_NAME__'
        self.assertIn('macro_unknown', codes(preflight.lint(bad, policy())))


class CampaignTests(unittest.TestCase):
    def test_undeclared_special_category_fails(self):
        result = preflight.lint(checklist(offer_category='job_listings'), policy())
        self.assertEqual(cells(result, 'cmp-1')['special_category'], 'fail')
        self.assertEqual(result['findings'][0]['detail']['required'], 'EMPLOYMENT')

    def test_declared_special_category_passes(self):
        result = preflight.lint(checklist(offer_category='personal_loans',
                                          special_ad_categories=['FINANCIAL_PRODUCTS_SERVICES']),
                                policy())
        self.assertEqual(result['result'], 'pass')

    def test_unstated_offer_category_warns(self):
        result = preflight.lint(checklist(offer_category=None), policy())
        self.assertEqual(codes(result), ['category_not_stated'])

    def test_mixed_attribution_in_one_campaign_fails(self):
        mixed = [adset(), adset(key='as-2', attribution={'click_days': 1, 'view_days': 0})]
        result = preflight.lint(checklist(mixed), policy())
        self.assertEqual(cells(result, 'cmp-1')['attribution'], 'fail')

    def test_missing_attribution_warns(self):
        missing = adset()
        missing['attribution'] = None
        result = preflight.lint(checklist([missing]), policy())
        self.assertEqual(codes(result), ['attribution_missing'])


class CreativeTests(unittest.TestCase):
    def test_duplicate_file_in_one_adset_fails(self):
        result = preflight.lint(checklist([adset(ads=[ad('ad-1'), ad('ad-2')])]), policy())
        self.assertEqual(cells(result, 'as-1')['duplicate_creative'], 'fail')

    def test_same_file_in_different_adsets_passes(self):
        result = preflight.lint(checklist([adset(), adset(key='as-2')]), policy())
        self.assertEqual(result['result'], 'pass')

    def test_distinct_files_pass_and_missing_hash_warns(self):
        result = preflight.lint(checklist([adset(ads=[ad('ad-1'), ad('ad-2', digest=HASH_B)])]), policy())
        self.assertEqual(result['result'], 'pass')
        result = preflight.lint(checklist([adset(ads=[ad('ad-1', digest='')])]), policy())
        self.assertEqual(codes(result), ['hash_missing'])


class InputTests(unittest.TestCase):
    def test_policy_without_url_rules_is_refused(self):
        rules = policy()
        del rules['destination_url']
        with self.assertRaises(preflight.PreflightError):
            preflight.lint(checklist(), rules)

    def test_duplicate_keys_are_refused(self):
        with self.assertRaises(preflight.PreflightError):
            preflight.lint(checklist([adset(), adset()]), policy())

    def test_special_categories_must_be_a_list(self):
        # 'EMPLOYMENT' in 'EMPLOYMENT_X' is True for a string, so a scalar would
        # pass the declaration check by substring.
        with self.assertRaises(preflight.PreflightError):
            preflight.lint(checklist(offer_category='job_listings',
                                     special_ad_categories='EMPLOYMENT_X'), policy())

    def test_url_parameters_object_is_refused_not_crashed(self):
        bad = ad()
        bad['url_parameters'] = {'utm_source': 'meta'}
        with self.assertRaises(preflight.PreflightError):
            preflight.lint(checklist([adset(ads=[bad])]), policy())


class ReportTests(unittest.TestCase):
    def test_goldens_match_a_fresh_render(self):
        for lang, suffix in (('en', ''), ('zh-CN', '.zh-CN')):
            with self.subTest(lang=lang):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = preflight.main([
                        '--checklist', str(FIXTURES / 'checklist.json'),
                        '--policy', str(FIXTURES / 'policy.json'), '--lang', lang,
                        '--check', str(FIXTURES / 'expected' / f'checklist{suffix}.md')])
                self.assertEqual(code, 0)

    def test_strict_exits_3_on_fail(self):
        result = subprocess.run(
            [sys.executable, 'preflight.py', '--checklist', 'examples/preflight/checklist.json',
             '--policy', 'examples/preflight/policy.json', '--strict'],
            cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 3)
        self.assertTrue(result.stdout.startswith('# Pre-flight check — replay, fictional values'))
        self.assertNotIn(str(ROOT), result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
