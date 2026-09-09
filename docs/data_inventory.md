# Data inventory

Generated from `data/raw/*.csv`. There is a `data_dictionary.csv` in the package, but it is **not** treated as a source of truth — it lists dtypes only and does not define keys, grains, or metric logic.

## Package notes (from supplier README)

- Synthetic collections dataset, seed 42.
- Intentionally includes duplicates, missing values, mixed timezones, inconsistent IDs, late events, schema versions, legacy disposition codes, and duplicate payment events.
- Event-table row counts can exceed nominal size because duplicate rows were injected.

## Files discovered

| File | Rows | Columns | Exact duplicate rows | Candidate PK (unique + non-null) |
| --- | ---: | ---: | ---: | --- |
| `borrowers.csv` | 30,600 | 8 | 600 | — (none at row grain) |
| `accounts.csv` | 30,000 | 11 | 0 | account_id |
| `agents.csv` | 30,000 | 8 | 0 | — (none at row grain) |
| `agent_sessions.csv` | 15,000 | 7 | 0 | session_id |
| `campaigns.csv` | 120 | 7 | 0 | campaign_id, start_at, end_at |
| `daily_targeting.csv` | 45,000 | 7 | 0 | target_id |
| `calls.csv` | 91,350 | 11 | 1,271 | — (none at row grain) |
| `call_attempts.csv` | 120,000 | 9 | 0 | attempt_id |
| `call_dispositions.csv` | 35,000 | 8 | 0 | disposition_id |
| `whatsapp_events.csv` | 60,600 | 8 | 600 | — (none at row grain) |
| `sms_events.csv` | 45,000 | 8 | 0 | sms_event_id |
| `field_visits.csv` | 25,000 | 10 | 0 | visit_id, latitude, longitude |
| `promises_to_pay.csv` | 18,000 | 9 | 0 | ptp_id |
| `payments.csv` | 25,500 | 9 | 486 | — (none at row grain) |
| `vendor_telephony.csv` | 15 | 6 | 0 | vendor_id, vendor_account_id |
| `complaints.csv` | 8,000 | 9 | 0 | complaint_id |
| `account_status_history.csv` | 60,000 | 8 | 0 | history_id |

## Empirical relationships (not assumed)

| Child | Key | Parent | Notes |
| --- | --- | --- | --- |
| Almost all event tables | `account_id` | `accounts` | Strong; payments orphan rate <1% after clean |
| Event tables | `borrower_id` | `borrowers` | **Weak** — ~8–10% orphan ids; borrower file is not SoT |
| `accounts` | `borrower_id` | `borrowers` | 2,913 accounts orphan |
| `calls` | `vendor_id` | `vendor_telephony` | OK |
| `calls` | `campaign_id` | `campaigns` | Present |
| `call_attempts` / `call_dispositions` | `call_id` | `calls` | Attempts always match; dispositions cover ~32% of calls |
| `daily_targeting` | `campaign_id` | `campaigns` | OK; channel fields disagree |

`agents.agent_id` is unique as an **entity** (1,000 ids) but not as a **row** (30,000 snapshots). `campaigns.start_at`/`end_at` being unique does not make them keys.

## Likely business meaning (inferred)

| File | Meaning | Grain we trust |
| --- | --- | --- |
| accounts | Loan/credit account snapshot | `account_id` |
| borrowers | Customer PII, heavily conflicted | none at row; entity id only |
| agents | Agent HR dump, conflicted SCD | `agent_id` on **events** |
| agent_sessions | Login/logout for hours | `session_id` |
| campaigns | Marketing/ops campaign header; labels untrustworthy | `campaign_id` |
| daily_targeting | Who to work that day | `target_id` |
| calls | Dialer call fact | `call_id` after dedupe |
| call_attempts | Nested attempts — **not** aligned to call_status | `attempt_id` |
| call_dispositions | Outcome codes, dual PTP labels | `disposition_id` |
| whatsapp_events / sms_events | Digital funnel events | event id after dedupe |
| field_visits | Field activity | `visit_id` |
| promises_to_pay | PTP objects | `ptp_id` |
| payments | Cash / fail / pending / reverse | `payment_id` after dedupe |
| vendor_telephony | Dialer vendor master | `vendor_id` |
| complaints | Complaints | `complaint_id` |
| account_status_history | Status events; clocks disordered | `history_id` |

