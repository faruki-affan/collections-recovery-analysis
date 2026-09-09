# Metric definitions

Independent definitions. Existing reporting is not trusted. All rates show **numerator and denominator**.

Window: IST dates **2026-01-01 to 2026-08-08**. Payments with unique `payment_id`.

---

## 1. Recovery (₹)

- **Business:** Cash posted as successful collections.
- **Formula:** Σ `amount` where `payment_status = SUCCESS` after `payment_id` dedupe.
- **Numerator:** SUCCESS amount.
- **Denominator:** none (stock total).
- **Eligible population:** all payment rows retained in `fact_payment`.
- **Attribution:** none. Cash is not assigned to a campaign in the headline metric.
- **Exclusions:** FAILED, PENDING, REVERSED. Exact duplicate payment rows.
- **Edge cases:** `payment_reference` collisions are **not** treated as one transaction. August is partial.
- **SQL:** `sql/metrics/01_core_metrics.sql`
- **Limitation:** SUCCESS may include payments that will later reverse; reversals are not paired by id.

## 2. Recovery month-on-month

Several definitions are computed. Only one can look like “11%”:

| Definition | Feb → Mar |
| --- | ---: |
| Total SUCCESS ₹ | **+11.03%** |
| Paying accounts | **+11.32%** |
| ₹ / 30k accounts (same as total ₹ because the book is closed) | **+11.03%** |
| ₹ / calendar days in month | **+0.29%** |
| 31/28 calendar ratio | **+10.71%** |
| ₹ / paying account (intensity) | **≈ −0.26%** (from payment-level reconstruction) |

**Appropriate definition for “did operations improve?”:** recovery **per day** (or a 28-day normalized month), plus recovery **per paying account** and **per agent-hour**. Total rupees without day-count adjustment confuses calendar length with performance.

## 3. Recovery rate

- **Portfolio recovery rate:** distinct accounts with SUCCESS in the month / **30,000** accounts.
- **Targeted recovery rate:** distinct paying accounts / distinct targeted accounts that month.
- **Why two:** targeted recovery rate can rise if targeting shrinks to easy accounts (denominator manipulation). Portfolio rate cannot hide that.

Observed portfolio recovery rate is ~7.2–8.1% of the book per complete month (not 44% — the 44% figure is “ever paid in the window” / 30k).

## 4. Recovery per account

SUCCESS ₹ in month / 30,000.

## 5. Recovery per agent-hour

SUCCESS ₹ / Σ clipped session hours (`logout − login` in session timezone, clipped to [0, 16] hours).

**Limitation:** sessions may not cover all work; clipping is conservative. No wage or telecom cost in the data, so this is productivity not unit economics.

## 6. Cost per ₹ recovered

**Not computable.** No salary, vendor invoice, SMS, WhatsApp, or field-cost fields exist.

## 7. Contact rate

- **Voice contact (account-month):** accounts with ≥1 `ANSWERED` call / accounts with ≥1 targeting row that month.
- **Alternative (attempts):** not used as primary — attempt outcomes do not match call outcomes.

**Limitation:** an account can be called without being in `daily_targeting`.

## 8. RPC (Right-Party Connect proxy)

ANSWERED calls / all calls after `call_id` dedupe.

This is a **call-level connect rate**, not confirmed right-party. Dispositions cover only ~32% of unique calls, so RPC cannot be restricted to “borrower confirmed” without throwing away most calls.

Observed RPC ≈ **19–20%** every month.

## 9. PTP rate

Distinct accounts with a `promises_to_pay` row in the month / distinct targeted accounts.

**Not** disposition `PTP` counts (those are a different system and use two labels).

## 10. PTP kept rate

`status = KEPT` PTP rows / all PTP rows in the month.

Observed ≈ **24–27%**, essentially uniform by source channel.

**Limitation:** KEPT is a label in the PTP table; it is not independently matched to a SUCCESS payment in the headline metric (matching would require an attribution window).

## 11. Channel conversion

**Default: do not report last-touch conversion as fact.**

Sensitivity tables in `metrics_channel_attribution.parquet`: last interaction in 1/7/14/30-day windows vs unbounded.

Within 7 days, most SUCCESS rupees have **no prior interaction** (~₹1,051 Cr of ₹1,316 Cr unattributed). Last-touch would **over-credit** whichever channel happens to fire near payday and **under-count** unpaid work.

## Eligible population (anti-manipulation)

| Population | Definition |
| --- | --- |
| Portfolio | 30,000 accounts every month |
| Targeted | `daily_targeting` that month |
| Attempted (voice) | ≥1 call |
| Contacted (voice) | ≥1 ANSWERED call |
| Recovered | ≥1 SUCCESS payment |

If a dashboard uses only recovered or only contacted accounts as the base for “recovery rate,” treat it as a **red flag**.
