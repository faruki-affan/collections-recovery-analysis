"""Build staging, clean, golden, and metric tables from raw CSVs."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .clean import (
    add_ist_from_zone,
    dedupe_by_key,
    drop_exact_duplicates,
    map_dispositions,
    resolve_agents,
    resolve_borrowers,
)
from .config import (
    DATA_CLEAN,
    DATA_GOLDEN,
    DATA_REJECTED,
    DATA_STAGING,
    WINDOW_END,
    WINDOW_START,
)
from .io_utils import ensure_dirs, read_raw, write_parquet
from .timestamps import naive_as_ist, parse_naive


def _concat_reject(path: Path, df: pd.DataFrame, rule: str) -> None:
    if df.empty:
        return
    out = df.copy()
    out["reject_rule"] = rule
    if path.exists():
        prev = pd.read_parquet(path)
        out = pd.concat([prev, out], ignore_index=True)
    out.to_parquet(path, index=False)


def build_all() -> dict:
    ensure_dirs()
    impacts = []
    cleaning_ledgers = []

    # ----- staging: typed copies -----
    borrowers_raw = read_raw("borrowers")
    accounts = read_raw("accounts")
    agents_raw = read_raw("agents")
    sessions = read_raw("agent_sessions")
    campaigns = read_raw("campaigns")
    targeting = read_raw("daily_targeting")
    calls = read_raw("calls")
    attempts = read_raw("call_attempts")
    dispositions = read_raw("call_dispositions")
    wa = read_raw("whatsapp_events")
    sms = read_raw("sms_events")
    field = read_raw("field_visits")
    ptp = read_raw("promises_to_pay")
    payments = read_raw("payments")
    vendors = read_raw("vendor_telephony")
    complaints = read_raw("complaints")
    history = read_raw("account_status_history")

    for name, df in [
        ("borrowers", borrowers_raw),
        ("accounts", accounts),
        ("agents", agents_raw),
        ("agent_sessions", sessions),
        ("campaigns", campaigns),
        ("daily_targeting", targeting),
        ("calls", calls),
        ("call_attempts", attempts),
        ("call_dispositions", dispositions),
        ("whatsapp_events", wa),
        ("sms_events", sms),
        ("field_visits", field),
        ("promises_to_pay", ptp),
        ("payments", payments),
        ("vendor_telephony", vendors),
        ("complaints", complaints),
        ("account_status_history", history),
    ]:
        write_parquet(df, DATA_STAGING, name)

    reject_pay = DATA_REJECTED / "payments.parquet"
    if reject_pay.exists():
        reject_pay.unlink()

    # ----- payments -----
    pay = payments.copy()
    pay["amount"] = pd.to_numeric(pay["amount"], errors="coerce")
    pay["event_at"] = parse_naive(pay["event_at"])
    pay0 = pay.copy()
    pay, rej, imp = drop_exact_duplicates(pay, "payments_exact_row_dedupe", "amount")
    impacts.append(imp.as_dict())
    _concat_reject(reject_pay, rej, imp.rule)
    pay, rej, imp = dedupe_by_key(pay, "payment_id", "payments_dedupe_payment_id", "amount")
    impacts.append(imp.as_dict())
    _concat_reject(reject_pay, rej, imp.rule)
    # Do NOT dedupe payment_reference: empirically it collides across accounts.
    pay["event_at_ist"] = naive_as_ist(pay["event_at"])
    pay["date_ist"] = pay["event_at_ist"].dt.date
    pay["month_ist"] = pd.to_datetime(pay["date_ist"]).dt.to_period("M").astype(str)
    pay["is_success"] = pay["payment_status"].str.upper() == "SUCCESS"
    pay["is_reversed"] = pay["payment_status"].str.upper() == "REVERSED"
    pay["in_window"] = (pay["date_ist"] >= pd.to_datetime(WINDOW_START).date()) & (
        pay["date_ist"] <= pd.to_datetime(WINDOW_END).date()
    )
    write_parquet(pay, DATA_CLEAN, "payments")

    # reference-collision diagnostic (not applied as a drop)
    ref_acct = pay.groupby("payment_reference")["account_id"].nunique()
    impacts.append(
        {
            "rule": "payment_reference_NOT_used_as_key",
            "records_before": int(len(pay0)),
            "rejected": 0,
            "corrected": 0,
            "retained": int(len(pay)),
            "amount_before": None,
            "amount_after": None,
            "amount_impact": None,
            "notes": (
                f"{int((ref_acct > 1).sum())} payment_references map to multiple accounts. "
                "Treating reference as a transaction key would mix unrelated payments."
            ),
        }
    )

    # ----- calls -----
    calls_c = add_ist_from_zone(calls)
    calls_c, rej, imp = drop_exact_duplicates(calls_c, "calls_exact_row_dedupe")
    impacts.append(imp.as_dict())
    calls_c, rej, imp = dedupe_by_key(calls_c, "call_id", "calls_dedupe_call_id")
    impacts.append(imp.as_dict())
    write_parquet(calls_c, DATA_CLEAN, "calls")

    att_c = add_ist_from_zone(attempts.drop(columns=["timezone"], errors="ignore"))
    write_parquet(att_c, DATA_CLEAN, "call_attempts")

    disp_c, imp = map_dispositions(dispositions)
    impacts.append(imp.as_dict())
    disp_c = add_ist_from_zone(disp_c.drop(columns=["timezone"], errors="ignore"))
    write_parquet(disp_c, DATA_CLEAN, "call_dispositions")

    wa_c, rej, imp = drop_exact_duplicates(wa, "whatsapp_exact_row_dedupe")
    impacts.append(imp.as_dict())
    wa_c, rej, imp = dedupe_by_key(wa_c, "whatsapp_event_id", "whatsapp_dedupe_id")
    impacts.append(imp.as_dict())
    wa_c = add_ist_from_zone(wa_c.drop(columns=["timezone"], errors="ignore"))
    write_parquet(wa_c, DATA_CLEAN, "whatsapp_events")

    sms_c = add_ist_from_zone(sms.drop(columns=["timezone"], errors="ignore"))
    write_parquet(sms_c, DATA_CLEAN, "sms_events")

    field_c = add_ist_from_zone(field.drop(columns=["timezone"], errors="ignore"))
    if "scheduled_at" in field_c.columns:
        field_c["scheduled_at"] = parse_naive(field_c["scheduled_at"])
    write_parquet(field_c, DATA_CLEAN, "field_visits")

    ptp_c = add_ist_from_zone(ptp.drop(columns=["timezone"], errors="ignore"))
    ptp_c["promised_date"] = parse_naive(ptp_c["promised_date"])
    ptp_c["promised_amount"] = pd.to_numeric(ptp_c["promised_amount"], errors="coerce")
    write_parquet(ptp_c, DATA_CLEAN, "promises_to_pay")

    sessions_c = add_ist_from_zone(
        sessions.rename(columns={"login_at": "event_at"}), ts_col="event_at", tz_col="timezone"
    )
    sessions_c = sessions_c.rename(columns={"event_at": "login_at", "event_at_ist": "login_at_ist"})
    sessions_c["logout_at"] = parse_naive(sessions_c["logout_at"])
    # logout tz unknown: interpret in same session timezone
    sessions_c["logout_at_ist"] = localize_logout(sessions_c)
    sessions_c["session_hours"] = (
        sessions_c["logout_at_ist"] - sessions_c["login_at_ist"]
    ).dt.total_seconds() / 3600.0
    sessions_c["session_hours_clipped"] = sessions_c["session_hours"].clip(lower=0, upper=16)
    sessions_c["hours_clipped_flag"] = sessions_c["session_hours"] != sessions_c["session_hours_clipped"]
    write_parquet(sessions_c, DATA_CLEAN, "agent_sessions")

    targeting_c = targeting.copy()
    targeting_c["target_date"] = parse_naive(targeting_c["target_date"])
    targeting_c["month_ist"] = targeting_c["target_date"].dt.to_period("M").astype(str)
    write_parquet(targeting_c, DATA_CLEAN, "daily_targeting")

    campaigns_c = campaigns.copy()
    campaigns_c["start_at"] = parse_naive(campaigns_c["start_at"])
    campaigns_c["end_at"] = parse_naive(campaigns_c["end_at"])
    campaigns_c["name_channel_mismatch"] = False  # documented at campaign grain below
    write_parquet(campaigns_c, DATA_CLEAN, "campaigns")
    write_parquet(vendors, DATA_CLEAN, "vendor_telephony")
    write_parquet(accounts, DATA_CLEAN, "accounts")

    agents_g, imp = resolve_agents(agents_raw)
    impacts.append(imp.as_dict())
    write_parquet(agents_g, DATA_CLEAN, "agents_resolved")
    write_parquet(agents_g, DATA_GOLDEN, "dim_agent")

    borrowers_g, imp = resolve_borrowers(borrowers_raw)
    impacts.append(imp.as_dict())
    write_parquet(borrowers_g, DATA_CLEAN, "borrowers_resolved")
    write_parquet(borrowers_g, DATA_GOLDEN, "dim_borrower")

    complaints_c = add_ist_from_zone(complaints.drop(columns=["timezone"], errors="ignore"))
    write_parquet(complaints_c, DATA_CLEAN, "complaints")

    hist_c = history.copy()
    hist_c["event_at"] = parse_naive(hist_c["event_at"])
    hist_c["recorded_at"] = parse_naive(hist_c["recorded_at"])
    hist_c["recorded_before_event"] = hist_c["recorded_at"] < hist_c["event_at"]
    hist_c["event_at_ist"] = naive_as_ist(hist_c["event_at"])
    hist_c["date_ist"] = hist_c["event_at_ist"].dt.date
    hist_c["month_ist"] = pd.to_datetime(hist_c["date_ist"]).dt.to_period("M").astype(str)
    write_parquet(hist_c, DATA_CLEAN, "account_status_history")

    # ----- golden facts -----
    dim_account = accounts.copy()
    dim_account["orphan_borrower"] = ~dim_account["borrower_id"].isin(borrowers_g["borrower_id"])
    dim_account = dim_account.merge(
        borrowers_g[["borrower_id", "state_mode", "city_mode", "pii_conflict_flag"]],
        on="borrower_id",
        how="left",
    )
    write_parquet(dim_account, DATA_GOLDEN, "dim_account")
    write_parquet(campaigns_c, DATA_GOLDEN, "dim_campaign")
    write_parquet(vendors, DATA_GOLDEN, "dim_vendor")

    fact_payment = pay.copy()
    write_parquet(fact_payment, DATA_GOLDEN, "fact_payment")

    # Interaction spine (account-event)
    call_ev = calls_c.rename(columns={"call_id": "event_id"}).assign(
        event_source="CALL",
        channel="VOICE",
        outcome=lambda x: x["call_status"],
    )[["event_id", "account_id", "borrower_id", "event_at_ist", "date_ist", "month_ist", "agent_id", "campaign_id", "event_source", "channel", "outcome"]]

    wa_ev = wa_c.rename(columns={"whatsapp_event_id": "event_id"}).assign(
        event_source="WHATSAPP",
        channel="WHATSAPP",
        outcome=lambda x: x["event_type"],
        agent_id=pd.NA,
        campaign_id=pd.NA,
    )[["event_id", "account_id", "borrower_id", "event_at_ist", "date_ist", "month_ist", "agent_id", "campaign_id", "event_source", "channel", "outcome"]]

    sms_ev = sms_c.rename(columns={"sms_event_id": "event_id"}).assign(
        event_source="SMS",
        channel="SMS",
        outcome=lambda x: x["event_type"],
        agent_id=pd.NA,
        campaign_id=pd.NA,
    )[["event_id", "account_id", "borrower_id", "event_at_ist", "date_ist", "month_ist", "agent_id", "campaign_id", "event_source", "channel", "outcome"]]

    field_ev = field_c.rename(columns={"visit_id": "event_id"}).assign(
        event_source="FIELD",
        channel="FIELD",
        outcome=lambda x: x["outcome"],
        campaign_id=pd.NA,
    )[["event_id", "account_id", "borrower_id", "event_at_ist", "date_ist", "month_ist", "agent_id", "campaign_id", "event_source", "channel", "outcome"]]

    fact_interaction = pd.concat([call_ev, wa_ev, sms_ev, field_ev], ignore_index=True)
    write_parquet(fact_interaction, DATA_GOLDEN, "fact_interaction")

    # Attribution sensitivity: last interaction at or before each SUCCESS payment
    succ = fact_payment[fact_payment["is_success"]].copy()
    inter = fact_interaction.dropna(subset=["event_at_ist"]).copy()
    succ_m = succ[["payment_id", "account_id", "amount", "event_at_ist"]].rename(
        columns={"event_at_ist": "payment_at_ist"}
    )
    inter_m = inter[["account_id", "event_at_ist", "event_id", "channel"]].rename(
        columns={"event_at_ist": "touch_at_ist", "event_id": "last_touch_event_id", "channel": "last_touch_channel"}
    )
    succ_m["payment_at_ist"] = pd.to_datetime(succ_m["payment_at_ist"], utc=True).astype("datetime64[ns, UTC]")
    inter_m["touch_at_ist"] = pd.to_datetime(inter_m["touch_at_ist"], utc=True).astype("datetime64[ns, UTC]")
    succ_m = succ_m.sort_values("payment_at_ist")
    inter_m = inter_m.sort_values("touch_at_ist")
    fact_attribution = pd.merge_asof(
        succ_m,
        inter_m,
        left_on="payment_at_ist",
        right_on="touch_at_ist",
        by="account_id",
        direction="backward",
    )
    hours = (fact_attribution["payment_at_ist"] - fact_attribution["touch_at_ist"]).dt.total_seconds() / 3600.0
    fact_attribution["last_touch_hours"] = hours
    fact_attribution["attr_1d"] = np.where(hours <= 24, fact_attribution["last_touch_channel"], pd.NA)
    fact_attribution["attr_7d"] = np.where(hours <= 24 * 7, fact_attribution["last_touch_channel"], pd.NA)
    fact_attribution["attr_14d"] = np.where(hours <= 24 * 14, fact_attribution["last_touch_channel"], pd.NA)
    fact_attribution["attr_30d"] = np.where(hours <= 24 * 30, fact_attribution["last_touch_channel"], pd.NA)
    write_parquet(fact_attribution, DATA_GOLDEN, "fact_payment_attribution")

    # Account-month grain (chosen KPI grain)
    months = pd.period_range(WINDOW_START, WINDOW_END, freq="M").astype(str)
    acc_ids = dim_account["account_id"].unique()
    am = pd.MultiIndex.from_product([acc_ids, months], names=["account_id", "month_ist"]).to_frame(index=False)

    targeted = targeting_c.groupby(["account_id", "month_ist"], as_index=False).agg(
        n_target_rows=("target_id", "count"),
        n_campaigns=("campaign_id", "nunique"),
        any_contacted_flag=("status", lambda s: int((s == "CONTACTED").any())),
    )
    targeted["targeted"] = 1

    rec = (
        fact_payment[fact_payment["is_success"]]
        .groupby(["account_id", "month_ist"], as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "recovery_amount"})
    )
    rev = (
        fact_payment[fact_payment["is_reversed"]]
        .groupby(["account_id", "month_ist"], as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "reversed_amount"})
    )

    calls_m = calls_c.groupby(["account_id", "month_ist"], as_index=False).agg(
        n_calls=("call_id", "count"),
        n_answered=("call_status", lambda s: int((s == "ANSWERED").sum())),
        n_call_agents=("agent_id", "nunique"),
    )
    ptp_m = ptp_c.groupby(["account_id", "month_ist"], as_index=False).agg(
        n_ptp=("ptp_id", "count"),
        n_ptp_kept=("status", lambda s: int((s == "KEPT").sum())),
        n_ptp_broken=("status", lambda s: int((s == "BROKEN").sum())),
    )
    wa_m = wa_c.groupby(["account_id", "month_ist"], as_index=False).agg(
        n_wa=("event_id" if "event_id" in wa_c.columns else "whatsapp_event_id", "count")
        if False
        else ("whatsapp_event_id", "count")
    )
    # fix wa_m
    wa_m = wa_c.groupby(["account_id", "month_ist"], as_index=False).agg(n_wa=("whatsapp_event_id", "count"))
    sms_m = sms_c.groupby(["account_id", "month_ist"], as_index=False).agg(n_sms=("sms_event_id", "count"))
    field_m = field_c.groupby(["account_id", "month_ist"], as_index=False).agg(n_field=("visit_id", "count"))

    golden_am = am.merge(targeted, on=["account_id", "month_ist"], how="left")
    golden_am = golden_am.merge(rec, on=["account_id", "month_ist"], how="left")
    golden_am = golden_am.merge(rev, on=["account_id", "month_ist"], how="left")
    golden_am = golden_am.merge(calls_m, on=["account_id", "month_ist"], how="left")
    golden_am = golden_am.merge(ptp_m, on=["account_id", "month_ist"], how="left")
    golden_am = golden_am.merge(wa_m, on=["account_id", "month_ist"], how="left")
    golden_am = golden_am.merge(sms_m, on=["account_id", "month_ist"], how="left")
    golden_am = golden_am.merge(field_m, on=["account_id", "month_ist"], how="left")
    golden_am["targeted"] = golden_am["targeted"].fillna(0).astype(int)
    for c in [
        "n_target_rows",
        "n_campaigns",
        "any_contacted_flag",
        "n_calls",
        "n_answered",
        "n_call_agents",
        "n_ptp",
        "n_ptp_kept",
        "n_ptp_broken",
        "n_wa",
        "n_sms",
        "n_field",
        "recovery_amount",
        "reversed_amount",
    ]:
        if c in golden_am.columns:
            golden_am[c] = golden_am[c].fillna(0)
    golden_am["recovered_flag"] = (golden_am["recovery_amount"] > 0).astype(int)
    golden_am["contacted_voice"] = (golden_am["n_answered"] > 0).astype(int)
    golden_am["attempted_voice"] = (golden_am["n_calls"] > 0).astype(int)
    golden_am["eligible_portfolio"] = 1  # closed-book 30k accounts every month
    golden_am = golden_am.merge(
        dim_account[
            [
                "account_id",
                "borrower_id",
                "loan_type",
                "dpd",
                "risk_segment",
                "status",
                "principal_amount",
                "outstanding_amount",
                "state_mode",
                "orphan_borrower",
            ]
        ],
        on="account_id",
        how="left",
    )
    write_parquet(golden_am, DATA_GOLDEN, "golden_account_month")

    write_parquet(pd.DataFrame(impacts), DATA_GOLDEN, "cleaning_impact")
    (DATA_GOLDEN / "cleaning_impact.json").write_text(json.dumps(impacts, default=str, indent=2), encoding="utf-8")

    summary = {
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
        "n_accounts": int(dim_account["account_id"].nunique()),
        "n_payments_clean": int(len(fact_payment)),
        "success_amount_clean": float(fact_payment.loc[fact_payment["is_success"], "amount"].sum()),
        "n_interactions": int(len(fact_interaction)),
        "account_month_rows": int(len(golden_am)),
    }
    (DATA_GOLDEN / "build_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def localize_logout(sessions_c: pd.DataFrame) -> pd.Series:
    from .timestamps import localize_to_ist

    return localize_to_ist(sessions_c["logout_at"], sessions_c["timezone"])


if __name__ == "__main__":
    print(build_all())
