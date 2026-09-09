-- Independent metric implementations. See docs/metric_definitions.md.

CREATE SCHEMA IF NOT EXISTS metrics;

-- Recovery (₹): SUCCESS payments, unique payment_id, no calendar filter here.
CREATE VIEW metrics.recovery_amount AS
SELECT
    date_trunc('month', event_at) AS month,
    SUM(amount) AS recovery_amount,
    COUNT(*) AS n_success_payments,
    COUNT(DISTINCT account_id) AS n_paying_accounts
FROM clean.payments
WHERE upper(payment_status) = 'SUCCESS'
GROUP BY 1;

-- Recovery per account uses the closed 30k book as denominator.
CREATE VIEW metrics.recovery_per_account AS
SELECT
    r.month,
    r.recovery_amount,
    30000 AS n_accounts,
    r.recovery_amount / 30000.0 AS recovery_per_account,
    r.recovery_amount / NULLIF(r.n_paying_accounts, 0) AS recovery_per_paying_account
FROM metrics.recovery_amount r;

-- Contact rate (voice): distinct accounts with ANSWERED call / distinct targeted accounts.
-- RPC: ANSWERED calls / all calls (not accounts).

CREATE VIEW metrics.voice_funnel AS
SELECT
    date_trunc('month', event_at) AS month,
    COUNT(*) AS n_calls,
    SUM(CASE WHEN call_status = 'ANSWERED' THEN 1 ELSE 0 END) AS n_answered,
    SUM(CASE WHEN call_status = 'ANSWERED' THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0) AS rpc
FROM clean.calls
GROUP BY 1;
