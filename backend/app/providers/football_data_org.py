"""
football-data.org provider — the free-tier provider already used elsewhere
in this app for historical training data, now also wrapped to match the
same live-fixture interface as Sportmonks and API-Football so all three
can be toggled through one consistent system.

Docs: https://www.football-data.org/documentation/quickstart
Free tier: 10 requests/minute, top-tier competitions only, no true live
in-play scores (fixtures + results, refreshed periodically) — the other
two providers are the ones that give real live in-play data if you need
it; this one is included because it's free and already integrated.
"""
from __future__ import annotations
import os
import httpx

from .base import LiveDataProvider, NormalizedFixture

BASE_URL = "https://api.football-data.org/v4"

STATUS_MAP = {
    "SCHEDULED": "SCHEDULED", "TIMED": "SCHEDULED",
    "IN_PLAY": "LIVE", "PAUSED": "LIVE",
    "FINISHED": "FINISHED",
    "POSTPONED": "POSTPONED", "SUSPENDED": "SUSPENDED", "CANCELLED": "CANCELLED",
}


class FootballDataOrgProvider(LiveDataProvider):
    key = "football_data_org"
    label = "football-data.org"

    def __init__(self):
        self.api_key = os.environ.get("FOOTBALL_DATA_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _normalize(self, raw: dict) -> NormalizedFixture:
        try:
            score = raw.get("score", {}).get("fullTime", {})
            return NormalizedFixture(
                id=str(raw.get("id", "")),
                source=self.key,
                league=(raw.get("competition") or {}).get("name", "Unknown"),
                home_team=(raw.get("homeTeam") or {}).get("name", "Unknown"),
                away_team=(raw.get("awayTeam") or {}).get("name", "Unknown"),
                utc_date=raw.get("utcDate", ""),
                status=STATUS_MAP.get(raw.get("status", "SCHEDULED"), "SCHEDULED"),
                home_score=score.get("home"),
                away_score=score.get("away"),
                minute=raw.get("minute"),
            )
        except Exception:
            return NormalizedFixture(
                id=str(raw.get("id", "unknown")),
                source=self.key,
                league="Unknown",
                home_team="Unparsed fixture",
                away_team="",
                utc_date="",
                status="UNKNOWN",
            )

    async def _get(self, path: str, params: dict | None = None) -> list[dict]:
        headers = {"X-Auth-Token": self.api_key}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BASE_URL}{path}", headers=headers, params=params or {})
            resp.raise_for_status()
            data = resp.json()
        return data.get("matches", [])

    async def fetch_live_fixtures(self, competition: str | None = None) -> list[NormalizedFixture]:
        comp = competition or "PL"
        raw = await self._get(f"/competitions/{comp}/matches", {"status": "IN_PLAY"})
        return [self._normalize(r) for r in raw]

    async def fetch_upcoming_fixtures(self, competition: str | None = None) -> list[NormalizedFixture]:
        comp = competition or "PL"
        raw = await self._get(f"/competitions/{comp}/matches", {"status": "SCHEDULED"})
        return [self._normalize(r) for r in raw]
