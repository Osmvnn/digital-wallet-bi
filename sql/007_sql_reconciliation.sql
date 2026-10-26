-- Synthetic data. Export this result as CSV in pgAdmin, then compare it with
-- the result of 008_powerbi_reconciliation.dax using src/reconcile.py.
-- Grain: one calendar month/service pair. Integer fils throughout.
WITH originals AS (
    SELECT to_char(event_date,'YYYY-MM') AS month, type AS service,
        count(*) AS attempts,
        count(*) FILTER (WHERE status='successful') AS successes,
        count(*) FILTER (WHERE status='failed') AS failures,
        count(*) FILTER (WHERE status='pending') AS pending,
        sum(successful_value_minor) AS gross_value_minor,
        sum(fee_minor) AS gross_fees_minor
    FROM reporting.fact_transaction GROUP BY 1,2
), refunds AS (
    SELECT to_char(event_date,'YYYY-MM') AS month, type AS service,
        count(*) AS reversals, sum(amount_minor) AS reversed_value_minor,
        sum(fee_refund_minor) AS fee_refunds_minor
    FROM reporting.fact_reversal GROUP BY 1,2
)
SELECT coalesce(t.month,r.month) AS month, coalesce(t.service,r.service) AS service,
    coalesce(attempts,0) AS attempts, coalesce(successes,0) AS successes,
    coalesce(failures,0) AS failures, coalesce(pending,0) AS pending,
    coalesce(gross_value_minor,0) AS gross_value_minor,
    coalesce(gross_fees_minor,0) AS gross_fees_minor,
    coalesce(reversals,0) AS reversals,
    coalesce(reversed_value_minor,0) AS reversed_value_minor,
    coalesce(fee_refunds_minor,0) AS fee_refunds_minor
FROM originals t FULL JOIN refunds r USING (month,service)
ORDER BY 1,2;
