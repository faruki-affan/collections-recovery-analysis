-- Monthly performance used to test the 11% claim.

CREATE SCHEMA IF NOT EXISTS analysis;

CREATE VIEW analysis.monthly_recovery AS
SELECT
    date_trunc('month', event_at) AS month,
    SUM(amount) AS recovery_amount,
    COUNT(*) AS n_success,
    COUNT(DISTINCT account_id) AS n_paying_accounts,
    COUNT(DISTINCT CAST(event_at AS date)) AS n_days,
    SUM(amount) / NULLIF(COUNT(DISTINCT CAST(event_at AS date)), 0) AS recovery_per_day
FROM clean.payments
WHERE upper(payment_status) = 'SUCCESS'
GROUP BY 1
ORDER BY 1;

-- Mix: snapshot risk_segment is NOT a historical mix. Use only as a cross-section.

CREATE VIEW analysis.recovery_by_risk_snapshot AS
SELECT
    a.risk_segment,
    COUNT(*) AS n_accounts,
    SUM(CASE WHEN p.recovery_amount > 0 THEN 1 ELSE 0 END) AS n_paid,
    SUM(COALESCE(p.recovery_amount, 0)) AS recovery_amount
FROM clean.accounts a
LEFT JOIN (
    SELECT account_id, SUM(amount) AS recovery_amount
    FROM clean.payments
    WHERE upper(payment_status) = 'SUCCESS'
    GROUP BY 1
) p ON p.account_id = a.account_id
GROUP BY 1;
