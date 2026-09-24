from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import memory_store as memory


def record(record_id='method-1', product_id='product-a', status='active'):
    return {
        'record_id': record_id, 'product_id': product_id, 'kind': 'methodology',
        'title': 'Creative testing method', 'text': 'Keep the product and market fixed while comparing hooks.',
        'status': status,
        'source': {'kind': 'user_confirmation', 'reference': 'User explicitly selected this method.',
                   'mode': 'user_statement'},
        'scope': {'platforms': ['meta'], 'accounts': [{'platform': 'meta', 'account_id': 'fictional-a'}],
                  'countries': ['US'], 'surfaces': ['web'], 'monetization': ['leadgen']},
        'stages': ['planning', 'creative'],
    }


class MemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = self.root / 'private.sqlite'
        memory.init_store(self.store, 'workspace-a')

    def put(self, item=None, version=0, event='create-1'):
        return memory.upsert_record(self.store, 'workspace-a', item or record(),
                                    expected_version=version, event_id=event)

    def history(self):
        return memory.record_history(self.store, 'workspace-a', 'product-a', 'method-1')

    def test_persists_across_connections_and_initialization_is_idempotent(self):
        created = self.put()
        self.assertEqual(1, created['version'])
        self.assertTrue(created['updated_at'].endswith('Z'))
        before = self.store.read_bytes()
        self.assertEqual({'schema_version': 1, 'workspace_id': 'workspace-a'},
                         memory.init_store(self.store, 'workspace-a'))
        self.assertEqual(before, self.store.read_bytes())
        self.assertEqual([created], memory.list_records(self.store, 'workspace-a', 'product-a'))
        self.assertEqual([created], self.history())
        self.assertEqual(0o600, self.store.stat().st_mode & 0o777)

    def test_other_workspace_cannot_read_mutate_or_rebind(self):
        self.put()
        calls = [
            lambda: memory.init_store(self.store, 'workspace-b'),
            lambda: memory.list_records(self.store, 'workspace-b', 'product-a'),
            lambda: memory.record_history(self.store, 'workspace-b', 'product-a', 'method-1'),
            lambda: memory.upsert_record(self.store, 'workspace-b', record(), expected_version=1, event_id='other'),
            lambda: memory.revoke_record(self.store, 'workspace-b', 'product-a', 'method-1',
                                         expected_version=1, event_id='other', reason='request'),
        ]
        for call in calls:
            with self.subTest(call=call), self.assertRaises(memory.MemoryError):
                call()
        self.assertEqual(1, len(self.history()))

    def test_products_are_isolated_and_record_ids_can_be_reused(self):
        first = self.put()
        self.assertEqual([], memory.list_records(self.store, 'workspace-a', 'product-b'))
        self.assertEqual([], memory.record_history(self.store, 'workspace-a', 'product-b', 'method-1'))
        with self.assertRaises(memory.MemoryError):
            memory.revoke_record(self.store, 'workspace-a', 'product-b', 'method-1',
                                 expected_version=0, event_id='other', reason='request')
        second = self.put(record(product_id='product-b'), event='create-b')
        self.assertEqual(1, second['version'])
        self.assertEqual([first], memory.list_records(self.store, 'workspace-a', 'product-a'))
        self.assertEqual([second], memory.list_records(self.store, 'workspace-a', 'product-b'))

    def test_candidates_are_not_returned_as_active(self):
        item = record(status='candidate')
        item['source'] = {'kind': 'task_observation', 'reference': 'Fictional offline observation.', 'mode': 'simulation'}
        result = self.put(item)
        self.assertEqual([], memory.list_records(self.store, 'workspace-a', 'product-a'))
        self.assertEqual([result], memory.list_records(self.store, 'workspace-a', 'product-a', include_inactive=True))
        item['status'] = 'active'
        with self.assertRaises(memory.MemoryError):
            self.put(item, version=1, event='promote')
        self.assertEqual(1, len(self.history()))

    def test_only_explicit_user_statement_can_be_active(self):
        for kind, mode in [('task_observation', 'user_statement'), ('user_confirmation', 'simulation'),
                           ('user_confirmation', 'imported'), ('task_observation', 'imported')]:
            item = record()
            item['source'].update(kind=kind, mode=mode)
            with self.subTest(kind=kind, mode=mode), self.assertRaises(memory.MemoryError):
                self.put(item)
        self.assertEqual([], self.history())

    def test_cas_and_history_preserve_prior_revisions(self):
        first = self.put()
        item = record()
        item['text'] = 'A user correction applies to the next test.'
        second = self.put(item, version=1, event='correction')
        self.assertEqual(2, second['version'])
        for version in (0, 1, 3):
            with self.subTest(version=version), self.assertRaises(memory.MemoryError):
                self.put(item, version=version, event='stale')
        self.assertEqual([first, second], self.history())
        self.assertEqual([second], memory.list_records(self.store, 'workspace-a', 'product-a'))

    def test_same_event_is_idempotent_even_after_newer_revision(self):
        first = self.put()
        item = record()
        item['text'] = 'Changed by the user.'
        self.put(item, version=1, event='correction')
        self.assertEqual(first, self.put())
        self.assertEqual(2, len(self.history()))
        with self.assertRaises(memory.MemoryError):
            self.put(item, version=2)
        with self.assertRaises(memory.MemoryError):
            self.put(record(product_id='product-b'))
        with self.assertRaises(memory.MemoryError):
            memory.revoke_record(self.store, 'workspace-a', 'product-a', 'method-1',
                                 expected_version=2, event_id='create-1', reason='request')
        self.assertEqual([], memory.list_records(self.store, 'workspace-a', 'product-b', include_inactive=True))

    def test_revoke_is_versioned_idempotent_and_retains_history(self):
        first = self.put()
        kwargs = dict(expected_version=1, event_id='revoke-1', reason='The user stopped using this method.')
        revoked = memory.revoke_record(self.store, 'workspace-a', 'product-a', 'method-1', **kwargs)
        self.assertEqual('revoked', revoked['status'])
        self.assertEqual(2, revoked['version'])
        self.assertEqual(revoked, memory.revoke_record(self.store, 'workspace-a', 'product-a', 'method-1', **kwargs))
        self.assertEqual([], memory.list_records(self.store, 'workspace-a', 'product-a'))
        self.assertEqual([revoked], memory.list_records(self.store, 'workspace-a', 'product-a', include_inactive=True))
        self.assertEqual([first, revoked], self.history())
        with self.assertRaises(memory.MemoryError):
            memory.revoke_record(self.store, 'workspace-a', 'product-a', 'method-1',
                                 expected_version=2, event_id='revoke-2', reason='Again')
        with self.assertRaises(memory.MemoryError):
            memory.revoke_record(self.store, 'workspace-a', 'product-a', 'method-1',
                                 **{**kwargs, 'reason': 'Changed request'})
        restored = self.put(version=2, event='restore-explicit')
        self.assertEqual(3, restored['version'])
        self.assertNotIn('reason', restored)
        self.assertEqual(3, len(self.history()))

    def test_missing_database_reads_and_writes_do_not_create_it(self):
        missing = self.root / 'missing.sqlite'
        calls = [
            lambda: memory.list_records(missing, 'workspace-a', 'product-a'),
            lambda: memory.record_history(missing, 'workspace-a', 'product-a', 'method-1'),
            lambda: memory.upsert_record(missing, 'workspace-a', record(), expected_version=0, event_id='event'),
            lambda: memory.revoke_record(missing, 'workspace-a', 'product-a', 'method-1',
                                         expected_version=0, event_id='event', reason='request'),
        ]
        for call in calls:
            with self.subTest(call=call), self.assertRaises(memory.MemoryError):
                call()
            self.assertFalse(missing.exists())

    def test_invalid_files_versions_and_schema_are_rejected_without_repair(self):
        text = self.root / 'not-sqlite'
        text.write_text('private invalid input', encoding='utf-8')
        empty = self.root / 'empty.sqlite'
        empty.touch()
        unrelated = self.root / 'unrelated.sqlite'
        with sqlite3.connect(unrelated) as conn:
            conn.execute('CREATE TABLE unrelated (value TEXT)')
        for path in (text, empty, unrelated):
            before = path.read_bytes()
            with self.subTest(path=path), self.assertRaises(memory.MemoryError):
                memory.init_store(path, 'workspace-a')
            self.assertEqual(before, path.read_bytes())
        with sqlite3.connect(self.store) as conn:
            conn.execute('UPDATE metadata SET schema_version=2')
        with self.assertRaises(memory.MemoryError):
            memory.list_records(self.store, 'workspace-a', 'product-a')
        with self.assertRaises(memory.MemoryError):
            self.put()

    def test_read_functions_use_sqlite_read_only_mode(self):
        self.put()
        connect = sqlite3.connect
        calls = []

        def spy(database, *args, **kwargs):
            calls.append(database)
            return connect(database, *args, **kwargs)

        with patch.object(memory.sqlite3, 'connect', side_effect=spy):
            memory.list_records(self.store, 'workspace-a', 'product-a')
            self.history()
        self.assertEqual(2, len(calls))
        self.assertTrue(all(uri.endswith('?mode=ro') for uri in calls))

    def test_failure_between_revision_and_event_rolls_back_everything(self):
        first = self.put()
        connect = memory._connect

        class EventWriteFailure:
            def __init__(self, connection):
                self.connection = connection

            def execute(self, statement, *args):
                if statement.startswith('INSERT INTO events'):
                    raise sqlite3.OperationalError('injected private failure')
                return self.connection.execute(statement, *args)

            def __getattr__(self, name):
                return getattr(self.connection, name)

        with patch.object(memory, '_connect', side_effect=lambda path, mode: EventWriteFailure(connect(path, mode))):
            with self.assertRaises(memory.MemoryError) as error:
                self.put(version=1, event='retryable-event')
        self.assertNotIn('injected', str(error.exception))
        self.assertEqual([first], self.history())
        with sqlite3.connect(self.store) as conn:
            self.assertEqual(1, conn.execute('SELECT COUNT(*) FROM events').fetchone()[0])
        second = self.put(version=1, event='retryable-event')
        self.assertEqual(2, second['version'])

    def test_strict_validation_and_bool_rejection_are_atomic(self):
        variants = []
        for field, value in [('unexpected', True), ('status', True), ('kind', []), ('text', ''), ('stages', []),
                             ('stages', ['planning', 'planning']), ('stages', [True]), ('version', 1)]:
            item = record()
            item[field] = value
            variants.append(item)
        for field, value in [('platforms', ['meta', 'meta']), ('platforms', ['unknown']), ('accounts', True),
                             ('accounts', [{'platform': 'google', 'account_id': 'fictional-a'}]),
                             ('countries', [False]), ('surfaces', ['unknown']), ('monetization', ['unknown']),
                             ('accounts', [{'platform': 'meta', 'account_id': 'fictional-a'}] * 2)]:
            item = record()
            item['scope'][field] = value
            variants.append(item)
        item = record()
        del item['scope']['countries']
        variants.append(item)
        item = record()
        item['source']['extra'] = True
        variants.append(item)
        for item in variants:
            with self.subTest(item=item), self.assertRaises(memory.MemoryError):
                self.put(item)
        for version in (True, False, -1, 1.0, '0'):
            with self.subTest(version=version), self.assertRaises(memory.MemoryError):
                self.put(version=version)
        for value in (0, 1, 'true', None):
            with self.subTest(value=value), self.assertRaises(memory.MemoryError):
                memory.list_records(self.store, 'workspace-a', 'product-a', include_inactive=value)
        self.assertEqual([], self.history())
        with sqlite3.connect(self.store) as conn:
            self.assertEqual(0, conn.execute('SELECT COUNT(*) FROM events').fetchone()[0])

    def test_empty_scopes_are_valid_and_list_is_stably_sorted(self):
        for identifier in ('z-last', 'a-first'):
            item = record(record_id=identifier)
            item['scope'] = {key: [] for key in item['scope']}
            self.put(item, event=identifier)
        self.assertEqual(['a-first', 'z-last'],
                         [item['record_id'] for item in memory.list_records(self.store, 'workspace-a', 'product-a')])

    def test_concurrent_updates_have_exactly_one_winner(self):
        self.put()

        def update(index):
            item = record()
            item['text'] = 'Correction ' + str(index)
            try:
                return self.put(item, version=1, event='update-' + str(index))
            except memory.MemoryError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(update, [1, 2]))
        self.assertEqual(1, sum(result is not None for result in results))
        self.assertEqual(2, len(self.history()))

    def test_cli_json_success_and_errors_do_not_echo_private_input(self):
        source = self.root / 'input.json'
        source.write_text(json.dumps(record()), encoding='utf-8')
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = memory.main(['put', '--store', str(self.store), '--workspace', 'workspace-a',
                                     '--input', str(source), '--expected-version', '0', '--event-id', 'cli-1'])
        self.assertEqual(0, exit_code)
        self.assertEqual(1, json.loads(stdout.getvalue())['version'])
        self.assertEqual('', stderr.getvalue())
        source.write_text('{"text":"private-marker", "text":"duplicate"}', encoding='utf-8')
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = memory.main(['put', '--store', str(self.store), '--workspace', 'workspace-a',
                                     '--input', str(source), '--expected-version', '1', '--event-id', 'cli-2'])
        self.assertEqual(2, exit_code)
        self.assertEqual('', stdout.getvalue())
        self.assertIn('error', json.loads(stderr.getvalue()))
        self.assertNotIn('private-marker', stderr.getvalue())
        self.assertEqual(1, len(self.history()))


if __name__ == '__main__':
    unittest.main()
