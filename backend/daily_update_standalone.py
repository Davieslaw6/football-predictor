"""
Standalone daily update: re-fetches match data for the currently-selected
leagues and retrains both models, WITHOUT needing the FastAPI backend to
be running. This is the more reliable option for unattended daily runs
via Windows Task Scheduler or cron, since it doesn't depend on a server
process already being up.

The running backend (if there is one) will pick up the refreshed model
files automatically the next time it handles a request that needs them —
no restart required, since ml/analyze.py loads lazily and this script
doesn't touch the live server process.

Usage:
    python3 daily_update_standalone.py

Windows Task Scheduler setup:
   1. Open Task Scheduler -> Create Basic Task
   2. Name: "Football Predictor Daily Update"
   3. Trigger: Daily, pick a time (e.g. 6:00 AM)
   4. Action: Start a program
        Program/script:  C:\\path\\to\\venv\\Scripts\\python.exe
        Add arguments:   daily_update_standalone.py
        Start in:        C:\\path\\to\\football-predictor\\backend
   5. Finish, then right-click the task -> Run, to test it once manually.

macOS/Linux cron setup (crontab -e):
    0 6 * * * cd /path/to/football-predictor/backend && /path/to/venv/bin/python3 daily_update_standalone.py >> update.log 2>&1
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
ML_DIR = ROOT_DIR / "ml"
SELECTION_FILE = DATA_DIR / "league_selection.json"


def load_selected_leagues() -> list[str]:
    if SELECTION_FILE.exists():
        return json.loads(SELECTION_FILE.read_text())["leagues"]
    return ["premier_league", "championship", "champions_league"]  # default: all


def run_step(name: str, cmd: list[str], cwd: Path, timeout: int) -> bool:
    print(f"[{datetime.now()}] {name}...")
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    print(result.stdout)
    if result.returncode != 0:
        print(f"FAILED: {name}")
        print(result.stderr)
        return False
    return True


def main():
    leagues = load_selected_leagues()
    print(f"[{datetime.now()}] Starting daily update for leagues: {leagues}")

    ok = run_step(
        "Fetching latest match data",
        [sys.executable, "build_dataset.py", "--leagues", ",".join(leagues)],
        DATA_DIR, timeout=180,
    )
    if not ok:
        sys.exit(1)

    ok = run_step("Retraining 1X2 model", [sys.executable, "train.py"], ML_DIR, timeout=300)
    if not ok:
        sys.exit(1)

    ok = run_step("Retraining goals market model", [sys.executable, "goals_model.py"], ML_DIR, timeout=180)
    if not ok:
        sys.exit(1)

    print(f"[{datetime.now()}] Daily update completed successfully.")


if __name__ == "__main__":
    main()
