"""The operating loop must refuse to guess: unknown evidence, small samples and
unexplained current-state differences each have a distinct, testable outcome."""
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


def methodology():
    return rules.load_methodology(EXAMPLES / 'methodology-reference.json')


def adset(**overrides):
    base = {
        'adset_key': 'fictional-adset', 'name': '1n1 | X | MAX | $10',
        'campaign_key': 'fictional-campaign',
        'configured_status': 'ACTIVE', 'effective_status': 'ACTIVE',
        'bid_strategy': 'LOWEST_COST_WITHOUT_CAP', 'bid_amount': None,
        'optimization_goal': 'OFFSITE_CONVERSIONS',
        'daily_budget': '10.00', 'ladder_stage': 'T',
        'spend': '10.00', 'impressions': 1000, 'clicks': 60, 'results': 3,
        'value': '12.00', 'frequency': '1.10', 'linked': True, 'tracking_ok': True,
        'creatives': [],
    }
    base.update(overrides)
    return base


def account(adsets, **overrides):
    base = {
        'account_key': 'fictional-meta-account', 'platform': 'meta',
        'account_timezone': 'Etc/GMT', 'report_timezone': 'Etc/GMT',
        'spend_cap': '1000.00', 'balance': '500.00', 'today_spend': '50.00',
        'offer': {'offer_key': 'fictional-offer', 'unit_price': '4.000'},
        'observation': {'complete_delivery_day': True},
        'adsets': adsets,
    }
    base.update(overrides)
    return base


def codes_for(adsets, **overrides):
    proposals, _ = rules.decide_account(account(adsets, **overrides), methodology())
    return [item['code'] for item in proposals]


class TargetCostTests(unittest.TestCase):
    def test_target_is_price_over_roas(self):
        value = rules.target_cost('4.000', methodology())
        self.assertEqual(rules.num2(value), '4.71')

    def test_quality_factor_applies_before_roas(self):
        document = methodology()
        document['quality_factor'] = '0.9'
        self.assertEqual(rules.num2(rules.target_cost('4.000', document)), '4.24')

    def test_missing_price_is_rejected(self):
        document = methodology()
        with self.assertRaises(rules.RuleError):
            rules.target_cost(None, document)

    def test_ladder_multiplier_follows_declared_order(self):
        document = methodology()
        self.assertEqual(str(rules.ladder_multiplier('T', document)), '1')
        self.assertEqual(str(rules.ladder_multiplier('3T', document)), '3')
        self.assertIsNone(rules.next_stage('3T', document))


class MetricTests(unittest.TestCase):
    def test_derived_metrics(self):
        values = rules.adset_metrics(adset(spend='12.40', impressions=3200, clicks=210, results=3),
                                     '4.000', methodology())
        self.assertEqual(values['spend'], '12.40')
        self.assertEqual(values['results'], 3)
        self.assertEqual(values['cpa'], '4.13')
        self.assertEqual(values['T_display'], '4.71')
        self.assertEqual(values['stop_loss_line'], '14.12')

    def test_zero_denominator_is_missing_not_zero(self):
        values = rules.adset_metrics(adset(clicks=0, results=0), '4.000', methodology())
        # A genuine zero (nobody clicked out of 1000 impressions) stays zero...
        self.assertEqual(values['ctr'], '0.0000')
        # ...but a metric with a zero denominator is missing, not zero.
        self.assertIsNone(values['cpc'])
        self.assertIsNone(values['cpa'])
        self.assertIsNone(values['cvr'])

    def test_overcost_margin_can_be_negative(self):
        values = rules.adset_metrics(adset(spend='4.00', results=2), '4.000', methodology())
        self.assertEqual(values['overcost_margin'], '-5.41')

    def test_decimal_parsing_rejects_text(self):
        with self.assertRaises(rules.RuleError):
            rules.adset_metrics(adset(spend='not-a-number'), '4.000', methodology())


