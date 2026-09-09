CREATE SCHEMA IF NOT EXISTS golden;

-- Grain: one row per account_id × calendar month (IST operational calendar).
-- Why: leadership metrics are monthly; the book is closed (30,000 accounts).
-- Account-month lets denominators stay visible (portfolio vs targeted vs contacted).

CREATE TABLE golden.account_month AS
WITH months AS (
    SELECT DATE '2026-01-01' AS month_start
    UNION ALL SELECT DATE '2026-02-01'
    UNION ALL SELECT DATE '2026-03-01'
    UNION ALL SELECT DATE '2026-04-01'
    UNION ALL SELECT DATE '2026-05-01'
    UNION ALL SELECT DATE '2026-06-01'
    UNION ALL SELECT DATE '2026-07-01'
    UNION ALL SELECT DATE '2026-08-01'
),
accounts AS (
    SELECT account_id FROM staging.accounts
),
spine AS (
    SELECT a.account_id, m.month_start
    FROM accounts a CROSS JOIN months m
),
pay AS (
    SELECT
        account_id,
        date_trunc('month', event_at)::date AS month_start,
        SUM(CASE WHEN upper(payment_status) = 'SUCCESS' THEN amount ELSE 0 END) AS recovery_amount
    FROM clean.payments
    GROUP BY 1, 2
),
tgt AS (
    SELECT
        account_id,
        date_trunc('month', target_date)::date AS month_start,
        COUNT(*) AS n_target_rows
    FROM staging.daily_targeting
    GROUP BY 1, 2
)
SELECT
    s.account_id,
    s.month_start,
    COALESCE(t.n_target_rows, 0) AS n_target_rows,
    CASE WHEN t.n_target_rows > 0 THEN 1 ELSE 0 END AS targeted,
    COALESCE(p.recovery_amount, 0) AS recovery_amount,
    CASE WHEN COALESCE(p.recovery_amount, 0) > 0 THEN 1 ELSE 0 END AS recovered_flag
FROM spine s
LEFT JOIN tgt t
  ON t.account_id = s.account_id AND t.month_start = s.month_start
LEFT JOIN pay p
  ON p.account_id = s.account_id AND p.month_start = s.month_start;
