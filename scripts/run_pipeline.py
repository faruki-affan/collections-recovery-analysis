from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collections_analytics.build import build_all
from collections_analytics.metrics import calculate_metrics


def main() -> None:
    summary = build_all()
    print("build:", summary)
    metrics = calculate_metrics()
    print("claim verdict:", metrics["claim"].get("verdict"))
    print("feb-mar rupees mom:", metrics["claim"].get("total_rupees_mom_feb_mar"))
    print("feb-mar per-day mom:", metrics["claim"].get("per_day_mom_feb_mar"))
    print("did:", metrics["counterfactual"].get("did_recovery_amount_per_account_month"))


if __name__ == "__main__":
    main()