class AttributionTests(unittest.TestCase):
    def reference(self):
        return {'cpm': 58.82, 'ctr': 0.1411, 'cvr': 0.1179, 'cpa': 3.54}

    def test_terms_reconstruct_the_total(self):
        result = rules.attribution(self.reference(),
                                   {'cpm': 68.58, 'ctr': 0.1224, 'cvr': 0.0413, 'cpa': 13.57})
        self.assertTrue(result['complete'])
        # The identity holds only up to the rounding of the quoted CPA, so the
        # residual is itself the signal that the inputs are reported values.
        self.assertLess(abs(result['residual']), 0.002)
        # CVR must dominate: the cost gap is a post-click problem here.
        self.assertEqual(max(result['shares'], key=result['shares'].get), 'cvr')

    def test_missing_metric_refuses_to_attribute(self):
        broken = self.reference()
        broken['cvr'] = None
        result = rules.attribution(broken, {'cpm': 68.58, 'ctr': 0.1224, 'cvr': 0.0413, 'cpa': 13.57})
        self.assertFalse(result['complete'])
        self.assertIsNone(result['terms'])


class CreativeRuleTests(unittest.TestCase):
    def test_circuit_breaker_needs_at_least_two_creatives(self):
        single = adset(spend='30.00', results=3, creatives=[
            {'creative_key': 'only', 'spend': '30.00', 'results': 3}])
        values = rules.adset_metrics(single, '4.000', methodology())
        self.assertEqual([f['kind'] for f in rules.creative_findings(single, values, methodology())], [])

    def test_circuit_breaker_fires_on_concentration_and_cost(self):
        group = adset(spend='22.00', results=5, creatives=[
            {'creative_key': 'heavy', 'spend': '10.56', 'results': 1},
            {'creative_key': 'light', 'spend': '11.44', 'results': 4}])
        values = rules.adset_metrics(group, '4.000', methodology())
        kinds = [f['kind'] for f in rules.creative_findings(group, values, methodology())]
        self.assertIn('circuit_breaker', kinds)

    def test_fatigue_requires_all_three_conditions(self):
        group = adset(spend='10.00', results=3, creatives=[
            {'creative_key': 'tired', 'spend': '5.00', 'results': 2, 'frequency': '2.70',
             'ctr': '0.0500', 'prior_ctr': '0.0700', 'cvr': '0.0600', 'prior_cvr': '0.0900'},
            {'creative_key': 'other', 'spend': '5.00', 'results': 1}])
        values = rules.adset_metrics(group, '4.000', methodology())
        self.assertIn('fatigue', [f['kind'] for f in rules.creative_findings(group, values, methodology())])

        # Drop the frequency below the threshold: CTR and CVR drops alone are noise.
        group['creatives'][0]['frequency'] = '1.20'
        values = rules.adset_metrics(group, '4.000', methodology())
        self.assertNotIn('fatigue', [f['kind'] for f in rules.creative_findings(group, values, methodology())])

    def test_overflow_uses_declared_cap(self):
        group = adset(spend='10.00', results=3, creatives=[
            {'creative_key': f'k{i}', 'spend': '1.00', 'results': 0} for i in range(9)])
        values = rules.adset_metrics(group, '4.000', methodology())
        self.assertIn('creative_count', [f['kind'] for f in rules.creative_findings(group, values, methodology())])


class StructureTests(unittest.TestCase):
    def test_name_mismatch_is_flagged(self):
        found = rules.structure_findings(
            account([adset(name='1n1 | X | MAX | $10', bid_strategy='LOWEST_COST_WITH_COST_CAP',
                           bid_amount='4.70')]), methodology())
        self.assertIn('name_mismatch', [f['kind'] for f in found])

    def test_effective_status_is_read_separately(self):
        found = rules.structure_findings(
            account([adset(configured_status='ACTIVE', effective_status='DISAPPROVED')]), methodology())
        self.assertIn('effective_status', [f['kind'] for f in found])

    def test_null_cap_is_a_capability_gap_not_a_zero(self):
        found = rules.structure_findings(account([adset()], spend_cap=None), methodology())
        self.assertIn('capability_gap', [f['kind'] for f in found])


