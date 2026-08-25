"""
FastAPI backend for the football match prediction platform.

Endpoints:
  GET  /api/teams                 -> searchable list of known teams
  POST /api/analyze               -> full match analysis for two teams
  GET  /api/fixtures/live         -> live in-play fixtures aggregated across all
                                      enabled + configured live data providers
                                      (Sportmonks, API-Football, football-data.org)
  GET  /api/providers             -> status of each live data provider
  POST /api/providers/selection   -> enable/disable a single provider independently
  GET  /api/premium-stats         -> status of the premium match-statistics toggle
  POST /api/premium-stats/selection -> enable real corners/shots data, or disable (use heuristic estimate)
  GET  /api/leagues               -> which leagues exist + which are selected for updates
  POST /api/leagues/selection     -> set which leagues get refreshed by /api/update
  POST /api/update                -> re-fetch data + retrain for selected leagues (background)
  GET  /api/update/status         -> poll the status of the last/current update run
  GET  /api/health                -> health check

Run with:
    uvicorn app.main:app --reload --port 8000
"""
import os
import sys
import json
import subprocess
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

# Make the ml/ package importable
ROOT_DIR = Path(__file__).parent.parent.parent
ML_DIR = ROOT_DIR / "ml"
DATA_DIR = ROOT_DIR / "data"
sys.path.insert(0, str(ML_DIR))

import analyze as analysis_engine  # noqa: E402
from build_dataset_loader import LEAGUES  # noqa: E402
from app.providers import registry as providers_registry  # noqa: E402
from app.providers import premium_stats  # noqa: E402

app = FastAPI(
    title="Football Match Prediction API",
    description="Predicts match outcomes using Elo, form, H2H, and availability-adjusted features.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://football-predictor-lime.vercel.app"],  # tighten in production to your frontend's actual origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FOOTBALL_DATA_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"

LEAGUE_SELECTION_FILE = DATA_DIR / "league_selection.json"


def _load_selection() -> list[str]:
    if LEAGUE_SELECTION_FILE.exists():
        return json.loads(LEAGUE_SELECTION_FILE.read_text())["leagues"]
    return list(LEAGUES.keys())  # default: all leagues


def _save_selection(leagues: list[str]):
    LEAGUE_SELECTION_FILE.write_text(json.dumps({"leagues": leagues}))


# In-memory update status (fine for a single-process local/dev deployment;
# a real production deployment with multiple workers would want this in
# Redis or a DB instead).
_update_state = {"status": "idle", "started_at": None, "finished_at": None, "log": "", "error": None}
_update_lock = threading.Lock()


def _run_update(leagues: list[str]):
    with _update_lock:
        _update_state["status"] = "running"
        _update_state["started_at"] = time.time()
        _update_state["finished_at"] = None
        _update_state["error"] = None
        _update_state["log"] = ""

    log_lines = []
    try:
        # Step 1: re-fetch data for selected leagues
        result = subprocess.run(
            [sys.executable, "build_dataset.py", "--leagues", ",".join(leagues)],
            cwd=str(DATA_DIR), capture_output=True, text=True, timeout=180,
        )
        log_lines.append(result.stdout)
        if result.returncode != 0:
            raise RuntimeError(f"build_dataset.py failed: {result.stderr}")

        # Step 2: retrain both models on the refreshed data
        result = subprocess.run(
            [sys.executable, "train.py"], cwd=str(ML_DIR),
            capture_output=True, text=True, timeout=300,
        )
        log_lines.append(result.stdout)
        if result.returncode != 0:
            raise RuntimeError(f"train.py failed: {result.stderr}")

        result = subprocess.run(
            [sys.executable, "goals_model.py"], cwd=str(ML_DIR),
            capture_output=True, text=True, timeout=180,
        )
        log_lines.append(result.stdout)
        if result.returncode != 0:
            raise RuntimeError(f"goals_model.py failed: {result.stderr}")

        # Reload the analysis engine's cached model/data in this process
        analysis_engine._model = None
        analysis_engine._feature_cols = None
        analysis_engine._engineered = None

        with _update_lock:
            _update_state["status"] = "success"
    except Exception as e:
        with _update_lock:
            _update_state["status"] = "error"
            _update_state["error"] = str(e)
    finally:
        with _update_lock:
            _update_state["finished_at"] = time.time()
            _update_state["log"] = "\n".join(log_lines)


