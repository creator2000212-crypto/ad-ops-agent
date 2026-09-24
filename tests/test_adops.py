import contextlib
import copy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adops
import onboarding

ROOT = Path(__file__).resolve().parents[1]


class OfflineContractTests(unittest.TestCase):
    def setUp(self):
        self.brief = adops.load(ROOT / 'examples' / 'brief.json')
        self.candidates = adops.load(ROOT / 'examples' / 'candidates.json')
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name) / 'state'
        self.addCleanup(self.temp.cleanup)
        profile = onboarding.read(ROOT / "examples" / "onboarding-learning.json")
        for check in profile["connections"]["checks"]:
            for permission in ("read", "write"):
                check[permission]["checked_at"] = datetime.now(timezone.utc).isoformat()
        self.profile_source = Path(self.temp.name) / "profile.json"
        onboarding.write(self.profile_source, profile)
        onboarding.build_context(self.profile_source, Path(self.temp.name) / "context")
        self.context = Path(self.temp.name) / "context" / "context.json"

    def ready(self):
        plan = adops.build_plan(self.brief, self.candidates, context_path=self.context)
        self.assertEqual(plan['status'], 'ready')
        return plan, adops.authorization_for(plan)

    def test_virtual_three_platform_plan_is_stable_and_metadata_only(self):
        plan, _ = self.ready()
        self.assertEqual({op['desired']['platform'] for op in plan['operations']}, adops.PLATFORMS)
        self.assertEqual(plan['plan_hash'], adops.build_plan(self.brief, self.candidates, context_path=self.context)['plan_hash'])
        for operation in plan['operations']:
            self.assertEqual(operation['adapter'], 'simulation')
            self.assertEqual(operation['desired']['profile'], 'generic_draft')
            self.assertIsNone(operation['desired']['native_payload'])
            self.assertEqual([a['asset_id'] for a in operation['desired']['assets']], ['fictional_image_a', 'fictional_image_b'])
        decision = next(d for d in plan['asset_decisions'] if d['asset_id'] == 'fictional_unknown_size')
        self.assertEqual(decision['status'], 'excluded')
        self.assertIn('unknown: width', decision['reasons'])

    def test_missing_required_fields_block_execution(self):
        for key in ('objective', 'target_event', 'currency', 'timezone', 'budget'):
            with self.subTest(field=key):
                brief = copy.deepcopy(self.brief)
                del brief[key]
                plan = adops.build_plan(brief, self.candidates, context_path=self.context)
                self.assertEqual(plan['status'], 'needs_input')
                self.assertEqual(plan['operations'], [])
                with self.assertRaises(adops.ContractError):
                    adops.authorization_for(plan)
        for key in ('account_id', 'profile', 'budget_amount'):
            with self.subTest(target_field=key):
                brief = copy.deepcopy(self.brief)
                del brief['targets'][0][key]
                self.assertEqual(adops.build_plan(brief, self.candidates, context_path=self.context)['status'], 'needs_input')

    def test_unsupported_profile_or_configuration_never_downgrades(self):
        for mutate in (lambda b: b['targets'][2].update(profile='search'),
                       lambda b: b['targets'][2].update(profile='pmax'),
                       lambda b: b.update(mode='live'),
                       lambda b: b['budget'].update(period='daily'),
                       lambda b: b['asset_requirements'].update(visual_quality_min=8),
                       lambda b: b['targets'][0].update(automatic_audience=True),
                       lambda b: b['targets'][0].update(currency='EUR'),
                       lambda b: b.update(landing_page='https://example.invalid/unsupported'),
                       lambda b: b['budget'].update(unimplemented_spend_guard='hard')):
            brief = copy.deepcopy(self.brief)
            mutate(brief)
            plan = adops.build_plan(brief, self.candidates, context_path=self.context)
            self.assertEqual(plan['status'], 'unsupported')
            self.assertEqual(plan['operations'], [])

    def test_budget_unknown_negative_nonfinite_or_excess_is_blocked(self):
        for value in (None, True, 'NaN', 'Infinity', '-1', '0'):
            with self.subTest(value=value):
                brief = copy.deepcopy(self.brief)
                brief['budget']['amount'] = value
                self.assertEqual(adops.build_plan(brief, self.candidates, context_path=self.context)['status'], 'needs_input')
        self.brief['budget']['amount'] = '89.99'
        self.assertEqual(adops.build_plan(self.brief, self.candidates, context_path=self.context)['status'], 'needs_input')

    def test_insufficient_assets_or_duplicate_id_blocks(self):
        self.brief['asset_requirements']['count'] = 3
        self.assertEqual(adops.build_plan(self.brief, self.candidates, context_path=self.context)['status'], 'needs_input')
        self.brief['asset_requirements']['count'] = 2
        self.candidates['assets'].append(copy.deepcopy(self.candidates['assets'][0]))
        self.assertEqual(adops.build_plan(self.brief, self.candidates, context_path=self.context)['status'], 'needs_input')

    def test_modified_plan_invalidates_hash_and_old_authorization(self):
        plan, auth = self.ready()
        plan['operations'][0]['desired']['budget']['amount'] = '31.00'
        with self.assertRaisesRegex(adops.ContractError, 'hash'):
            adops.execute(plan, auth, self.state)
        plan['plan_hash'] = adops.digest({k: v for k, v in plan.items() if k != 'plan_hash'})
        with self.assertRaisesRegex(adops.ContractError, 'hash/task_id'):
            adops.execute(plan, auth, self.state)
        self.assertFalse(self.state.exists())

    def test_account_action_and_budget_authorization_are_enforced(self):
        plan, original = self.ready()
        mutations = [lambda a: a['account_scopes'][0].update(account_id='outside_account'),
                     lambda a: a['account_scopes'][0].update(max_amount='29.99'),
                     lambda a: a['account_scopes'][0].update(currency='EUR'),
                     lambda a: a.update(allowed_actions=['create_simulated_draft']),
                     lambda a: a.update(simulation_only=False)]
        for mutate in mutations:
            auth = copy.deepcopy(original)
            mutate(auth)
            with self.assertRaises(adops.ContractError):
                adops.execute(plan, auth, self.state)
        self.assertFalse(self.state.exists())

    def test_execute_then_resume_has_no_duplicate_objects_or_submissions(self):
        plan, auth = self.ready()
        first = adops.execute(plan, auth, self.state)
        second = adops.execute(plan, auth, self.state)
        self.assertEqual(first['status'], 'completed_simulation')
        self.assertEqual(first['created_this_run'], 3)
        self.assertEqual(second['created_this_run'], 0)
        self.assertEqual(second['simulated_object_count'], 3)
        self.assertEqual([r['object_id'] for r in first['receipts']], [r['object_id'] for r in second['receipts']])
        with sqlite3.connect(self.state / 'simulation.sqlite3') as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE state='submitted'").fetchone()[0], 3)

    def test_uncertain_write_is_reconciled_then_remaining_steps_resume(self):
        plan, auth = self.ready()
        interrupted = adops.execute(plan, auth, self.state, interrupt_after_write=1)
        self.assertEqual(interrupted['status'], 'interrupted')
        result = adops.execute(plan, auth, self.state)
        self.assertEqual(result['created_this_run'], 2)
        self.assertEqual(result['simulated_object_count'], 3)
        with sqlite3.connect(self.state / 'simulation.sqlite3') as db:
            states = [r[0] for r in db.execute('SELECT state FROM events WHERE operation_id=? ORDER BY seq', (interrupted['operation_id'],))]
        self.assertEqual(states, ['submitted', 'uncertain', 'reconcile', 'verified'])

    def test_unresolved_write_with_no_object_is_not_blindly_retried(self):
        plan, auth = self.ready()
        interrupted = adops.execute(plan, auth, self.state, interrupt_after_write=1)
        with sqlite3.connect(self.state / 'simulation.sqlite3') as db:
            db.execute('DELETE FROM simulated_objects WHERE operation_id=?', (interrupted['operation_id'],))
        with self.assertRaisesRegex(adops.ContractError, '禁止盲重试'):
            adops.execute(plan, auth, self.state)
        with sqlite3.connect(self.state / 'simulation.sqlite3') as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM simulated_objects').fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE state='submitted'").fetchone()[0], 1)

    def test_readback_drift_is_blocked_without_overwrite(self):
        plan, auth = self.ready()
        adops.execute(plan, auth, self.state)
        with sqlite3.connect(self.state / 'simulation.sqlite3') as db:
            db.execute("UPDATE simulated_objects SET payload='{}' WHERE operation_id=?", (plan['operations'][0]['operation_id'],))
        with self.assertRaisesRegex(adops.ContractError, '读回与期望配置不同'):
            adops.execute(plan, auth, self.state)
        latest = adops.load(self.state / 'result.json')
        self.assertEqual(latest['status'], 'blocked')
        self.assertIn('读回与期望配置不同', latest['error'])
        with sqlite3.connect(self.state / 'simulation.sqlite3') as db:
            self.assertEqual(db.execute('SELECT state FROM events ORDER BY seq DESC LIMIT 1').fetchone()[0], 'blocked')

    def test_invalid_authorization_or_other_plan_preserves_existing_state(self):
        plan, auth = self.ready()
        adops.execute(plan, auth, self.state)
        previous = (self.state / 'result.json').read_bytes()
        bad_auth = copy.deepcopy(auth)
        bad_auth['allowed_actions'] = []
        with self.assertRaises(adops.ContractError):
            adops.execute(plan, bad_auth, self.state)
        self.assertEqual((self.state / 'result.json').read_bytes(), previous)
        self.brief['task_id'] = 'different-task'
        other, other_auth = self.ready()
        with self.assertRaisesRegex(adops.ContractError, '另一个计划'):
            adops.execute(other, other_auth, self.state)
        self.assertEqual((self.state / 'result.json').read_bytes(), previous)

    def test_cli_live_is_rejected_before_loading_any_input(self):
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            code = adops.main(['execute', '--plan', 'not-read.json', '--authorization', 'not-read.json', '--state', str(self.state), '--mode', 'live'])
        self.assertEqual(code, 2)
        self.assertIn('live', errors.getvalue())
        self.assertFalse(self.state.exists())


if __name__ == '__main__':
    unittest.main()
