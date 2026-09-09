from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import DATA_GOLDEN, DATA_CLEAN
from .io_utils import read_parquet, write_parquet


def calculate_metrics() -> dict:
    am = read_parquet(DATA_GOLDEN, "golden_account_month")
    pay = read_parquet(DATA_GOLDEN, "fact_payment")
    calls = read_parquet(DATA_CLEAN, "calls")
    sessions = read_parquet(DATA_CLEAN, "agent_sessions")
    ptp = read_parquet(DATA_CLEAN, "promises_to_pay")
    attr = read_parquet(DATA_GOLDEN, "fact_payment_attribution")

    # Monthly performance
    monthly = am.groupby("month_ist", as_index=False).agg(
        n_accounts=("account_id", "nunique"),
        n_targeted=("targeted", "sum"),
        n_attempted_voice=("attempted_voice", "sum"),
        n_contacted_voice=("contacted_voice", "sum"),
        n_recovered=("recovered_flag", "sum"),
        recovery_amount=("recovery_amount", "sum"),
        n_ptp=("n_ptp", "sum"),
        n_ptp_kept=("n_ptp_kept", "sum"),
        n_calls=("n_calls", "sum"),
        n_answered=("n_answered", "sum"),
        n_wa=("n_wa", "sum"),
        n_sms=("n_sms", "sum"),
        n_field=("n_field", "sum"),
    )
    monthly["days"] = pd.to_datetime(monthly["month_ist"]).dt.days_in_month
    # August is partial through 8th
    monthly.loc[monthly["month_ist"] == "2026-08", "days"] = 8
    monthly["contact_rate_targeted"] = monthly["n_contacted_voice"] / monthly["n_targeted"].replace(0, np.nan)
    monthly["contact_rate_portfolio"] = monthly["n_contacted_voice"] / monthly["n_accounts"]
    monthly["rpc_among_answered"] = monthly["n_answered"] / monthly["n_calls"].replace(0, np.nan)
    monthly["recovery_rate_portfolio"] = monthly["n_recovered"] / monthly["n_accounts"]
    monthly["recovery_rate_targeted"] = monthly["n_recovered"] / monthly["n_targeted"].replace(0, np.nan)
    monthly["recovery_per_account"] = monthly["recovery_amount"] / monthly["n_accounts"]
    monthly["recovery_per_targeted"] = monthly["recovery_amount"] / monthly["n_targeted"].replace(0, np.nan)
    monthly["recovery_per_day"] = monthly["recovery_amount"] / monthly["days"]
    monthly["ptp_kept_rate"] = monthly["n_ptp_kept"] / monthly["n_ptp"].replace(0, np.nan)
    monthly["ptp_rate_targeted"] = (monthly["n_ptp"] > 0).astype(float)  # placeholder overwritten below

    ptp_accts = (
        ptp.groupby(ptp["month_ist"])["account_id"].nunique()
        if "month_ist" in ptp.columns
        else pd.Series(dtype=float)
    )
    monthly["ptp_accounts"] = monthly["month_ist"].map(
        ptp.groupby("month_ist")["account_id"].nunique()
    )
    monthly["ptp_rate_targeted"] = monthly["ptp_accounts"] / monthly["n_targeted"].replace(0, np.nan)

    sess = sessions.copy()
    sess["month_ist"] = pd.to_datetime(sess["date_ist"]).dt.to_period("M").astype(str)
    hours = sess.groupby("month_ist", as_index=False)["session_hours_clipped"].sum().rename(
        columns={"session_hours_clipped": "agent_hours"}
    )
    monthly = monthly.merge(hours, on="month_ist", how="left")
    monthly["recovery_per_agent_hour"] = monthly["recovery_amount"] / monthly["agent_hours"].replace(0, np.nan)
    monthly["recovery_amount_mom"] = monthly["recovery_amount"].pct_change()
    monthly["recovery_per_day_mom"] = monthly["recovery_per_day"].pct_change()
    monthly["recovery_per_account_mom"] = monthly["recovery_per_account"].pct_change()
    monthly["n_recovered_mom"] = monthly["n_recovered"].pct_change()

    write_parquet(monthly, DATA_GOLDEN, "metrics_monthly")

    # Channel conversion via attribution windows
    channel_rows = []
    for col, window in [("attr_1d", "1d"), ("attr_7d", "7d"), ("attr_14d", "14d"), ("attr_30d", "30d"), ("last_touch_channel", "unbounded")]:
        g = attr.groupby(col, dropna=False)["amount"].agg(["sum", "count"]).reset_index()
        g["window"] = window
        g = g.rename(columns={col: "channel"})
        channel_rows.append(g)
    channel_attr = pd.concat(channel_rows, ignore_index=True)
    write_parquet(channel_attr, DATA_GOLDEN, "metrics_channel_attribution")

    # Drivers: snapshot mix (LOW confidence because snapshot ≠ history)
    acc = read_parquet(DATA_GOLDEN, "dim_account")
    rec_acc = (
        pay[pay["is_success"]].groupby("account_id")["amount"].sum().rename("recovery_amount")
    )
    drv = acc.merge(rec_acc, on="account_id", how="left")
    drv["recovery_amount"] = drv["recovery_amount"].fillna(0)
    drv["paid"] = (drv["recovery_amount"] > 0).astype(int)

    def summarize(df: pd.DataFrame, col: str) -> pd.DataFrame:
        g = df.groupby(col, dropna=False).agg(
            n=("account_id", "count"),
            n_paid=("paid", "sum"),
            recovery=("recovery_amount", "sum"),
        ).reset_index().rename(columns={col: "segment"})
        g["driver"] = col
        g["recovery_rate"] = g["n_paid"] / g["n"]
        g["recovery_per_account"] = g["recovery"] / g["n"]
        return g

    drivers = pd.concat(
        [
            summarize(drv, "risk_segment"),
            summarize(drv, "loan_type"),
            summarize(drv, "status"),
            summarize(drv, "state_mode"),
        ],
        ignore_index=True,
    )
    write_parquet(drivers, DATA_GOLDEN, "metrics_drivers_snapshot")

    # Claim tests
    m = monthly.set_index("month_ist")
    claim = {
        "reported_claim": "Recovery has improved by 11% month-on-month.",
        "likely_compared_months": ["2026-02", "2026-03"],
        "total_rupees_mom_feb_mar": None,
        "per_day_mom_feb_mar": None,
        "per_account_mom_feb_mar": None,
        "paying_accounts_mom_feb_mar": None,
        "verdict": "",
        "notes": [],
    }
    if "2026-02" in m.index and "2026-03" in m.index:
        claim["total_rupees_mom_feb_mar"] = float(m.loc["2026-03", "recovery_amount"] / m.loc["2026-02", "recovery_amount"] - 1)
        claim["per_day_mom_feb_mar"] = float(m.loc["2026-03", "recovery_per_day"] / m.loc["2026-02", "recovery_per_day"] - 1)
        claim["per_account_mom_feb_mar"] = float(
            m.loc["2026-03", "recovery_per_account"] / m.loc["2026-02", "recovery_per_account"] - 1
        )
        claim["paying_accounts_mom_feb_mar"] = float(m.loc["2026-03", "n_recovered"] / m.loc["2026-02", "n_recovered"] - 1)
        claim["feb_days"] = int(m.loc["2026-02", "days"])
        claim["mar_days"] = int(m.loc["2026-03", "days"])
        claim["calendar_ratio"] = 31 / 28 - 1
        if abs(claim["total_rupees_mom_feb_mar"] - 0.11) < 0.02 and abs(claim["per_day_mom_feb_mar"]) < 0.02:
            claim["verdict"] = (
                "True only under a specific definition: total SUCCESS rupees, February to March, "
                "without calendar-day adjustment. Operationally the improvement is not real."
            )
        else:
            claim["verdict"] = "See computed MoM values; 11% is not a general property of the series."
    write_parquet(monthly, DATA_GOLDEN, "metrics_monthly")
    (DATA_GOLDEN / "claim_reconciliation.json").write_text(json.dumps(claim, indent=2), encoding="utf-8")

    # Counterfactual: targeting strategy v2/v3 vs legacy/v1 around April
    targeting = read_parquet(DATA_CLEAN, "daily_targeting")
    campaigns = read_parquet(DATA_GOLDEN, "dim_campaign")
    t = targeting.merge(campaigns[["campaign_id", "strategy_version"]], on="campaign_id", how="left")
    t["treated_campaign"] = t["strategy_version"].isin(["v2", "v3"]).astype(int)
    acct_treat = t.groupby(["account_id", "month_ist"], as_index=False)["treated_campaign"].max()
    cf = am.merge(acct_treat, on=["account_id", "month_ist"], how="left")
    cf["treated_campaign"] = cf["treated_campaign"].fillna(0).astype(int)
    cf["post"] = (cf["month_ist"] >= "2026-04").astype(int)
    # DiD on recovery_amount at account-month among targeted rows
    cf_t = cf[cf["targeted"] == 1].copy()
    means = cf_t.groupby(["treated_campaign", "post"])["recovery_amount"].mean().unstack()
    did = None
    if means.shape == (2, 2):
        # treated post-pre minus control post-pre
        did = float((means.loc[1, 1] - means.loc[1, 0]) - (means.loc[0, 1] - means.loc[0, 0]))
    cf_out = {
        "method": "difference-in-differences on account-month recovery among targeted accounts",
        "treatment": "account-month has any v2/v3 campaign targeting",
        "control": "account-month targeted only by legacy/v1 (or no v2/v3)",
        "post_start": "2026-04",
        "did_recovery_amount_per_account_month": did,
        "cell_means": means.astype(float).to_dict() if means is not None else None,
        "n": int(len(cf_t)),
        "identification_warning": (
            "Strategy mix is stable across months; this is not a clean mid-year switch. "
            "DiD is a robustness check, not a causal claim."
        ),
    }
    (DATA_GOLDEN / "counterfactual.json").write_text(json.dumps(cf_out, default=str, indent=2), encoding="utf-8")

    # Vendor answered rates
    vendors = read_parquet(DATA_GOLDEN, "dim_vendor")
    cv = calls.merge(vendors, on="vendor_id", how="left")
    vendor_m = (
        cv.groupby("vendor_name")
        .agg(n=("call_id", "count"), answered=("call_status", lambda s: (s == "ANSWERED").mean()))
        .reset_index()
    )
    write_parquet(vendor_m, DATA_GOLDEN, "metrics_vendor")

    out = {
        "monthly_rows": int(len(monthly)),
        "claim": claim,
        "counterfactual": cf_out,
        "success_amount": float(pay.loc[pay["is_success"], "amount"].sum()),
    }
    (DATA_GOLDEN / "analysis_summary.json").write_text(json.dumps(out, default=str, indent=2), encoding="utf-8")
    return out
