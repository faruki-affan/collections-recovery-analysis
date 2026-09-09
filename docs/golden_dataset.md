# Golden dataset

## Grain

**Primary analytical grain: `account_id` × calendar month (`month_ist`).**

Table: `data/golden/golden_account_month.parquet` (240,000 rows = 30,000 accounts × 8 months).

### Why this grain

Leadership asked a **month-on-month recovery** question. The loan book is **closed**: every account `opened_at` is on or before 2025-11-30, so the same 30,000 accounts exist throughout the operational window. An account-month spine keeps the **denominator visible** (all accounts vs targeted vs contacted vs paid) and prevents unsuccessful accounts from silently disappearing from rates.

Supporting grains:

| Table | Grain | Role |
| --- | --- | --- |
| `fact_payment` | `payment_id` | Cash recovered / failed / reversed |
| `fact_interaction` | event | Voice, WhatsApp, SMS, field |
| `fact_payment_attribution` | `payment_id` | Last-touch sensitivity, not the default KPI |
| `dim_account` | `account_id` | Snapshot attributes (untrusted as “current status”) |
| `dim_agent` | `agent_id` | 1,000 operational IDs; attributes LOW trust |
| `dim_borrower` | `borrower_id` | Mode geography; PII conflicts flagged |
| `dim_campaign` | `campaign_id` | Labels are internally inconsistent |
| `dim_vendor` | `vendor_id` | Telephony vendor master |

## Window

Operational events run **2026-01-01 through 2026-08-08** (August is a partial month). This is **~7.3 months**, not 12. Calls include 5 rows slightly outside that window after timezone conversion.

All KPI months use **Asia/Kolkata** dates (`month_ist`).

## Source-of-truth decisions

| Question | Decision | Why |
| --- | --- | --- |
| How much cash was recovered? | `payments` with `payment_status = SUCCESS`, **unique `payment_id`** | Exact duplicate rows and 14 extra `payment_id` copies inflate totals. |
| Is `payment_reference` a transaction id? | **No** | 3,406 references map to **multiple accounts** with different amounts and dates (ID collision, not retries). |
| What is an eligible account? | Closed book of 30,000 `accounts.account_id` every month | Snapshot `status` matches last history status only **12%** of the time; using `ACTIVE` as the denominator would be denominator manipulation. |
| Who was worked? | `daily_targeting` in that month | Operational denominator for contact/PTP rates. |
| Agent identity | Event `agent_id` (1,000 values) | `agents.csv` has 30,000 rows; every `agent_id` has conflicting name, employee code, vendor, team, and status. Only 10 distinct names exist in the file. |
| Borrower geography | Mode city/state per `borrower_id`, LOW confidence | 8,517 / 11,015 IDs have conflicting PII. 2,913 accounts have borrower_ids absent from `borrowers`. |
| Call outcome | `calls.call_status` after `call_id` dedupe | `call_attempts.attempt_status` is **uncorrelated** with `calls.call_status` (~20% in every cell). Attempts are not a nested fact. |
| Disposition | Mapped `PTP` = `PROMISE_TO_PAY` | Dual labels coexist in legacy/v1/v2 for the whole period. |
| Payment attribution for the headline recovery KPI | **None** (cash is cash) | Payments have no campaign_id. Last-touch within 7 days explains only a minority of SUCCESS rupees. |
| Campaign channel | Do not trust `campaign_name` or even `campaigns.channel` vs targeting | `recommended_channel` ≠ campaign `channel` on **80%** of targeting rows. Names like `30DPD_W1` are used with NPA / HIGH_RISK / PROMISE_BROKEN definitions. |

## Deduplication

- Payments: exact row, then `payment_id`.
- Calls: exact row, then `call_id`.
- WhatsApp: exact row, then event id.
- Agents/borrowers: collapse to entity id; **do not treat latest snapshot attributes as truth**.

Rejected payment rows are written to `data/rejected/payments.parquet`.

## Timestamps

- `calls`, `agent_sessions`: naive `event_at` interpreted in the row `timezone`, converted to IST.
- **9.8% of unique calls change calendar date** after conversion (0% Asia/Kolkata, 6.3% Asia/Dubai, 23.0% UTC).
- Payments, PTP, digital, field, complaints, history: **no timezone column**. Assumption: treat naive timestamps as IST. This is documented, not proven.
- `account_status_history.recorded_at` is **before** `event_at` on 50% of rows (clock / pipeline disorder).

## Missing data

- Field `scheduled_at` is null on ~1% of visits; rows kept.
- Orphan borrower_ids on accounts: flag `orphan_borrower`, do not drop accounts (they still pay).
- Unmapped dispositions: `UNMAPPED`, not deleted.

## Exclusion rules

- Negative amounts: none observed; tests fail if they appear.
- Partial August is **kept** but KPIs that are month totals must not be compared to July without day-count adjustment.
- Reversed payments are stored separately and **not** netted in the headline SUCCESS total (no evidence they reverse a matched SUCCESS `payment_id`).

## Pipeline

```text
data/raw/*.csv
  → scripts/build_staging.py     (parquet copies)
  → clean rules in src/collections_analytics/build.py
  → data/clean/*.parquet
  → data/golden/*.parquet
  → src/collections_analytics/metrics.py
```

Run: `python scripts/run_pipeline.py`

SQL equivalents live under `sql/staging|clean|golden|metrics|analysis` and can be loaded with `python scripts/load_duckdb.py` (DuckDB local warehouse). Production mapping is PostgreSQL schemas of the same names.
