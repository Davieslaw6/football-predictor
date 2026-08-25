"""
Premium match-statistics provider.

The heuristic estimator in estimated_stats.py is the default and always
works, since it needs no API key. THIS module is the "real data" toggle
alternative: when enabled and given a working Sportmonks or API-Football
key with a plan that includes match statistics, it fetches actual
historical corners/shots-per-game averages for a team instead of the
heuristic estimate.

This is deliberately separate from the live-fixtures providers in
providers/ — a user might want live scores from one provider and premium
match stats from another, or neither, independently.

Toggle state is persisted the same way as the other provider toggles.
Both Sportmonks and API-Football's basic plans do NOT include historical
team statistics endpoints (that's typically a higher tier) — this module
does not attempt to guess which plan you're on; it just tries the request
and reports a clear per-provider error if your plan doesn't include it,
the same honest-degradation pattern used everywhere else in this app.
"""
from __future__ import annotations
import os
import json
import httpx
from pathlib import Path

TOGGLE_FILE = Path(__file__).parent.parent.parent / "data" / "premium_stats_selection.json"


def _load_enabled() -> str | None:
    """Returns the enabled premium stats provider key, or None if disabled
    (the default — the heuristic estimate is used instead)."""
    if TOGGLE_FILE.exists():
        try:
            data = json.loads(TOGGLE_FILE.read_text())
            return data.get("provider")  # "sportmonks" | "api_football" | None
        except json.JSONDecodeError:
            pass
    return None


def _save_enabled(provider: str | None):
    TOGGLE_FILE.parent.mkdir(exist_ok=True)
    TOGGLE_FILE.write_text(json.dumps({"provider": provider}))


def get_status() -> dict:
    enabled_provider = _load_enabled()
    sportmonks_key = bool(os.environ.get("SPORTMONKS_API_KEY", ""))
    api_football_key = bool(os.environ.get("API_FOOTBALL_API_KEY", ""))
    return {
        "enabled_provider": enabled_provider,
        "options": [
            {"key": "sportmonks", "label": "Sportmonks", "configured": sportmonks_key},
            {"key": "api_football", "label": "API-Football", "configured": api_football_key},
        ],
    }


def set_enabled_provider(provider: str | None):
    if provider not in (None, "sportmonks", "api_football"):
        raise ValueError(f"Unknown premium stats provider: {provider}")
    _save_enabled(provider)


async def fetch_team_match_stats(team_name: str) -> dict | None:
    """
    Attempts to fetch real season-average corners/shots for a team from
    whichever premium provider is currently enabled. Returns None if no
    provider is enabled (caller should fall back to the heuristic
    estimate), or a dict with an "error" key if enabled but the call
    failed (bad key, plan doesn't include this data, network issue) —
    callers should also fall back to the heuristic estimate in that case,
    never crash the analysis.
    """
    provider = _load_enabled()
    if provider is None:
        return None

    if provider == "sportmonks":
        return await _fetch_sportmonks_team_stats(team_name)
    elif provider == "api_football":
        return await _fetch_api_football_team_stats(team_name)
    return None


async def _fetch_sportmonks_team_stats(team_name: str) -> dict:
    api_key = os.environ.get("SPORTMONKS_API_KEY", "")
    if not api_key:
        return {"error": "SPORTMONKS_API_KEY not set", "source": "sportmonks"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            search_resp = await client.get(
                "https://api.sportmonks.com/v3/football/teams/search",
                params={"api_token": api_key, "name": team_name},
            )
            search_resp.raise_for_status()
            teams = search_resp.json().get("data", [])
            if not teams:
                return {"error": f"Team '{team_name}' not found on Sportmonks", "source": "sportmonks"}
            team_id = teams[0]["id"]

            stats_resp = await client.get(
                f"https://api.sportmonks.com/v3/football/teams/{team_id}",
                params={"api_token": api_key, "include": "statistics"},
            )
            stats_resp.raise_for_status()
            # NOTE: exact statistics response shape is unverified against a
            # live account with a stats-tier plan — same caveat as
            # providers/sportmonks.py. This will very likely need a small
            # field-mapping adjustment once tested against real data.
            return {
                "source": "sportmonks",
                "raw": stats_resp.json().get("data", {}),
                "note": "Field mapping unverified — check against your actual plan's response shape.",
            }
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            return {"error": "Sportmonks key invalid or plan doesn't include team statistics", "source": "sportmonks"}
        return {"error": f"Sportmonks error: {e.response.status_code}", "source": "sportmonks"}
    except httpx.RequestError as e:
        return {"error": f"Could not reach Sportmonks: {e}", "source": "sportmonks"}


async def _fetch_api_football_team_stats(team_name: str) -> dict:
    api_key = os.environ.get("API_FOOTBALL_API_KEY", "")
    use_rapidapi = os.environ.get("API_FOOTBALL_USE_RAPIDAPI", "").lower() == "true"
    if not api_key:
        return {"error": "API_FOOTBALL_API_KEY not set", "source": "api_football"}

    base_url = "https://api-football-v1.p.rapidapi.com/v3" if use_rapidapi else "https://v3.football.api-sports.io"
    headers = (
        {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
        if use_rapidapi else {"x-apisports-key": api_key}
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            search_resp = await client.get(f"{base_url}/teams", headers=headers, params={"search": team_name})
            search_resp.raise_for_status()
            teams = search_resp.json().get("response", [])
            if not teams:
                return {"error": f"Team '{team_name}' not found on API-Football", "source": "api_football"}
            team_id = teams[0]["team"]["id"]

            # api-football's /teams/statistics needs a league+season param;
            # a real integration would resolve this from the league
            # selection elsewhere in the app rather than guessing.
            return {
                "error": "API-Football team statistics require a league+season parameter — "
                         "wire this to the app's league selection to complete this integration.",
                "source": "api_football",
                "team_id": team_id,
            }
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            return {"error": "API-Football key invalid or plan doesn't include statistics", "source": "api_football"}
        return {"error": f"API-Football error: {e.response.status_code}", "source": "api_football"}
    except httpx.RequestError as e:
        return {"error": f"Could not reach API-Football: {e}", "source": "api_football"}
