"""Create analysis notebooks that read golden artifacts (no fabricated numbers)."""
from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"
NB.mkdir(exist_ok=True)

PREAMBLE = """\
import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path('..').resolve()
RAW = ROOT / 'data' / 'raw'
GOLDEN = ROOT / 'data' / 'golden'
CLEAN = ROOT / 'data' / 'clean'
plt.rcParams['figure.figsize'] = (9, 4)
assert (GOLDEN / 'metrics_monthly.parquet').exists(), 'Run python scripts/run_pipeline.py first'
"""


def md_cell(src: str):
    return nbf.v4.new_markdown_cell(src)


def code_cell(src: str):
    return nbf.v4.new_code_cell(src)


def write(name: str, cells: list) -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}
    }
    path = NB / name
    path.write_text(nbf.writes(nb), encoding="utf-8")
    print("wrote", path)


write(
    "01_data_profiling.ipynb",
    [
        md_cell("# 01 — Data profiling\n\nInspect every supplied file before modeling. The package README warns the data are intentionally dirty."),
        code_cell(PREAMBLE),
        code_cell(
            """
tables = sorted(p.stem for p in RAW.glob('*.csv') if p.stem != 'data_dictionary')
rows = []
for t in tables:
    df = pd.read_csv(RAW / f'{t}.csv')
    rows.append({
        'table': t, 'rows': len(df), 'cols': df.shape[1],
        'exact_dups': int(df.duplicated().sum()),
        'columns': ', '.join(df.columns),
    })
inv = pd.DataFrame(rows)
inv
"""
        ),
        md_cell("## Date ranges and identifier uniqueness"),
        code_cell(
            """
for t, col in [('payments','event_at'),('calls','event_at'),('daily_targeting','target_date'),('accounts','opened_at')]:
    s = pd.to_datetime(pd.read_csv(RAW / f'{t}.csv', usecols=[col])[col], errors='coerce')
    print(t, s.min(), '→', s.max(), 'n=', s.notna().sum())
print('accounts PK unique', pd.read_csv(RAW/'accounts.csv')['account_id'].is_unique)
print('payment_id unique?', pd.read_csv(RAW/'payments.csv')['payment_id'].is_unique)
print('agent_id unique in agents?', pd.read_csv(RAW/'agents.csv')['agent_id'].is_unique)
"""
        ),
        md_cell("See `docs/data_inventory.md` for the full column-level inventory. Do not treat `data_dictionary.csv` as keys or metric logic — it is dtypes only."),
    ],
)

write(
    "02_data_forensics.ipynb",
    [
        md_cell("# 02 — Data forensics\n\nDuplicate payments, attribution, timezones, vendors, agents, mix, denominators."),
        code_cell(PREAMBLE),
        code_cell(
            """
pay = pd.read_csv(RAW/'payments.csv')
print('raw rows', len(pay), 'unique payment_id', pay.payment_id.nunique(), 'exact dups', pay.duplicated().sum())
print('SUCCESS raw ₹', pay.loc[pay.payment_status=='SUCCESS','amount'].sum())
print('SUCCESS unique id ₹', pay.drop_duplicates('payment_id').query('payment_status==\"SUCCESS\"').amount.sum())
ref = pay.groupby('payment_reference')['account_id'].nunique()
print('references with >1 account', int((ref>1).sum()))
"""
        ),
        code_cell(
            """
calls = pd.read_csv(RAW/'calls.csv').drop_duplicates('call_id')
calls['event_at'] = pd.to_datetime(calls.event_at)
parts=[]
for tz, g in calls.groupby('timezone'):
    parts.append(g.event_at.dt.tz_localize(tz, ambiguous='NaT', nonexistent='NaT').dt.tz_convert('Asia/Kolkata'))
calls['ist'] = pd.concat(parts)
print('call date shift rate', (calls.event_at.dt.date != calls.ist.dt.date).mean())
"""
        ),
        code_cell(
            """
ag = pd.read_csv(RAW/'agents.csv')
print(ag.groupby('agent_id').nunique()[['employee_code','agent_name','vendor_id','team','status']].gt(1).mean())
print('distinct names', ag.agent_name.nunique())
"""
        ),
        md_cell("Full treatment and severity: `docs/data_quality_report.md`."),
    ],
)

write(
    "03_performance_reconstruction.ipynb",
    [
        md_cell("# 03 — 12-month? performance reconstruction\n\nThe extract covers **Jan–8 Aug 2026**, not 12 months. August is partial."),
        code_cell(PREAMBLE),
        code_cell(
            """
m = pd.read_parquet(GOLDEN/'metrics_monthly.parquet')
m[['month_ist','n_accounts','n_targeted','n_calls','n_answered','n_ptp','n_ptp_kept','n_recovered','recovery_amount','recovery_per_day','rpc_among_answered','ptp_kept_rate','recovery_per_agent_hour','recovery_amount_mom','recovery_per_day_mom']]
"""
        ),
        code_cell(
            """
fig, ax = plt.subplots()
ax.plot(m.month_ist, m.recovery_amount/1e7, marker='o', label='₹ Cr in month')
ax.set_ylabel('₹ Cr')
ax2 = ax.twinx()
ax2.plot(m.month_ist, m.recovery_per_day/1e6, marker='s', color='C1', label='₹ Lakh / day')
ax.set_title('Totals move with month length; per-day does not')
ax.legend(loc='upper left'); ax2.legend(loc='upper right')
plt.xticks(rotation=30); plt.tight_layout()
"""
        ),
        md_cell("Volume (paying accounts) tracks days in month. Conversion (RPC, PTP kept, ₹/hour) does not step up 11%."),
    ],
)

