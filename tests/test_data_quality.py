from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
RAW = ROOT / "data" / "raw"
GOLDEN = ROOT / "data" / "golden"


def _require_raw():
    if not (RAW / "payments.csv").exists():
        pytest.skip("raw data not present")


def _require_golden():
    if not (GOLDEN / "fact_payment.parquet").exists():
        pytest.skip("golden data not built; run python scripts/run_pipeline.py")


def test_raw_files_present():
    _require_raw()
    expected = [
        "borrowers", "accounts", "agents", "agent_sessions", "campaigns",
        "daily_targeting", "calls", "call_attempts", "call_dispositions",
        "whatsapp_events", "sms_events", "field_visits", "promises_to_pay",
        "payments", "vendor_telephony", "complaints", "account_status_history",
    ]
    missing = [n for n in expected if not (RAW / f"{n}.csv").exists()]
    assert missing == []


def test_payment_id_unique_in_golden():
    _require_golden()
    df = pd.read_parquet(GOLDEN / "fact_payment.parquet")
    assert df["payment_id"].is_unique
    assert (df["amount"] > 0).all()
    assert df["payment_status"].isin(["SUCCESS", "FAILED", "PENDING", "REVERSED"]).all()


def test_account_id_unique_on_dim():
    _require_golden()
    acc = pd.read_parquet(GOLDEN / "dim_account.parquet")
    assert acc["account_id"].is_unique
    assert acc["account_id"].notna().all()


def test_account_month_grain():
    _require_golden()
    am = pd.read_parquet(GOLDEN / "golden_account_month.parquet")
    assert not am.duplicated(["account_id", "month_ist"]).any()
    assert set(am["month_ist"]) <= {
        "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"
    }
    assert am["recovery_amount"].min() >= 0


def test_referential_payments_to_accounts():
    _require_golden()
    pay = pd.read_parquet(GOLDEN / "fact_payment.parquet")
    acc = pd.read_parquet(GOLDEN / "dim_account.parquet")
    orphan = ~pay["account_id"].isin(acc["account_id"])
    assert orphan.mean() < 0.01, "unexpected payment account orphans"


def test_no_negative_session_hours_clipped():
    _require_golden()
    from collections_analytics.config import DATA_CLEAN
    ses = pd.read_parquet(DATA_CLEAN / "agent_sessions.parquet")
    assert (ses["session_hours_clipped"] >= 0).all()
    assert (ses["session_hours_clipped"] <= 16).all()


def test_disposition_mapping_ptp():
    _require_golden()
    from collections_analytics.config import DATA_CLEAN
    d = pd.read_parquet(DATA_CLEAN / "call_dispositions.parquet")
    raw_ptp = d["disposition_code_raw"].isin(["PTP", "PROMISE_TO_PAY"])
    assert (d.loc[raw_ptp, "disposition_code_std"] == "PTP").all()


def test_metric_reconciliation_success_amount():
    _require_golden()
    pay = pd.read_parquet(GOLDEN / "fact_payment.parquet")
    am = pd.read_parquet(GOLDEN / "golden_account_month.parquet")
    a = pay.loc[pay["is_success"], "amount"].sum()
    b = am["recovery_amount"].sum()
    assert a == pytest.approx(b, rel=1e-9)


def test_claim_file_exists_and_finite():
    _require_golden()
    claim = json.loads((GOLDEN / "claim_reconciliation.json").read_text(encoding="utf-8"))
    assert claim["total_rupees_mom_feb_mar"] is not None
    assert abs(claim["calendar_ratio"] - (31 / 28 - 1)) < 1e-12


def test_duplicate_payments_detected_in_raw():
    _require_raw()
    raw = pd.read_csv(RAW / "payments.csv")
    assert raw["payment_id"].duplicated().sum() == 500


def test_impossible_future_window_small():
    _require_golden()
    pay = pd.read_parquet(GOLDEN / "fact_payment.parquet")
    assert pay["event_at"].max() < pd.Timestamp("2026-08-10")