Operational window in events is Jan–8 Aug **2026**. Account opening dates are 2024–Nov 2025.

## Per-dataset profile

### `borrowers.csv`

- Rows: **30,600** | Columns: **8**
- Exact duplicate rows: **600**
- Candidate primary keys: none

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `borrower_id` | str | 0.00% | 11,015 |
| `name` | str | 0.00% | 10 |
| `phone` | float64 | 2.01% | 29,395 |
| `email` | str | 2.92% | 15,377 |
| `city` | str | 0.00% | 10 |
| `created_at` | str | 0.00% | 29,997 |
| `updated_at` | str | 0.00% | 29,991 |
| `state` | str | 0.00% | 9 |

**Date-like columns**

- `phone`: 1970-01-01 00:00:09.000004704 → 1970-01-01 00:00:09.999938435 (parse rate 98.0%)
- `created_at`: 2025-01-01 00:14:38 → 2026-08-03 23:37:55 (parse rate 100.0%)
- `updated_at`: 2025-01-01 00:19:40 → 2026-08-03 23:48:36 (parse rate 100.0%)

### `accounts.csv`

- Rows: **30,000** | Columns: **11**
- Exact duplicate rows: **0**
- Candidate primary keys: ['account_id']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `account_id` | str | 0.00% | 30,000 |
| `borrower_id` | str | 1.52% | 10,943 |
| `loan_type` | str | 0.00% | 5 |
| `principal_amount` | float64 | 0.00% | 29,996 |
| `outstanding_amount` | float64 | 0.00% | 29,994 |
| `dpd` | int64 | 0.00% | 11 |
| `risk_segment` | str | 0.00% | 4 |
| `status` | str | 0.00% | 4 |
| `opened_at` | str | 0.00% | 29,993 |
| `timezone` | str | 0.00% | 3 |
| `schema_version` | str | 0.00% | 3 |

**Date-like columns**

- `principal_amount`: 1970-01-01 00:00:00.000010055 → 1970-01-01 00:00:00.000799968 (parse rate 100.0%)
- `outstanding_amount`: 1970-01-01 00:00:00.000001002 → 1970-01-01 00:00:00.000699963 (parse rate 100.0%)
- `dpd`: 1970-01-01 00:00:00 → 1970-01-01 00:00:00.000000180 (parse rate 100.0%)
- `opened_at`: 2024-01-01 00:02:27 → 2025-11-30 23:52:36 (parse rate 100.0%)

### `agents.csv`

- Rows: **30,000** | Columns: **8**
- Exact duplicate rows: **0**
- Candidate primary keys: none

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `agent_id` | str | 0.00% | 1,000 |
| `employee_code` | str | 0.00% | 1,099 |
| `agent_name` | str | 0.00% | 10 |
| `vendor_id` | str | 0.00% | 15 |
| `team` | str | 0.00% | 5 |
| `status` | str | 0.00% | 3 |
| `joined_at` | str | 0.00% | 29,995 |
| `updated_at` | str | 0.00% | 29,987 |

**Date-like columns**

- `joined_at`: 2024-01-01 00:10:05 → 2025-11-30 23:23:30 (parse rate 100.0%)
- `updated_at`: 2025-01-01 00:57:32 → 2026-08-03 23:45:38 (parse rate 100.0%)

### `agent_sessions.csv`

- Rows: **15,000** | Columns: **7**
- Exact duplicate rows: **0**
- Candidate primary keys: ['session_id']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `session_id` | str | 0.00% | 15,000 |
| `agent_id` | str | 0.00% | 1,000 |
| `login_at` | str | 0.00% | 14,996 |
| `channel` | str | 0.00% | 4 |
| `device_id` | str | 0.00% | 1,500 |
| `timezone` | str | 0.00% | 2 |
| `logout_at` | str | 0.00% | 14,996 |

