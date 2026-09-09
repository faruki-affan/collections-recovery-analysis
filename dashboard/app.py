"""One-screen CEO dashboard. Run: streamlit run dashboard/app.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "golden"
sys.path.insert(0, str(ROOT / "src"))

st.set_page_config(page_title="Collections CEO dashboard", layout="wide")

if not (GOLDEN / "metrics_monthly.parquet").exists():
    st.error("Golden metrics missing. Run `python scripts/run_pipeline.py` from the repo root.")
    st.stop()

monthly = pd.read_parquet(GOLDEN / "metrics_monthly.parquet")
claim = json.loads((GOLDEN / "claim_reconciliation.json").read_text(encoding="utf-8"))
drivers = pd.read_parquet(GOLDEN / "metrics_drivers_snapshot.parquet")
pay = pd.read_parquet(GOLDEN / "fact_payment.parquet")

complete = monthly[monthly["month_ist"] != "2026-08"].copy()
last = complete.iloc[-1]
prev = complete.iloc[-2]
success = float(pay.loc[pay["is_success"], "amount"].sum())

st.markdown("### Collections — CEO view (60 seconds)")
st.caption("Window 1 Jan–8 Aug 2026 · SUCCESS ₹ after payment_id dedupe · IST calendar · closed book 30,000 accounts")

warn = (
    f"**Data-quality:** raw SUCCESS is inflated by ~1.9% duplicate payment_ids. "
    f"Borrower/agent masters are not usable as people. Snapshot account status matches history 12%. "
    f"The 11% MoM claim is Feb→Mar total ₹ (+{claim['total_rupees_mom_feb_mar']*100:.1f}%) vs per-day +{claim['per_day_mom_feb_mar']*100:.2f}%."
)
st.warning(warn)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Recovery (window)", f"₹{success/1e7:.1f} Cr")
c2.metric(
    "Reported MoM (Feb→Mar ₹)",
    f"{claim['total_rupees_mom_feb_mar']*100:.1f}%",
    delta="calendar, not ops",
)
c3.metric("Independent MoM (₹/day)", f"{claim['per_day_mom_feb_mar']*100:.2f}%")
c4.metric("Recovery / account (Jul)", f"₹{last['recovery_per_account']:,.0f}")
c5.metric("RPC (Jul)", f"{last['rpc_among_answered']*100:.1f}%")
c6.metric("PTP kept (Jul)", f"{last['ptp_kept_rate']*100:.1f}%")

left, right = st.columns((2, 1))
with left:
    fig = go.Figure()
    fig.add_bar(x=monthly["month_ist"], y=monthly["recovery_amount"] / 1e7, name="Total ₹ Cr")
    fig.add_scatter(
        x=monthly["month_ist"],
        y=monthly["recovery_per_day"] / 1e7,
        name="₹ Cr / day",
        yaxis="y2",
        mode="lines+markers",
    )
    fig.update_layout(
        title="Recovery: totals (can fake MoM) vs per day (operational)",
        yaxis_title="₹ Cr in month",
        yaxis2=dict(title="₹ Cr per day", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        height=340,
        margin=dict(l=40, r=40, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.markdown("**11% claim reconciliation**")
    st.markdown(
        f"""
| Definition | Feb→Mar |
| --- | ---: |
| Reported story | +11% |
| Total SUCCESS ₹ | {claim['total_rupees_mom_feb_mar']*100:.2f}% |
| Calendar 31/28 | {claim['calendar_ratio']*100:.2f}% |
| ₹ per day | {claim['per_day_mom_feb_mar']*100:.2f}% |
| Paying accounts | {claim['paying_accounts_mom_feb_mar']*100:.2f}% |
"""
    )
    st.info("Verdict: true only for unadjusted total rupees February to March.")

st.markdown("**Drivers (snapshot — low trust on status/geo)**")
d1, d2, d3 = st.columns(3)
for col, dim in zip((d1, d2, d3), ("risk_segment", "loan_type", "status")):
    sub = drivers[drivers["driver"] == dim]
    col.bar_chart(sub.set_index("segment")["recovery_rate"], height=180)
    col.caption(dim + " · ever-paid rate (flat)")

st.markdown("**₹10 Cr investment**")
i1, i2, i3, i4 = st.columns(4)
i1.write("**Recommendation:** Better borrower targeting")
i2.write("**Incremental recovery:** Not estimable (₹0 in-sample)")
i3.write("**ROI / break-even:** Not estimable")
i4.write("**Downside:** ₹10 Cr / ₹0 lift · confidence on rupees: very low")
st.caption("Campaign names, channels, and target definitions do not match. Do not scale dialer, agents, AI, WhatsApp, or field on this extract.")
