# Collections analytics — was recovery really up 11%?

Independent reconstruction of a messy collections extract (synthetic challenge data, seed 42). The business reported that **recovery improved 11% month-on-month**. Leadership asked whether that is true, why the series moved, and where to put **₹10 Cr**.

## 1. Executive summary

**The 11% figure is real only as February→March total SUCCESS rupees. It is not operational improvement.** March has 31 days, February 28 (+10.7%). Recovery **per day** rose **+0.29%**. RPC (~20%), PTP kept (~25%), and rupees per agent-hour (~₹16–17k) did not step up.

Duplicate `payment_id` rows inflate raw SUCCESS by **~1.9% (₹2.59 Cr)**. They do not create the 11%.

**₹10 Cr recommendation: better borrower targeting** — because campaign names, channels, and target definitions contradict each other (fact). **Incremental recovery, ROI, and break-even are not estimable** from this file (no experiment, no costs, flat outcomes). In-sample expected lift: **₹0**. Downside: spend ₹10 Cr, recover nothing extra.

## 2. Business question

1. What happened to collections over the supplied window?  
2. Why?  
3. Is +11% MoM real?  
4. One investment area among: telephony, more agents, AI voice, targeting, WhatsApp/digital, field.

## 3. Dataset overview

17 relational CSVs in `data/raw/` plus a dtype-only `data_dictionary.csv` and a supplier README (intentional dirt: duplicates, mixed timezones, identity collisions).

Operational events: **2026-01-01 to 2026-08-08** (~7.3 months, not 12). **30,000 accounts** (opened by Nov 2025 — closed book), **1,000 agent_ids**, **120 campaigns**.

## 4–10. How to run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/profile_data.py
python scripts/run_pipeline.py
python scripts/load_duckdb.py
python scripts/render_architecture.py
python scripts/build_notebooks.py
python -m pytest tests -q
streamlit run dashboard/app.py
```

Optional Postgres: copy `.env.example` and run the SQL under `sql/` against schemas `staging/clean/golden/metrics/analysis`. Local warehouse is DuckDB at `data/warehouse/collections.duckdb`.

Notebooks in `notebooks/` read golden parquet; they do not hand-edit raw files.

## 11. Data-quality methodology

Forensic checklist (duplicates, attribution, timezones, vendor maps, agent identity, mix, denominators) is in `docs/data_quality_report.md`. Cleaning **impact is quantified** in `data/golden/cleaning_impact.json`. Rejected payment rows: `data/rejected/`.

## 12. Golden dataset

Grain: **account × month (IST)**. Why: MoM question + closed 30k book so denominators cannot vanish. Details: `docs/golden_dataset.md`.

## 13. Metric definitions

Independent dictionary: `docs/metric_definitions.md`. Headline recovery = unique `payment_id` SUCCESS ₹. Do **not** last-touch. Do **not** use `payment_reference` as a txn key (multi-account collisions).

## 14. Statistical methodology

Stratification, calendar normalization, mix tables, and a 2×2 DiD. No ML. Simpson: totals vs intensity. Survivorship: snapshot status ≠ history. Attribution-window bias: 7-day last-touch misses most cash.

## 15. Counterfactual methodology

Treatment = targeted with v2/v3 campaigns; post = Apr 2026+. **Not identified** — strategy mix does not jump. DiD ≈ ₹95 / account-month (noise).

## 16. Investment recommendation

`docs/investment_recommendation.md` — targeting rebuild; rupees not estimable.

## 17. Key findings

| Item | Result | Class |
| --- | --- | --- |
| 11% MoM | Feb–Mar total ₹ only; per-day +0.29% | Fact |
| Duplicates | +1.9% SUCCESS if ignored | Fact |
| Agents/borrowers | Not person tables | Fact |
| Channel/vendor lifts | Flat | Fact in-sample |
| ₹10 Cr ROI | Cannot compute | Limitation |

## 18. Limitations

Synthetic uniformity may hide live-book heterogeneity. No costs. No 12th month. Payment TZ unknown. Campaign labels unusable as policy.

## 19. Production architecture

`docs/production_architecture.md`, `docs/architecture.mmd`, `docs/architecture.png`.

## 20. Tests

`pytest tests` — uniqueness, referential payments→accounts, non-negative amounts, metric reconciliation, duplicate detection on raw, PTP mapping.
