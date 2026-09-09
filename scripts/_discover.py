"""One-shot discovery profiler. Writes JSON + prints summaries."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "staging"
OUT.mkdir(parents=True, exist_ok=True)

TABLES = [
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


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW / f"{name}.csv")


def profile(name: str, df: pd.DataFrame) -> dict:
    n, p = df.shape
    info = {
        "name": name,
        "rows": int(n),
        "cols": int(p),
        "columns": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "null_rate": {c: float(df[c].isna().mean()) for c in df.columns},
        "nunique": {c: int(df[c].nunique(dropna=True)) for c in df.columns},
        "exact_dup_rows": int(df.duplicated().sum()),
        "candidate_pks": [],
        "date_cols": {},
        "categoricals": {},
        "id_samples": {},
    }
    for c in df.columns:
        nun = df[c].nunique(dropna=True)
        if nun == n and df[c].isna().sum() == 0:
            info["candidate_pks"].append(c)
        if df[c].dtype == object or str(df[c].dtype).startswith("datetime"):
            parsed = pd.to_datetime(df[c], errors="coerce", utc=False)
            if parsed.notna().mean() > 0.5 and parsed.nunique() > 10:
                info["date_cols"][c] = {
                    "min": str(parsed.min()),
                    "max": str(parsed.max()),
                    "parse_rate": float(parsed.notna().mean()),
                }
        if df[c].dtype == object and nun <= 50:
            vc = df[c].value_counts(dropna=False).head(30)
            info["categoricals"][c] = {str(k): int(v) for k, v in vc.items()}
        if "id" in c.lower() or c.endswith("_code") or c in ("employee_code", "payment_reference"):
            s = df[c].dropna().astype(str)
            info["id_samples"][c] = {
                "sample": s.head(5).tolist(),
                "min_len": int(s.str.len().min()) if len(s) else None,
                "max_len": int(s.str.len().max()) if len(s) else None,
                "prefixes": s.str[:3].value_counts().head(8).to_dict(),
            }
    return info


def main() -> None:
    inventory = []
    frames = {}
    for name in TABLES:
        print(f"loading {name}...")
        df = load(name)
        frames[name] = df
        inv = profile(name, df)
        inventory.append(inv)
        print(
            f"  {name}: {inv['rows']:,} x {inv['cols']} "
            f"dups={inv['exact_dup_rows']} pk={inv['candidate_pks']}"
        )

    # Relationships
    rels = []
    id_map = {
        "borrower_id": "borrowers",
        "account_id": "accounts",
        "agent_id": "agents",
        "campaign_id": "campaigns",
        "vendor_id": "vendor_telephony",
        "call_id": "calls",
    }
    for name, df in frames.items():
        for col, parent in id_map.items():
            if col in df.columns and name != parent:
                child = set(df[col].dropna().astype(str))
                par = set(frames[parent][col].dropna().astype(str)) if col in frames[parent].columns else set()
                orphan = len(child - par)
                rels.append(
                    {
                        "child": name,
                        "col": col,
                        "parent": parent,
                        "child_unique": len(child),
                        "parent_unique": len(par),
                        "orphan_ids": orphan,
                        "coverage": float(1 - orphan / max(len(child), 1)),
                    }
                )

    # Payments forensics
    pay = frames["payments"]
    pay_forensics = {
        "rows": len(pay),
        "payment_id_unique": int(pay["payment_id"].nunique()),
        "payment_id_dups": int(pay["payment_id"].duplicated().sum()),
        "reference_unique": int(pay["payment_reference"].nunique()),
        "exact_row_dups": int(pay.duplicated().sum()),
        "status_counts": pay["payment_status"].value_counts(dropna=False).to_dict(),
        "method_counts": pay["payment_method"].value_counts(dropna=False).to_dict(),
        "amount_min": float(pay["amount"].min()),
        "amount_max": float(pay["amount"].max()),
        "amount_neg": int((pay["amount"] < 0).sum()),
        "amount_zero": int((pay["amount"] == 0).sum()),
        "gross_amount": float(pay["amount"].sum()),
        "success_amount_raw": float(pay.loc[pay["payment_status"].str.upper() == "SUCCESS", "amount"].sum())
        if pay["payment_status"].notna().any()
        else None,
    }
    # duplicate by payment_id
    pid_dups = pay[pay.duplicated("payment_id", keep=False)]
    pref_dups = pay[pay.duplicated("payment_reference", keep=False)]
    pay_forensics["dup_payment_id_rows"] = int(len(pid_dups))
    pay_forensics["dup_payment_id_amount"] = float(pid_dups["amount"].sum()) if len(pid_dups) else 0
    pay_forensics["dup_reference_rows"] = int(len(pref_dups))
    pay_forensics["dup_reference_amount"] = float(pref_dups["amount"].sum()) if len(pref_dups) else 0

    # Agent identity
    ag = frames["agents"]
    agent_id = {
        "rows": len(ag),
        "agent_id_unique": int(ag["agent_id"].nunique()),
        "employee_code_unique": int(ag["employee_code"].nunique()),
        "name_unique": int(ag["agent_name"].nunique()),
        "dup_employee_code_rows": int(ag.duplicated("employee_code", keep=False).sum()),
        "dup_name_rows": int(ag.duplicated("agent_name", keep=False).sum()),
        "status": ag["status"].value_counts(dropna=False).to_dict(),
        "team": ag["team"].value_counts(dropna=False).to_dict(),
    }

    # Dispositions over time
    disp = frames["call_dispositions"].copy()
    disp["event_at"] = pd.to_datetime(disp["event_at"], errors="coerce")
    disp["month"] = disp["event_at"].dt.to_period("M").astype(str)
    codes = pd.crosstab(disp["month"], disp["disposition_code"])
    versions = pd.crosstab(disp["month"], disp["disposition_version"])

    # Timezones
    tz_info = {}
    for tname, tcol in [
        ("accounts", "timezone"),
        ("agent_sessions", "timezone"),
        ("calls", "timezone"),
        ("vendor_telephony", "timezone"),
    ]:
        tz_info[tname] = frames[tname][tcol].value_counts(dropna=False).to_dict()

    # Portfolio mix by opened month / dpd
    acc = frames["accounts"].copy()
    acc["opened_at"] = pd.to_datetime(acc["opened_at"], errors="coerce")
    mix = {
        "status": acc["status"].value_counts(dropna=False).to_dict(),
        "loan_type": acc["loan_type"].value_counts(dropna=False).to_dict(),
        "risk_segment": acc["risk_segment"].value_counts(dropna=False).to_dict(),
        "schema_version": acc["schema_version"].value_counts(dropna=False).to_dict(),
        "dpd_describe": acc["dpd"].describe().to_dict(),
        "timezone": acc["timezone"].value_counts(dropna=False).to_dict(),
    }

    # Targeting strategy versions over time
    tgt = frames["daily_targeting"].copy()
    tgt["target_date"] = pd.to_datetime(tgt["target_date"], errors="coerce")
    tgt["month"] = tgt["target_date"].dt.to_period("M").astype(str)
    camp = frames["campaigns"]
    tgt2 = tgt.merge(camp[["campaign_id", "strategy_version", "channel", "target_definition", "campaign_name"]], on="campaign_id", how="left")
    targeting_mix = pd.crosstab(tgt2["month"], tgt2["strategy_version"], normalize="index").round(4)

    payload = {
        "inventory": inventory,
        "relationships": rels,
        "payments": pay_forensics,
        "agents": agent_id,
        "timezones": tz_info,
        "portfolio": mix,
        "disposition_codes_by_month": codes.to_dict(),
        "disposition_versions_by_month": versions.to_dict(),
        "targeting_strategy_by_month": targeting_mix.to_dict(),
    }
    outp = OUT / "discovery.json"
    outp.write_text(json.dumps(payload, default=str), encoding="utf-8")
    print("wrote", outp)

    print("\n=== RELATIONSHIPS (orphans) ===")
    for r in rels:
        if r["orphan_ids"] > 0:
            print(r)

    print("\n=== PAYMENTS ===")
    print(json.dumps(pay_forensics, indent=2, default=str))
    print("\n=== AGENTS ===")
    print(json.dumps(agent_id, indent=2, default=str))


if __name__ == "__main__":
    main()
