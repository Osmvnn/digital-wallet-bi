-- SYNTHETIC PORTFOLIO SIMULATION ONLY.
-- Read-only query: run in pgAdmin connected to digital_wallet_b.
-- Grain: one base month M. Retention looks FORWARD from M to M+1.
-- Activity includes successful-original senders and recipients, deduplicated
-- by reporting.customer_month_activity. Later reversals do not erase activity.
WITH months AS (
    SELECT month_start::date AS month
    FROM staging.dataset d
    CROSS JOIN LATERAL generate_series(
        (d.manifest->>'window_start')::timestamptz AT TIME ZONE 'UTC',
        ((d.manifest->>'window_end_exclusive')::timestamptz AT TIME ZONE 'UTC')
            - interval '1 month',
        interval '1 month'
    ) AS calendar(month_start)
), counts AS (
    SELECT m.month,
        following.month IS NOT NULL AS next_month_observed,
        count(a.customer_id) AS active_customers,
        count(b.customer_id) AS retained_customers
    FROM months m
    LEFT JOIN months following
        ON following.month = (m.month + interval '1 month')::date
    LEFT JOIN reporting.customer_month_activity a ON a.month = m.month
    LEFT JOIN reporting.customer_month_activity b
        ON b.customer_id = a.customer_id
        AND b.month = following.month
    GROUP BY m.month, following.month
)
SELECT month,
    (month + interval '1 month')::date AS next_month,
    next_month_observed,
    active_customers,
    CASE WHEN next_month_observed THEN retained_customers END AS retained_next_month,
    CASE WHEN next_month_observed
        THEN active_customers - retained_customers END AS not_active_next_month,
    CASE WHEN next_month_observed
        THEN round(100.0 * retained_customers / nullif(active_customers, 0), 2)
        END AS next_month_retention_pct
FROM counts
ORDER BY month;
