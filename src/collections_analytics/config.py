"""Paths and analysis constants. Override with environment variables."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
DATA_RAW = Path(os.environ.get("DATA_RAW", ROOT / "data" / "raw"))
DATA_STAGING = Path(os.environ.get("DATA_STAGING", ROOT / "data" / "staging"))
DATA_CLEAN = Path(os.environ.get("DATA_CLEAN", ROOT / "data" / "clean"))
DATA_GOLDEN = Path(os.environ.get("DATA_GOLDEN", ROOT / "data" / "golden"))
DATA_REJECTED = Path(os.environ.get("DATA_REJECTED", ROOT / "data" / "rejected"))

ANALYSIS_TZ = "Asia/Kolkata"
WINDOW_START = "2026-01-01"
WINDOW_END = "2026-08-08"  # last full calendar day present in payments/targeting

# Payment statuses treated as recovered cash (net of reversals handled separately)
SUCCESS_STATUS = "SUCCESS"
REVERSED_STATUS = "REVERSED"

# Disposition codes that mean the same business outcome
DISPOSITION_MAP = {
    "PTP": "PTP",
    "PROMISE_TO_PAY": "PTP",
    "PTP_BROKEN": "PTP_BROKEN",
    "NO_CONTACT": "NO_CONTACT",
    "WRONG_NUMBER": "WRONG_NUMBER",
    "CALLBACK": "CALLBACK",
    "DISPUTE": "DISPUTE",
    "PAID": "PAID",
    "REFUSED": "REFUSED",
}

RAW_TABLES = [
    "borrowers",
    "accounts",
    "agents",
    "agent_sessions",
    "campaigns",
    "daily_targeting",
    "calls",
    "call_attempts",
    "call_dispositions",
    "whatsapp_events",
    "sms_events",
    "field_visits",
    "promises_to_pay",
    "payments",
    "vendor_telephony",
    "complaints",
    "account_status_history",
]
