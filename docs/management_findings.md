# Management findings — synthetic data

Scope: October 2025–September 2026, UTC. These results reflect the seeded simulation,
not real customer or partner behavior.

Of 10,000 attempts, 9,185 succeeded, 608 failed and 207 were pending at cutoff.
Gross successful value was AED 9,215,598.99. Full reversals removed AED 233,451.40,
leaving AED 8,982,147.59 of net payment value. Gross fees of AED 40,376.32 less
AED 1,065.76 in refunds produced AED 39,310.56 of net wallet fees. This is not profit.

The 6.08% failure rate uses all attempts as denominator. Reversals are separate
completed events; they do not turn original successes into failed attempts. Pending
records are cutoff snapshots, not an aging/SLA analysis. Failure reasons, retry
identifiers and resolution times would be needed to diagnose operational issues.

All 1,000 customers were active at least once. Monthly active customers ranged
from 613 to 650, averaging 630.67. Of October's 626 active customers, 394 returned
in November (62.94%). August-to-September retention was 60.51%. September's
next-month retention is unobservable. This is activity retention, not signup-cohort
retention; inactivity next month is not proof of permanent churn.

Merchant payments generated 3,725 successes, 99 reversals and AED 37,065.56 in net
wallet fees. Cash-out generated 936 successes, 22 reversals and AED 914.00 in net
fees. Cash-in is free by design. Fee concentration reflects the configured prices
and service mix. Agent activity values are not cash balances or agent earnings.

The portfolio demonstrates reproducible reporting and reconciliation. A real
implementation would need event histories, a balanced ledger, costs, incremental
ingestion and privacy controls before drawing business conclusions.
