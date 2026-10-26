"""Synthetic portfolio data only. Run from repository root; no database required."""
import argparse
import hashlib
import json
import random
from datetime import date
from pathlib import Path

import pandas as pd

TYPES = ['transfer', 'merchant_payment', 'cash_in', 'cash_out']
PARTICIPANTS = {
    'transfer': {'sender_id', 'recipient_id'},
    'merchant_payment': {'sender_id', 'merchant_id'},
    'cash_in': {'recipient_id', 'agent_id'},
    'cash_out': {'sender_id', 'agent_id'},
}
REFS = {'sender_id': 'customers', 'recipient_id': 'customers',
        'merchant_id': 'merchants', 'agent_id': 'agents'}


def fee(kind, amount):
    # Fils: transfer flat 50; merchant 1%, half-up; cash-in free; cash-out flat 100.
    return {'transfer': 50, 'merchant_payment': (amount + 50) // 100,
            'cash_in': 0, 'cash_out': 100}[kind]


def generate(customers=1000, transactions=10000, seed=42, as_of='2026-10-25'):
    if customers < 2 or transactions < 12:
        raise ValueError('Require at least 2 customers and 12 transactions.')
    rng = random.Random(seed)
    end = pd.Timestamp(as_of, tz='UTC').normalize().replace(day=1)
    start = end - pd.DateOffset(months=12)
    tables = {}
    for name, prefix, count in [('customers', 'C', customers), ('merchants', 'M', 60), ('agents', 'A', 30)]:
        # Accounts all open before the window; staggered dates avoid one artificial opening date.
        tables[name] = pd.DataFrame([
            {'id': f'{prefix}{i:06d}', 'created_at': start - pd.Timedelta(days=rng.randint(1, 365))}
            for i in range(1, count + 1)])
    rows, reversals = [], []
    for i in range(transactions):
        month_start = start + pd.DateOffset(months=i % 12)
        month_end = month_start + pd.DateOffset(months=1)
        timestamp = month_start + pd.Timedelta(seconds=rng.randrange(int((month_end-month_start).total_seconds())))
        kind = rng.choices(TYPES, weights=[30, 40, 20, 10])[0]
        status = rng.choices(['successful', 'failed', 'pending'], weights=[92, 6, 2])[0]
        amount = rng.randint(100, 200000)
        sender, recipient = rng.sample(tables['customers']['id'].tolist(), 2)
        candidates = {'sender_id': sender, 'recipient_id': recipient,
                      'merchant_id': rng.choice(tables['merchants']['id'].tolist()),
                      'agent_id': rng.choice(tables['agents']['id'].tolist())}
        row = {'id': f'T{i+1:08d}', 'occurred_at': timestamp, 'type': kind, 'status': status,
               'currency': 'AED', 'amount_minor': amount,
               'fee_minor': fee(kind, amount) if status == 'successful' else 0}
        row.update({key: value if key in PARTICIPANTS[kind] else '' for key, value in candidates.items()})
        rows.append(row)
        if status == 'successful' and rng.random() < 0.025:
            reversed_at = timestamp + pd.Timedelta(seconds=rng.randint(1, 7*86400))
            if reversed_at < end:
                reversals.append({'id': f'R{len(reversals)+1:08d}', 'original_id': row['id'],
                                  'occurred_at': reversed_at, 'currency': 'AED',
                                  'amount_minor': amount, 'fee_refund_minor': row['fee_minor']})
    tables['transactions'] = pd.DataFrame(rows)
    tables['reversals'] = pd.DataFrame(reversals, columns=[
        'id', 'original_id', 'occurred_at', 'currency', 'amount_minor', 'fee_refund_minor'])
    return tables, {'label': 'SYNTHETIC PORTFOLIO SIMULATION — synthetic data',
                    'seed': seed, 'customers': customers, 'transactions': transactions,
                    'as_of': as_of, 'window_start': start.isoformat(), 'window_end_exclusive': end.isoformat(),
                    'currency': 'AED', 'minor_units_per_major': 100}