class DecisionTests(unittest.TestCase):
    def test_healthy_stage_promotes_and_doubles_budget(self):
        proposals, _ = rules.decide_account(account([adset()]), methodology())
        promote = [p for p in proposals if p['code'] == 'LADDER_PROMOTE']
        self.assertEqual(len(promote), 1)
        self.assertEqual(promote[0]['baseline'], {'daily_budget': '10.00'})
        self.assertEqual(promote[0]['target'], {'daily_budget': '20.00'})

    def test_zero_conversion_below_sample_gate_is_not_judged(self):
        self.assertEqual(codes_for([adset(spend='3.10', impressions=180, clicks=12, results=0)]),
                         ['TEST_UNDERTESTED'])

    def test_zero_conversion_with_sample_and_loss_line_stops(self):
        self.assertEqual(codes_for([adset(spend='15.30', impressions=420, clicks=26, results=0)]),
                         ['TEST_STOP_NOCONV'])

    def test_zero_conversion_early_stop_on_expensive_click(self):
        self.assertEqual(codes_for([adset(spend='6.00', impressions=120, clicks=4, results=0)]),
                         ['TEST_EARLY_STOP'])

    def test_overcost_margin_triggers_stop(self):
        self.assertEqual(codes_for([adset(spend='30.00', impressions=9100, clicks=540, results=3)]),
                         ['TEST_STOP_OVERCOST'])

    def test_incomplete_delivery_day_blocks_promotion(self):
        proposals, _ = rules.decide_account(
            account([adset()], observation={'complete_delivery_day': False}), methodology())
        self.assertEqual([p['code'] for p in proposals], [])

    def test_under_delivering_is_reported_separately_from_over_cost(self):
        proposals, _ = rules.decide_account(
            account([adset(daily_budget='20.00', spend='6.40', impressions=1500, clicks=96, results=4)]),
            methodology())
        self.assertEqual([p['code'] for p in proposals], ['TEST_UNDERTESTED'])
        self.assertIn('花不动', ' '.join(proposals[0]['evidence']))

    def test_link_failure_pauses_without_waiting(self):
        proposals, _ = rules.decide_account(account([adset(linked=False)]), methodology())
        self.assertEqual([p['code'] for p in proposals], ['LINK_OR_TRACKING_BAD'])
        self.assertEqual(proposals[0]['target'], {'status': 'PAUSED'})

    def test_disapproved_ad_is_not_treated_as_a_delivery_problem(self):
        self.assertEqual(codes_for([adset(effective_status='DISAPPROVED')]), ['AD_STATUS'])

    def test_account_level_signals(self):
        stopped = codes_for([], today_spend='0.00')
        self.assertIn('ACC_STOPPED', stopped)
        low = codes_for([adset()], balance='41.20')
        self.assertIn('ACC_BALANCE_LOW', low)
        silent = codes_for([adset()], today_spend='0.00')
        self.assertIn('ACC_NO_DELIVERY', silent)

    def test_unreadable_metric_blocks_instead_of_passing(self):
        proposals, diagnostics = rules.decide_account(
            account([adset(spend=None)]), methodology())
        self.assertEqual([p['code'] for p in proposals], [])
        self.assertTrue(any(item.get('blocked') for item in diagnostics))


