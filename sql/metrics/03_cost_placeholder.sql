-- Cost per ₹ recovered cannot be implemented: no cost facts exist.
-- Placeholder for production once vendor invoices / agent cost land.

-- CREATE VIEW metrics.cost_per_rupee AS
-- SELECT month, total_cost / NULLIF(recovery_amount, 0) AS cost_per_rupee
-- FROM metrics.ops_cost c
-- JOIN metrics.recovery_kpis r USING (month);
