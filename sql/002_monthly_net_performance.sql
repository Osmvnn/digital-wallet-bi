-- SYNTHETIC PORTFOLIO SIMULATION ONLY.
-- Read-only query. Run in pgAdmin connected to digital_wallet_b.
-- Grain: one row per UTC calendar month in the dataset's reporting window.
WITH months AS (
    SELECT month_start::date AS month
    FROM staging.dataset d
    CROSS JOIN LATERAL generate_series(
        (d.manifest->>'window_start')::timestamptz AT TIME ZONE 'UTC',
        ((d.manifest->>'window_end_exclusive')::timestamptz AT TIME ZONE 'UTC')
            - interval '1 month',
        interval '1 month'
    ) AS calendar(month_start)
), originals AS (
    SELECT date_trunc('month', event_date::timestamp)::date AS month,
        count(*) FILTER (WHERE status = 'successful') AS successful_count,
        sum(successful_value_minor) AS successful_value_minor,
        sum(fee_minor) AS gross_fee_revenue_minor
    FROM reporting.fact_transaction
    GROUP BY 1
), reversals AS (
    SELECT date_trunc('month', event_date::timestamp)::date AS month,
        count(*) AS reversal_count,
        sum(amount_minor) AS reversed_value_minor,
        sum(fee_refund_minor) AS fee_refunds_minor
    FROM reporting.fact_reversal
    GROUP BY 1
)
SELECT m.month,
    coalesce(t.successful_count, 0) AS successful_count,
    coalesce(r.reversal_count, 0) AS reversal_count,
    round(coalesce(t.successful_value_minor, 0) / 100.0, 2) AS successful_value_aed,
    round(coalesce(r.reversed_value_minor, 0) / 100.0, 2) AS reversed_value_aed,
    round((coalesce(t.successful_value_minor, 0)
        - coalesce(r.reversed_value_minor, 0)) / 100.0, 2) AS net_value_aed,
    round(coalesce(t.gross_fee_revenue_minor, 0) / 100.0, 2) AS gross_fee_revenue_aed,
    round(coalesce(r.fee_refunds_minor, 0) / 100.0, 2) AS fee_refunds_aed,
    round((coalesce(t.gross_fee_revenue_minor, 0)
        - coalesce(r.fee_refunds_minor, 0)) / 100.0, 2) AS net_fee_revenue_aed
FROM months m
LEFT JOIN originals t ON t.month = m.month
LEFT JOIN reversals r ON r.month = m.month
ORDER BY m.month;
