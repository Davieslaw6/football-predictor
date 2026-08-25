"""
API-Football provider (api-sports.io / RapidAPI).

Docs: https://www.api-football.com/documentation-v3
Supports two auth modes depending on where you subscribed:
  - Direct at api-sports.io: header "x-apisports-key: <key>"
  - Via RapidAPI: headers "X-RapidAPI-Key" + "X-RapidAPI-Host"
Set API_FOOTBALL_API_KEY, and optionally API_FOOTBALL_USE_RAPIDAPI=true if
you subscribed through RapidAPI rather than directly.

Free tier exists (100 requests/day at time of writing) which is enough for
occasional manual testing but not for continuous live-score polling — see
README for current pricing tiers.

This client's request/response shape (GET /fixtures?live=all, the
response.fixture / response.teams / response.goals structure) matches
API-Football's v3 documentation and multiple independent third-party
integration guides — this one is on firmer ground than the Sportmonks
client's field mapping, but you should still sanity-check your first real
response, since providers do change fields between versions.
"""
from __future__ import annotations
import os
import httpx

from .base import LiveDataProvider, NormalizedFixture

DIRECT_BASE_URL = "https://v3.football.api-sports.io"
RAPIDAPI_BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"
RAPIDAPI_HOST = "api-football-v1.p.rapidapi.com"

STATUS_MAP = {
    "TBD": "SCHEDULED", "NS": "SCHEDULED",
    "1H": "LIVE", "HT": "LIVE", "2H": "LIVE", "ET": "LIVE", "P": "LIVE", "BT": "LIVE",
    "FT": "FINISHED", "AET": "FINISHED", "PEN": "FINISHED",
    "SUSP": "SUSPENDED", "INT": "SUSPENDED",
    "PST": "POSTPONED", "CANC": "CANCELLED", "ABD": "CANCELLED", "AWD": "FINISHED", "WO": "FINISHED",
}


class ApiFootballProvider(LiveDataProvider):
    key = "api_football"
    label = "API-Football"

    def __init__(self):
        self.api_key = os.environ.get("API_FOOTBALL_API_KEY", "")
        self.use_rapidapi = os.environ.get("API_FOOTBALL_USE_RAPIDAPI", "").lower() == "true"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict:
        if self.use_rapidapi:
            return {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": RAPIDAPI_HOST}
        return {"x-apisports-key": self.api_key}

    def _base_url(self) -> str:
        return RAPIDAPI_BASE_URL if self.use_rapidapi else DIRECT_BASE_URL

    def _normalize(self, raw: dict) -> NormalizedFixture:
        try:
            fixture = raw.get("fixture", {})
            league = raw.get("league", {})
            teams = raw.get("teams", {})
            goals = raw.get("goals", {})
            status = fixture.get("status", {})

            return NormalizedFixture(
                id=str(fixture.get("id", "")),
                source=self.key,
                league=league.get("name", "Unknown"),
                home_team=(teams.get("home") or {}).get("name", "Unknown"),
                away_team=(teams.get("away") or {}).get("name", "Unknown"),
                utc_date=fixture.get("date", ""),
                status=STATUS_MAP.get(status.get("short", "NS"), "SCHEDULED"),
                home_score=goals.get("home"),
                away_score=goals.get("away"),
                minute=status.get("elapsed"),
            )
        except Exception:
            return NormalizedFixture(
                id=str((raw.get("fixture") or {}).get("id", "unknown")),
                source=self.key,
                league="Unknown",
                home_team="Unparsed fixture",
                away_team="",
                utc_date="",
                status="UNKNOWN",
            )

    async def _get(self, path: str, params: dict | None = None) -> list[dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self._base_url()}{path}", headers=self._headers(), params=params or {}
            )
            resp.raise_for_status()
            data = resp.json()
        return data.get("response", [])

    async def fetch_live_fixtures(self, competition: str | None = None) -> list[NormalizedFixture]:
        params = {"live": "all"}
        raw = await self._get("/fixtures", params)
        return [self._normalize(r) for r in raw]

    async def fetch_upcoming_fixtures(self, competition: str | None = None) -> list[NormalizedFixture]:
        params = {"next": "20"}
        if competition:
            params["league"] = competition
        raw = await self._get("/fixtures", params)
        return [self._normalize(r) for r in raw]