# ---------- Schemas ----------

class AnalyzeRequest(BaseModel):
    home_team: str
    away_team: str
    home_injury_penalty: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of home squad strength unavailable (0-1)")
    away_injury_penalty: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of away squad strength unavailable (0-1)")
    home_out_players: list[str] = Field(default_factory=list)
    away_out_players: list[str] = Field(default_factory=list)


class LeagueSelectionRequest(BaseModel):
    leagues: list[str]


# ---------- Routes ----------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/teams")
def get_teams(q: str | None = None):
    """Searchable team list. Pass ?q=ars to filter (case-insensitive substring)."""
    teams = analysis_engine.list_teams()
    if q:
        q_lower = q.lower()
        teams = [t for t in teams if q_lower in t.lower()]
    return {"teams": teams, "count": len(teams)}


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    try:
        result = analysis_engine.analyze_match(
            home_team=req.home_team,
            away_team=req.away_team,
            home_injury_penalty=req.home_injury_penalty,
            away_injury_penalty=req.away_injury_penalty,
            home_out_players=req.home_out_players,
            away_out_players=req.away_out_players,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # If a premium match-statistics provider is enabled, try it for real
    # corners/shots data; on any failure (no key, plan doesn't include
    # this data, network issue) fall back to the heuristic estimate that
    # analyze_match() already computed — never let a premium-provider
    # problem break the whole analysis.
    premium_home = await premium_stats.fetch_team_match_stats(req.home_team)
    premium_away = await premium_stats.fetch_team_match_stats(req.away_team)
    if premium_home and not premium_home.get("error") and premium_away and not premium_away.get("error"):
        result["estimated_stats"]["premium_data_available"] = True
        result["estimated_stats"]["premium_source"] = premium_home.get("source")
        result["estimated_stats"]["premium_raw"] = {"home": premium_home, "away": premium_away}
    elif premium_home or premium_away:
        # premium stats were attempted (enabled) but failed — surface why,
        # while still returning the heuristic estimate as the usable result
        error = (premium_home or {}).get("error") or (premium_away or {}).get("error")
        result["estimated_stats"]["premium_data_available"] = False
        result["estimated_stats"]["premium_error"] = error

    return result


@app.get("/api/leagues")
def get_leagues():
    """All available leagues plus which are currently selected for updates."""
    selected = _load_selection()
    return {
        "leagues": [
            {
                "key": key,
                "label": cfg["label"],
                "competition_type": cfg["competition_type"],
                "seasons_available": cfg["seasons"],
                "selected": key in selected,
            }
            for key, cfg in LEAGUES.items()
        ]
    }


@app.post("/api/leagues/selection")
def set_league_selection(req: LeagueSelectionRequest):
    """Sets which leagues get refreshed the next time /api/update runs."""
    invalid = [l for l in req.leagues if l not in LEAGUES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown league key(s): {invalid}")
    if not req.leagues:
        raise HTTPException(status_code=400, detail="At least one league must be selected")
    _save_selection(req.leagues)
    return {"leagues": req.leagues}


@app.post("/api/update")
def trigger_update():
    """
    Re-fetches match data for the currently-selected leagues and retrains
    both models. Runs in a background thread since it can take up to a
    couple of minutes; poll /api/update/status for progress. This is what
    a daily scheduled task (cron / Windows Task Scheduler) should call.
    """
    with _update_lock:
        if _update_state["status"] == "running":
            raise HTTPException(status_code=409, detail="An update is already running")

    leagues = _load_selection()
    thread = threading.Thread(target=_run_update, args=(leagues,), daemon=True)
    thread.start()
    return {"message": f"Update started for leagues: {leagues}", "status": "running"}


@app.get("/api/update/status")
def update_status():
    with _update_lock:
        state = dict(_update_state)
    return state


@app.get("/api/fixtures/live")
async def live_fixtures(competition: str | None = None):
    """
    Live in-play fixtures, aggregated across every enabled + API-key-configured
    provider (Sportmonks, API-Football, football-data.org). Providers can be
    toggled independently via /api/providers/selection — a disabled or
    unconfigured provider is skipped silently and reported in
    provider_results, never crashes the request, and never blocks the others.
    """
    result = await providers_registry.fetch_live_fixtures_all(competition)
    any_active = any(p["configured"] and p["enabled"] for p in result["provider_results"])
    return {
        "configured": any_active,
        "message": None if any_active else (
            "No live data provider is both enabled and has an API key configured. "
            "See /api/providers for status, or the README for setup steps."
        ),
        **result,
    }


@app.get("/api/providers")
def get_providers():
    """Status of every live data provider: enabled/disabled + whether an API key is set."""
    statuses = providers_registry.get_provider_statuses()
    return {
        "providers": [
            {
                "key": s.key,
                "label": s.label,
                "enabled": s.enabled,
                "configured": s.configured,
                "available": s.available,
            }
            for s in statuses
        ]
    }


class ProviderToggleRequest(BaseModel):
    provider: str
    enabled: bool


@app.post("/api/providers/selection")
def set_provider_selection(req: ProviderToggleRequest):
    """Enable or disable a single live data provider (Sportmonks, API-Football,
    or football-data.org) independently of the others."""
    try:
        providers_registry.set_provider_enabled(req.provider, req.enabled)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"provider": req.provider, "enabled": req.enabled}


class PremiumStatsSelectionRequest(BaseModel):
    provider: str | None = None  # "sportmonks" | "api_football" | None (disabled)


@app.get("/api/premium-stats")
def get_premium_stats_status():
    """
    Status of the premium match-statistics toggle: real corners/shots
    data (if enabled and working) vs. the always-available heuristic
    estimate (the default). Separate from /api/providers, which is about
    live fixture/score data — a user might want one enabled without the
    other.
    """
    return premium_stats.get_status()


@app.post("/api/premium-stats/selection")
def set_premium_stats_selection(req: PremiumStatsSelectionRequest):
    """Enable real match-statistics data from Sportmonks or API-Football
    (if your plan includes it), or pass provider: null to go back to the
    always-available heuristic estimate."""
    try:
        premium_stats.set_enabled_provider(req.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"provider": req.provider}


@app.get("/api/data-source")
def data_source():
    """Transparency endpoint for the dataset used by the prediction engine."""
    dataset_path = DATA_DIR / "matches.csv"
    configured = []
    for env_name, label in [
        ("FOOTBALL_DATA_API_KEY", "football-data.org"),
        ("SPORTMONKS_API_KEY", "Sportmonks"),
        ("API_FOOTBALL_API_KEY", "API-Football"),
    ]:
        if os.environ.get(env_name):
            configured.append(label)

    return {
        # analyze_match currently predicts from the locally stored/trained dataset.
        # API providers can refresh/live/premium data but are not silently substituted
        # into the core prediction calculation.
        "prediction_source": "local",
        "prediction_source_label": "Local trained dataset",
        "dataset_available": dataset_path.exists(),
        "dataset_last_updated": (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(dataset_path.stat().st_mtime))
            if dataset_path.exists() else None
        ),
        "api_providers_configured": configured,
        "note": (
            "The match prediction is calculated from the local dataset and trained model. "
            "Configured APIs may be used for data refresh, live fixtures, or optional premium "
            "match statistics; they are not automatically substituted for the local prediction dataset."
        ),
    }


@app.get("/api/model/metrics")
def model_metrics():
    """Returns the training-time validation metrics for transparency."""
    import joblib
    metrics_path = ML_DIR / "models" / "metrics.joblib"
    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail="Model metrics not found — has the model been trained?")
    return joblib.load(metrics_path)
