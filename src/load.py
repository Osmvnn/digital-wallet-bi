"""Validate and atomically load one synthetic dataset into local PostgreSQL."""
import argparse
import getpass
import hashlib
import io
import json
import os
from pathlib import Path

import pandas as pd
from generate import validate, summarize

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = {
    'customers': ['id', 'created_at'],
    'merchants': ['id', 'created_at'],
    'agents': ['id', 'created_at'],
    'transactions': ['id', 'occurred_at', 'type', 'status', 'currency', 'amount_minor',
                     'fee_minor', 'sender_id', 'recipient_id', 'merchant_id', 'agent_id'],
    'reversals': ['id', 'original_id', 'occurred_at', 'currency', 'amount_minor', 'fee_refund_minor'],
}
MONEY = ['successful_value_minor', 'reversed_value_minor', 'net_value_minor',
         'gross_fee_revenue_minor', 'fee_refunds_minor', 'net_fee_revenue_minor']


def read_dataset(folder):
    config = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    tables, payloads = {}, {}
    for name, columns in COLUMNS.items():
        # Read once: hash, validate and COPY exactly the same bytes.
        raw = (folder / f'{name}.csv').read_bytes()
        if hashlib.sha256(raw).hexdigest() != config['sha256'].get(f'{name}.csv'):
            raise ValueError(f'{name}: CSV hash differs from manifest; regenerate into a new folder.')
        frame = pd.read_csv(io.BytesIO(raw), keep_default_na=False)
        if list(frame.columns) != columns:
            raise ValueError(f'{name}: unexpected columns or column order.')
        tables[name], payloads[name] = frame, raw
    report = validate(tables, config)
    if not report['passed']:
        raise ValueError('Source validation failed: ' + json.dumps(report))
    expected = summarize(tables, config)
    recorded = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    for key in ['row_counts', 'status_distribution', *MONEY]:
        if expected[key] != recorded[key]:
            raise ValueError(f'Source summary mismatch: {key}')
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    return tables, payloads, config, expected, fingerprint


def reconcile(conn, tables, expected):
    """Compare every persisted field, then independently compare SQL measures."""
    from psycopg import sql
    for name, columns in COLUMNS.items():
        query = sql.SQL('SELECT {} FROM staging.{} ORDER BY id').format(
            sql.SQL(',').join(map(sql.Identifier, columns)), sql.Identifier(name))
        rows = conn.execute(query).fetchall()
        actual = pd.DataFrame(rows, columns=columns).fillna('')
        source = tables[name].sort_values('id').reset_index(drop=True).copy()
        for col in ['created_at', 'occurred_at']:
            if col in source:
                source[col] = pd.to_datetime(source[col], utc=True)
                actual[col] = pd.to_datetime(actual[col], utc=True)
        pd.testing.assert_frame_equal(source, actual, check_dtype=False, check_exact=True)
    cursor = conn.execute('SELECT * FROM reporting.executive_summary')
    totals = dict(zip([col.name for col in cursor.description], cursor.fetchone()))
    checks = {key: int(totals[key]) == expected[key] for key in MONEY}
    checks['attempts'] = totals['attempts'] == expected['row_counts']['transactions']
    checks['reversals'] = totals['reversal_count'] == expected['row_counts']['reversals']
    for status in ['successful', 'failed', 'pending']:
        checks[status] = totals[f'{status}_count'] == expected['status_distribution'].get(status, 0)
    if not all(checks.values()):
        raise ValueError('SQL reconciliation failed: ' + json.dumps(checks))
    return {'all_source_rows_match': True, 'checks': checks,
            'sql_totals': {key: int(value) for key, value in totals.items()}}


def load_dataset(conn, dataset):
    from psycopg import sql
    from psycopg.types.json import Jsonb
    tables, payloads, config, expected, fingerprint = dataset
    # One transaction for DDL, all rows, reconciliation and the dataset marker.
    with conn.transaction():
        conn.execute("SET LOCAL TIME ZONE 'UTC'")
        conn.execute("SET LOCAL lock_timeout = '10s'")
        conn.execute("SET LOCAL statement_timeout = '60s'")
        conn.execute('SELECT pg_advisory_xact_lock(78451230)')
        exists = conn.execute("SELECT to_regclass('staging.dataset')").fetchone()[0]
        if exists:
            existing = conn.execute('SELECT schema_version, fingerprint FROM staging.dataset').fetchall()
            if existing != [(1, fingerprint)]:
                raise ValueError('Different dataset/schema already present. No rows were changed. Use a separate project database.')
            action = 'already_loaded'
        else:
            schemas = conn.execute("SELECT nspname FROM pg_namespace WHERE nspname IN ('staging','reporting')").fetchall()
            if schemas:
                raise ValueError('Unrecognized existing staging/reporting schemas; refusing to overwrite them.')
            conn.execute((ROOT / 'sql/001_staging_reporting.sql').read_text(encoding='utf-8'))
            for name, columns in COLUMNS.items():
                command = sql.SQL('COPY staging.{} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)').format(
                    sql.Identifier(name), sql.SQL(',').join(map(sql.Identifier, columns)))
                with conn.cursor() as cursor:
                    with cursor.copy(command) as copy:
                        copy.write(payloads[name])
            action = 'loaded'
        result = reconcile(conn, tables, expected)
        if action == 'loaded':
            conn.execute('INSERT INTO staging.dataset (schema_version, fingerprint, manifest) VALUES (1, %s, %s)',
                         (fingerprint, Jsonb(config)))
    return {'label': config['label'], 'action': action, 'fingerprint': fingerprint, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data/synthetic')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5432)
    parser.add_argument('--database', default='digital_wallet_b')
    parser.add_argument('--user', default='wallet_bi')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    dataset = read_dataset(args.data)
    if args.validate_only:
        print('Source hashes, 57 data-quality checks and summary reconciliation passed. No database connection made.')
        return
    import psycopg
    password = os.environ.get('WALLET_DB_PASSWORD') or getpass.getpass(f'PostgreSQL password for {args.user}: ')
    with psycopg.connect(host=args.host, port=args.port, dbname=args.database, user=args.user,
                         password=password, connect_timeout=5, autocommit=True) as conn:
        result = load_dataset(conn, dataset)
    # Do not write a misleading success report until the transaction has committed.
    print(json.dumps(result, indent=2))
    print('Committed. No duplicate rows were inserted.' if result['action'] == 'already_loaded'
          else 'Committed. Run again to verify action=already_loaded.')


if __name__ == '__main__':
    main()
