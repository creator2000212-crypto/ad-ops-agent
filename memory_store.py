#!/usr/bin/env python3
"""Local, explicit, versioned private records. No inference, network or ad execution.

Workspace and product checks provide local logical isolation, not authentication.
An active record expresses a user's choice; it is not evidence of business impact.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile


SCHEMA_VERSION = 1
PLATFORMS = {'meta', 'tiktok', 'google'}
STAGES = {'discovery', 'planning', 'creative', 'launch', 'measurement', 'diagnosis'}
SCOPE_CHOICES = {
    'platforms': PLATFORMS,
    'countries': None,
    'surfaces': {'web', 'app'},
    'monetization': {'iaa', 'iap', 'hybrid', 'subscription', 'ecommerce', 'leadgen'},
}
RECORD_FIELDS = {'record_id', 'product_id', 'kind', 'title', 'text', 'status',
                 'source', 'scope', 'stages'}
_SCHEMA = (
    'CREATE TABLE metadata (singleton INTEGER PRIMARY KEY CHECK(singleton=1), '
    'schema_version INTEGER NOT NULL, workspace_id TEXT NOT NULL)',
    'CREATE TABLE revisions (workspace_id TEXT NOT NULL, product_id TEXT NOT NULL, '
    'record_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>0), '
    'payload TEXT NOT NULL, PRIMARY KEY(workspace_id, product_id, record_id, version))',
    'CREATE TABLE events (workspace_id TEXT NOT NULL, event_id TEXT NOT NULL, '
    'request_fingerprint TEXT NOT NULL, result_json TEXT NOT NULL, '
    'PRIMARY KEY(workspace_id, event_id))',
)
_COLUMNS = {
    'metadata': [('singleton', 'INTEGER'), ('schema_version', 'INTEGER'), ('workspace_id', 'TEXT')],
    'revisions': [('workspace_id', 'TEXT'), ('product_id', 'TEXT'), ('record_id', 'TEXT'),
                  ('version', 'INTEGER'), ('payload', 'TEXT')],
    'events': [('workspace_id', 'TEXT'), ('event_id', 'TEXT'),
               ('request_fingerprint', 'TEXT'), ('result_json', 'TEXT')],
}


class MemoryError(ValueError):
    """A safe-to-display private-store validation or operation error."""


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise MemoryError(label + ' must be a nonempty string.')


def _object(value, fields, label):
    if not isinstance(value, dict) or set(value) != fields:
        raise MemoryError(label + ' has missing or unknown fields.')


def _strings(value, label, choices=None, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise MemoryError(label + ' must be a list' + (' with at least one item.' if nonempty else '.'))
    for item in value:
        _text(item, label + ' item')
    if len(set(value)) != len(value):
        raise MemoryError(label + ' contains duplicate values.')
    if choices is not None and not set(value) <= choices:
        raise MemoryError(label + ' contains an unsupported value.')


def validate_record(record):
    """Validate user input only; versions and timestamps belong to the store."""
    _object(record, RECORD_FIELDS, 'record')
    for field in ('record_id', 'product_id', 'title', 'text'):
        _text(record[field], field)
    if record['kind'] not in ('methodology', 'operational_note'):
        raise MemoryError('kind must be methodology or operational_note.')
    if record['status'] not in ('candidate', 'active'):
        raise MemoryError('status must be candidate or active.')
    source = record['source']
    _object(source, {'kind', 'reference', 'mode'}, 'source')
    if source['kind'] not in ('user_confirmation', 'task_observation'):
        raise MemoryError('source.kind is unsupported.')
    if source['mode'] not in ('user_statement', 'simulation', 'imported'):
        raise MemoryError('source.mode is unsupported.')
    _text(source['reference'], 'source.reference')
    if record['status'] == 'active' and (source['kind'] != 'user_confirmation' or source['mode'] != 'user_statement'):
        raise MemoryError('active requires an explicit user confirmation in user_statement mode.')
    scope = record['scope']
    _object(scope, set(SCOPE_CHOICES) | {'accounts'}, 'scope')
    for field, choices in SCOPE_CHOICES.items():
        _strings(scope[field], 'scope.' + field, choices)
    if not isinstance(scope['accounts'], list):
        raise MemoryError('scope.accounts must be a list.')
    accounts = set()
    for account in scope['accounts']:
        _object(account, {'platform', 'account_id'}, 'scope.accounts item')
        if account['platform'] not in ('meta', 'tiktok', 'google'):
            raise MemoryError('scope.accounts platform is unsupported.')
        _text(account['account_id'], 'scope.accounts account_id')
        if scope['platforms'] and account['platform'] not in scope['platforms']:
            raise MemoryError('scope.accounts platforms must be within scope.platforms.')
        pair = (account['platform'], account['account_id'])
        if pair in accounts:
            raise MemoryError('scope.accounts contains duplicate accounts.')
        accounts.add(pair)
    _strings(record['stages'], 'stages', STAGES, nonempty=True)
    return record


def _version(value):
    if type(value) is not int or value < 0:
        raise MemoryError('expected_version must be a nonnegative integer.')


def _path(value):
    try:
        return Path(value).expanduser().absolute()
    except (TypeError, ValueError, OSError):
        raise MemoryError('store path is invalid.') from None


def _connect(path, mode):
    # mode=ro/rw prevents all non-init operations from creating a missing DB.
    connection = None
    try:
        connection = sqlite3.connect(_path(path).as_uri() + '?mode=' + mode, uri=True,
                                     timeout=10, isolation_level=None)
        connection.execute('PRAGMA trusted_schema=OFF')
        if mode == 'ro':
            connection.execute('PRAGMA query_only=ON')
        return connection
    except (sqlite3.Error, OSError, ValueError):
        if connection is not None:
            connection.close()
        raise MemoryError('Cannot open the existing private store in the required mode.') from None


def _check_store(connection, workspace_id):
    _text(workspace_id, 'workspace_id')
    rows = connection.execute("SELECT name, type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    if set(rows) != {(name, 'table') for name in _COLUMNS}:
        raise MemoryError('Private store schema is invalid or unsupported.')
    for table, columns in _COLUMNS.items():
        actual = [(row[1], row[2]) for row in connection.execute('PRAGMA table_info(' + table + ')')]
        if actual != columns:
            raise MemoryError('Private store schema is invalid or unsupported.')
    metadata = connection.execute('SELECT singleton, schema_version, workspace_id FROM metadata').fetchall()
    if len(metadata) != 1 or metadata[0][0] != 1 or metadata[0][1] != SCHEMA_VERSION:
        raise MemoryError('Private store metadata version is invalid or unsupported.')
    if metadata[0][2] != workspace_id:
        raise MemoryError('Private store is bound to a different workspace.')


def init_store(path, workspace_id):
    """Create a mode-0600 database, or verify an existing same-workspace store."""
    _text(workspace_id, 'workspace_id')
    destination = _path(path)
    if destination.exists() or destination.is_symlink():
        connection = _connect(destination, 'ro')
        try:
            _check_store(connection, workspace_id)
        except sqlite3.Error:
            raise MemoryError('Private store is not a valid supported database.') from None
        finally:
            connection.close()
        return {'schema_version': SCHEMA_VERSION, 'workspace_id': workspace_id}
    temporary = None
    connection = None
    try:
        fd, temporary = tempfile.mkstemp(prefix='.adops-private-', suffix='.sqlite', dir=str(destination.parent))
        os.close(fd)
        connection = sqlite3.connect(temporary, isolation_level=None)
        connection.execute('BEGIN IMMEDIATE')
        for statement in _SCHEMA:
            connection.execute(statement)
        connection.execute('INSERT INTO metadata VALUES (1, ?, ?)', (SCHEMA_VERSION, workspace_id))
        connection.commit()
        connection.close()
        connection = None
        # Linking publishes only a complete database and never replaces a file.
        try:
            os.link(temporary, destination)
        except FileExistsError:
            return init_store(destination, workspace_id)
    except (sqlite3.Error, OSError):
        raise MemoryError('Could not initialize the private store; use an existing writable parent directory.') from None
    finally:
        if connection is not None:
            connection.close()
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
    return {'schema_version': SCHEMA_VERSION, 'workspace_id': workspace_id}


def _decode(payload, product_id=None, record_id=None, version=None):
    try:
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ValueError()
        expected_fields = RECORD_FIELDS | {'version', 'updated_at'}
        if value.get('status') == 'revoked':
            expected_fields |= {'reason'}
        _object(value, expected_fields, 'stored record')
        base = {key: value[key] for key in RECORD_FIELDS}
        if value['status'] == 'revoked':
            _text(value['reason'], 'stored reason')
            base['status'] = 'candidate'
        validate_record(base)
        if type(value['version']) is not int or value['version'] < 1:
            raise ValueError()
        timestamp = datetime.fromisoformat(value['updated_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError()
        if ((product_id is not None and value['product_id'] != product_id)
                or (record_id is not None and value['record_id'] != record_id)
                or (version is not None and value['version'] != version)):
            raise ValueError()
        return value
    except (ValueError, TypeError, KeyError, AttributeError):
        raise MemoryError('Private store contains an invalid record revision.') from None


def _latest(connection, workspace_id, product_id, record_id):
    row = connection.execute(
        'SELECT version, payload FROM revisions WHERE workspace_id=? AND product_id=? AND record_id=? '
        'ORDER BY version DESC LIMIT 1', (workspace_id, product_id, record_id)).fetchone()
    return None if row is None else _decode(row[1], product_id, record_id, row[0])


def _mutate(path, workspace_id, product_id, record_id, expected_version, event_id, request, make_revision):
    _text(workspace_id, 'workspace_id')
    _text(product_id, 'product_id')
    _text(record_id, 'record_id')
    _text(event_id, 'event_id')
    _version(expected_version)
    fingerprint = hashlib.sha256(_canonical(request).encode('utf-8')).hexdigest()
    connection = _connect(path, 'rw')
    try:
        connection.execute('BEGIN IMMEDIATE')
        _check_store(connection, workspace_id)
        event = connection.execute(
            'SELECT request_fingerprint, result_json FROM events WHERE workspace_id=? AND event_id=?',
            (workspace_id, event_id)).fetchone()
        if event is not None:
            if event[0] != fingerprint:
                raise MemoryError('event_id was already used for a different request.')
            result = _decode(event[1], product_id, record_id)
            connection.commit()
            return result
        current = _latest(connection, workspace_id, product_id, record_id)
        if expected_version != (0 if current is None else current['version']):
            raise MemoryError('Version conflict; read the current record before retrying.')
        result = make_revision(current)
        result['version'] = expected_version + 1
        result['updated_at'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        serialized = _canonical(result)
        connection.execute('INSERT INTO revisions VALUES (?, ?, ?, ?, ?)',
                           (workspace_id, product_id, record_id, result['version'], serialized))
        connection.execute('INSERT INTO events VALUES (?, ?, ?, ?)',
                           (workspace_id, event_id, fingerprint, serialized))
        connection.commit()
        return result
    except sqlite3.Error:
        raise MemoryError('Private store write failed; no partial update was committed.') from None
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()


def upsert_record(path, workspace_id, record, *, expected_version, event_id):
    validate_record(record)
    # Detach the stored revision from mutable input data.
    data = json.loads(_canonical(record))
    request = {'operation': 'put', 'workspace_id': workspace_id, 'record': data,
               'expected_version': expected_version}
    return _mutate(path, workspace_id, data['product_id'], data['record_id'], expected_version,
                   event_id, request, lambda current: data.copy())


def revoke_record(path, workspace_id, product_id, record_id, *, expected_version, event_id, reason):
    _text(reason, 'reason')
    request = {'operation': 'revoke', 'workspace_id': workspace_id, 'product_id': product_id,
               'record_id': record_id, 'expected_version': expected_version, 'reason': reason}

    def revoke(current):
        if current is None:
            raise MemoryError('Cannot revoke a record that does not exist in this product.')
        if current['status'] == 'revoked':
            raise MemoryError('Record is already revoked.')
        return {**current, 'status': 'revoked', 'reason': reason}

    return _mutate(path, workspace_id, product_id, record_id, expected_version, event_id, request, revoke)


def list_records(path, workspace_id, product_id, *, include_inactive=False):
    _text(workspace_id, 'workspace_id')
    _text(product_id, 'product_id')
    if type(include_inactive) is not bool:
        raise MemoryError('include_inactive must be a boolean.')
    connection = _connect(path, 'ro')
    try:
        connection.execute('BEGIN')
        _check_store(connection, workspace_id)
        rows = connection.execute(
            'SELECT r.record_id, r.version, r.payload FROM revisions r '
            'WHERE r.workspace_id=? AND r.product_id=? AND r.version=('
            'SELECT MAX(v.version) FROM revisions v WHERE v.workspace_id=r.workspace_id '
            'AND v.product_id=r.product_id AND v.record_id=r.record_id) ORDER BY r.record_id',
            (workspace_id, product_id)).fetchall()
        records = [_decode(row[2], product_id, row[0], row[1]) for row in rows]
        return records if include_inactive else [record for record in records if record['status'] == 'active']
    except sqlite3.Error:
        raise MemoryError('Private store read failed; the database may be invalid or unsupported.') from None
    finally:
        connection.close()


def record_history(path, workspace_id, product_id, record_id):
    for label, value in [('workspace_id', workspace_id), ('product_id', product_id), ('record_id', record_id)]:
        _text(value, label)
    connection = _connect(path, 'ro')
    try:
        connection.execute('BEGIN')
        _check_store(connection, workspace_id)
        rows = connection.execute(
            'SELECT version, payload FROM revisions WHERE workspace_id=? AND product_id=? AND record_id=? '
            'ORDER BY version', (workspace_id, product_id, record_id)).fetchall()
        return [_decode(row[1], product_id, record_id, row[0]) for row in rows]
    except sqlite3.Error:
        raise MemoryError('Private store history read failed; the database may be invalid or unsupported.') from None
    finally:
        connection.close()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MemoryError('Input JSON contains duplicate object fields.')
        result[key] = value
    return result


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise MemoryError('Invalid command arguments; run with --help for usage.')


def main(argv=None):
    parser = _Parser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'put', 'revoke', 'list', 'history'):
        command = commands.add_parser(name)
        command.add_argument('--store', required=True)
        command.add_argument('--workspace', required=True)
        if name in ('revoke', 'list', 'history'):
            command.add_argument('--product', required=True)
        if name in ('revoke', 'history'):
            command.add_argument('--record', required=True)
        if name in ('put', 'revoke'):
            command.add_argument('--expected-version', required=True, type=int)
            command.add_argument('--event-id', required=True)
        if name == 'put':
            command.add_argument('--input', required=True, help='Path to one record JSON file.')
        if name == 'revoke':
            command.add_argument('--reason', required=True)
        if name == 'list':
            command.add_argument('--all', action='store_true')
    try:
        args = parser.parse_args(argv)
        if args.command == 'init':
            result = init_store(args.store, args.workspace)
        elif args.command == 'put':
            try:
                with open(args.input, encoding='utf-8') as source:
                    record = json.load(source, object_pairs_hook=_pairs,
                                       parse_constant=lambda value: (_ for _ in ()).throw(MemoryError('Nonfinite JSON is invalid.')))
            except (OSError, UnicodeError, json.JSONDecodeError):
                raise MemoryError('Cannot read a valid input JSON record.') from None
            result = upsert_record(args.store, args.workspace, record,
                                   expected_version=args.expected_version, event_id=args.event_id)
        elif args.command == 'revoke':
            result = revoke_record(args.store, args.workspace, args.product, args.record,
                                   expected_version=args.expected_version, event_id=args.event_id, reason=args.reason)
        elif args.command == 'history':
            result = record_history(args.store, args.workspace, args.product, args.record)
        else:
            result = list_records(args.store, args.workspace, args.product, include_inactive=args.all)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except MemoryError as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
