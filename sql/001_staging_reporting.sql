-- SYNTHETIC PORTFOLIO SIMULATION ONLY. Schema version 1.
-- Executed by load.py inside its transaction, only for an empty project schema.
CREATE SCHEMA staging;
CREATE SCHEMA reporting;

-- Grain: one accepted, immutable simulation dataset for this database.
CREATE TABLE staging.dataset (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    schema_version integer NOT NULL CHECK (schema_version = 1),
    fingerprint text NOT NULL,
    manifest jsonb NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT current_timestamp
);

-- Grain: one fictional account per row in each entity table.
CREATE TABLE staging.customers (
    id text PRIMARY KEY CHECK (id <> ''), created_at timestamptz NOT NULL
);
CREATE TABLE staging.merchants (
    id text PRIMARY KEY CHECK (id <> ''), created_at timestamptz NOT NULL
);
CREATE TABLE staging.agents (
    id text PRIMARY KEY CHECK (id <> ''), created_at timestamptz NOT NULL
);

-- Grain: one original attempt, including unsuccessful attempts.
CREATE TABLE staging.transactions (
    id text PRIMARY KEY CHECK (id <> ''),
    occurred_at timestamptz NOT NULL,
    type text NOT NULL CHECK (type IN ('transfer','merchant_payment','cash_in','cash_out')),
    status text NOT NULL CHECK (status IN ('successful','failed','pending')),
    currency text NOT NULL CHECK (currency = 'AED'),
    amount_minor bigint NOT NULL CHECK (amount_minor >= 0),
    fee_minor bigint NOT NULL CHECK (fee_minor >= 0),
    sender_id text REFERENCES staging.customers(id),
    recipient_id text REFERENCES staging.customers(id),
    merchant_id text REFERENCES staging.merchants(id),
    agent_id text REFERENCES staging.agents(id),
    CHECK (
        (type = 'transfer' AND sender_id IS NOT NULL AND recipient_id IS NOT NULL
         AND sender_id <> recipient_id AND merchant_id IS NULL AND agent_id IS NULL)
        OR (type = 'merchant_payment' AND sender_id IS NOT NULL AND merchant_id IS NOT NULL
            AND recipient_id IS NULL AND agent_id IS NULL)
        OR (type = 'cash_in' AND recipient_id IS NOT NULL AND agent_id IS NOT NULL
            AND sender_id IS NULL AND merchant_id IS NULL)
        OR (type = 'cash_out' AND sender_id IS NOT NULL AND agent_id IS NOT NULL
            AND recipient_id IS NULL AND merchant_id IS NULL)
    ),
    CHECK (fee_minor = CASE WHEN status <> 'successful' THEN 0
        WHEN type = 'transfer' THEN 50
        WHEN type = 'merchant_payment' THEN floor((amount_minor::numeric + 50) / 100)
        WHEN type = 'cash_in' THEN 0 ELSE 100 END)
);

-- Grain: one completed full reversal, at most one per successful original.
CREATE TABLE staging.reversals (
    id text PRIMARY KEY CHECK (id <> ''),
    original_id text NOT NULL UNIQUE REFERENCES staging.transactions(id),
    occurred_at timestamptz NOT NULL,
    currency text NOT NULL CHECK (currency = 'AED'),
    amount_minor bigint NOT NULL CHECK (amount_minor >= 0),
    fee_refund_minor bigint NOT NULL CHECK (fee_refund_minor >= 0)
);

-- Initial reporting layer uses views: no duplicated reporting storage yet.
-- Grain: one original attempt. Successful value and fees are explicit measures.
CREATE VIEW reporting.fact_transaction AS
SELECT t.*, (occurred_at AT TIME ZONE 'UTC')::date AS event_date,
    CASE WHEN status = 'successful' THEN amount_minor ELSE 0 END AS successful_value_minor
FROM staging.transactions t;

-- Grain: one completed reversal, attributed to the original parties and service.
CREATE VIEW reporting.fact_reversal AS
SELECT r.*, (r.occurred_at AT TIME ZONE 'UTC')::date AS event_date,
    t.type, t.sender_id, t.recipient_id, t.merchant_id, t.agent_id
FROM staging.reversals r JOIN staging.transactions t ON t.id = r.original_id;

-- Grain: one customer per month with at least one successful original.
-- UNION deduplicates both roles; reversal alone never creates activity.
CREATE VIEW reporting.customer_month_activity AS
SELECT DISTINCT date_trunc('month', occurred_at AT TIME ZONE 'UTC')::date AS month,
    sender_id AS customer_id
FROM staging.transactions WHERE status = 'successful' AND sender_id IS NOT NULL
UNION
SELECT DISTINCT date_trunc('month', occurred_at AT TIME ZONE 'UTC')::date,
    recipient_id
FROM staging.transactions WHERE status = 'successful' AND recipient_id IS NOT NULL;

-- Grain: one row summarizing the entire loaded window. Aggregate separately
-- before combining, so joins can never multiply original payment values.
CREATE VIEW reporting.executive_summary AS
WITH originals AS (
    SELECT count(*) AS attempts,
        count(*) FILTER (WHERE status = 'successful') AS successful_count,
        count(*) FILTER (WHERE status = 'failed') AS failed_count,
        count(*) FILTER (WHERE status = 'pending') AS pending_count,
        coalesce(sum(amount_minor) FILTER (WHERE status = 'successful'), 0) AS successful_value_minor,
        coalesce(sum(fee_minor), 0) AS gross_fee_revenue_minor
    FROM staging.transactions
), refunds AS (
    SELECT count(*) AS reversal_count,
        coalesce(sum(amount_minor), 0) AS reversed_value_minor,
        coalesce(sum(fee_refund_minor), 0) AS fee_refunds_minor
    FROM staging.reversals
)
SELECT originals.*, refunds.*,
    successful_value_minor - reversed_value_minor AS net_value_minor,
    gross_fee_revenue_minor - fee_refunds_minor AS net_fee_revenue_minor
FROM originals CROSS JOIN refunds;

COMMENT ON SCHEMA staging IS 'Synthetic portfolio simulation only; synthetic data.';
COMMENT ON SCHEMA reporting IS 'Synthetic portfolio simulation only; fees are not profit.';
