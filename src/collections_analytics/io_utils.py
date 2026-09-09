from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import DATA_CLEAN, DATA_GOLDEN, DATA_RAW, DATA_REJECTED, DATA_STAGING, RAW_TABLES


def ensure_dirs() -> None:
    for p in (DATA_STAGING, DATA_CLEAN, DATA_GOLDEN, DATA_REJECTED):
        p.mkdir(parents=True, exist_ok=True)


def read_raw(name: str) -> pd.DataFrame:
    path = DATA_RAW / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing raw file: {path}")
    return pd.read_csv(path)


def write_parquet(df: pd.DataFrame, folder: Path, name: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return path


def read_parquet(folder: Path, name: str) -> pd.DataFrame:
    return pd.read_parquet(folder / f"{name}.parquet")


def available_raw_tables() -> list[str]:
    return [t for t in RAW_TABLES if (DATA_RAW / f"{t}.csv").exists()]
