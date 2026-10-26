# Data model

**Synthetic portfolio simulation only.** A grain states exactly what one row represents. Define it first to prevent duplicate counts later.

## Source and staging tables

| Table | Grain / primary key | Columns and references |
| --- | --- | --- |
| customers | One fictional customer account / id | created_at UTC |
| merchants | One fictional merchant account / id | created_at UTC |
| agents | One fictional agent account / id | created_at UTC |
| transactions | One original payment attempt / id | occurred_at UTC, type, status, currency, amount_minor, fee_minor; sender_id and recipient_id → customers; merchant_id → merchants; agent_id → agents |
| reversals | One completed full reversal / id | original_id → transactions (unique), occurred_at UTC, currency, amount_minor, fee_refund_minor |

No names, contact information, bank details or real account identifiers are present. `amount_minor` is requested value for unsuccessful attempts and completed value for successful attempts. Fees are recognized amounts, not quoted fees. CSV absent roles are empty strings; the loader will map these to SQL NULL.

| Type | Required participants | All other roles |
| --- | --- | --- |
| transfer | sender_id, recipient_id (different customers) | Absent |
| merchant_payment | sender_id, merchant_id | Absent |
| cash_in | recipient_id, agent_id | Absent |
| cash_out | sender_id, agent_id | Absent |

Every participating account must exist by the transaction timestamp. Reversal timestamp must be strictly later than its original and before the cutoff. One row is one transfer, not separate debit and credit rows. This is a reporting model, not a double-entry ledger; balances, liquidity, overdrafts and settlement are not modeled.

## Implemented reporting model

The `staging` tables retain the source grains. `staging.dataset` contains one accepted dataset's manifest, fingerprint and load time. Reporting views expose `dim_customer`, `dim_merchant`, `dim_agent` (one current account each), `dim_date` (one UTC calendar day) and `dim_service` (one service). `fact_transaction` stays one original attempt; `fact_reversal` stays one completed reversal and carries original service/party keys for attribution. PostgreSQL money uses BIGINT minor units; timestamps use TIMESTAMPTZ. Status remains a transaction attribute.

Power BI imports the two fact views and four dimensions: date, merchant, agent and service. Each dimension filters both facts through active single-direction one-to-many relationships. The facts are not directly related. Calendar dates cover full years; a report-level flag limits reporting to the observed window.

Customer measures union successful sender and recipient IDs and deduplicate them in DAX. No physical customer bridge is needed at this dataset size. `reporting.customer_month_activity` provides an independent SQL reference with one customer/month row. `dim_customer` is available in SQL but is not imported into the six-table Power BI model. Retention intersects current- and next-month customer sets, preserving service/partner context while changing date context. It returns blank for unobserved next months and multi-month totals. The customer page uses month filtering only.

The loader validates before committing, uses stable source IDs and unique constraints, and records source hashes. An identical rerun reconciles existing rows without inserting duplicates. Different data is rejected. Status updates, incremental batches and evolving dimensions are outside scope.
