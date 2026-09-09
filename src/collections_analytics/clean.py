"""Cleaning rules. Never overwrite raw files. Emit rejected/corrected ledgers."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd

from .config import DISPOSITION_MAP
from .timestamps import localize_to_ist, naive_as_ist, parse_naive


@dataclass
class CleanImpact:
    rule: str
    records_before: int
    rejected: int
    corrected: int
    retained: int
    amount_before: float | None = None
    amount_after: float | None = None
    notes: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        if d["amount_before"] is not None and d["amount_after"] is not None:
            d["amount_impact"] = d["amount_after"] - d["amount_before"]
        else:
            d["amount_impact"] = None
        return d


def drop_exact_duplicates(df: pd.DataFrame, rule: str, amount_col: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, CleanImpact]:
    before = len(df)
    amt_before = float(df[amount_col].sum()) if amount_col and amount_col in df.columns else None
    mask = df.duplicated(keep="first")
    rejected = df.loc[mask].copy()
    out = df.loc[~mask].copy()
    amt_after = float(out[amount_col].sum()) if amount_col and amount_col in df.columns else None
    impact = CleanImpact(
        rule=rule,
        records_before=before,
        rejected=int(mask.sum()),
        corrected=0,
        retained=len(out),
        amount_before=amt_before,
        amount_after=amt_after,
        notes="Exact row duplicates retained once (first occurrence).",
    )
    return out, rejected, impact


def dedupe_by_key(
    df: pd.DataFrame,
    key: str,
    rule: str,
    amount_col: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, CleanImpact]:
    before = len(df)
    amt_before = float(df[amount_col].sum()) if amount_col and amount_col in df.columns else None
    mask = df.duplicated(key, keep="first")
    rejected = df.loc[mask].copy()
    out = df.loc[~mask].copy()
    amt_after = float(out[amount_col].sum()) if amount_col and amount_col in df.columns else None
    impact = CleanImpact(
        rule=rule,
        records_before=before,
        rejected=int(mask.sum()),
        corrected=0,
        retained=len(out),
        amount_before=amt_before,
        amount_after=amt_after,
        notes=f"Keep first row per {key}. Do not treat other columns as a natural key unless proven.",
    )
    return out, rejected, impact


def map_dispositions(df: pd.DataFrame) -> tuple[pd.DataFrame, CleanImpact]:
    before = len(df)
    out = df.copy()
    out["disposition_code_raw"] = out["disposition_code"]
    out["disposition_code_std"] = out["disposition_code"].map(DISPOSITION_MAP)
    unknown = out["disposition_code_std"].isna() & out["disposition_code"].notna()
    out.loc[unknown, "disposition_code_std"] = "UNMAPPED"
    impact = CleanImpact(
        rule="map_disposition_codes",
        records_before=before,
        rejected=0,
        corrected=int((out["disposition_code_raw"] != out["disposition_code_std"]).sum()),
        retained=before,
        notes="PTP and PROMISE_TO_PAY mapped to PTP. Unmapped codes flagged, not dropped.",
    )
    return out, impact


def resolve_agents(agents: pd.DataFrame) -> tuple[pd.DataFrame, CleanImpact]:
    """agent_id is the operational key. Attributes on agents.csv conflict and are not trusted."""
    before = len(agents)
    df = agents.copy()
    df["joined_at"] = parse_naive(df["joined_at"])
    df["updated_at"] = parse_naive(df["updated_at"])
    # Tenure proxy: earliest joined_at per agent_id (hypothesis-grade)
    tenure = df.groupby("agent_id", as_index=False).agg(
        joined_at_min=("joined_at", "min"),
        updated_at_max=("updated_at", "max"),
        n_snapshots=("agent_id", "size"),
        n_employee_codes=("employee_code", "nunique"),
        n_names=("agent_name", "nunique"),
        n_vendors=("vendor_id", "nunique"),
        n_teams=("team", "nunique"),
        n_statuses=("status", "nunique"),
    )
    latest = df.sort_values("updated_at").groupby("agent_id", as_index=False).tail(1)
    latest = latest.rename(
        columns={
            "employee_code": "employee_code_latest_untrusted",
            "agent_name": "agent_name_latest_untrusted",
            "vendor_id": "vendor_id_latest_untrusted",
            "team": "team_latest_untrusted",
            "status": "status_latest_untrusted",
        }
    )
    out = tenure.merge(
        latest[
            [
                "agent_id",
                "employee_code_latest_untrusted",
                "agent_name_latest_untrusted",
                "vendor_id_latest_untrusted",
                "team_latest_untrusted",
                "status_latest_untrusted",
            ]
        ],
        on="agent_id",
        how="left",
    )
    out["identity_trust"] = "LOW"
    impact = CleanImpact(
        rule="resolve_agent_identity",
        records_before=before,
        rejected=before - len(out),
        corrected=0,
        retained=len(out),
        notes="Collapsed snapshots to 1 row per agent_id. Names/employee codes are not unique humans.",
    )
    return out, impact


def resolve_borrowers(borrowers: pd.DataFrame) -> tuple[pd.DataFrame, CleanImpact]:
    before = len(borrowers)
    df = borrowers.copy()
    df["created_at"] = parse_naive(df["created_at"])
    df["updated_at"] = parse_naive(df["updated_at"])

    def mode_or_na(s: pd.Series):
        m = s.dropna().mode()
        return m.iloc[0] if len(m) else pd.NA

    out = df.groupby("borrower_id", as_index=False).agg(
        n_snapshots=("borrower_id", "size"),
        n_names=("name", "nunique"),
        n_phones=("phone", "nunique"),
        n_cities=("city", "nunique"),
        n_states=("state", "nunique"),
        city_mode=("city", mode_or_na),
        state_mode=("state", mode_or_na),
        created_at_min=("created_at", "min"),
        updated_at_max=("updated_at", "max"),
    )
    out["pii_conflict_flag"] = (
        (out["n_names"] > 1) | (out["n_phones"] > 1) | (out["n_cities"] > 1) | (out["n_states"] > 1)
    )
    impact = CleanImpact(
        rule="resolve_borrower_identity",
        records_before=before,
        rejected=before - len(out),
        corrected=int(out["pii_conflict_flag"].sum()),
        retained=len(out),
        notes="Borrower PII conflicts are common. city/state mode is LOW-confidence geography only.",
    )
    return out, impact


def add_ist_from_zone(df: pd.DataFrame, ts_col: str = "event_at", tz_col: str = "timezone") -> pd.DataFrame:
    out = df.copy()
    out[ts_col] = parse_naive(out[ts_col])
    if tz_col in out.columns:
        out["event_at_ist"] = localize_to_ist(out[ts_col], out[tz_col])
        out["date_naive"] = out[ts_col].dt.date
        out["date_ist"] = out["event_at_ist"].dt.date
        out["date_shift_flag"] = out["date_naive"] != out["date_ist"]
    else:
        out["event_at_ist"] = naive_as_ist(out[ts_col])
        out["date_ist"] = out["event_at_ist"].dt.date
        out["date_shift_flag"] = False
    out["month_ist"] = pd.to_datetime(out["date_ist"]).dt.to_period("M").astype(str)
    return out
