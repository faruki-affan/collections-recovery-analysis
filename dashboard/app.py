"""Interactive CEO dashboard. Run: streamlit run dashboard/app.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "golden"
sys.path.insert(0, str(ROOT / "src"))

st.set_page_config(
    page_title="Collections CEO dashboard",
    page_icon="₹",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 1.5rem; }
      div[data-testid="stMetricValue"] { font-size: 1.35rem; }
      .story { font-size: 1.05rem; line-height: 1.45; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load() -> dict:
    if not (GOLDEN / "metrics_monthly.parquet").exists():
        return {}
    monthly = pd.read_parquet(GOLDEN / "metrics_monthly.parquet").sort_values("month_ist")
    monthly["label"] = monthly["month_ist"].map(
        lambda m: {"2026-08": "2026-08 (8 days)"}.get(m, m)
    )
    pay = pd.read_parquet(GOLDEN / "fact_payment.parquet")
    attr = pd.read_parquet(GOLDEN / "metrics_channel_attribution.parquet")
    attr["channel"] = attr["channel"].fillna("No prior interaction")
    return {
        "monthly": monthly,
        "claim": json.loads((GOLDEN / "claim_reconciliation.json").read_text(encoding="utf-8")),
        "drivers": pd.read_parquet(GOLDEN / "metrics_drivers_snapshot.parquet"),
        "attr": attr,
        "success_window": float(pay.loc[pay["is_success"], "amount"].sum()),
    }


def cr(amount: float) -> str:
    return f"₹{amount / 1e7:,.2f} Cr"


def pct(x: float) -> str:
    sign = "+" if x >= 0 else ""
    return f"{sign}{x * 100:.2f}%"


def mom(a: float, b: float) -> float:
    if a == 0:
        return float("nan")
    return b / a - 1


data = load()
if not data:
    st.error("Golden metrics missing. From the repo root run: `python scripts/run_pipeline.py`")
    st.stop()

monthly: pd.DataFrame = data["monthly"]
claim = data["claim"]
months = [m for m in monthly["month_ist"].tolist() if m != "2026-08"]

# ----- sidebar -----
with st.sidebar:
    st.header("Play the numbers")
    st.caption("Only controls the data can support.")

    st.subheader("Months")
    preset = st.radio(
        "Jump to a comparison",
        ["Reported claim (Feb → Mar)", "Pick any two complete months"],
        help="The business claim is Feb→Mar total rupees. August is excluded (8 days only).",
    )
    if preset.startswith("Reported"):
        m0, m1 = "2026-02", "2026-03"
        st.success("Locked to February vs March — the pair behind the 11% claim.")
    else:
        c_a, c_b = st.columns(2)
        m0 = c_a.selectbox("From", months, index=months.index("2026-02"))
        m1 = c_b.selectbox("To", months, index=months.index("2026-03"))

    st.subheader("Chart")
    series = st.multiselect(
        "Show",
        ["Total ₹ (can mislead)", "₹ per day (fairer)"],
        default=["Total ₹ (can mislead)", "₹ per day (fairer)"],
        help="Total rupees rise in longer months. Per-day is the operational series.",
    )
    if not series:
        series = ["₹ per day (fairer)"]

    st.subheader("Groups")
    driver = st.selectbox(
        "Compare",
        ["risk_segment", "loan_type"],
        format_func=lambda x: {"risk_segment": "Risk", "loan_type": "Product"}[x],
        help="Snapshot status and geography are not reliable in this file, so they are not offered.",
    )

    st.divider()
    with st.expander("What do these words mean?"):
        st.markdown(
            """
