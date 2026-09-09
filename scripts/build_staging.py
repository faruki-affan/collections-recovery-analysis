from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collections_analytics.io_utils import ensure_dirs, read_raw, write_parquet
from collections_analytics.config import DATA_STAGING, RAW_TABLES


def main() -> None:
    ensure_dirs()
    for name in RAW_TABLES:
        df = read_raw(name)
        write_parquet(df, DATA_STAGING, name)
        print(f"staged {name}: {len(df):,} rows")


if __name__ == "__main__":
    main()
