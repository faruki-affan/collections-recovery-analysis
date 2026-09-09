-- Driver, cohort, channel, campaign views.

CREATE OR REPLACE VIEW analysis.driver_risk AS
SELECT risk_segment, COUNT(*) n, AVG(recovered_flag) recovery_rate, SUM(recovery_amount) recovery
FROM golden.account_month
GROUP BY 1;

CREATE OR REPLACE VIEW analysis.channel_activity AS
SELECT month_ist,
       SUM(n_calls) calls, SUM(n_wa) wa, SUM(n_sms) sms, SUM(n_field) field
FROM golden.account_month
GROUP BY 1;

CREATE OR REPLACE VIEW analysis.campaign_inconsistency AS
SELECT campaign_name, channel, target_definition, strategy_version, COUNT(*) n
FROM golden.dim_campaign
GROUP BY 1,2,3,4;
