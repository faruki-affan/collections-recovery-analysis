from __future__ import annotations

import pandas as pd

from .config import ANALYSIS_TZ


def parse_naive(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")


def localize_to_ist(event_at: pd.Series, timezone: pd.Series) -> pd.Series:
    """Interpret naive timestamps as local in `timezone`, convert to Asia/Kolkata."""
    out = pd.Series(pd.NaT, index=event_at.index, dtype="datetime64[ns, Asia/Kolkata]")
    event_at = parse_naive(event_at)
    tz = timezone.fillna("UTC").astype(str)
    for zone, idx in tz.groupby(tz).groups.items():
        try:
            localized = event_at.loc[idx].dt.tz_localize(
                zone, ambiguous="NaT", nonexistent="NaT"
            )
            out.loc[idx] = localized.dt.tz_convert(ANALYSIS_TZ)
        except Exception:
            # Fall back: treat as UTC
            localized = event_at.loc[idx].dt.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT")
            out.loc[idx] = localized.dt.tz_convert(ANALYSIS_TZ)
    return out


def naive_as_ist(event_at: pd.Series) -> pd.Series:
    """When no timezone is provided, treat naive clock as already IST (documented assumption)."""
    return parse_naive(event_at).dt.tz_localize(ANALYSIS_TZ, ambiguous="NaT", nonexistent="NaT")
