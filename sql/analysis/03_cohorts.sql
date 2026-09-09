-- Cohort: accounts by opened year (book is pre-2026). Snapshot only.

CREATE OR REPLACE VIEW analysis.opened_year_cohort AS
SELECT
    date_trunc('year', opened_at) AS opened_year,
    COUNT(*) AS n_accounts
FROM clean.accounts
GROUP BY 1;

-- Targeting strategy mix over months (test for a mid-year switch).

CREATE OR REPLACE VIEW analysis.targeting_strategy_month AS
SELECT
    date_trunc('month', t.target_date) AS month,
    c.strategy_version,
    COUNT(*) AS n_rows
FROM clean.daily_targeting t
JOIN clean.campaigns c ON c.campaign_id = t.campaign_id
GROUP BY 1, 2;
