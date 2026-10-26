"""Compare month/service Power BI exports to synthetic source data or SQL exports."""
import argparse
import json
from pathlib import Path
import pandas as pd

KEYS = ['month', 'service']
METRICS = ['attempts', 'successes', 'failures', 'pending', 'gross_value_minor',
           'gross_fees_minor', 'reversals', 'reversed_value_minor', 'fee_refunds_minor']


def source_totals(folder):
    t = pd.read_csv(folder/'transactions.csv', keep_default_na=False)
    r = pd.read_csv(folder/'reversals.csv', keep_default_na=False)
    t['month'] = t['occurred_at'].str[:7]
    t['service'] = t['type']
    for status, col in [('successful','successes'),('failed','failures'),('pending','pending')]:
        t[col] = t['status'].eq(status).astype(int)
    t['gross_value_minor'] = t['amount_minor'].where(t['status'].eq('successful'),0)
    totals = t.groupby(KEYS).agg(attempts=('id','size'), successes=('successes','sum'),
        failures=('failures','sum'), pending=('pending','sum'), gross_value_minor=('gross_value_minor','sum'),
        gross_fees_minor=('fee_minor','sum'))
    r = r.merge(t[['id','service']],left_on='original_id',right_on='id',validate='many_to_one')
    r['month'] = r['occurred_at'].str[:7]
    refunds = r.groupby(KEYS).agg(reversals=('original_id','size'),reversed_value_minor=('amount_minor','sum'),
        fee_refunds_minor=('fee_refund_minor','sum'))
    return totals.join(refunds,how='outer').fillna(0).reset_index()


def compare(expected, actual):
    normalized = []
    for frame in [expected, actual]:
        frame = frame.copy()
        # Power BI DAX query exports may wrap result column names in brackets.
        frame.columns = [c.strip('[]') for c in frame.columns]
        missing = set(KEYS+METRICS)-set(frame.columns)
        if missing:
            raise ValueError(f'Missing columns: {sorted(missing)}')
        if frame.duplicated(KEYS).any():
            raise ValueError('Duplicate month/service rows')
        for col in METRICS:
            frame[col] = pd.to_numeric(frame[col], errors='raise').fillna(0)
            if frame[col].mod(1).ne(0).any():
                raise ValueError(f'Noninteger count or money in {col}')
            frame[col] = frame[col].astype('int64')
        normalized.append(frame[KEYS+METRICS].sort_values(KEYS).reset_index(drop=True))
    pd.testing.assert_frame_equal(*normalized, check_dtype=False, check_exact=True)
    return {'passed':True,'groups_checked':len(normalized[0]),'metrics_per_group':len(METRICS),
            'comparisons':len(normalized[0])*len(METRICS),
            'totals': {c:int(normalized[0][c].sum()) for c in METRICS}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,default=Path('data/synthetic'))
    p.add_argument('--powerbi-csv',type=Path,default=Path('docs/validation/powerbi_month_service.csv'))
    p.add_argument('--sql-csv',type=Path)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    expected=pd.read_csv(args.sql_csv) if args.sql_csv else source_totals(args.data)
    result=compare(expected,pd.read_csv(args.powerbi_csv))
    result.update({'label':'Synthetic data','reference':'SQL export' if args.sql_csv else 'Generated CSVs',
                   'powerbi_export':args.powerbi_csv.as_posix()})
    text=json.dumps(result,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text,encoding='utf-8')
    print(text)


if __name__=='__main__':
    main()
