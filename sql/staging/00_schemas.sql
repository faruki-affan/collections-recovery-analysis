-- Load parquet golden tables into local DuckDB (maps to Postgres schemas).
-- Usage: python scripts/load_duckdb.py

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS clean;
CREATE SCHEMA IF NOT EXISTS golden;
CREATE SCHEMA IF NOT EXISTS metrics;
CREATE SCHEMA IF NOT EXISTS analysis;
