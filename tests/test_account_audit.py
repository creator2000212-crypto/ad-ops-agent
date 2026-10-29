"""The account audit catches what went wrong on live accounts in October 2026.

Each test mirrors one incident: a budget written in the wrong unit, an ad set
whose name named a different offer than its link, an outside tool that kept
changing budgets, a full day counted from an intraday start or a fixed UTC
offset, an ad set counted live with no active ad, a targeting update that would
have cleared the rest of the targeting, a locked field, a paused batch that
duplicated live ad sets, and writes sent to a disabled account.
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
import account_audit

FIXTURES = ROOT / 'examples' / 'audit'
AS_OF = '2026-10-27T12:00:00Z'


def policy():
    return json.loads((FIXTURES / 'policy.json').read_text(encoding='utf-8'))


def fixture():
    return json.loads((FIXTURES / 'snapshot.json').read_text(encoding='utf-8'))


def ad(key='ad-1', status='ACTIVE', offer='o-101', fingerprint='fp-1'):
    return {'ad_key': key, 'status': status, 'creative_fingerprint': fingerprint,
            'destination_url': f'https://go.example.com/r/{offer}?sub1={{{{ad.id}}}}'}


def adset(key='as-1', name='1n1 | o-101 | C1 | $5', status='ACTIVE', budget=500, ads=None,
          created='2026-10-01T09:00:00Z', spend=None, today=0, **extra):
    item = {'adset_key': key, 'name': name, 'status': status, 'created_at': created,
            'daily_budget_minor': budget,
            'spend_minor_by_day': spend if spend is not None else
            {'2026-10-24': 450, '2026-10-25': 480, '2026-10-26': 470},
            'spend_minor_today': today,
            'ads': ads if ads is not None else [ad(key='ad-' + key)]}
    item.update(extra)
    return item


def account(key='acct-1', adsets=None, status='ACTIVE', tz='Etc/GMT', since='2026-10-20T12:00:00Z',
            campaign_status='ACTIVE'):
    return {'account_key': key, 'status': status, 'timezone_name': tz, 'activity_since': since,
            'campaigns': [{'campaign_key': 'cmp-' + key, 'name': 'LG', 'status': campaign_status,
                           'adsets': adsets if adsets is not None else [adset()]}]}


def snapshot(accounts=None, activity=None, requests=None, as_of=AS_OF):
    return {'kind': 'account_audit_snapshot', 'as_of': as_of, 'platform': 'meta', 'currency': 'USD',
            'accounts': accounts if accounts is not None else [account()],
            'activity': activity or [], 'write_requests': requests or []}


def budget_change(at, key, old, new, writer='owner-console', account_key='acct-1'):
    return {'at': at, 'account_key': account_key, 'object_key': key, 'writer': writer,
            'event': 'budget_change', 'old_minor': old, 'new_minor': new}


def request(key='w1', object_key='as-1', field='daily_budget', value='10.00', unit='major', **extra):
    item = {'request_key': key, 'account_key': 'acct-1', 'object_key': object_key, 'field': field,
            'value': value}
    if unit is not None:
        item['unit'] = unit
    item.update(extra)
    return item


def codes(result, object_key=None):
    return [item['code'] for item in result['findings']
            if object_key is None or item['object_key'] == object_key]


def decision(result, key='w1'):
    row = next(item for item in result['requests'] if item['request_key'] == key)
    return row['decision'], row['code']


def tier(result, key='as-1'):
    return next(item for item in result['tiers'] if item['adset_key'] == key)


class CleanTests(unittest.TestCase):
    def test_clean_account_has_no_findings(self):
        result = account_audit.audit(snapshot(), policy())
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['counts'], {'P0': 0, 'P1': 0, 'P2': 0})
        self.assertEqual(result['native_platform_calls'], 0)
        self.assertEqual(tier(result)['full_day'], 'yes')

    def test_fixture_shows_every_finding(self):
        result = account_audit.audit(fixture(), policy())
        self.assertEqual(result['counts'], {'P0': 2, 'P1': 5, 'P2': 3})
        self.assertEqual(result['decisions'], {'allow': 4, 'refuse': 6, 'wait': 2})
        self.assertEqual(set(codes(result)), set(account_audit.SEVERITY) - {'OFFER_LINK_UNREADABLE',
                                                                            'OFFER_NOT_DECLARED'})

    def test_empty_read_fails_instead_of_looking_healthy(self):
        with self.assertRaisesRegex(account_audit.AuditError, 'no accounts'):
            account_audit.audit(snapshot(accounts=[]), policy())


class BudgetTests(unittest.TestCase):
    """Oct 25: a connector field in dollars was written as if it were cents."""

    def test_budget_at_p0_line_is_p0_even_when_paused(self):
        result = account_audit.audit(snapshot([account(adsets=[adset(status='PAUSED', budget=100000,
                                                                       name='1n1 | o-101 | C1 | $1000')])]),
                                     policy())
        self.assertEqual(codes(result), ['BUDGET_CANARY'])
        self.assertEqual(result['findings'][0]['level'], 'P0')

    def test_live_budget_with_no_spend_is_p1(self):
        quiet = adset(name='1n1 | o-101 | C1 | $150', budget=15000,
                      spend={'2026-10-24': 0, '2026-10-25': 0, '2026-10-26': 0})
        self.assertEqual(codes(account_audit.audit(snapshot([account(adsets=[quiet])]), policy())),
                         ['BUDGET_NO_SPEND'])

    def test_missing_day_is_not_counted_as_zero_spend(self):
        quiet = adset(name='1n1 | o-101 | C1 | $150', budget=15000, spend={'2026-10-25': 0, '2026-10-26': 0})
        self.assertEqual(codes(account_audit.audit(snapshot([account(adsets=[quiet])]), policy())), [])

    def test_budget_far_above_recent_spend_is_p1(self):
        big = adset(name='1n1 | o-101 | C1 | $120', budget=12000,
                    spend={'2026-10-24': 800, '2026-10-25': 800, '2026-10-26': 800})
        result = account_audit.audit(snapshot([account(adsets=[big])]), policy())
        self.assertEqual(codes(result), ['BUDGET_FAR_ABOVE_SPEND'])
        self.assertEqual(result['findings'][0]['detail']['multiple'], '15.0')

    def test_name_budget_that_drifted_from_the_field(self):
        stale = adset(name='1n1 | o-101 | C1 | $5', budget=15000, spend={'2026-10-24': 9000, '2026-10-25': 9000,
                                                                           '2026-10-26': 9000})
        self.assertEqual(codes(account_audit.audit(snapshot([account(adsets=[stale])]), policy())),
                         ['NAME_BUDGET_STALE'])

    def test_money_without_unit_is_refused_not_guessed(self):
        result = account_audit.audit(snapshot(requests=[request(value='1000', unit=None)]), policy())
        self.assertEqual(decision(result), ('refuse', 'UNIT_MISSING'))

    def test_minor_and_major_units_convert_to_the_same_budget(self):
        major = account_audit.audit(snapshot(requests=[request(value='10.00', unit='major')]), policy())
        minor = account_audit.audit(snapshot(requests=[request(value='1000', unit='minor')]), policy())
        self.assertEqual(decision(major), ('allow', 'BUDGET_OK'))
        self.assertEqual(major['requests'][0]['detail'], minor['requests'][0]['detail'])

    def test_fraction_of_a_minor_unit_is_refused(self):
        result = account_audit.audit(snapshot(requests=[request(value='10.005', unit='major')]), policy())
        self.assertEqual(decision(result), ('refuse', 'UNIT_INVALID'))

    def test_budget_at_ceiling_is_refused_even_with_a_reason(self):
        result = account_audit.audit(snapshot(requests=[request(value='100.00', override_reason='scale')]), policy())
        self.assertEqual(decision(result), ('refuse', 'ABOVE_CEILING'))

    def test_one_ladder_step_passes_and_a_larger_raise_needs_a_reason(self):
        ok = account_audit.audit(snapshot(requests=[request(value='10.00')]), policy())
        big = account_audit.audit(snapshot(requests=[request(value='10.01')]), policy())
        reasoned = account_audit.audit(snapshot(requests=[request(value='20.00', override_reason='restore')]),
                                       policy())
        self.assertEqual(decision(ok), ('allow', 'BUDGET_OK'))
        self.assertEqual(decision(big), ('refuse', 'RAISE_TOO_LARGE'))
        self.assertEqual(decision(reasoned), ('allow', 'RAISE_OVERRIDE'))

    def test_blank_reason_does_not_override(self):
        result = account_audit.audit(snapshot(requests=[request(value='20.00', override_reason='  ')]), policy())
        self.assertEqual(decision(result), ('refuse', 'RAISE_TOO_LARGE'))

    def test_cut_below_todays_spend_waits_for_the_next_account_day(self):
        spent = account(adsets=[adset(budget=5000, name='1n1 | o-101 | C1 | $50', today=1500,
                                      spend={'2026-10-24': 4000, '2026-10-25': 4000, '2026-10-26': 4000})])
        result = account_audit.audit(snapshot([spent], requests=[request(value='5.00')]), policy())
        self.assertEqual(decision(result), ('wait', 'INTRADAY_CUT'))
        self.assertEqual(result['requests'][0]['detail']['when'], '2026-10-28 00:00')

    def test_cut_above_todays_spend_is_allowed(self):
        spent = account(adsets=[adset(budget=5000, name='1n1 | o-101 | C1 | $50', today=100,
                                      spend={'2026-10-24': 4000, '2026-10-25': 4000, '2026-10-26': 4000})])
        result = account_audit.audit(snapshot([spent], requests=[request(value='5.00')]), policy())
        self.assertEqual(decision(result), ('allow', 'BUDGET_OK'))

    def test_unknown_currency_is_refused(self):
        document = snapshot()
        document['currency'] = 'XYZ'
        with self.assertRaisesRegex(account_audit.AuditError, 'refused, not guessed'):
            account_audit.audit(document, policy())


class LiveTests(unittest.TestCase):
    def test_active_ad_set_without_active_ad_is_a_shell(self):
        shell = adset(ads=[ad(status='PAUSED')])
        result = account_audit.audit(snapshot([account(adsets=[shell])]), policy())
        self.assertEqual(codes(result), ['SHELL_ADSET'])
        self.assertEqual(result['tiers'], [])
        self.assertEqual(result['accounts'][0]['live_adsets'], 0)

    def test_paused_campaign_makes_its_ad_sets_not_live_without_a_finding(self):
        result = account_audit.audit(snapshot([account(campaign_status='PAUSED')]), policy())
        self.assertEqual(codes(result), [])
        self.assertEqual(result['accounts'][0]['live_adsets'], 0)

    def test_disabled_account_is_p0_and_its_requests_wait(self):
        result = account_audit.audit(snapshot([account(status='DISABLED')], requests=[request()]), policy())
        self.assertEqual(codes(result), ['ACCOUNT_DISABLED'])
        self.assertEqual(decision(result), ('wait', 'ACCOUNT_DISABLED'))
        self.assertEqual(result['tiers'], [])


class OfferLinkTests(unittest.TestCase):
    """Oct 26: an ad set named for one offer was sending traffic to another."""

    def test_name_and_link_disagree(self):
        wrong = adset(ads=[ad(offer='o-117')])
        result = account_audit.audit(snapshot([account(adsets=[wrong, adset(key='as-2')])]), policy())
        self.assertEqual(codes(result), ['OFFER_LINK_MISMATCH'])
        self.assertEqual(result['findings'][0]['detail']['share'], '50.0%')

    def test_two_offers_in_one_ad_set_is_a_mismatch(self):
        mixed = adset(ads=[ad(key='ad-x'), ad(key='ad-y', offer='o-117', fingerprint='fp-2')])
        self.assertEqual(codes(account_audit.audit(snapshot([account(adsets=[mixed])]), policy())),
                         ['OFFER_LINK_MISMATCH'])

    def test_link_without_offer_code_is_unverified(self):
        bare = adset()
        bare['ads'][0]['destination_url'] = 'https://go.example.com/landing'
        self.assertEqual(codes(account_audit.audit(snapshot([account(adsets=[bare])]), policy())),
                         ['OFFER_LINK_UNREADABLE'])

    def test_name_without_offer(self):
        unnamed = adset(name='1n1 | C1 | $5')
        self.assertEqual(codes(account_audit.audit(snapshot([account(adsets=[unnamed])]), policy())),
                         ['OFFER_NOT_DECLARED'])


class WriterTests(unittest.TestCase):
    """Oct 24-29: an outside tool changed budgets 22 times in 48 hours."""

    def test_outside_writer_is_named_with_its_net_changes(self):
        activity = [budget_change('2026-10-26T05:00:00Z', 'as-1', 10000, 5000, writer='bulk-editor-x'),
                    budget_change('2026-10-27T05:00:00Z', 'as-1', 5000, 500, writer='bulk-editor-x'),
                    budget_change('2026-10-27T06:00:00Z', 'as-2', 500, 5000, writer='bulk-editor-x')]
        two = account(adsets=[adset(), adset(key='as-2', name='1n1 | o-101 | C2 | $50', budget=5000,
                                            ads=[ad(key='ad-2', fingerprint='fp-2')],
                                            spend={'2026-10-24': 4000, '2026-10-25': 4000, '2026-10-26': 4000})])
        result = account_audit.audit(snapshot([two], activity=activity), policy())
        self.assertEqual(codes(result), ['EXTERNAL_WRITER'])
        row = result['writers'][0]
        self.assertEqual((row['writer'], row['role'], row['budget_changes']), ('bulk-editor-x', None, 3))
        self.assertEqual(row['net_change'], '−95.0% … +900.0%')
        self.assertTrue(tier(result)['outside_writer'])

    def test_change_outside_the_window_is_not_attributed(self):
        activity = [budget_change('2026-10-21T05:00:00Z', 'as-1', 400, 500, writer='bulk-editor-x')]
        result = account_audit.audit(snapshot(activity=activity), policy())
        self.assertEqual(codes(result), [])
        self.assertEqual(result['writers'], [])
        self.assertFalse(tier(result)['outside_writer'])

    def test_change_without_writer_is_outside_the_owner_list(self):
        change = budget_change('2026-10-27T05:00:00Z', 'as-1', 400, 500)
        change['writer'] = ''
        result = account_audit.audit(snapshot(activity=[change]), policy())
        self.assertEqual(codes(result), ['EXTERNAL_WRITER'])
        self.assertEqual(result['findings'][0]['detail']['writer'], 'unknown writer')

    def test_activity_after_the_read_is_refused(self):
        with self.assertRaisesRegex(account_audit.AuditError, 'later than the snapshot'):
            account_audit.audit(snapshot(activity=[budget_change('2026-10-27T13:00:00Z', 'as-1', 1, 2)]), policy())


class FullDayTests(unittest.TestCase):
    """Oct 25-26: a full day counted from an intraday start, and a fixed UTC offset."""

    def test_budget_set_yesterday_afternoon_has_no_full_day(self):
        activity = [budget_change('2026-10-26T15:00:00Z', 'as-1', 300, 500)]
        self.assertEqual(tier(account_audit.audit(snapshot(activity=activity), policy()))['full_day'], 'no')

    def test_budget_set_before_yesterdays_local_midnight_has_a_full_day(self):
        activity = [budget_change('2026-10-25T23:59:00Z', 'as-1', 300, 500)]
        self.assertEqual(tier(account_audit.audit(snapshot(activity=activity), policy()))['full_day'], 'yes')

    def test_named_time_zone_follows_the_daylight_saving_change(self):
        # Atlantic/Azores moved from UTC+0 to UTC-1 on Oct 25, so Oct 26 began at 01:00 UTC.
        # 00:30 UTC on Oct 26 is 23:30 local on Oct 25: a full day. A fixed UTC+0 offset says no.
        activity = [budget_change('2026-10-26T00:30:00Z', 'as-1', 300, 500)]
        azores = account_audit.audit(snapshot([account(tz='Atlantic/Azores')], activity=activity), policy())
        utc = account_audit.audit(snapshot([account(tz='Etc/GMT')], activity=activity), policy())
        self.assertEqual(tier(azores)['full_day'], 'yes')
        self.assertEqual(tier(azores)['since_local'], '2026-10-25 23:30')
        self.assertEqual(tier(utc)['full_day'], 'no')

    def test_short_change_log_gives_unknown_not_yes(self):
        short = account(since='2026-10-27T06:00:00Z')
        result = account_audit.audit(snapshot([short]), policy())
        self.assertEqual(tier(result)['full_day'], 'unknown')
        self.assertFalse(tier(result)['since_exact'])

    def test_created_inside_the_log_uses_creation_time(self):
        fresh = account(adsets=[adset(created='2026-10-27T02:00:00Z')])
        result = account_audit.audit(snapshot([fresh]), policy())
        self.assertEqual((tier(result)['full_day'], tier(result)['since_exact']), ('no', True))

    def test_unknown_time_zone_is_refused(self):
        with self.assertRaisesRegex(account_audit.AuditError, 'unknown time zone'):
            account_audit.audit(snapshot([account(tz='Mars/Olympus')]), policy())

    def test_time_without_offset_is_refused(self):
        with self.assertRaisesRegex(account_audit.AuditError, 'UTC offset'):
            account_audit.audit(snapshot(as_of='2026-10-27T12:00:00'), policy())


class DuplicateTests(unittest.TestCase):
    """Oct 28: a paused batch repeated live ad sets with the same offer and creative."""

    def test_paused_copy_of_a_live_ad_set_is_flagged_with_the_budget_jump(self):
        copy_of = adset(key='as-2', status='PAUSED', name='1n1 | o-101 | C1 | $50', budget=5000,
                        ads=[ad(key='ad-2')], spend={})
        result = account_audit.audit(snapshot([account(adsets=[adset(), copy_of])]), policy())
        self.assertEqual(codes(result), ['DUPLICATE_ACTIVATION'])
        detail = result['findings'][0]['detail']
        self.assertEqual((detail['before'], detail['after']), ('$5.00', '$55.00'))

    def test_same_creative_for_another_offer_is_not_a_duplicate(self):
        other = adset(key='as-2', status='PAUSED', name='1n1 | o-117 | C1 | $5', ads=[ad(key='ad-2', offer='o-117')],
                      spend={})
        self.assertEqual(codes(account_audit.audit(snapshot([account(adsets=[adset(), other])]), policy())), [])

    def test_duplicate_in_another_account_is_not_flagged(self):
        other = account(key='acct-2', adsets=[adset(key='as-2', status='PAUSED', ads=[ad(key='ad-2')], spend={})])
        self.assertEqual(codes(account_audit.audit(snapshot([account(), other]), policy())), [])


class FieldTests(unittest.TestCase):
    def target(self):
        return account(adsets=[adset(targeting={'geo_locations': {'countries': ['US']}, 'age_min': 18})])

    def test_partial_targeting_is_refused_with_the_keys_it_would_clear(self):
        result = account_audit.audit(snapshot([self.target()], requests=[
            request(field='targeting', value={'user_os': ['Android']}, unit=None)]), policy())
        self.assertEqual(decision(result), ('refuse', 'PARTIAL_REPLACE'))
        self.assertEqual(result['requests'][0]['detail']['missing'], 'age_min, geo_locations')

    def test_full_targeting_with_the_change_is_allowed(self):
        value = {'geo_locations': {'countries': ['US']}, 'age_min': 18, 'user_os': ['Android']}
        result = account_audit.audit(snapshot([self.target()], requests=[
            request(field='targeting', value=value, unit=None)]), policy())
        self.assertEqual(decision(result), ('allow', 'OK'))

    def test_targeting_not_in_the_snapshot_is_refused(self):
        result = account_audit.audit(snapshot(requests=[
            request(field='targeting', value={'user_os': ['Android']}, unit=None)]), policy())
        self.assertEqual(decision(result), ('refuse', 'CURRENT_UNKNOWN'))

    def test_locked_field_needs_a_new_object(self):
        ad_set = account_audit.audit(snapshot(requests=[
            request(field='promoted_object', value={'pixel_key': 'p-2'}, unit=None)]), policy())
        campaign = account_audit.audit(snapshot(requests=[
            request(object_key='cmp-acct-1', field='special_ad_categories', value=['EMPLOYMENT'], unit=None)]),
            policy())
        self.assertEqual(decision(ad_set), ('refuse', 'LOCKED_FIELD'))
        self.assertEqual(decision(campaign), ('refuse', 'LOCKED_FIELD'))

    def test_resuming_a_human_pause_is_refused(self):
        activity = [{'at': '2026-10-27T08:00:00Z', 'account_key': 'acct-1', 'object_key': 'as-1',
                     'writer': 'owner-console', 'event': 'status_change', 'new_status': 'PAUSED'}]
        result = account_audit.audit(snapshot([account(adsets=[adset(status='PAUSED')])], activity=activity,
                                              requests=[request(field='status', value='ACTIVE', unit=None)]),
                                     policy())
        self.assertEqual(decision(result), ('refuse', 'RESUME_HUMAN_PAUSE'))

    def test_resuming_an_agent_pause_is_left_to_the_gate(self):
        activity = [{'at': '2026-10-27T08:00:00Z', 'account_key': 'acct-1', 'object_key': 'as-1',
                     'writer': 'ops-agent', 'event': 'status_change', 'new_status': 'PAUSED'}]
        result = account_audit.audit(snapshot([account(adsets=[adset(status='PAUSED')])], activity=activity,
                                              requests=[request(field='status', value='ACTIVE', unit=None)]),
                                     policy())
        self.assertEqual(decision(result), ('allow', 'NO_RULE'))

    def test_unknown_object_is_refused(self):
        result = account_audit.audit(snapshot(requests=[request(object_key='as-404')]), policy())
        self.assertEqual(decision(result), ('refuse', 'UNKNOWN_OBJECT'))

    def test_request_for_another_accounts_object_is_refused(self):
        result = account_audit.audit(snapshot(requests=[request(account_key='acct-9')]), policy())
        self.assertEqual(decision(result), ('refuse', 'ACCOUNT_MISMATCH'))

    def test_duplicate_request_key_is_refused(self):
        with self.assertRaisesRegex(account_audit.AuditError, 'duplicate request_key'):
            account_audit.audit(snapshot(requests=[request(), request()]), policy())


class ReviewFixTests(unittest.TestCase):
    """Fail closed: the audit must not let through what it cannot see, nor hold the fix for its own P0."""

    def runaway(self, today=2200):
        return account(adsets=[adset(name='1n1 | o-101 | C1 | $1000', budget=100000, today=today)])

    def test_rollback_of_a_runaway_budget_is_not_held_for_tomorrow(self):
        result = account_audit.audit(snapshot([self.runaway()], requests=[request(value='5.00')]), policy())
        self.assertEqual(decision(result), ('allow', 'RUNAWAY_CUT'))

    def test_partial_cut_of_a_runaway_budget_is_allowed(self):
        result = account_audit.audit(snapshot([self.runaway()], requests=[request(value='500.00')]), policy())
        self.assertEqual(decision(result), ('allow', 'RUNAWAY_CUT'))

    def test_cut_without_a_reading_of_todays_spend_waits(self):
        spent = account(adsets=[adset(budget=5000, name='1n1 | o-101 | C1 | $50', today=None,
                                      spend={'2026-10-24': 4000, '2026-10-25': 4000, '2026-10-26': 4000})])
        del spent['campaigns'][0]['adsets'][0]['spend_minor_today']
        result = account_audit.audit(snapshot([spent], requests=[request(value='20.00')]), policy())
        self.assertEqual(decision(result), ('wait', 'SPEND_UNKNOWN'))

    def test_campaign_budget_raise_is_checked(self):
        document = snapshot(requests=[request(object_key='cmp-acct-1', value='1000')])
        document['accounts'][0]['campaigns'][0]['daily_budget_minor'] = 5000
        self.assertEqual(decision(account_audit.audit(document, policy())), ('refuse', 'ABOVE_CEILING'))

    def test_campaign_without_a_budget_in_the_read_is_refused(self):
        result = account_audit.audit(snapshot(requests=[request(object_key='cmp-acct-1', value='20.00')]), policy())
        self.assertEqual(decision(result), ('refuse', 'CURRENT_UNKNOWN'))

    def test_platform_without_field_rules_is_refused(self):
        document = snapshot()
        document['platform'] = 'tiktok'
        with self.assertRaisesRegex(account_audit.AuditError, 'refused, not guessed'):
            account_audit.audit(document, policy())
        del document['platform']
        with self.assertRaises(account_audit.AuditError):
            account_audit.audit(document, policy())

    def paused(self, activity, value='ACTIVE'):
        return account_audit.audit(snapshot([account(adsets=[adset(status='PAUSED')])], activity=activity,
                                            requests=[request(field='status', value=value, unit=None)]), policy())

    def test_pause_not_in_the_log_waits(self):
        self.assertEqual(decision(self.paused([])), ('wait', 'PAUSE_UNATTRIBUTED'))

    def test_pause_by_an_outside_writer_waits(self):
        activity = [{'at': '2026-10-27T08:00:00Z', 'account_key': 'acct-1', 'object_key': 'as-1',
                     'writer': 'bulk-editor-x', 'event': 'status_change', 'new_status': 'PAUSED'}]
        self.assertEqual(decision(self.paused(activity)), ('wait', 'PAUSE_UNATTRIBUTED'))

    def test_lowercase_active_is_still_a_resume(self):
        activity = [{'at': '2026-10-27T08:00:00Z', 'account_key': 'acct-1', 'object_key': 'as-1',
                     'writer': 'owner-console', 'event': 'status_change', 'new_status': 'PAUSED'}]
        self.assertEqual(decision(self.paused(activity, value='active')), ('refuse', 'RESUME_HUMAN_PAUSE'))

    def test_log_value_that_differs_from_the_field_gives_unknown(self):
        activity = [budget_change('2026-10-25T10:00:00Z', 'as-1', 300, 500)]
        drifted = account(adsets=[adset(budget=5000, name='1n1 | o-101 | C1 | $50',
                                        spend={'2026-10-24': 4000, '2026-10-25': 4000, '2026-10-26': 4000})])
        result = account_audit.audit(snapshot([drifted], activity=activity), policy())
        self.assertEqual(tier(result)['full_day'], 'unknown')
        self.assertEqual(tier(result)['log_value'], '$5.00')

    def test_platform_time_formats_parse_on_every_python(self):
        for raw in ('2026-10-27T12:00:00+0000', '2026-10-27T12:00:00.5Z', '2026-10-27T12:00:00.123456789+00:00'):
            with self.subTest(raw=raw):
                self.assertEqual(account_audit.parse_time(raw, 't').strftime('%Y-%m-%d %H:%M'), '2026-10-27 12:00')

    def test_malformed_request_is_refused_without_stopping_the_audit(self):
        result = account_audit.audit(snapshot(requests=[request(value=10.5), request(key='w2')]), policy())
        self.assertEqual(decision(result), ('refuse', 'INVALID_REQUEST'))
        self.assertEqual(decision(result, 'w2'), ('allow', 'BUDGET_OK'))

    def test_ad_level_request_is_judged(self):
        result = account_audit.audit(snapshot(requests=[request(object_key='ad-as-1', field='status',
                                                                value='PAUSED', unit=None)]), policy())
        self.assertEqual(decision(result), ('allow', 'NO_RULE'))

    def test_activity_for_an_object_in_another_account_is_refused(self):
        other = account(key='acct-2', adsets=[adset(key='as-2', ads=[ad(key='ad-2')])])
        change = budget_change('2026-10-27T05:00:00Z', 'as-2', 400, 500, account_key='acct-1')
        with self.assertRaisesRegex(account_audit.AuditError, 'belongs to'):
            account_audit.audit(snapshot([account(), other], activity=[change]), policy())

    def test_offer_share_is_unknown_when_a_day_reading_is_missing(self):
        wrong = adset(ads=[ad(offer='o-117')])
        gap = adset(key='as-2', ads=[ad(key='ad-2', fingerprint='fp-2')], spend={'2026-10-25': 480})
        result = account_audit.audit(snapshot([account(adsets=[wrong, gap])]), policy())
        self.assertEqual(result['findings'][0]['detail']['share'], account_audit.UNKNOWN_SHARE)
        self.assertIn('an unknown share', account_audit.render_report(result))

    def test_name_budget_with_thousands_separator(self):
        named = adset(name='1n1 | o-101 | C1 | $1,000', budget=100000)
        self.assertEqual(codes(account_audit.audit(snapshot([account(adsets=[named])]), policy())), ['BUDGET_CANARY'])

    def test_ratio_just_above_the_limit_is_not_printed_as_the_limit(self):
        result = account_audit.audit(snapshot([account(adsets=[adset(budget=1000, name='1n1 | o-101 | C1 | $10')])],
                                              requests=[request(value='20.50')]), policy())
        self.assertEqual(decision(result), ('refuse', 'RAISE_TOO_LARGE'))
        self.assertEqual(result['requests'][0]['detail']['ratio'], '2.05')


class PolicyTests(unittest.TestCase):
    def test_pattern_without_offer_group_is_refused(self):
        bad = policy()
        bad['offer_link']['destination_pattern'] = '/r/o-\\d+'
        with self.assertRaisesRegex(account_audit.AuditError, 'named group'):
            account_audit.audit(snapshot(), bad)

    def test_writer_role_must_be_human_or_agent(self):
        bad = policy()
        bad['writers']['own']['someone'] = 'friend'
        with self.assertRaises(account_audit.AuditError):
            account_audit.audit(snapshot(), bad)

    def test_policy_line_with_too_many_decimals_is_refused(self):
        bad = policy()
        bad['budget_writes']['ceiling_daily_budget'] = '100.005'
        with self.assertRaisesRegex(account_audit.AuditError, 'decimals'):
            account_audit.audit(snapshot(), bad)

    def test_window_and_full_days_must_be_whole_numbers(self):
        for path, value in ((('writers', 'window_hours'), '48h'), (('budget_canary', 'full_days'), 0)):
            bad = policy()
            bad[path[0]][path[1]] = value
            with self.subTest(path=path), self.assertRaises(account_audit.AuditError):
                account_audit.audit(snapshot(), bad)

    def test_changing_the_ceiling_changes_the_verdict(self):
        loose = policy()
        loose['budget_writes']['ceiling_daily_budget'] = '2000.00'
        loose['budget_writes']['max_raise_ratio'] = '500'
        result = account_audit.audit(snapshot(requests=[request(value='1000')]), loose)
        self.assertEqual(decision(result), ('allow', 'BUDGET_OK'))


class ReportTests(unittest.TestCase):
    def test_goldens_match_a_fresh_render(self):
        for lang, suffix in (('en', ''), ('zh-CN', '.zh-CN')):
            with self.subTest(lang=lang):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = account_audit.main([
                        '--snapshot', str(FIXTURES / 'snapshot.json'),
                        '--policy', str(FIXTURES / 'policy.json'), '--lang', lang,
                        '--check', str(FIXTURES / 'expected' / f'audit{suffix}.md')])
                self.assertEqual(code, 0)

    def test_report_is_deterministic(self):
        first = account_audit.render_report(account_audit.audit(fixture(), policy()))
        second = account_audit.render_report(account_audit.audit(copy.deepcopy(fixture()), policy()))
        self.assertEqual(first, second)

    def test_strict_exits_3_on_p0(self):
        result = subprocess.run(
            [sys.executable, 'account_audit.py', '--snapshot', 'examples/audit/snapshot.json',
             '--policy', 'examples/audit/policy.json', '--strict'],
            cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 3)
        self.assertTrue(result.stdout.startswith('# Account audit — replay, fictional values'))
        self.assertNotIn(str(ROOT), result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
