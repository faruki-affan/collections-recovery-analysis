"""Rebuild clean + golden layers (full pipeline)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collections_analytics.build import build_all

if __name__ == "__main__":
    print(build_all())
