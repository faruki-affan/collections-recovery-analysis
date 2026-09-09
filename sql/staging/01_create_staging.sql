-- Staging: read raw CSVs with explicit types (DuckDB / PostgreSQL-style).
-- Production: replace read_csv_auto with COPY/external tables.

CREATE SCHEMA IF NOT EXISTS staging;

-- DuckDB local:
-- CREATE TABLE staging.payments AS SELECT * FROM read_csv_auto('data/raw/payments.csv', header=true);

CREATE TABLE IF NOT EXISTS staging.payments (
    payment_id VARCHAR NOT NULL,
    account_id VARCHAR,
    borrower_id VARCHAR,
    event_at TIMESTAMP,
    payment_reference VARCHAR,
    amount DOUBLE PRECISION,
    payment_status VARCHAR,
    payment_method VARCHAR,
    provider_id VARCHAR
);

CREATE TABLE IF NOT EXISTS staging.calls (
    call_id VARCHAR NOT NULL,
    account_id VARCHAR,
    borrower_id VARCHAR,
    event_at TIMESTAMP,
    agent_id VARCHAR,
    campaign_id VARCHAR,
    direction VARCHAR,
    vendor_id VARCHAR,
    call_status VARCHAR,
    duration_sec INTEGER,
    timezone VARCHAR
);

CREATE TABLE IF NOT EXISTS staging.accounts (
    account_id VARCHAR PRIMARY KEY,
    borrower_id VARCHAR,
    loan_type VARCHAR,
    principal_amount DOUBLE PRECISION,
    outstanding_amount DOUBLE PRECISION,
    dpd INTEGER,
    risk_segment VARCHAR,
    status VARCHAR,
    opened_at TIMESTAMP,
    timezone VARCHAR,
    schema_version VARCHAR
);

CREATE TABLE IF NOT EXISTS staging.daily_targeting (
    target_id VARCHAR PRIMARY KEY,
    account_id VARCHAR,
    campaign_id VARCHAR,
    target_date DATE,
    priority INTEGER,
    recommended_channel VARCHAR,
    status VARCHAR
);

CREATE TABLE IF NOT EXISTS staging.campaigns (
    campaign_id VARCHAR PRIMARY KEY,
    campaign_name VARCHAR,
    channel VARCHAR,
    strategy_version VARCHAR,
    start_at TIMESTAMP,
    target_definition VARCHAR,
    end_at TIMESTAMP
);
