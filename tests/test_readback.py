"""The readback verifier activates only what the platform actually returned.

Every test here mirrors a way a build can look finished without being right: a
status copied from the plan, a budget read in the wrong unit, a field the API
did not return, a URL parameter that was dropped, or an extra object left by a
retried request.
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
import readback

FIXTURES = ROOT / 'examples' / 'readback'


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def meta():
    return fixture('meta-plan.json'), fixture('meta-readback.json')


def tiktok():
    return fixture('tiktok-plan.json'), fixture('tiktok-readback.json')


def response(document, key):
    for item in document['objects']:
        if item['object_key'] == key:
            return item['response']
    raise KeyError(key)


def row(result, key, field):
    matches = [item for item in result['rows'] if item['object_key'] == key and item['field'] == field]
    if len(matches) != 1:
        raise AssertionError(f'expected one row for {key}.{field}, found {len(matches)}')
    return matches[0]


def fix_meta_url_tags(document):
    response(document, 'ad-h3')['creative']['url_tags'] = (
        'utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}')
    return document


class FixtureTests(unittest.TestCase):
    def test_missing_url_parameter_holds_activation(self):
        plan, read = meta()
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'hold')
        self.assertEqual([item for item in result['rows'] if not item['match']],
                         [row(result, 'ad-h3', 'url_parameters')])
        self.assertEqual(len(result['reasons']), 1)
        self.assertEqual(result['reasons'][0]['code'], 'missing_url_parameter')
        self.assertEqual(result['reasons'][0]['names'], ['utm_content'])

    def test_meta_case_activates_once_the_parameter_is_restored(self):
        plan, read = meta()
        result = readback.verify_build(plan, fix_meta_url_tags(read))
        self.assertEqual(result['decision'], 'activate')
        self.assertEqual(result['fields_matched'], result['fields'])

    def test_tiktok_case_matches_every_field(self):
        plan, read = tiktok()
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'activate')
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['objects_paused'], result['objects'])
        self.assertEqual(result['native_platform_calls'], 0)

    def test_url_parameter_with_a_different_value_holds(self):
        plan, read = tiktok()
        ad = response(read, 'ad-t2')
        ad['landing_page_url'] = ad['landing_page_url'].replace('utm_source=tiktok', 'utm_source=tt')
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'hold')
        self.assertEqual(result['reasons'][0]['code'], 'url_parameter_value')
        self.assertEqual(result['reasons'][0]['names'], ['utm_source'])


class StatusTests(unittest.TestCase):
    def test_receipt_status_comes_from_readback_not_plan(self):
        plan, read = meta()
        fix_meta_url_tags(read)
        response(read, 'ad-h2')['status'] = 'ACTIVE'
        result = readback.verify_build(plan, read)
        status = row(result, 'ad-h2', 'status')
        self.assertEqual(status['planned'], 'PAUSED')
        self.assertEqual(status['read_back'], 'ACTIVE')
        self.assertEqual(result['objects_paused'], 6)
        receipt = readback.render_receipt(result)
        self.assertIn('Created PAUSED 6/7', receipt)
        self.assertIn('| ad | `ad-h2` | Status | `PAUSED` | `ACTIVE` | ✗ |', receipt)
        self.assertIn('6 read back `PAUSED`', receipt)

    def test_status_must_be_paused_before_activation(self):
        plan, read = tiktok()
        response(read, 'ag-t1')['operation_status'] = 'ENABLE'
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'hold')
        self.assertEqual([reason['code'] for reason in result['reasons']], ['not_paused'])
        # Everything else still matches: status alone blocks activation.
        self.assertEqual(result['fields_matched'], result['fields'] - 1)

    def test_status_not_returned_is_not_paused(self):
        plan, read = tiktok()
        del response(read, 'ad-t1')['operation_status']
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'hold')
        self.assertIsNone(row(result, 'ad-t1', 'status')['read_back'])
        self.assertEqual(result['objects_paused'], 4)

    def test_plan_that_creates_an_object_active_is_refused(self):
        plan, read = meta()
        plan['objects'][0]['status'] = 'ACTIVE'
        with self.assertRaises(readback.ReadbackError):
            readback.verify_build(plan, read)

    def test_review_state_is_recorded_not_gated(self):
        plan, read = meta()
        result = readback.verify_build(plan, fix_meta_url_tags(read))
        self.assertEqual(result['decision'], 'activate')
        observed = {(item['object_key'], item['value']) for item in result['observed']}
        self.assertIn(('ad-h1', 'IN_PROCESS'), observed)


class MoneyTests(unittest.TestCase):
    def test_budget_minor_units_follow_currency_offset(self):
        plan, read = meta()
        fix_meta_url_tags(read)
        result = readback.verify_build(plan, read)
        self.assertEqual(row(result, 'as-h1', 'daily_budget')['read_back'], '20.00 USD (raw 2000)')
        self.assertEqual(row(result, 'as-h3', 'bid_amount')['read_back'], '6.50 USD (raw 650)')

        # Offset 1 currency: the same raw digits are whole yen, not hundredths.
        plan['currency'] = 'JPY'
        read['account']['response']['currency'] = 'JPY'
        for item in plan['objects']:
            if item['level'] == 'adset':
                item['daily_budget'] = '2000'
                if 'bid_amount' in item:
                    item['bid_amount'] = '650'
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'activate')
        self.assertEqual(row(result, 'as-h1', 'daily_budget')['read_back'], '2000 JPY (raw 2000)')

    def test_twd_uses_the_platform_offset_not_iso(self):
        self.assertEqual(readback.MINOR_UNIT_EXPONENT['TWD'], 0)
        self.assertEqual(readback.MINOR_UNIT_EXPONENT['USD'], 2)

    def test_account_currency_differs_from_plan_holds(self):
        plan, read = meta()
        fix_meta_url_tags(read)
        read['account']['response']['currency'] = 'JPY'
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'hold')
        self.assertFalse(row(result, 'fictional-meta-account-a', 'currency')['match'])
        budget = row(result, 'as-h1', 'daily_budget')
        self.assertFalse(budget['match'])
        self.assertEqual(budget['read_back'], '2000 JPY (raw 2000)')

    def test_same_digits_in_another_currency_do_not_match(self):
        plan, read = meta()
        fix_meta_url_tags(read)
        read['account']['response']['currency'] = 'EUR'
        result = readback.verify_build(plan, read)
        budget = row(result, 'as-h1', 'daily_budget')
        self.assertEqual(budget['read_back'], '20.00 EUR (raw 2000)')
        self.assertFalse(budget['match'])

    def test_unknown_currency_is_refused_not_guessed(self):
        plan, read = meta()
        plan['currency'] = 'XAU'
        read['account']['response']['currency'] = 'XAU'
        with self.assertRaises(readback.ReadbackError):
            readback.verify_build(plan, read)

    def test_account_currency_not_returned_leaves_budgets_unconverted(self):
        plan, read = meta()
        fix_meta_url_tags(read)
        del read['account']['response']['currency']
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'hold')
        self.assertIsNone(row(result, 'fictional-meta-account-a', 'currency')['read_back'])
        self.assertFalse(row(result, 'as-h1', 'daily_budget')['match'])

    def test_major_unit_platform_is_not_divided(self):
        plan, read = tiktok()
        result = readback.verify_build(plan, read)
        self.assertEqual(row(result, 'ag-t1', 'daily_budget')['read_back'], '30.00 USD')

    def test_lifetime_budget_is_not_a_daily_budget(self):
        plan, read = tiktok()
        response(read, 'ag-t1')['budget_mode'] = 'BUDGET_MODE_TOTAL'
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'hold')
        self.assertFalse(row(result, 'ag-t1', 'daily_budget')['match'])

    def test_plan_amount_finer_than_the_currency_is_refused(self):
        plan, read = meta()
        plan['objects'][1]['daily_budget'] = '20.005'
        with self.assertRaises(readback.ReadbackError):
            readback.verify_build(plan, read)

    def test_boolean_is_not_an_amount(self):
        plan, read = meta()
        fix_meta_url_tags(read)
        response(read, 'as-h1')['daily_budget'] = True
        result = readback.verify_build(plan, read)
        self.assertFalse(row(result, 'as-h1', 'daily_budget')['match'])


class MissingAndExtraTests(unittest.TestCase):
    def test_missing_field_is_not_returned_never_assumed_equal(self):
        plan, read = meta()
        fix_meta_url_tags(read)
        del response(read, 'as-h2')['attribution_spec']
        result = readback.verify_build(plan, read)
        attribution = row(result, 'as-h2', 'attribution')
        self.assertIsNone(attribution['read_back'])
        self.assertFalse(attribution['match'])
        self.assertEqual(result['reasons'][0]['code'], 'not_returned')
        self.assertIn('*not returned*', readback.render_receipt(result))

    def test_missing_object_holds_and_counts_every_field(self):
        plan, read = tiktok()
        read['objects'] = [item for item in read['objects'] if item['object_key'] != 'ad-t2']
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'hold')
        self.assertEqual(result['objects_returned'], 4)
        self.assertEqual([reason['code'] for reason in result['reasons']], ['object_not_returned'])
        self.assertTrue(all(item['read_back'] is None for item in result['rows']
                            if item['object_key'] == 'ad-t2'))

    def test_extra_object_from_a_retried_request_holds(self):
        plan, read = tiktok()
        duplicate = copy.deepcopy(read['objects'][-1])
        duplicate['object_key'] = 'ad-t2-retry'
        read['objects'].append(duplicate)
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'hold')
        self.assertEqual(result['reasons'][-1]['code'], 'unexpected_object')

    def test_unknown_tiktok_window_is_shown_raw_and_mismatches(self):
        plan, read = tiktok()
        response(read, 'ag-t1')['click_attribution_window'] = 'THIRTY_DAYS'
        result = readback.verify_build(plan, read)
        attribution = row(result, 'ag-t1', 'attribution')
        self.assertFalse(attribution['match'])
        self.assertIn('THIRTY_DAYS', attribution['read_back'])

    def test_plan_must_state_fields_it_wants_checked(self):
        plan, read = meta()
        del plan['objects'][1]['geo']
        with self.assertRaises(readback.ReadbackError):
            readback.verify_build(plan, read)

    def test_platform_mismatch_is_refused(self):
        plan, _ = meta()
        _, read = tiktok()
        with self.assertRaises(readback.ReadbackError):
            readback.verify_build(plan, read)

    def test_planned_field_at_unchecked_level_is_refused(self):
        # A CBO-style campaign budget, or a geo stated on an ad, is never compared,
        # so the plan is refused instead of passing with "every field matches".
        for key, field, value in (('cmp-t', 'daily_budget', '500.00'),
                                  ('cmp-t', 'bid_strategy', 'BID_TYPE_CUSTOM'),
                                  ('ad-t1', 'geo', ['XX'])):
            plan, read = tiktok()
            for item in plan['objects']:
                if item['level'] == ('campaign' if key.startswith('cmp') else 'ad'):
                    item[field] = value
                    break
            with self.subTest(field=field):
                with self.assertRaises(readback.ReadbackError) as caught:
                    readback.verify_build(plan, read)
                self.assertIn('is not verified at the', str(caught.exception))

    def test_field_without_a_platform_path_is_refused(self):
        plan, read = tiktok()
        campaign = next(item for item in plan['objects'] if item['level'] == 'campaign')
        campaign['special_ad_categories'] = ['EMPLOYMENT']
        with self.assertRaises(readback.ReadbackError) as caught:
            readback.verify_build(plan, read)
        self.assertIn('is not read back on TikTok', str(caught.exception))

    def test_cleared_special_category_holds_activation(self):
        plan, read = meta()
        fix_meta_url_tags(read)
        plan['objects'][0]['special_ad_categories'] = ['EMPLOYMENT']
        result = readback.verify_build(plan, read)
        self.assertEqual(result['decision'], 'hold')
        categories = row(result, 'cmp-quote-01', 'special_ad_categories')
        self.assertFalse(categories['match'])
        self.assertEqual(categories['planned'], 'EMPLOYMENT')
        self.assertEqual(categories['read_back'], '(none)')

    def test_url_parameters_must_be_an_object_of_strings(self):
        for where in ('plan', 'object'):
            plan, read = meta()
            if where == 'plan':
                plan['url_parameters'] = [['utm_source', 'meta']]
            else:
                plan['objects'][4]['url_parameters'] = {'utm_source': 1}
            with self.subTest(where=where):
                with self.assertRaises(readback.ReadbackError):
                    readback.verify_build(plan, read)


class ReceiptTests(unittest.TestCase):
    def test_goldens_match_a_fresh_render(self):
        for platform in ('meta', 'tiktok'):
            for lang, suffix in (('en', ''), ('zh-CN', '.zh-CN')):
                expected = FIXTURES / 'expected' / f'{platform}-receipt{suffix}.md'
                with self.subTest(platform=platform, lang=lang):
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        code = readback.main([
                            '--plan', str(FIXTURES / f'{platform}-plan.json'),
                            '--readback', str(FIXTURES / f'{platform}-readback.json'),
                            '--lang', lang, '--check', str(expected)])
                    self.assertEqual(code, 0)

    def test_receipt_header_and_timeline(self):
        plan, read = meta()
        receipt = readback.render_receipt(readback.verify_build(plan, read),
                                          plan_name='meta-plan.json', readback_name='meta-readback.json')
        self.assertTrue(receipt.startswith('# Build receipt — replay, fictional values\n'))
        self.assertIn('**Created PAUSED 7/7 → Readback 40/41 fields → HOLD**', receipt)
        self.assertEqual(receipt.count('| ✗ |'), 1)

    def test_check_reports_a_difference(self):
        plan_path = FIXTURES / 'meta-plan.json'
        read_path = FIXTURES / 'meta-readback.json'
        tiktok_golden = FIXTURES / 'expected' / 'tiktok-receipt.md'
        result = subprocess.run(
            [sys.executable, 'readback.py', '--plan', str(plan_path.relative_to(ROOT)),
             '--readback', str(read_path.relative_to(ROOT)),
             '--check', str(tiktok_golden.relative_to(ROOT))],
            cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('+++ fresh receipt', result.stderr)
        self.assertNotIn(str(ROOT), result.stdout + result.stderr)

    def test_invalid_input_exits_2(self):
        result = subprocess.run(
            [sys.executable, 'readback.py', '--plan', 'examples/readback/meta-plan.json',
             '--readback', 'examples/readback/tiktok-readback.json'],
            cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('platform does not match', result.stderr)


if __name__ == '__main__':
    unittest.main()
