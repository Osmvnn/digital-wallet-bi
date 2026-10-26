# Verification — synthetic data

## Completed

- 57 generator checks passed against saved CSVs; a repeat generation matched CSV hashes.
- The user ran the PostgreSQL loader twice. The rerun returned `already_loaded`,
  `all_source_rows_match: true`, and all 11 aggregate checks true.
- Live Power BI outputs matched generated source rows for 48 month/service groups
  and nine integer metrics each: **432/432 comparisons passed**. Evidence:
  [reconciliation.json](validation/reconciliation.json).
- Live DAX customer activity and retention matched Python sets for all 12 months.
  Evidence: [powerbi_retention.csv](validation/powerbi_retention.csv).
- 11 automated tests passed, covering generation, malformed input, duplicate
  groups, a one-fil discrepancy, page layouts, fields and the reporting-window filter.
- The user visually inspected and approved the executive page before the three
  additional pages were added.

The evidence snapshots are synthetic aggregates for seed 42, 1,000 customers,
10,000 attempts and `--as-of 2026-10-25`.

## Repeat

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe src/load.py --validate-only
.\.venv\Scripts\python.exe src/reconcile.py
```

For a fresh direct SQL-versus-Power-BI comparison, export the paired queries in
`sql/007_sql_reconciliation.sql` and `sql/008_powerbi_reconciliation.dax`, then pass
both CSV paths to `src/reconcile.py`. Current 432-check evidence compares live
Power BI to generated CSVs; the loader's completed reconciliation provides the
source-to-SQL link. The agent did not independently run a fresh SQL export because
database credentials remain with the user.

## Desktop refresh checklist

- No slicer selections: 9,185 successes, AED 39,310.56 net fees, 6.08% failure rate.
- Merchant-payment service: 3,725 successes and 99 reversals.
- October customer row: 626 active, 394 retained, 62.94% retention.
- September customer row: 613 active and blank retention/retained count.
- Select and clear month/service slicers; applicable visuals should follow the filter.

Structural tests do not replace inspecting each rendered visual after a fresh
clone and refresh. The additional three pages have verified field bindings and
live-tested measures; final visual appearance still needs Desktop inspection.
