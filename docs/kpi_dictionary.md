# KPI dictionary

**All definitions apply to synthetic portfolio simulation data.** Periods are UTC calendar months unless specified. Money is stored in fils and displayed as AED only after aggregation. Reversal metrics use reversal event date; original metrics use transaction event date. Zero denominators return blank, not zero.

| KPI | Definition |
| --- | --- |
| Attempt count | Count transaction IDs across successful, failed and pending statuses. Exclude reversal rows. A customer transfer counts once. |
| Successful transaction count | Count original transactions with status successful, including those later reversed. |
| Successful transaction value | Sum amount_minor for successful originals only. This is gross payment value, not fees. |
| Reversal count/value | Count completed reversal rows / sum their amount_minor in the period. |
| Net transaction value | Successful transaction value minus reversal value occurring in the period. |
| Gross fee revenue | Sum fee_minor on successful originals. |
| Fee refunds | Sum fee_refund_minor on reversal rows. |
| Net fee revenue | Gross fee revenue minus fee refunds. Not profit; costs are not modeled. |
| Failure rate | Failed original attempts / all original attempts in the period. Pending attempts remain in denominator. |
| Pending rate | Pending original attempts / all original attempts. Snapshot at cutoff, not historical status reconstruction. |
| Active customers (monthly) | Distinct customer IDs participating in at least one successful original that month: both transfer sender and recipient, merchant-payment payer, cash-in recipient, cash-out sender. Union all roles then deduplicate. Later reversal does not remove activity; reversal alone does not establish activity. |
| Month-to-month retention | Customers active in month M and M+1 / customers active in M. Last month has no observable next month and returns blank. This is activity retention, not signup-cohort retention. |
| Merchant performance | Successful merchant-payment count, gross value and fees grouped by merchant; linked reversals/refunds grouped through original merchant; net amounts use event dates. Failure rate includes merchant-payment attempts only. |
| Agent activity | Cash-in and cash-out successful count and value grouped by agent and service; linked reversal value and refunds separately. Never treat combined activity value as agent cash balance. |
| Active merchants / agents | Distinct merchants / agents with a successful original in the period, irrespective of later reversal. |

Active customer counts cannot be summed across months or service types. Reversal rows must be aggregated separately before joining to original aggregates to avoid multiplying sums. Pending/failed requested amounts may be inspected operationally but never included in successful value.
