"""
Thin importable wrapper around the LEAGUES registry defined in
data/build_dataset.py, so the backend can list available leagues without
importing (and accidentally triggering) the fetch/CLI logic in that script.
"""
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
sys.path.insert(0, str(DATA_DIR))

from build_dataset import LEAGUES  # noqa: E402