class GateTests(unittest.TestCase):
    def verdict(self, code='LADDER_PROMOTE', baseline=None, target=None, writeback=None):
        proposals = [{'code': code, 'level': 'P1', 'object_type': 'adset',
                      'object_key': 'obj', 'account_key': 'acct', 'offer_key': 'offer',
                      'action': 'x', 'window': 'y', 'acceptance': 'z', 'stop_condition': 'w',
                      'evidence': []}
                     ]
        if target is not None:
            proposals[0]['baseline'] = baseline or {}
            proposals[0]['target'] = target
        return rules.gate(proposals, writeback or {'objects': {}})[0]

    def test_ready_when_value_matches_baseline(self):
        verdict = self.verdict(baseline={'daily_budget': '10.00'}, target={'daily_budget': '20.00'},
                               writeback={'objects': {'obj': {'daily_budget': '10.00'}}})
        self.assertEqual(verdict['gate'], rules.READY)
        self.assertEqual(verdict['writable_fields'], ['daily_budget'])

    def test_satisfied_when_target_already_in_place(self):
        verdict = self.verdict(baseline={'status': 'ACTIVE'}, target={'status': 'PAUSED'},
                               writeback={'objects': {'obj': {'status': 'PAUSED'}}})
        self.assertEqual(verdict['gate'], rules.SATISFIED)
        self.assertEqual(verdict['writable_fields'], [])

    def test_conflict_when_current_value_matches_neither_baseline_nor_target(self):
        verdict = self.verdict(baseline={'daily_budget': '10.00'}, target={'daily_budget': '20.00'},
                               writeback={'objects': {'obj': {'daily_budget': '30.00'}}})
        self.assertEqual(verdict['gate'], rules.CONFLICT)
        self.assertEqual(verdict['conflict_fields'], ['daily_budget'])
        self.assertEqual(verdict['writable_fields'], [])

    def test_absent_object_is_unknown(self):
        verdict = self.verdict(baseline={'daily_budget': '10.00'}, target={'daily_budget': '20.00'},
                               writeback={'objects': {}})
        self.assertEqual(verdict['gate'], rules.UNKNOWN)

    def test_absent_field_is_unknown_not_ready(self):
        verdict = self.verdict(baseline={'bid_amount': None}, target={'bid_amount': '4.70'},
                               writeback={'objects': {'obj': {'daily_budget': '10.00'}}})
        self.assertEqual(verdict['gate'], rules.UNKNOWN)

    def test_absent_baseline_field_is_unknown_not_ready(self):
        verdict = self.verdict(baseline={}, target={'daily_budget': '20.00'},
                               writeback={'objects': {'obj': {'daily_budget': '30.00'}}})
        self.assertEqual(verdict['gate'], rules.UNKNOWN)
        self.assertEqual(verdict['writable_fields'], [])
        self.assertEqual(rules.writable_rows([verdict]), [])
        self.assertIn('基线未记录', ' '.join(verdict['gate_detail']))

    def test_omitted_baseline_document_is_unknown(self):
        verdict = rules.gate(
            [{'object_key': 'obj', 'target': {'daily_budget': '20.00'}}],
            {'objects': {'obj': {'daily_budget': '30.00'}}})[0]
        self.assertEqual(verdict['gate'], rules.UNKNOWN)
        self.assertEqual(rules.writable_rows([verdict]), [])

    def test_null_baseline_is_unknown_even_when_current_is_null(self):
        for present in ('30.00', None):
            with self.subTest(present=present):
                verdict = self.verdict(
                    baseline={'daily_budget': None}, target={'daily_budget': '20.00'},
                    writeback={'objects': {'obj': {'daily_budget': present}}})
                self.assertEqual(verdict['gate'], rules.UNKNOWN)
                self.assertEqual(verdict['writable_fields'], [])
                self.assertEqual(rules.writable_rows([verdict]), [])
                self.assertIn('基线明确为 null', ' '.join(verdict['gate_detail']))

    def test_missing_or_null_baseline_does_not_block_an_already_satisfied_target(self):
        for baseline in ({}, {'daily_budget': None}):
            for target in ('20.00', None):
                with self.subTest(baseline=baseline, target=target):
                    verdict = self.verdict(
                        baseline=baseline, target={'daily_budget': target},
                        writeback={'objects': {'obj': {'daily_budget': target}}})
                    self.assertEqual(verdict['gate'], rules.SATISFIED)
                    self.assertEqual(verdict['satisfied_fields'], ['daily_budget'])
                    self.assertEqual(verdict['writable_fields'], [])
                    self.assertEqual(rules.writable_rows([verdict]), [])

    def test_zero_is_a_recorded_baseline(self):
        verdict = self.verdict(baseline={'daily_budget': 0}, target={'daily_budget': '20.00'},
                               writeback={'objects': {'obj': {'daily_budget': '0.00'}}})
        self.assertEqual(verdict['gate'], rules.READY)
        self.assertEqual(rules.writable_rows([verdict])[0]['patch'], {'daily_budget': '20.00'})

    def test_satisfied_field_needs_no_baseline_when_another_field_is_ready(self):
        verdict = self.verdict(
            baseline={'daily_budget': '10.00'},
            target={'daily_budget': '20.00', 'status': 'PAUSED'},
            writeback={'objects': {'obj': {'daily_budget': '10.00', 'status': 'PAUSED'}}})
        self.assertEqual(verdict['gate'], rules.READY)
        self.assertEqual(rules.writable_rows([verdict])[0]['patch'], {'daily_budget': '20.00'})

    def test_unknown_baseline_blocks_the_whole_row_but_not_other_rows(self):
        for status_baseline in ({}, {'status': None}):
            with self.subTest(status_baseline=status_baseline):
                blocked = self.verdict(
                    baseline={'daily_budget': '10.00', **status_baseline},
                    target={'daily_budget': '20.00', 'status': 'PAUSED'},
                    writeback={'objects': {'obj': {'daily_budget': '10.00', 'status': 'ACTIVE'}}})
                ready = self.verdict(
                    baseline={'daily_budget': '10.00'}, target={'daily_budget': '20.00'},
                    writeback={'objects': {'obj': {'daily_budget': '10.00'}}})
                ready['object_key'] = 'another-object'
                self.assertEqual(blocked['gate'], rules.UNKNOWN)
                self.assertEqual(blocked['writable_fields'], [])
                self.assertEqual([row['object_key'] for row in rules.writable_rows([blocked, ready])],
                                 ['another-object'])

    def test_unknown_baseline_preserves_other_field_conflicts(self):
        for fields in [('daily_budget', 'status'), ('status', 'daily_budget')]:
            with self.subTest(fields=fields):
                targets = {'daily_budget': '20.00', 'status': 'PAUSED'}
                verdict = self.verdict(
                    baseline={'daily_budget': '10.00'},
                    target={field: targets[field] for field in fields},
                    writeback={'objects': {'obj': {'daily_budget': '30.00', 'status': 'ACTIVE'}}})
                self.assertEqual(verdict['gate'], rules.UNKNOWN)
                self.assertEqual(verdict['conflict_fields'], ['daily_budget'])
                self.assertEqual(verdict['writable_fields'], [])
                self.assertIn('基线未记录', ' '.join(verdict['gate_detail']))
                self.assertIn('暂缓修改并核对变更来源', ' '.join(verdict['gate_detail']))

    def test_generated_pause_preserves_missing_and_null_status_baselines(self):
        for code, overrides in (
                ('LINK_OR_TRACKING_BAD', {'linked': False}),
                ('TEST_STOP_NOCONV', {'results': 0, 'spend': '20.00', 'impressions': 1800})):
            for missing in (True, False):
                with self.subTest(code=code, missing=missing):
                    source = adset(configured_status=None, **overrides)
                    if missing:
                        del source['configured_status']
                    proposals, _ = rules.decide_account(account([source]), methodology())
                    proposed = next(item for item in proposals if item['code'] == code)
                    self.assertEqual(proposed['baseline'], {} if missing else {'status': None})
                    verdict = rules.gate([proposed], {'objects': {
                        source['adset_key']: {'status': 'ACTIVE'}}})[0]
                    self.assertEqual(verdict['gate'], rules.UNKNOWN)
                    self.assertEqual(rules.writable_rows([verdict]), [])

    def test_finding_without_write_intent_is_advisory(self):
        verdict = self.verdict(code='TEST_UNDERTESTED')
        self.assertEqual(verdict['gate'], rules.ADVISORY)

    def test_only_ready_rows_enter_the_write_plan(self):
        proposals = [
            {'code': 'A', 'level': 'P1', 'object_type': 'adset', 'object_key': 'one',
             'baseline': {'daily_budget': '10.00'}, 'target': {'daily_budget': '20.00'}},
            {'code': 'B', 'level': 'P1', 'object_type': 'adset', 'object_key': 'two',
             'baseline': {'status': 'ACTIVE'}, 'target': {'status': 'PAUSED'}},
            {'code': 'C', 'level': 'P1', 'object_type': 'adset', 'object_key': 'three'},
        ]
        verdicts = rules.gate(proposals, {'objects': {'one': {'daily_budget': '10.00'},
                                                      'two': {'status': 'PAUSED'}}})
        plan = rules.writable_rows(verdicts)
        self.assertEqual([row['object_key'] for row in plan], ['one'])
        self.assertEqual(plan[0]['patch'], {'daily_budget': '20.00'})
        summary = rules.gate_summary(verdicts)
        self.assertEqual(summary[rules.ADVISORY], 1)
        self.assertEqual(summary['needs_human'], 0)

    def test_reconcile_detects_a_write_that_did_not_take_effect(self):
        verdicts = rules.gate(
            [{'code': 'A', 'level': 'P1', 'object_type': 'adset', 'object_key': 'one',
              'baseline': {'daily_budget': '10.00'}, 'target': {'daily_budget': '20.00'}}],
            {'objects': {'one': {'daily_budget': '10.00'}}})
        report = rules.reconcile(verdicts, {'one': {'daily_budget': '10.00'}})
        self.assertTrue(report[0]['checked'])
        self.assertFalse(report[0]['effective'])


