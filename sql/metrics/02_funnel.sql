-- Contact rate, RPC, PTP, channel conversion.
-- DuckDB: run after scripts/load_duckdb.py

CREATE OR REPLACE VIEW metrics.contact_rate AS
SELECT
    month_ist,
    SUM(contacted_voice) * 1.0 / NULLIF(SUM(targeted), 0) AS contact_rate_targeted,
    SUM(contacted_voice) * 1.0 / NULLIF(COUNT(*), 0) AS contact_rate_portfolio,
    SUM(n_answered) * 1.0 / NULLIF(SUM(n_calls), 0) AS rpc
FROM golden.account_month
GROUP BY 1;

CREATE OR REPLACE VIEW metrics.ptp_rates AS
SELECT
    month_ist,
    SUM(n_ptp) AS ptp_events,
    SUM(n_ptp_kept) AS ptp_kept_events,
    SUM(n_ptp_kept) * 1.0 / NULLIF(SUM(n_ptp), 0) AS ptp_kept_rate
FROM golden.account_month
GROUP BY 1;

CREATE OR REPLACE VIEW metrics.recovery_kpis AS
SELECT
    month_ist,
    SUM(recovery_amount) AS recovery_amount,
    SUM(recovered_flag) * 1.0 / COUNT(*) AS recovery_rate_portfolio,
    SUM(recovery_amount) * 1.0 / COUNT(*) AS recovery_per_account
FROM golden.account_month
GROUP BY 1;
