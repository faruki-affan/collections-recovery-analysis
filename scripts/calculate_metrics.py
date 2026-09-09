from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collections_analytics.metrics import calculate_metrics

if __name__ == "__main__":
    print(calculate_metrics())