write(
    "04_driver_analysis.ipynb",
    [
        md_cell("# 04 — Driver analysis\n\nClassify: Fact / Strong Evidence / Correlation / Hypothesis. Snapshot mix is **not** a historical mix."),
        code_cell(PREAMBLE),
        code_cell(
            """
d = pd.read_parquet(GOLDEN/'metrics_drivers_snapshot.parquet')
print(d.to_string(index=False))
print('\\nVendor connect')
print(pd.read_parquet(GOLDEN/'metrics_vendor.parquet'))
"""
        ),
        md_cell(
            """
## Driver matrix

| Driver | Observation | Evidence | Confidence | Classification | Business interpretation |
| --- | --- | --- | --- | --- | --- |
| Calendar | Feb–Mar ₹ +11% ≈ 31/28 | per-day +0.29% | High | **Fact** | Do not celebrate MoM totals |
| Payment duplicates | +1.9% SUCCESS if not deduped | 500 extra payment_ids | High | **Fact** | Reporting hygiene |
| Risk / loan / status | Ever-paid ~44% all groups | golden drivers | High in-sample | **Fact** (flatness) | No segment to “scale” |
| Vendor | Answer 19.5–20.7% | calls ⋈ vendors | Medium | **Correlation** | Not an investment thesis |
| Agent tenure/team | Unusable master | 30 rows/id conflicting | High | **Fact** | Cannot buy “more good agents” from this file |
| Campaign / targeting | Labels contradict; 80% channel mismatch | campaigns, targeting | High | **Fact** | Targeting system is incoherent |
| Last-touch channel | Voice gets most attributed ₹ | merge_asof | Low causal | **Hypothesis** if used for ROI | Default KPI must not last-touch |
| Mix / DPD over time | Targeted risk mix stable | monthly crosstab | Medium | **Not found** | Mix does not explain 11% |
"""
        ),
    ],
)

write(
    "05_counterfactual_analysis.ipynb",
    [
        md_cell(
            """# 05 — Counterfactual: targeting strategy

Leadership asked what recovery would have been without a mid-year targeting change.

**Identification problem:** monthly strategy_version mix is stable (~30% legacy every month). There is no clean switch. DiD is reported as a **robustness check**, not a causal estimate.
"""
        ),
        code_cell(PREAMBLE),
        code_cell(
            """
print(json.loads((GOLDEN/'counterfactual.json').read_text()))
"""
        ),
        md_cell(
            """
### Design (simplest credible method)

- **Treatment:** account-month with any v2/v3 campaign on `daily_targeting`
- **Control:** targeted account-months without v2/v3
- **Outcome:** SUCCESS ₹ on that account-month
- **Post:** month ≥ 2026-04 (calendar midpoint of the extract)
- **Method:** 2×2 difference-in-differences
- **Confounders:** targeting is not as-if random; campaign labels do not mean DPD rules; snapshot risk is not as-of DPD
- **Result:** DiD ≈ **₹95** per targeted account-month vs ~₹6,000 cell means — economically **zero**
- **Limitation:** parallel trends not testable as a policy change because treatment share does not jump. **Causal identification is not credible.**
"""
        ),
    ],
)

write(
    "06_investment_analysis.ipynb",
    [
        md_cell("# 06 — ₹10 Cr investment\n\nSee `docs/investment_recommendation.md`. Do not invent ROI."),
        code_cell(PREAMBLE),
        code_cell(
            """
print('Vendor', pd.read_parquet(GOLDEN/'metrics_vendor.parquet'))
print('Channel last-touch 7d')
a = pd.read_parquet(GOLDEN/'metrics_channel_attribution.parquet')
print(a[a.window=='7d'])
"""
        ),
        md_cell(
            """
**Recommendation: Better borrower targeting.**

| | |
| --- | --- |
| Incremental recovery | Not estimable; in-sample ₹0 |
| Cost | ₹10 Cr given |
| ROI / break-even | Not estimable |
| Downside | ₹10 Cr / ₹0 |
| Confidence (rupees) | Very low |

Required next: RCT + stamp target_id on payments + channel costs.
"""
        ),
    ],
)

# Master notebook
sections = [
    ("# Collections analysis — master notebook", "Reasoning notebook. Numbers come from the golden pipeline, not edits to raw CSV."),
    ("## 1. Objective", "Test the 11% MoM recovery claim, reconstruct performance, and recommend one ₹10 Cr investment — or say the data cannot support a rupee ROI."),
    ("## 2–6. Inventory, quality, cleaning, golden, metrics", "See notebooks 01–02 and docs. Pipeline: `python scripts/run_pipeline.py`."),
    ("## 7. Performance reconstruction", "Jan–Jul complete; Aug partial. Per-day recovery is the operational series."),
    ("## 8. 11% claim", "True only for Feb→Mar total SUCCESS ₹. Per-day +0.29%."),
    ("## 9–10. Drivers and statistical issues", "Mix, Simpson (totals vs intensity), survivorship (status snapshot), attribution windows, time-series calendar."),
    ("## 11. Counterfactual", "DiD not identified. Result ~₹0."),
    ("## 12. Investment", "Targeting rebuild; ROI not estimable."),
    ("## 13–15. Conclusions, limitations, next steps", "Calendar ≠ performance. Fix reporting. Pilot targeting. Do not scale channels on last-touch."),
]
cells = [md_cell(f"{h}\n\n{b}") for h, b in sections]
cells.insert(1, code_cell(PREAMBLE + """
m = pd.read_parquet(GOLDEN/'metrics_monthly.parquet')
claim = json.loads((GOLDEN/'claim_reconciliation.json').read_text())
print(json.dumps(claim, indent=2))
m
"""))
write("analysis.ipynb", cells)
