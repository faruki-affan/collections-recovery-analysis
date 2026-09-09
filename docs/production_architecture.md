# Production analytics architecture

## Flow

```text
Source systems → Raw (immutable) → Staging → Clean → Golden → Feature → Metrics → Dashboard
                                                                      ↘ DQ tests / monitors
```

Local implementation: CSV/parquet + DuckDB. Production mapping: **PostgreSQL** (or warehouse) schemas `staging`, `clean`, `golden`, `metrics`, `analysis`.

## Data contracts

| Dataset | Primary key | Required fields | Freshness | Owner |
| --- | --- | --- | --- | --- |
| payments | `payment_id` | account_id, event_at, amount > 0, payment_status | Daily + late window 7d | Payments |
| calls | `call_id` | account_id, event_at, timezone, call_status, vendor_id | Daily | Telephony |
| daily_targeting | `target_id` | account_id, campaign_id, target_date | Daily 06:00 IST | Strategy |
| accounts | `account_id` | borrower_id, opened_at | Daily snapshot **plus** history | Core |
| agents | `agent_id` + `valid_from` (SCD2) | employee_code stable, status | Daily | HR / vendor |
| borrowers | `borrower_id` + `valid_from` | phone, city — conflicts rejected | Daily | Core |
| sessions | `session_id` | login, logout, timezone | Daily | WFM |
| ptp | `ptp_id` | promised_amount, status, source | Daily | Ops |

**Contract rule:** payments must carry optional `target_id`, `campaign_id`, `interaction_id` when known. They do not today.

## Keys and lineage

- Golden account-month is composed of accounts ⋈ calendar ⋈ targeting ⋈ payments ⋈ calls ⋈ ptp ⋈ digital ⋈ field.
- Lineage: each metric row stores `as_of_ist`, `pipeline_version`, `window_start`, `window_end`.
- Rejected records land in `rejected.*` with `reject_rule` — never deleted from raw.

## Incremental processing

- Daily incremental append of events with `event_at_ist >= last_watermark - 2 days` (timezone date-shift buffer).
- Recompute account-month for any month touched by late events.
- Full rebuild of identity tables (agents, borrowers) daily until SCD2 is real.

## Late-arriving data

- Calls already appear slightly outside the payment window.
- Watermark: 48 hours for calls, 7 days for payments (settlement).
- Dashboard shows “complete through D-2 IST” for daily, “complete months” for MoM.

## Backfills

- Parameterized `month_ist` rebuild.
- Payment dedupe is idempotent (`payment_id`).
- Do not backfill by overwriting raw.

## Data-quality checks (blocking vs warning)

**Blocking (fail the job):** duplicate `payment_id` after clean; negative amounts; account-month grain broken; SUCCESS sum ≠ account-month recovery sum.

**Warning:** orphan borrower_id > 5%; date-shift rate > 15%; snapshot vs history match < 50%; attempt/call independence chi-square; MoM total ₹ vs per-day sign disagreement (the 11% pattern).

Implemented in `tests/test_data_quality.py` and should be scheduled after each pipeline run.

## Monitoring and anomalies

1. **Calendar-adjusted recovery per day** with a 7-day rolling z-score. Alert if \|z\| > 3.
2. **Duplicate payment extra-row %** — should stay ~0 in production after the source fix.
3. **RPC** band 15–25% in this book; investigate vendor if a vendor moves >3 pp.
4. **Partial month detector:** if `n_days` < days_in_month, hide MoM total ₹ or mark PROVISIONAL.
5. **Identity drift:** count of agent_ids with >1 employee_code in a day.

## Feature layer

Account-month features already in golden: targeted, contacted, recovery, PTP, channel counts, snapshot attributes (marked untrusted). Future: true as-of DPD from a history table that reconciles.

## Dashboard

Streamlit one-screen CEO view: `dashboard/app.py`. Production would bind the same metrics views (Looker/Power BI/Metabase on PostgreSQL).
