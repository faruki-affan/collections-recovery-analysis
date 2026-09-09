-- Deduplicate payments. Do NOT use payment_reference as a transaction key:
-- empirically 3,406 references map to multiple accounts.

CREATE SCHEMA IF NOT EXISTS clean;

CREATE TABLE clean.payments AS
SELECT *
FROM (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY payment_id
            ORDER BY event_at, payment_status
        ) AS rn
    FROM staging.payments p
) x
WHERE rn = 1;

-- Map PTP synonyms. Never drop unmapped codes.
-- PROMISE_TO_PAY (legacy label) == PTP.

-- CREATE TABLE clean.call_dispositions AS
-- SELECT
--     d.*,
--     CASE
--         WHEN disposition_code IN ('PTP', 'PROMISE_TO_PAY') THEN 'PTP'
--         ELSE disposition_code
--     END AS disposition_code_std
-- FROM staging.call_dispositions d;
