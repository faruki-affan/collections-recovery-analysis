# Data quality report

Investigations requested in the assignment. Issues are listed only when the files support them. Expected problems that were **not** found are recorded at the bottom.

## Material issues

| Issue | Detection method | Records affected | Financial impact | Treatment | Severity |
| --- | --- | --- | ---: | --- | --- |
| Duplicate payment rows (exact) | `duplicated()` on `payments.csv` | 486 extra rows | −₹3.73 Cr on **all-status** amount if dropped; SUCCESS unique-`payment_id` vs raw SUCCESS = **−₹2.59 Cr (−1.93%)** | Keep first row | **High** — inflates reported recovery |
| Duplicate `payment_id` (non-exact extras) | `duplicated(payment_id)` after exact drop | 14 rows | −₹10.7 Lakh all-status | Keep first `payment_id` | Medium |
| `payment_reference` is not a txn key | nunique(account_id) per reference | 3,406 references → multiple accounts | Using it as a key would **drop ~₹16.6 Cr** of SUCCESS incorrectly | Do not dedupe on reference | **High** if misused |
| Duplicate calls | exact + `call_id` | 1,271 exact + 79 extra ids (91,350 → 90,000) | None in ₹ | Dedupe | Medium |
| Duplicate WhatsApp events | exact rows | 600 | None in ₹ | Dedupe | Low |
| Borrower PII conflicts | nunique(name/phone/city/state) per id | 8,517 / 11,015 IDs; 30,600 rows | Geography mix unreliable | Mode + conflict flag; do not drop accounts | **High** for geo analysis |
| Orphan `borrower_id` on accounts | anti-join to resolved borrowers | 2,913 accounts (9.7%) | Those accounts still pay ₹12.4 Cr SUCCESS | Keep; flag `orphan_borrower` | Medium |
| Agent master is not a person table | 30k rows, 1k `agent_id`; all attributes conflict; 10 names | 29,000 extra snapshots | Tenure/team/vendor on agents unusable | Use event `agent_id` only | **High** for agent ROI |
| Account `status` ≠ last history status | inner comparison | Match rate **12.3%**; 13.3% of accounts have no history | Any “active book” rate using snapshot status is wrong | Closed-book 30k denominator | **High** |
| Call timezone / date shift | localize to IST | 9.8% of unique calls change date (23% of UTC rows) | Hour-of-day and some month assignment wrong if naive | Convert using row timezone | Medium |
| History `recorded_at` before `event_at` | timestamp compare | 50.3% of history rows | SCD “as-of” queries wrong | Do not use recorded_at as event time | Medium |
| Dual disposition labels PTP vs PROMISE_TO_PAY | value counts × version | 3,926 PROMISE_TO_PAY + 3,904 PTP | Double-counting PTP if treated as distinct | Map both to PTP | Medium |
| Campaign definition incoherence | crosstab name × channel × target_def | 120 campaigns; 80% targeting channel mismatch | Targeting strategy cannot be read from labels | Treat labels as untrusted | **High** for investment in targeting |
| Attempts vs calls independent | crosstab attempt_status × call_status | 120,000 attempts | Funnel from attempts is noise | Do not nest attempts under call outcome | Medium |
| Window is not 12 months | min/max event dates | All event tables | Aug totals look like a −75% crash | Flag partial August; annualize carefully | Medium |
| No cost fields | schema scan | 0 cost columns | Cost/₹ and ROI **not in data** | State as missing | **High** for ₹10 Cr math |

## Forensic checklist

### A. Duplicate payments — **found**

Ingestion-style duplicates: 500 extra `payment_id` rows, of which 486 are exact copies. They inflate SUCCESS rupees by about **1.93%**. They are not different amounts or statuses for the same id.

### B. Attribution errors — **risk found; default KPI avoids last-touch**

Payments have no `campaign_id`. Last-touch within 7 days leaves **~₹1,051 Cr / ₹1,316 Cr** of SUCCESS unattributed. Using “latest campaign / latest agent / latest channel” would fabricate channel ROI.

### C. Timezone problems — **found on calls and sessions**

Three zones (UTC, Asia/Kolkata, Asia/Dubai) in equal share. Naive hour-of-day is uniform across 24 hours (synthetic). Date shifts are real after conversion and are corrected in golden calls/sessions. Payments have no zone metadata.

### D. Vendor mapping changes — **codes coexist; no sharp cutover**

Disposition versions `legacy` / `v1` / `v2` run in parallel all year with similar code mix. Vendor `schema_version` v1/v2/v3 also coexist. Answer rates differ by <1.2 pp across vendors (19.5–20.7%). **No evidence of a mapping break that creates the 11% claim.**

### E. Agent identity — **found**

Same `agent_id` appears with multiple employee codes, names, vendors, teams, and statuses. Employee codes map to many agent_ids. Names are 10 synthetic strings. **Cannot resolve “same human.”** Operational key = `agent_id` on events.

### F. Portfolio mix changes — **not visible as a true time series**

Account DPD / risk / loan_type / status are **snapshots**, not monthly. Targeted mix by risk is ~25% each bucket every month. Status history exists but does not reconcile to the snapshot. **No evidence the book became a different product mix** that would explain +11% rupees; calendar length does.

### G. Denominator manipulation — **possible in naive reporting; blocked in ours**

If someone used only paying accounts, MoM intensity is flat. If someone used snapshot `ACTIVE` only, the ACTIVE slice is a random-looking 25% and still pays like CLOSED/WRITEOFF. If someone compared July ₹ to August ₹, MoM is −75% because August has 8 days. Our portfolio denominator is 30,000 every month.

## Investigated and not found (in this extract)

| Hypothesis | Result |
| --- | --- |
| Negative payment amounts | None |
| Zero-amount SUCCESS | None |
| Sharp mid-year targeting-volume break | Targeting mix by strategy_version is stable (~30% legacy every month) |
| Vendor answer-rate collapse | Flat ~20% |
| Hour-of-day performance pattern | Flat (likely synthetic) |
| Material recovery difference by risk/loan/status/state | All ~43–45% ever-paid; not an operational lever in-sample |
