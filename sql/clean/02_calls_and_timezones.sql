-- Normalize naive timestamps. Production: store timestamptz in Asia/Kolkata.

-- Calls: interpret event_at in row timezone, convert to IST (PostgreSQL):
-- SELECT call_id,
--        timezone('Asia/Kolkata', timezone(timezone, event_at AT TIME ZONE 'UTC')) AS event_at_ist
-- FROM staging.calls;
-- The CSV timestamps are naive; bind timezone() using the timezone column, not AT TIME ZONE 'UTC', unless the column is UTC.

CREATE TABLE IF NOT EXISTS clean.calls AS
SELECT *
FROM (
    SELECT c.*, ROW_NUMBER() OVER (PARTITION BY call_id ORDER BY event_at) rn
    FROM staging.calls c
) x
WHERE rn = 1;
