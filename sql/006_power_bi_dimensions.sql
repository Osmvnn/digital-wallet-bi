-- SYNTHETIC PORTFOLIO SIMULATION ONLY.
-- Run in pgAdmin as wallet_bi, connected to digital_wallet_b.
-- Additive reporting views; source rows and existing fact views are unchanged.
-- Rerunnable with the same definitions. Separate from the immutable data loader.
BEGIN;

-- Grain: one calendar day. Full calendar years support date-table usage.
-- is_in_reporting_window distinguishes observed days from calendar padding.
CREATE OR REPLACE VIEW reporting.dim_date AS
WITH bounds AS (
    SELECT ((manifest->>'window_start')::timestamptz AT TIME ZONE 'UTC')::date AS start_date,
        ((manifest->>'window_end_exclusive')::timestamptz AT TIME ZONE 'UTC')::date AS end_date
    FROM staging.dataset
), days AS (
    SELECT day::date AS date, b.start_date, b.end_date
    FROM bounds b
    CROSS JOIN LATERAL generate_series(
        date_trunc('year', b.start_date::timestamp),
        date_trunc('year', (b.end_date - 1)::timestamp) + interval '1 year' - interval '1 day',
        interval '1 day'
    ) AS calendar(day)
)
SELECT date,
    extract(year FROM date)::integer AS year,
    extract(quarter FROM date)::integer AS quarter,
    extract(month FROM date)::integer AS month_number,
    to_char(date, 'Mon') AS month_name,
    to_char(date, 'YYYY-MM') AS year_month,
    (extract(year FROM date)::integer * 100 + extract(month FROM date)::integer) AS year_month_sort,
    date_trunc('month', date::timestamp)::date AS month_start,
    date >= start_date AND date < end_date AS is_in_reporting_window
FROM days;

-- Grain: one account. Current-state dimensions; no historical attributes yet.
CREATE OR REPLACE VIEW reporting.dim_customer AS
SELECT id AS customer_id, (created_at AT TIME ZONE 'UTC')::date AS opened_date
FROM staging.customers;

CREATE OR REPLACE VIEW reporting.dim_merchant AS
SELECT id AS merchant_id, (created_at AT TIME ZONE 'UTC')::date AS opened_date
FROM staging.merchants;

CREATE OR REPLACE VIEW reporting.dim_agent AS
SELECT id AS agent_id, (created_at AT TIME ZONE 'UTC')::date AS opened_date
FROM staging.agents;

-- Grain: one service. Include all services even if a smaller sample omits one.
CREATE OR REPLACE VIEW reporting.dim_service AS
SELECT * FROM (VALUES
    ('transfer', 'Customer transfer'),
    ('merchant_payment', 'Merchant payment'),
    ('cash_in', 'Agent cash-in'),
    ('cash_out', 'Agent cash-out')
) AS services(service_type, service_name);

COMMENT ON VIEW reporting.dim_date IS
    'Synthetic simulation calendar: full years; use is_in_reporting_window to filter observed dates.';
COMMENT ON VIEW reporting.dim_customer IS
    'Synthetic accounts. Customer activity must include both sender and recipient roles.';

COMMIT;

-- Initial dataset expected: 730 dates, 365 in window, 1000 customers,
-- 60 merchants, 30 agents, 4 services. Counts vary for other date windows/sizes.
SELECT 'dim_date' AS object_name, count(*) AS rows FROM reporting.dim_date
UNION ALL SELECT 'dates_in_reporting_window', count(*) FROM reporting.dim_date WHERE is_in_reporting_window
UNION ALL SELECT 'dim_customer', count(*) FROM reporting.dim_customer
UNION ALL SELECT 'dim_merchant', count(*) FROM reporting.dim_merchant
UNION ALL SELECT 'dim_agent', count(*) FROM reporting.dim_agent
UNION ALL SELECT 'dim_service', count(*) FROM reporting.dim_service;
