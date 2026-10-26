-- SYNTHETIC PORTFOLIO SIMULATION ONLY.
-- Read-only query; run against digital_wallet_b.
-- Grain: one merchant over the entire loaded reporting window (not monthly).
-- Include zero-activity merchants. Aggregate originals and reversals separately.
WITH originals AS (
    SELECT merchant_id, count(*) AS attempts,
        count(*) FILTER (WHERE status = 'successful') AS successful_count,
        count(*) FILTER (WHERE status = 'failed') AS failed_count,
        count(*) FILTER (WHERE status = 'pending') AS pending_count,
        sum(successful_value_minor) AS successful_value_minor,
        sum(fee_minor) AS gross_fee_revenue_minor
    FROM reporting.fact_transaction
    WHERE type = 'merchant_payment'
    GROUP BY merchant_id
), refunds AS (
    SELECT merchant_id, count(*) AS reversal_count,
        sum(amount_minor) AS reversed_value_minor,
        sum(fee_refund_minor) AS fee_refunds_minor
    FROM reporting.fact_reversal
    WHERE type = 'merchant_payment'
    GROUP BY merchant_id
)
SELECT m.id AS merchant_id,
    coalesce(t.attempts, 0) AS attempts,
    coalesce(t.successful_count, 0) AS successful_count,
    coalesce(t.failed_count, 0) AS failed_count,
    coalesce(t.pending_count, 0) AS pending_count,
    round(100.0 * coalesce(t.failed_count, 0) / nullif(t.attempts, 0), 2) AS failure_rate_pct,
    coalesce(r.reversal_count, 0) AS reversal_count,
    round(coalesce(t.successful_value_minor, 0) / 100.0, 2) AS successful_value_aed,
    round(coalesce(r.reversed_value_minor, 0) / 100.0, 2) AS reversed_value_aed,
    round((coalesce(t.successful_value_minor, 0)
        - coalesce(r.reversed_value_minor, 0)) / 100.0, 2) AS net_value_aed,
    round(coalesce(t.gross_fee_revenue_minor, 0) / 100.0, 2) AS gross_fee_revenue_aed,
    round(coalesce(r.fee_refunds_minor, 0) / 100.0, 2) AS fee_refunds_aed,
    round((coalesce(t.gross_fee_revenue_minor, 0)
        - coalesce(r.fee_refunds_minor, 0)) / 100.0, 2) AS net_fee_revenue_aed
FROM staging.merchants m
LEFT JOIN originals t ON t.merchant_id = m.id
LEFT JOIN refunds r ON r.merchant_id = m.id
ORDER BY net_value_aed DESC, m.id;