- **SUCCESS ₹** — cash after dropping duplicate `payment_id`s.
- **MoM** — the two months you selected.
- **RPC** — answered calls / all calls.
- **PTP kept** — KEPT promises / all PTPs.
- **Closed book** — same 30,000 accounts every month.
            """
        )

# ----- selected rows -----
r0 = monthly.loc[monthly["month_ist"] == m0].iloc[0]
r1 = monthly.loc[monthly["month_ist"] == m1].iloc[0]
same = m0 == m1
chart_df = monthly[monthly["month_ist"] != "2026-08"]

total_mom = mom(r0["recovery_amount"], r1["recovery_amount"])
day_mom = mom(r0["recovery_per_day"], r1["recovery_per_day"])
acct_mom = mom(r0["n_recovered"], r1["n_recovered"])
cal_mom = mom(r0["days"], r1["days"])
is_claim_pair = {m0, m1} == {"2026-02", "2026-03"}

# ----- header -----
st.title("Did recovery really improve 11%?")
st.markdown(
    f'<p class="story">You are comparing <b>{r0["label"]}</b> ({int(r0["days"])} days) with '
    f'<b>{r1["label"]}</b> ({int(r1["days"])} days). '
    f'Total rupees moved <b>{pct(total_mom) if not same else "n/a"}</b>. '
    f'Per day moved <b>{pct(day_mom) if not same else "n/a"}</b>.</p>',
    unsafe_allow_html=True,
)

if is_claim_pair and not same:
    st.success(
        f"This is the reported pair. Calendar days {int(r0['days'])} → {int(r1['days'])} "
        f"({pct(cal_mom)}). Almost all of the +11% is extra days, not better collections."
    )
elif same:
    st.warning("Pick two different months to see a month-on-month change.")
else:
    st.info("This is not the pair in the 11% claim. Check whether totals and per-day still agree.")

with st.expander("Data-quality (read once)", expanded=False):
    st.markdown(
        f"""