class SnapshotContractTests(unittest.TestCase):
    def test_reference_fixtures_are_valid(self):
        snapshot = operating_loop.load(EXAMPLES / 'snapshot-primary.json')
        operating_loop.validate_snapshot(snapshot)
        self.assertEqual(len(snapshot['accounts']), 3)

    def test_snapshot_without_unit_price_is_rejected(self):
        snapshot = operating_loop.load(EXAMPLES / 'snapshot-primary.json')
        broken = copy.deepcopy(snapshot)
        del broken['accounts'][0]['offer']['unit_price']
        with self.assertRaises(operating_loop.LoopError):
            operating_loop.validate_snapshot(broken)

    def test_snapshot_without_as_of_is_rejected(self):
        snapshot = operating_loop.load(EXAMPLES / 'snapshot-primary.json')
        broken = copy.deepcopy(snapshot)
        del broken['as_of']
        with self.assertRaises(operating_loop.LoopError):
            operating_loop.validate_snapshot(broken)

    def test_duplicate_account_keys_are_rejected(self):
        snapshot = operating_loop.load(EXAMPLES / 'snapshot-primary.json')
        broken = copy.deepcopy(snapshot)
        broken['accounts'][1]['account_key'] = broken['accounts'][0]['account_key']
        with self.assertRaises(operating_loop.LoopError):
            operating_loop.validate_snapshot(broken)


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / 'round'
        self.ledger = Path(self.tmp.name) / 'ledger.jsonl'

    def tearDown(self):
        self.tmp.cleanup()

    def run_round(self):
        import io
        import contextlib
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = operating_loop.main([
                'round',
                '--snapshot', str(EXAMPLES / 'snapshot-primary.json'),
                '--writeback', str(EXAMPLES / 'writeback-snapshot.json'),
                '--after', str(EXAMPLES / 'after-snapshot.json'),
                '--methodology', str(EXAMPLES / 'methodology-reference.json'),
                '--settlement', str(EXAMPLES / 'settlement-daily.json'),
                '--ledger', str(self.ledger),
                '--out', str(self.out),
                '--at', '2026-09-24T03:58:00+00:00',
            ])
        self.assertEqual(code, 0)
        return json.loads(stdout.getvalue())

    def test_round_produces_every_artifact(self):
        summary = self.run_round()
        for name in ('findings.json', 'gate.json', 'application.json',
                     'reconciliation.json', 'report.md', 'round-summary.json'):
            self.assertTrue((self.out / name).is_file(), name)
        self.assertEqual(summary['native_platform_calls'], 0)
        self.assertEqual(summary['mode'], 'offline_analysis_only')

    def test_round_never_writes_more_than_the_ready_rows(self):
        summary = self.run_round()
        self.assertEqual(summary['planned_writes'], summary['gate']['ready'])
        self.assertLess(summary['planned_writes'], summary['proposals'])

    def test_baseline_gaps_stay_out_of_write_plan_and_remain_in_the_ledger(self):
        findings = {'round_id': 'baseline-gaps', 'proposals': [
            {'code': 'MISSING', 'object_key': 'missing', 'target': {'daily_budget': '20.00'}},
            {'code': 'NULL', 'object_key': 'null', 'baseline': {'daily_budget': None},
             'target': {'daily_budget': '20.00'}},
        ]}
        gate = operating_loop.run_gate(findings, {
            'kind': 'writeback_snapshot', 'objects': {
                'missing': {'daily_budget': '30.00'}, 'null': {'daily_budget': '30.00'}}})
        result = operating_loop.apply_gate(self.ledger, gate, '2026-09-25T00:00:00+00:00')
        self.assertEqual(result['planned_writes'], 0)
        self.assertEqual(result['write_plan'], [])
        self.assertEqual(gate['summary'][rules.UNKNOWN], 2)
        events = operating_loop.read_events(self.ledger)
        self.assertEqual(len(events), 2)
        for event, verdict in zip(events, gate['verdicts']):
            self.assertEqual(event['type'], 'skipped')
            self.assertIn('原方案基线证据不足', event['reason'])
            self.assertEqual(event['detail'], verdict['gate_detail'])
        self.assertIn('基线未记录', ' '.join(events[0]['detail']))
        self.assertIn('基线明确为 null', ' '.join(events[1]['detail']))

    def test_round_catches_the_ineffective_write(self):
        summary = self.run_round()
        self.assertEqual(summary['reconciliation']['ineffective'], 1)

    def test_ledger_is_append_only_and_folds(self):
        self.run_round()
        first = len(operating_loop.read_events(self.ledger))
        self.run_round()
        second = len(operating_loop.read_events(self.ledger))
        self.assertGreater(second, first)
        rows = operating_loop.fold(self.ledger)
        self.assertTrue(rows)

    def test_open_rows_keep_the_ineffective_write_visible(self):
        self.run_round()
        rows = operating_loop.open_rows(self.ledger)
        self.assertTrue(any(row.get('status') == 'verified_not_effective' for row in rows))

    def test_report_states_the_conflict_and_the_ineffective_write(self):
        self.run_round()
        report = (self.out / 'report.md').read_text(encoding='utf-8')
        self.assertIn('冲突隔离', report)
        self.assertIn('当前值 30.00 与基线 10.00、目标 20.00 均不一致', report)
        self.assertIn('暂缓修改并核对变更来源', report)
        self.assertNotIn('人工改过', report)
        self.assertIn('未生效', report)
        self.assertIn('不连接任何广告平台', report)

    def test_repeat_run_is_deterministic(self):
        first = self.run_round()['snapshot_hash']
        second = self.run_round()['snapshot_hash']
        self.assertEqual(first, second)

    def test_corrupt_ledger_line_does_not_erase_history(self):
        self.run_round()
        with open(self.ledger, 'a', encoding='utf-8') as handle:
            handle.write('{not json}\n')
        events = operating_loop.read_events(self.ledger)
        self.assertTrue(any(event.get('type') == 'corrupt' for event in events))
        self.assertTrue(operating_loop.fold(self.ledger))

    def test_blocked_round_returns_two_without_a_traceback(self):
        import io
        import contextlib
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = operating_loop.main([
                'diagnose',
                '--snapshot', str(EXAMPLES / 'writeback-snapshot.json'),
                '--methodology', str(EXAMPLES / 'methodology-reference.json'),
                '--out', str(self.out),
            ])
        self.assertEqual(code, 2)
        self.assertIn('blocked', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
