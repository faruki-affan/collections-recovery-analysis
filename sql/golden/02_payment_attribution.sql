-- Last-touch is a SENSITIVITY table, not the recovery KPI.

CREATE TABLE golden.payment_attribution AS
SELECT
    p.payment_id,
    p.account_id,
    p.amount,
    p.event_at AS payment_at,
    i.channel AS last_touch_channel,
    i.event_at AS last_touch_at
FROM clean.payments p
LEFT JOIN LATERAL (
    SELECT channel, event_at
    FROM golden.fact_interaction i
    WHERE i.account_id = p.account_id
      AND i.event_at <= p.event_at
    ORDER BY i.event_at DESC
    LIMIT 1
) i ON TRUE
WHERE upper(p.payment_status) = 'SUCCESS';
