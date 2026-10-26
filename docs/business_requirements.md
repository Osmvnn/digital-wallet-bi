# Business requirements — milestone 1

**Synthetic portfolio simulation only; synthetic data.**

Management needs successful transaction counts and value, fee revenue, failure rates, customer activity and retention, and merchant/agent activity. Four services: customer transfers, merchant payments, agent cash-in and agent cash-out. All identities are fictional IDs without personal details.

## Scope and assumptions

- Initial population: 1,000 customers, 60 merchants, 30 agents and exactly 10,000 payment attempts. Additional reversal rows do not increase payment-attempt counts.
- Each party has one simulated account. All accounts open 1–365 days before the reporting window, so the first milestone focuses on activity rather than acquisition.
- Simulated currency: AED, 100 integer fils per AED. Amounts are uniformly sampled from 100 to 200,000 fils. No floating-point money.
- Attempts are spread approximately evenly across 12 complete calendar months. Service probabilities: transfers 30%, merchant payments 40%, cash-in 20%, cash-out 10%. Status probabilities: successful 92%, failed 6%, pending 2%. Actual sample proportions vary.
- Fees on successful transactions only: transfers 50 fils; merchant payments 1% rounded half-up to a fil; cash-in free; cash-out 100 fils. No tax, agent commissions, settlement costs or FX. Fee payer attribution is outside this milestone.
- Successful transactions have a 2.5% reversal-selection probability. Full reversals occur 1 second–7 days later; those falling outside the window are omitted. This creates cutoff censoring near the window end.
- These distributions are deliberately simple assumptions, not discoveries or forecasts. No profitability claims are supported.

## Transaction lifecycle

Conceptually an attempt enters pending, then becomes successful or failed. The dataset records one snapshot status at the reporting cutoff; it does not store transition history. `occurred_at` is the reporting event timestamp, with successful completion treated as instantaneous for this simulation. A pending row has no recognized value or fee; a failed row also has no recognized value or fee. Pending rows may be old because operational resolution is not simulated.

A successful original remains successful after reversal. A separate linked reversal row records a completed full reversal and full fee refund. Each original can have at most one reversal; failed and pending originals cannot be reversed. Partial reversals, reversal attempts, retries and later status changes are outside scope.

Gross successful counts/value stay on the original event date. Reversed counts/value and fee refunds appear on the reversal date. Net value = gross successful value minus reversal value; net fees = gross fees minus refunded fees. A reversal in a later month reduces that later month's net amounts, so monthly net figures can be negative. We do not rewrite the original month or relabel its status.

## Acceptance criteria

Generate deterministic CSVs and a manifest, validate persisted rows, and summarize counts and money. Reject duplicate IDs, unknown participants, missing/extra participant roles, self-transfers, invalid times, pre-account transactions, invalid statuses, negative/fractional money, incorrect fees and inconsistent reversals. Monetary reconciliation is arithmetic reporting, not proof of ledger balance or settlement.