**Date-like columns**

- `login_at`: 2026-01-01 00:01:57 → 2026-08-08 23:51:54 (parse rate 100.0%)
- `logout_at`: 2026-01-01 04:48:48 → 2026-08-09 07:50:12 (parse rate 100.0%)

### `campaigns.csv`

- Rows: **120** | Columns: **7**
- Exact duplicate rows: **0**
- Candidate primary keys: ['campaign_id', 'start_at', 'end_at']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `campaign_id` | str | 0.00% | 120 |
| `campaign_name` | str | 0.00% | 5 |
| `channel` | str | 0.00% | 5 |
| `strategy_version` | str | 0.00% | 4 |
| `start_at` | str | 0.00% | 120 |
| `target_definition` | str | 0.00% | 5 |
| `end_at` | str | 0.00% | 120 |

**Date-like columns**

- `start_at`: 2026-01-01 09:34:51 → 2026-05-29 20:31:27 (parse rate 100.0%)
- `end_at`: 2026-01-16 12:12:50 → 2026-08-16 18:13:39 (parse rate 100.0%)

### `daily_targeting.csv`

- Rows: **45,000** | Columns: **7**
- Exact duplicate rows: **0**
- Candidate primary keys: ['target_id']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `target_id` | str | 0.00% | 45,000 |
| `account_id` | str | 0.00% | 23,344 |
| `campaign_id` | str | 0.00% | 120 |
| `target_date` | str | 0.00% | 220 |
| `priority` | int64 | 0.00% | 10 |
| `recommended_channel` | str | 0.00% | 4 |
| `status` | str | 0.00% | 4 |

**Date-like columns**

- `target_date`: 2026-01-01 00:00:00 → 2026-08-08 00:00:00 (parse rate 100.0%)
- `priority`: 1970-01-01 00:00:00.000000001 → 1970-01-01 00:00:00.000000010 (parse rate 100.0%)

### `calls.csv`

- Rows: **91,350** | Columns: **11**
- Exact duplicate rows: **1,271**
- Candidate primary keys: none

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `call_id` | str | 0.00% | 90,000 |
| `account_id` | str | 0.00% | 28,408 |
| `borrower_id` | str | 0.00% | 11,992 |
| `event_at` | str | 0.00% | 89,796 |
| `agent_id` | str | 2.00% | 1,000 |
| `campaign_id` | str | 0.00% | 120 |
| `direction` | str | 0.00% | 2 |
| `vendor_id` | str | 0.00% | 15 |
| `call_status` | str | 0.00% | 5 |
| `duration_sec` | int64 | 0.00% | 900 |
| `timezone` | str | 0.00% | 3 |

**Date-like columns**

- `event_at`: 2025-12-29 06:52:37 → 2026-08-12 15:43:05 (parse rate 100.0%)
- `duration_sec`: 1970-01-01 00:00:00 → 1970-01-01 00:00:00.000000899 (parse rate 100.0%)

### `call_attempts.csv`

- Rows: **120,000** | Columns: **9**
- Exact duplicate rows: **0**
- Candidate primary keys: ['attempt_id']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `attempt_id` | str | 0.00% | 120,000 |
| `account_id` | str | 0.00% | 29,451 |
| `borrower_id` | str | 0.00% | 12,000 |
| `event_at` | str | 0.00% | 119,605 |
| `call_id` | str | 0.00% | 66,244 |
| `agent_id` | str | 0.00% | 1,000 |
| `attempt_no` | int64 | 0.00% | 7 |
| `vendor_id` | str | 2.00% | 15 |
| `attempt_status` | str | 0.00% | 5 |

**Date-like columns**

- `event_at`: 2026-01-01 00:01:18 → 2026-08-08 23:58:40 (parse rate 100.0%)
- `attempt_no`: 1970-01-01 00:00:00.000000001 → 1970-01-01 00:00:00.000000007 (parse rate 100.0%)

