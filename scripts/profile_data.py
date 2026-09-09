"""Profile every raw table and write docs/data_inventory.md plus staging JSON."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collections_analytics.config import DATA_RAW, DATA_STAGING, RAW_TABLES  # noqa: E402


def profile(name: str, df: pd.DataFrame) -> dict:
    n, p = df.shape
    info = {
        "name": name,
        "filename": f"{name}.csv",
        "rows": int(n),
        "cols": int(p),
        "columns": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "null_rate": {c: round(float(df[c].isna().mean()), 6) for c in df.columns},
        "nunique": {c: int(df[c].nunique(dropna=True)) for c in df.columns},
        "exact_dup_rows": int(df.duplicated().sum()),
        "candidate_pks": [],
        "date_cols": {},
        "categoricals": {},
    }
    for c in df.columns:
        nun = df[c].nunique(dropna=True)
        if nun == n and int(df[c].isna().sum()) == 0:
            info["candidate_pks"].append(c)
        parsed = pd.to_datetime(df[c], errors="coerce")
        if parsed.notna().mean() > 0.5 and parsed.nunique(dropna=True) > 5:
            info["date_cols"][c] = {
                "min": str(parsed.min()),
                "max": str(parsed.max()),
                "parse_rate": round(float(parsed.notna().mean()), 4),
            }
        if df[c].dtype == object and nun <= 40:
            vc = df[c].value_counts(dropna=False).head(20)
            info["categoricals"][c] = {str(k): int(v) for k, v in vc.items()}
    return info


def to_markdown(inventory: list[dict]) -> str:
    lines = [
        "# Data inventory",
        "",
        "Generated from `data/raw/*.csv`. There is a `data_dictionary.csv` in the package, but it is **not** treated as a source of truth — it lists dtypes only and does not define keys, grains, or metric logic.",
        "",
        "## Package notes (from supplier README)",
        "",
        "- Synthetic collections dataset, seed 42.",
        "- Intentionally includes duplicates, missing values, mixed timezones, inconsistent IDs, late events, schema versions, legacy disposition codes, and duplicate payment events.",
        "- Event-table row counts can exceed nominal size because duplicate rows were injected.",
        "",
        "## Files discovered",
        "",
        "| File | Rows | Columns | Exact duplicate rows | Candidate PK (unique + non-null) |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for inv in inventory:
        pk = ", ".join(inv["candidate_pks"]) if inv["candidate_pks"] else "— (none at row grain)"
        lines.append(
            f"| `{inv['filename']}` | {inv['rows']:,} | {inv['cols']} | {inv['exact_dup_rows']:,} | {pk} |"
        )
    lines += ["", "## Per-dataset profile", ""]
    for inv in inventory:
        lines += [
            f"### `{inv['filename']}`",
            "",
            f"- Rows: **{inv['rows']:,}** | Columns: **{inv['cols']}**",
            f"- Exact duplicate rows: **{inv['exact_dup_rows']:,}**",
            f"- Candidate primary keys: {inv['candidate_pks'] or 'none'}",
            "",
            "| Column | Dtype | Null % | Unique |",
            "| --- | --- | ---: | ---: |",
        ]
        for c in inv["columns"]:
            lines.append(
                f"| `{c}` | {inv['dtypes'][c]} | {inv['null_rate'][c]*100:.2f}% | {inv['nunique'][c]:,} |"
            )
        if inv["date_cols"]:
            lines += ["", "**Date-like columns**", ""]
            for c, d in inv["date_cols"].items():
                lines.append(f"- `{c}`: {d['min']} → {d['max']} (parse rate {d['parse_rate']:.1%})")
        if inv["categoricals"]:
            lines += ["", "**Low-cardinality columns**", ""]
            for c, vc in inv["categoricals"].items():
                preview = ", ".join(f"{k} ({v:,})" for k, v in list(vc.items())[:12])
                lines.append(f"- `{c}`: {preview}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    DATA_STAGING.mkdir(parents=True, exist_ok=True)
    inventory = []
    for name in RAW_TABLES:
        path = DATA_RAW / f"{name}.csv"
        if not path.exists():
            print("missing", path)
            continue
        df = pd.read_csv(path)
        inv = profile(name, df)
        inventory.append(inv)
        print(f"{name}: {inv['rows']:,} x {inv['cols']} dups={inv['exact_dup_rows']}")
    (DATA_STAGING / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    md = to_markdown(inventory)
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "data_inventory.md").write_text(md, encoding="utf-8")
    print("wrote docs/data_inventory.md")


if __name__ == "__main__":
    main()