def validate(tables, config):
    """Collect checks instead of relying on assert (which Python can disable)."""
    checks = []

    def check(name, condition):
        checks.append({'check': name, 'passed': bool(condition)})

    start, end = pd.Timestamp(config['window_start']), pd.Timestamp(config['window_end_exclusive'])
    for name, frame in tables.items():
        check(f'{name}: unique nonempty IDs', frame['id'].notna().all() and frame['id'].ne('').all() and frame['id'].is_unique)
        column = 'created_at' if name in ['customers', 'merchants', 'agents'] else 'occurred_at'
        parsed = pd.to_datetime(frame[column], utc=True, errors='coerce', format='ISO8601')
        check(f'{name}: valid timestamps', parsed.notna().all())
        if column == 'occurred_at':
            check(f'{name}: timestamps in reporting window', ((parsed >= start) & (parsed < end)).all())
        else:
            check(f'{name}: accounts exist before cutoff', (parsed < end).all())
    t, r = tables['transactions'], tables['reversals']
    check('expected customer count', len(tables['customers']) == config['customers'])
    check('expected transaction count', len(t) == config['transactions'])
    check('valid types', t['type'].isin(TYPES).all())
    check('valid statuses', t['status'].isin(['successful', 'failed', 'pending']).all())
    for name, cols in [('transactions', ['amount_minor', 'fee_minor']), ('reversals', ['amount_minor', 'fee_refund_minor'])]:
        f = tables[name]
        check(f'{name}: AED currency', f['currency'].eq('AED').all())
        for col in cols:
            numeric = pd.to_numeric(f[col], errors='coerce')
            check(f'{name}: {col} nonnegative integers', (numeric.notna() & numeric.ge(0) & numeric.mod(1).eq(0)).all())
    for kind, required in PARTICIPANTS.items():
        subset = t[t['type'] == kind]
        for col in REFS:
            populated = subset[col].notna() & subset[col].ne('')
            check(f'{kind}: {col} presence', populated.all() if col in required else (~populated).all())
    check('transfer has distinct customers', (t.loc[t['type'] == 'transfer', 'sender_id'] != t.loc[t['type'] == 'transfer', 'recipient_id']).all())
    for col, table in REFS.items():
        subset = t[t[col].notna() & t[col].ne('')]
        accounts = tables[table].drop_duplicates('id').set_index('id')['created_at']
        check(f'{col}: valid references', subset[col].isin(accounts.index).all())
        opened = pd.to_datetime(subset[col].map(accounts), utc=True, errors='coerce', format='ISO8601')
        occurred = pd.to_datetime(subset['occurred_at'], utc=True, errors='coerce', format='ISO8601')
        check(f'{col}: account opened before transaction', (opened <= occurred).all())
    expected_fees = t.apply(lambda row: fee(row['type'], row['amount_minor'])
                           if row['status'] == 'successful' and row['type'] in TYPES else 0, axis=1)
    check('fees obey rules and unsuccessful fees are zero', t['fee_minor'].eq(expected_fees).all())
    check('at most one reversal per original', r['original_id'].is_unique)
    original = t.drop_duplicates('id').set_index('id')
    check('reversal original exists', r['original_id'].isin(original.index).all())
    check('reversal original successful', r['original_id'].map(original['status']).eq('successful').all())
    check('reversal full value', r['amount_minor'].eq(r['original_id'].map(original['amount_minor'])).all())
    check('reversal full fee refund', r['fee_refund_minor'].eq(r['original_id'].map(original['fee_minor'])).all())
    check('reversal after original', (pd.to_datetime(r['occurred_at'], utc=True, errors='coerce', format='ISO8601') >
          pd.to_datetime(r['original_id'].map(original['occurred_at']), utc=True, errors='coerce', format='ISO8601')).all())
    return {'label': config['label'], 'passed': all(x['passed'] for x in checks), 'checks': checks}


def summarize(tables, config):
    t, r = tables['transactions'], tables['reversals']
    successful = t[t['status'] == 'successful']
    gross, reversed_value = int(successful['amount_minor'].sum()), int(r['amount_minor'].sum())
    fees, refunds = int(successful['fee_minor'].sum()), int(r['fee_refund_minor'].sum())
    return {'label': config['label'], 'row_counts': {k: len(v) for k, v in tables.items()},
            'window_start': config['window_start'], 'window_end_exclusive': config['window_end_exclusive'],
            'first_transaction': str(t['occurred_at'].min()), 'last_transaction': str(t['occurred_at'].max()),
            'status_distribution': {k: int(v) for k, v in t['status'].value_counts().items()},
            'successful_value_minor': gross, 'reversed_value_minor': reversed_value,
            'net_value_minor': gross-reversed_value, 'gross_fee_revenue_minor': fees,
            'fee_refunds_minor': refunds, 'net_fee_revenue_minor': fees-refunds,
            'currency': 'AED', 'minor_units_per_major': 100}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--customers', type=int, default=1000)
    parser.add_argument('--transactions', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--as-of', default=date.today().isoformat())
    parser.add_argument('--output', type=Path, default=Path('data/synthetic'))
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Output directory is nonempty; choose a new --output to preserve existing files.')
    tables, config = generate(args.customers, args.transactions, args.seed, args.as_of)
    report = validate(tables, config)
    if not report['passed']:
        raise ValueError(json.dumps(report, indent=2))
    args.output.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, frame in tables.items():
        path = args.output / f'{name}.csv'
        frame.to_csv(path, index=False, date_format='%Y-%m-%dT%H:%M:%SZ', lineterminator='\n')
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    # Validate the persisted representation too; CSV blanks are deliberately empty strings.
    loaded = {name: pd.read_csv(args.output / f'{name}.csv', keep_default_na=False) for name in tables}
    report = validate(loaded, config)
    summary = summarize(tables, config)
    config.update({'pandas_version': pd.__version__, 'sha256': hashes})
    for name, content in [('manifest', config), ('validation_report', report), ('summary', summary)]:
        (args.output / f'{name}.json').write_text(json.dumps(content, indent=2) + '\n', encoding='utf-8')
    if not report['passed']:
        raise ValueError('Persisted CSV validation failed; inspect validation_report.json')
    print(json.dumps(summary, indent=2))
    print(f"Validation: {len(report['checks'])} checks passed (persisted CSVs).")


if __name__ == '__main__':
    main()