- Raw SUCCESS is inflated ~**1.9%** by duplicate payment IDs. This dashboard uses **deduped** cash.
- Borrower and agent files are **not** usable as people. Geography is majority-vote.
- Account snapshot status matches history on **12%** of accounts — do not treat ACTIVE as the live book.
- Feb→Mar total ₹ = **{pct(claim['total_rupees_mom_feb_mar'])}**; per day = **{pct(claim['per_day_mom_feb_mar'])}**.
        """
    )

# ----- KPIs -----
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Window recovery", cr(data["success_window"]), help="All SUCCESS ₹ in Jan–8 Aug after payment_id dedupe.")
k2.metric(
    f"Total ₹  {m0[-2:]}→{m1[-2:]}",
    "—" if same else pct(total_mom),
    help="Unadjusted month totals. Longer months look better.",
)
k3.metric(
    "₹ per day",
    "—" if same else pct(day_mom),
    delta="use this for ops" if not same and abs(day_mom) < abs(total_mom) else None,
    help="Recovery divided by days in the month (August = 8).",
)
k4.metric(
    f"Recovery / account ({m1})",
    f"₹{r1['recovery_per_account']:,.0f}",
    help="SUCCESS ₹ / 30,000 accounts in the To month.",
)
k5.metric(
    f"RPC ({m1})",
    f"{r1['rpc_among_answered']*100:.1f}%",
    help="Answered calls / all calls.",
)
k6.metric(
    f"PTP kept ({m1})",
    f"{r1['ptp_kept_rate']*100:.1f}%",
    help="KEPT promises / all PTP rows.",
)

# ----- chart + reconciliation -----
left, right = st.columns((1.7, 1))
with left:
    fig = go.Figure()
    if "Total ₹ (can mislead)" in series:
        fig.add_bar(
            x=chart_df["label"],
            y=chart_df["recovery_amount"] / 1e7,
            name="Total ₹ Cr",
            hovertemplate="%{x}<br>Total: ₹%{y:.2f} Cr<extra></extra>",
            marker_color=["#1F6FEB" if m in (m0, m1) else "#9ECBFF" for m in chart_df["month_ist"]],
        )
    if "₹ per day (fairer)" in series:
        fig.add_scatter(
            x=chart_df["label"],
            y=chart_df["recovery_per_day"] / 1e7,
            name="₹ Cr / day",
            yaxis="y2" if "Total ₹ (can mislead)" in series else "y",
            mode="lines+markers",
            hovertemplate="%{x}<br>Per day: ₹%{y:.3f} Cr<extra></extra>",
            line=dict(color="#8B1E3F", width=3),
        )
    layout = dict(
        title="Highlighted bars are your two months · Jan–Jul complete months only",
        height=390,
        margin=dict(l=40, r=50, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
        yaxis_title="₹ Cr in month" if "Total ₹ (can mislead)" in series else None,
    )
    if "Total ₹ (can mislead)" in series and "₹ per day (fairer)" in series:
        layout["yaxis2"] = dict(title="₹ Cr per day", overlaying="y", side="right")
    fig.update_layout(**layout)
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Compare these two months")
    if same:
        st.write("Select two different months in the sidebar.")
    else:
        st.dataframe(
            pd.DataFrame(
                {
                    "Lens": [
                        "Total SUCCESS ₹",
                        "₹ per calendar day",
                        "Days in month",
                        "Paying accounts",
                        "RPC",
                        "PTP kept",
                        "₹ / agent-hour",
                    ],
                    m0: [
                        cr(r0["recovery_amount"]),
                        cr(r0["recovery_per_day"]),
                        int(r0["days"]),
                        f"{int(r0['n_recovered']):,}",
                        f"{r0['rpc_among_answered']*100:.1f}%",
                        f"{r0['ptp_kept_rate']*100:.1f}%",
                        f"₹{r0['recovery_per_agent_hour']:,.0f}",
                    ],
                    m1: [
                        cr(r1["recovery_amount"]),
                        cr(r1["recovery_per_day"]),
                        int(r1["days"]),
                        f"{int(r1['n_recovered']):,}",
                        f"{r1['rpc_among_answered']*100:.1f}%",
                        f"{r1['ptp_kept_rate']*100:.1f}%",
                        f"₹{r1['recovery_per_agent_hour']:,.0f}",
                    ],
                    "Change": [
                        pct(total_mom),
                        pct(day_mom),
                        pct(cal_mom),
                        pct(acct_mom),
                        pct(mom(r0["rpc_among_answered"], r1["rpc_among_answered"])),
                        pct(mom(r0["ptp_kept_rate"], r1["ptp_kept_rate"])),
                        pct(mom(r0["recovery_per_agent_hour"], r1["recovery_per_agent_hour"])),
                    ],
                }
            ),
            hide_index=True,
            width="stretch",
        )
        if abs(total_mom - day_mom) > 0.03:
            st.caption("Totals and per-day disagree — the month lengths are doing the work, not operations.")
        else:
            st.caption("Totals and per-day roughly agree — this move is not mainly a calendar artifact.")

# ----- drivers + channel -----
dcol, ccol = st.columns(2)
with dcol:
    st.subheader("Are some borrowers easier?")
    sub = data["drivers"][data["drivers"]["driver"] == driver].copy()
    sub["segment"] = sub["segment"].fillna("(missing)")
    plot = sub.copy()
    plot["y"] = plot["recovery_rate"]
    fig_d = px.bar(
        plot,
        x="segment",
        y="y",
        title="Ever-paid rate — groups are essentially the same",
        labels={"segment": "", "y": "Ever-paid rate"},
        hover_data={"n": True, "n_paid": True},
    )
    fig_d.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
    fig_d.update_yaxes(tickformat=".0%", range=[0, 0.6])
    st.plotly_chart(fig_d, width="stretch")
    st.caption("No investable segment lift in-sample. Status and geography are omitted because those fields are not trustworthy.")

with ccol:
    st.subheader("Last-touch is not the KPI")
    window = "7d"
    aw = data["attr"][data["attr"]["window"] == window].copy()
    aw["cr"] = aw["sum"] / 1e7
    aw["pct"] = aw["sum"] / aw["sum"].sum()
    fig_c = px.bar(
        aw.sort_values("pct", ascending=False),
        x="channel",
        y="pct",
        title=f"Share of SUCCESS ₹ if last-touch window = {window}",
        labels={"channel": "", "pct": "Share of cash"},
        hover_data={"cr": ":.2f", "count": True},
    )
    fig_c.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
    fig_c.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_c, width="stretch")
    unexplained = aw.loc[aw["channel"] == "No prior interaction", "sum"].sum()
    attributed = aw.loc[aw["channel"] != "No prior interaction", "sum"].sum()
    st.caption(
        f"At {window}: **{cr(attributed)}** has a prior interaction, **{cr(unexplained)}** does not. "
        "Headline recovery does not last-touch for that reason."
    )

# ----- investment -----
st.subheader("₹10 Cr recommendation")
st.markdown(
    "**Better borrower targeting** — campaign names, channels, and target rules do not match "
    "(80% recommended-channel mismatch). That is the only area with a proven system failure."
)
a, b, c = st.columns(3)
a.metric("Incremental recovery", "Not estimable")
b.metric("ROI / break-even", "Not estimable")
c.metric("Downside", "₹10 Cr / ₹0 extra cash")
st.caption(
    "Not recommended on this file: telephony, more agents, AI voice, WhatsApp/digital, or field. "
    "Those options have no identifiable lift and/or missing cost and treatment flags."
)

st.caption("Source: golden metrics from `python scripts/run_pipeline.py` · SUCCESS unique payment_id · IST months · 30,000-account book.")