### `call_dispositions.csv`

- Rows: **35,000** | Columns: **8**
- Exact duplicate rows: **0**
- Candidate primary keys: ['disposition_id']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `disposition_id` | str | 0.00% | 35,000 |
| `account_id` | str | 0.00% | 20,603 |
| `borrower_id` | str | 0.00% | 11,359 |
| `event_at` | str | 0.00% | 34,966 |
| `call_id` | str | 0.00% | 28,971 |
| `agent_id` | str | 0.00% | 1,000 |
| `disposition_code` | str | 0.00% | 9 |
| `disposition_version` | str | 0.00% | 3 |

**Date-like columns**

- `event_at`: 2026-01-01 00:10:00 → 2026-08-08 23:50:50 (parse rate 100.0%)

### `whatsapp_events.csv`

- Rows: **60,600** | Columns: **8**
- Exact duplicate rows: **600**
- Candidate primary keys: none

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `whatsapp_event_id` | str | 0.00% | 60,000 |
| `account_id` | str | 0.00% | 25,924 |
| `borrower_id` | str | 0.00% | 11,917 |
| `event_at` | str | 0.00% | 59,892 |
| `message_id` | str | 0.00% | 34,831 |
| `event_type` | str | 0.00% | 6 |
| `template_code` | str | 0.00% | 5 |
| `provider_id` | str | 0.00% | 15 |

**Date-like columns**

- `event_at`: 2026-01-01 00:01:49 → 2026-08-08 23:56:16 (parse rate 100.0%)

### `sms_events.csv`

- Rows: **45,000** | Columns: **8**
- Exact duplicate rows: **0**
- Candidate primary keys: ['sms_event_id']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `sms_event_id` | str | 0.00% | 45,000 |
| `account_id` | str | 0.00% | 23,207 |
| `borrower_id` | str | 0.00% | 11,728 |
| `event_at` | str | 0.00% | 44,949 |
| `message_id` | str | 0.00% | 27,001 |
| `event_type` | str | 0.00% | 4 |
| `template_code` | str | 0.00% | 4 |
| `provider_id` | str | 0.00% | 15 |

**Date-like columns**

- `event_at`: 2026-01-01 00:04:16 → 2026-08-08 23:46:06 (parse rate 100.0%)

### `field_visits.csv`

- Rows: **25,000** | Columns: **10**
- Exact duplicate rows: **0**
- Candidate primary keys: ['visit_id', 'latitude', 'longitude']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `visit_id` | str | 0.00% | 25,000 |
| `account_id` | str | 0.00% | 16,908 |
| `borrower_id` | str | 0.00% | 10,537 |
| `event_at` | str | 0.00% | 24,973 |
| `agent_id` | str | 0.00% | 1,000 |
| `visit_type` | str | 0.00% | 4 |
| `outcome` | str | 0.00% | 6 |
| `latitude` | float64 | 0.00% | 25,000 |
| `longitude` | float64 | 0.00% | 25,000 |
| `scheduled_at` | str | 1.00% | 24,730 |

**Date-like columns**

- `event_at`: 2026-01-01 00:07:53 → 2026-08-08 23:50:03 (parse rate 100.0%)
- `latitude`: 1970-01-01 00:00:00.000000008 → 1970-01-01 00:00:00.000000034 (parse rate 100.0%)
- `longitude`: 1970-01-01 00:00:00.000000068 → 1970-01-01 00:00:00.000000089 (parse rate 100.0%)
- `scheduled_at`: 2025-12-31 05:21:55 → 2026-08-08 21:50:07 (parse rate 99.0%)

### `promises_to_pay.csv`

- Rows: **18,000** | Columns: **9**
- Exact duplicate rows: **0**
- Candidate primary keys: ['ptp_id']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `ptp_id` | str | 0.00% | 18,000 |
| `account_id` | str | 0.00% | 13,532 |
| `borrower_id` | str | 0.00% | 9,299 |
| `event_at` | str | 0.00% | 17,990 |
| `agent_id` | str | 0.00% | 1,000 |
| `promised_amount` | float64 | 0.00% | 17,983 |
| `promised_date` | str | 0.00% | 17,992 |
| `status` | str | 0.00% | 4 |
| `source` | str | 0.00% | 4 |

