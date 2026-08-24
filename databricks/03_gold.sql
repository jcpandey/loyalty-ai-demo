CREATE OR REPLACE TABLE loyalty_demo.gold.daily_partner_points AS
SELECT
    event_date,
    partner_id,
    SUM(CASE WHEN event_type = 'POINTS_EARNED' THEN points ELSE 0 END) AS points_earned,
    ABS(SUM(CASE WHEN event_type = 'POINTS_REDEEMED' THEN points ELSE 0 END)) AS points_redeemed,
    SUM(points) AS net_points,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT member_id) AS active_members,
    SUM(amount_aud) AS transaction_value_aud
FROM loyalty_demo.silver.loyalty_events
GROUP BY event_date, partner_id;

CREATE OR REPLACE TABLE loyalty_demo.gold.hourly_event_metrics AS
SELECT
    date_trunc('hour', event_ts) AS event_hour,
    event_type,
    partner_id,
    COUNT(*) AS event_count,
    SUM(points) AS total_points,
    AVG(amount_aud) AS average_value_aud
FROM loyalty_demo.silver.loyalty_events
GROUP BY date_trunc('hour', event_ts), event_type, partner_id;

CREATE OR REPLACE VIEW loyalty_demo.gold.member_balance AS
SELECT
    member_id,
    SUM(points) AS current_points_balance,
    MAX(event_ts) AS last_activity_timestamp
FROM loyalty_demo.silver.loyalty_events
GROUP BY member_id;
