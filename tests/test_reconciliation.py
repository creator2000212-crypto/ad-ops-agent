"""Platform vs settlement: compare like with like before acting on cost.

Each account gets one status (scope, window, time zone, gap, ok). Missing rows
stay missing, tolerances come only from the methodology, and an account whose
numbers do not reconcile cannot drive a promotion or an over-cost pause."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import operating_loop
import operating_rules as rules

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples' / 'operating'
DATE = '2026-09-23'


def methodology():
    return rules.load_methodology(EXAMPLES / 'methodology-reference.json')


def adset(key='adset-1', spend='19.80', results=3, **overrides):
    base = {'adset_key': key, 'name': '1n1 | X | MAX | $20', 'configured_status': 'ACTIVE',
            'effective_status': 'ACTIVE', 'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
            'daily_budget': '20.00', 'ladder_stage': 'T', 'spend': spend, 'impressions': 4600,
            'clicks': 300, 'results': results, 'linked': True, 'tracking_ok': True, 'creatives': []}
    base.update(overrides)
    return base


def account(key='acct-1', adsets=None, **overrides):
    base = {'account_key': key, 'platform': 'meta', 'account_timezone': 'Etc/GMT',
            'report_timezone': 'Etc/GMT', 'spend_cap': '1000.00', 'balance': '500.00',
            'today_spend': '20.00', 'offer': {'offer_key': 'offer-1', 'unit_price': '10.00'},
            'observation': {'complete_delivery_day': True},
            'adsets': [adset()] if adsets is None else adsets}
    base.update(overrides)
    return base


def snapshot(*accounts):
    return {'kind': 'operating_snapshot', 'as_of': '2026-09-24T00:00:00Z', 'round_id': 'r',
            'observation': {'date': DATE, 'complete_delivery_day': True},
            'accounts': list(accounts) or [account()]}


def row(key='acct-1', spend='19.80', results=3, **overrides):
    base = {'platform': 'meta', 'account_key': key, 'unit_price': '10.00', 'spend': spend,
            'results': results, 'value': str(10 * results)}
    base.update(overrides)
    return base


def settlement(*rows, **overrides):
    base = {'kind': 'settlement_daily', 'date': DATE, 'timezone': 'Etc/GMT', 'currency': 'USD',
            'rows': list(rows)}
    base.update(overrides)
    return base


def reconcile(snap, settle, document=None, lang='en'):
    return rules.reconcile_settlement(snap, settle, document or methodology(), lang)


def status_of(result, key='acct-1'):
    return next(item for item in result['rows'] if item['account_key'] == key)


class StatusTests(unittest.TestCase):
    def test_within_tolerance_is_ok(self):
        # 3 platform leads x 0.90 approval = 2.7 expected; 3 settled is +11.1%, inside 20%.
        result = status_of(reconcile(snapshot(), settlement(row(spend='19.70', results=3))))
        self.assertEqual(result['status'], rules.RECON_OK)
        self.assertEqual(result['spend_delta_pct'], '-0.51')
        self.assertEqual(result['expected_settled_results'], '2.70')
        self.assertFalse(result['downgrade'])

    def test_spend_outside_tolerance_is_a_gap(self):
        result = status_of(reconcile(snapshot(), settlement(row(spend='16.00'))))
        self.assertEqual(result['status'], rules.RECON_GAP)
        self.assertEqual(result['spend_delta_pct'], '-19.19')
        self.assertIn('Spend differs by -19.2% (tolerance ±2.0%)', ' '.join(result['reasons']))
        self.assertTrue(result['downgrade'])

    def test_settled_leads_are_compared_with_the_approval_rate(self):
        # 10 platform leads x 0.90 = 9 expected. 9 settled is exact; 5 settled is -44.4%.
        snap = snapshot(account(adsets=[adset(spend='60.00', results=10)]))
        ok = status_of(reconcile(snap, settlement(row(spend='60.00', results=9))))
        self.assertEqual((ok['status'], ok['results_delta_pct'], ok['approval_rate']),
                         (rules.RECON_OK, '0.00', '0.900'))
        gap = status_of(reconcile(snap, settlement(row(spend='60.00', results=5))))
        self.assertEqual(gap['status'], rules.RECON_GAP)
        self.assertIn('approved 5 of 10 leads; expected 9.0', ' '.join(gap['reasons']))

    def test_unit_price_difference_is_a_gap(self):
        result = status_of(reconcile(snapshot(), settlement(row(unit_price='9.00'))))
        self.assertEqual(result['status'], rules.RECON_GAP)
        self.assertIn('unit price 9.00 differs from the offer price 10.00', ' '.join(result['reasons']))

    def test_time_zone_difference_is_reported_before_the_gap(self):
        snap = snapshot(account(account_timezone='Etc/GMT+5'))
        result = status_of(reconcile(snap, settlement(row(spend='5.00'))))
        self.assertEqual(result['status'], rules.RECON_TZ)
        self.assertTrue(result['downgrade'])

    def test_undeclared_time_zone_is_not_assumed_equal(self):
        snap = snapshot()
        settle = settlement(row())
        del settle['timezone']
        self.assertEqual(status_of(reconcile(snap, settle))['status'], rules.RECON_TZ)
        snap = snapshot(account(account_timezone=None))
        self.assertEqual(status_of(reconcile(snap, settlement(row())))['status'], rules.RECON_TZ)

    def test_row_level_time_zone_overrides_the_document(self):
        snap = snapshot(account(account_timezone='Etc/GMT+5'))
        result = status_of(reconcile(snap, settlement(row(timezone='Etc/GMT+5'))))
        self.assertEqual(result['status'], rules.RECON_OK)

    def test_date_mismatch_is_a_window_problem(self):
        result = status_of(reconcile(snapshot(), settlement(row(date='2026-09-22'))))
        self.assertEqual(result['status'], rules.RECON_WINDOW)
        self.assertEqual(result['settled_date'], '2026-09-22')
        self.assertIsNone(result['settled_spend'])
        self.assertTrue(result['downgrade'])

    def test_join_is_on_account_and_date(self):
        settle = settlement(row(date='2026-09-22', spend='99.00'), row(spend='19.80'))
        result = status_of(reconcile(snapshot(), settle))
        self.assertEqual((result['status'], result['settled_spend']), (rules.RECON_OK, '19.80'))

    def test_precedence_scope_window_tz_gap(self):
        settle = settlement(row(date='2026-09-22', spend='1.00'))
        snap = snapshot(account(account_timezone='Etc/GMT+5'))
        # The date mismatch is reported even though time zone and spend also differ.
        self.assertEqual(status_of(reconcile(snap, settle))['status'], rules.RECON_WINDOW)

    def test_duplicate_row_is_rejected(self):
        with self.assertRaises(rules.RuleError):
            reconcile(snapshot(), settlement(row(), row()))

    def test_wrong_document_kind_is_rejected(self):
        with self.assertRaises(rules.RuleError):
            reconcile(snapshot(), {'kind': 'writeback_snapshot', 'rows': []})


class MissingIsNotZeroTests(unittest.TestCase):
    def test_platform_only_account_is_scope_and_never_zero_filled(self):
        result = status_of(reconcile(snapshot(), settlement()))
        self.assertEqual((result['status'], result['side']), (rules.RECON_SCOPE, 'platform_only'))
        for field in ('settled_spend', 'settled_results', 'settled_cpa', 'spend_delta_pct',
                      'results_delta_pct'):
            self.assertIsNone(result[field], field)
        self.assertEqual(result['platform_spend'], '19.80')

    def test_settlement_only_row_is_scope_and_never_zero_filled(self):
        result = reconcile(snapshot(), settlement(row(), row(key='acct-elsewhere', spend='12.50', results=1)))
        extra = status_of(result, 'acct-elsewhere')
        self.assertEqual((extra['status'], extra['side']), (rules.RECON_SCOPE, 'settlement_only'))
        self.assertIsNone(extra['platform_spend'])
        self.assertIsNone(extra['platform_results'])
        self.assertEqual(extra['settled_spend'], '12.50')
        self.assertEqual(result['summary'][rules.RECON_SCOPE], 1)

    def test_scope_does_not_downgrade_by_default(self):
        self.assertFalse(status_of(reconcile(snapshot(), settlement()))['downgrade'])

    def test_incomplete_platform_totals_are_a_gap(self):
        snap = snapshot(account(adsets=[adset(), adset(key='adset-2', spend=None)]))
        result = status_of(reconcile(snap, settlement(row())))
        self.assertEqual(result['status'], rules.RECON_GAP)
        self.assertIsNone(result['platform_spend'])
        self.assertIn('missing is not zero', ' '.join(result['reasons']))

    def test_account_without_adsets_has_no_platform_total(self):
        result = status_of(reconcile(snapshot(account(adsets=[])), settlement()))
        self.assertIsNone(result['platform_spend'])
        self.assertIsNone(result['platform_results'])

    def test_zero_on_both_sides_is_ok_but_zero_against_spend_is_not(self):
        snap = snapshot(account(adsets=[adset(spend='0.00', results=0)]))
        self.assertEqual(status_of(reconcile(snap, settlement(row(spend='0.00', results=0))))['status'],
                         rules.RECON_OK)
        gap = status_of(reconcile(snap, settlement(row(spend='5.00', results=1))))
        self.assertEqual(gap['status'], rules.RECON_GAP)
        self.assertIn('where the platform shows 0', ' '.join(gap['reasons']))


class EconomicsTests(unittest.TestCase):
    def test_settled_cpa_is_compared_with_the_settled_target(self):
        result = status_of(reconcile(snapshot(), settlement(row())))
        # T = 10 x 0.90 / 1.25 = 7.20 per platform lead; 10 / 1.25 = 8.00 per approved lead.
        self.assertEqual((result['T'], result['settled_target']), ('7.20', '8.00'))
        self.assertEqual((result['platform_cpa'], result['settled_cpa']), ('6.60', '6.60'))
        self.assertEqual(result['settled_roas'], '1.5152')

    def test_tolerances_come_only_from_the_methodology(self):
        settle = settlement(row(spend='19.00'))   # -4.04% spend
        self.assertEqual(status_of(reconcile(snapshot(), settle))['status'], rules.RECON_GAP)
        document = methodology()
        document['reconciliation']['spend_tolerance_pct'] = '5'
        self.assertEqual(status_of(reconcile(snapshot(), settle, document))['status'], rules.RECON_OK)

    def test_missing_policy_is_rejected_when_a_settlement_is_supplied(self):
        for key in ('spend_tolerance_pct', 'results_tolerance_pct', 'downgrade_on', 'downgrade_codes'):
            with self.subTest(key=key):
                document = methodology()
                del document['reconciliation'][key]
                with self.assertRaises(rules.RuleError):
                    reconcile(snapshot(), settlement(row()), document)
        document = methodology()
        del document['reconciliation']
        rules.validate_methodology(document)   # optional until a settlement is supplied
        with self.assertRaises(rules.RuleError):
            reconcile(snapshot(), settlement(row()), document)

    def test_policy_rejects_unknown_codes(self):
        for key, value in (('downgrade_on', ['RECON_OK']), ('downgrade_on', ['RECON_BOGUS']),
                           ('downgrade_codes', ['LADDER_HOLD']), ('downgrade_codes', ['NOPE'])):
            with self.subTest(key=key, value=value):
                document = methodology()
                document['reconciliation'][key] = value
                with self.assertRaises(rules.RuleError):
                    rules.validate_methodology(document)


class DowngradeTests(unittest.TestCase):
    def proposals(self, settle, document=None, adsets=None):
        snap = snapshot(account(adsets=adsets))
        findings = operating_loop.collect_findings(snap, document or methodology(), settle)
        return findings['proposals']

    def test_gap_makes_a_promotion_advisory(self):
        proposals = self.proposals(settlement(row(spend='16.00')))
        promote = next(p for p in proposals if p['code'] == 'LADDER_PROMOTE')
        self.assertNotIn('target', promote)
        self.assertEqual(promote['downgraded']['status'], rules.RECON_GAP)
        self.assertIn('Measurement unreconciled (RECON_GAP)', promote['evidence'][-1])
        verdict = rules.gate([promote], {'objects': {'adset-1': {'daily_budget': '20.00'}}})[0]
        self.assertEqual(verdict['gate'], rules.ADVISORY)
        self.assertIn('Measurement unreconciled', verdict['gate_detail'][0])
        self.assertEqual(rules.writable_rows([verdict]), [])

    def test_gap_makes_an_overcost_pause_advisory(self):
        proposals = self.proposals(settlement(row(spend='30.00', results=2)),
                                   adsets=[adset(spend='40.00', results=2)])
        stop = next(p for p in proposals if p['code'] == 'TEST_STOP_OVERCOST')
        self.assertNotIn('target', stop)
        self.assertEqual(stop['downgraded']['status'], rules.RECON_GAP)

    def test_reconciled_account_keeps_its_writes(self):
        proposals = self.proposals(settlement(row()))
        promote = next(p for p in proposals if p['code'] == 'LADDER_PROMOTE')
        self.assertEqual(promote['target'], {'daily_budget': '40.00'})
        self.assertNotIn('downgraded', promote)

    def test_other_codes_are_not_downgraded(self):
        proposals = self.proposals(settlement(row(spend='5.00', results=0)),
                                   adsets=[adset(linked=False)])
        link = next(p for p in proposals if p['code'] == 'LINK_OR_TRACKING_BAD')
        self.assertEqual(link['target'], {'status': 'PAUSED'})

    def test_scope_downgrades_only_when_the_methodology_says_so(self):
        self.assertNotIn('downgraded', next(p for p in self.proposals(settlement())
                                            if p['code'] == 'LADDER_PROMOTE'))
        document = methodology()
        document['reconciliation']['downgrade_on'].append('RECON_SCOPE')
        promote = next(p for p in self.proposals(settlement(), document) if p['code'] == 'LADDER_PROMOTE')
        self.assertEqual(promote['downgraded']['status'], rules.RECON_SCOPE)

    def test_without_a_settlement_nothing_is_downgraded(self):
        findings = operating_loop.collect_findings(snapshot(), methodology())
        self.assertIsNone(findings['settlement'])
        self.assertFalse(any(p.get('downgraded') for p in findings['proposals']))

    def test_reason_text_follows_the_language(self):
        snap = snapshot()
        settle = settlement(row(spend='16.00'))
        english = status_of(reconcile(snap, settle))
        chinese = status_of(reconcile(snap, settle, lang='zh-CN'))
        self.assertEqual(english['status'], chinese['status'])
        self.assertIn('花费差', ' '.join(chinese['reasons']))


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = operating_loop.load(EXAMPLES / 'snapshot-primary.json')
        self.settlement = operating_loop.load(EXAMPLES / 'settlement-daily.json')
        self.result = reconcile(self.snapshot, self.settlement)

    def test_every_status_the_fixture_teaches(self):
        self.assertEqual({item['account_key']: (item['status'], item['side']) for item in self.result['rows']},
                         {'fictional-meta-account-a': ('RECON_OK', 'both'),
                          'fictional-meta-account-b': ('RECON_TZ', 'both'),
                          'fictional-meta-account-c': ('RECON_SCOPE', 'platform_only'),
                          'fictional-tiktok-account-d': ('RECON_GAP', 'both'),
                          'fictional-meta-account-e': ('RECON_SCOPE', 'settlement_only')})

    def test_one_account_is_deliberately_out_of_scope(self):
        keys = {item['account_key'] for item in self.settlement['rows']}
        self.assertNotIn('fictional-meta-account-c', keys)
        self.assertIn('fictional-meta-account-c', {item['account_key'] for item in self.snapshot['accounts']})

    def test_tiktok_account_looks_cheap_on_the_platform_only(self):
        d = status_of(self.result, 'fictional-tiktok-account-d')
        self.assertEqual((d['platform_cpa'], d['T']), ('4.20', '8.64'))
        self.assertEqual((d['settled_cpa'], d['settled_target']), ('9.80', '9.60'))
        self.assertEqual(d['approval_rate'], '0.429')

    def test_settlement_fixture_has_only_declared_fields_and_no_zero_filled_rows(self):
        self.assertEqual(set(self.settlement), {'schema_version', 'kind', 'notice', 'date', 'timezone',
                                                'currency', 'rows', 'scenario_notes'})
        for item in self.settlement['rows']:
            self.assertEqual(set(item), {'platform', 'account_key', 'offer_key', 'unit_price', 'spend',
                                         'results', 'value'})
            self.assertNotEqual((item['spend'], item['results']), ('0.00', 0))


if __name__ == '__main__':
    unittest.main()