**Date-like columns**

- `event_at`: 2026-01-01 00:24:14 → 2026-08-08 23:59:33 (parse rate 100.0%)
- `promised_amount`: 1970-01-01 00:00:00.000000511 → 1970-01-01 00:00:00.000099997 (parse rate 100.0%)
- `promised_date`: 2026-01-02 04:36:18 → 2026-09-06 21:23:52 (parse rate 100.0%)

### `payments.csv`

- Rows: **25,500** | Columns: **9**
- Exact duplicate rows: **486**
- Candidate primary keys: none

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `payment_id` | str | 0.00% | 25,000 |
| `account_id` | str | 0.00% | 16,934 |
| `borrower_id` | str | 0.00% | 10,474 |
| `event_at` | str | 0.00% | 24,984 |
| `payment_reference` | str | 1.50% | 20,821 |
| `amount` | float64 | 0.00% | 24,979 |
| `payment_status` | str | 0.00% | 4 |
| `payment_method` | str | 0.00% | 5 |
| `provider_id` | str | 0.00% | 15 |

**Date-like columns**

- `event_at`: 2026-01-01 00:14:40 → 2026-08-08 23:50:23 (parse rate 100.0%)
- `amount`: 1970-01-01 00:00:00.000000103 → 1970-01-01 00:00:00.000149993 (parse rate 100.0%)

### `vendor_telephony.csv`

- Rows: **15** | Columns: **6**
- Exact duplicate rows: **0**
- Candidate primary keys: ['vendor_id', 'vendor_account_id']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `vendor_id` | str | 0.00% | 15 |
| `vendor_name` | str | 0.00% | 5 |
| `vendor_account_id` | str | 0.00% | 15 |
| `timezone` | str | 0.00% | 2 |
| `status` | str | 0.00% | 2 |
| `schema_version` | str | 0.00% | 3 |

### `complaints.csv`

- Rows: **8,000** | Columns: **9**
- Exact duplicate rows: **0**
- Candidate primary keys: ['complaint_id']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `complaint_id` | str | 0.00% | 8,000 |
| `account_id` | str | 0.00% | 7,034 |
| `borrower_id` | str | 0.00% | 5,839 |
| `event_at` | str | 0.00% | 7,997 |
| `complaint_type` | str | 0.00% | 7 |
| `severity` | str | 0.00% | 4 |
| `status` | str | 0.00% | 4 |
| `source` | str | 0.00% | 5 |
| `resolution_at` | str | 0.00% | 7,998 |

**Date-like columns**

- `event_at`: 2026-01-01 00:38:02 → 2026-08-08 23:35:33 (parse rate 100.0%)
- `resolution_at`: 2026-01-02 07:36:01 → 2026-08-26 13:22:27 (parse rate 100.0%)

### `account_status_history.csv`

- Rows: **60,000** | Columns: **8**
- Exact duplicate rows: **0**
- Candidate primary keys: ['history_id']

| Column | Dtype | Null % | Unique |
| --- | --- | ---: | ---: |
| `history_id` | str | 0.00% | 60,000 |
| `account_id` | str | 0.00% | 25,999 |
| `borrower_id` | str | 0.00% | 11,916 |
| `event_at` | str | 0.00% | 59,898 |
| `status` | str | 0.00% | 7 |
| `changed_by` | str | 0.00% | 101 |
| `source` | str | 0.00% | 5 |
| `recorded_at` | str | 0.00% | 59,906 |

**Date-like columns**

- `event_at`: 2026-01-01 00:01:08 → 2026-08-08 23:50:45 (parse rate 100.0%)
- `recorded_at`: 2025-12-31 01:26:29 → 2026-08-09 22:02:27 (parse rate 100.0%)
