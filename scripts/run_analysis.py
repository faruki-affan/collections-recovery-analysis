"""Alias for the full reproducible run."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run_pipeline import main

if __name__ == "__main__":
    main()
