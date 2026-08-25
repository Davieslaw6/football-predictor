"""
Sportmonks Football API provider.

Docs: https://docs.sportmonks.com/football/
Requires a Sportmonks API token (env var SPORTMONKS_API_KEY). Sportmonks is
a paid service — see README for current pricing — with a limited free plan
covering only the Danish Superliga and Scottish Premiership, which is not
useful for this app's leagues (Premier League, Championship, Champions
League) unless you're on a paid plan that includes them.

This client only calls two read-only endpoints (live scores + fixtures by
date range) — enough for the "live updates" feature. It does not write
anything to your Sportmonks account.

IMPORTANT — response field mapping is UNVERIFIED against a live account:
Sportmonks' full v3 field-level docs sit behind an authenticated developer
portal, and I built this client's response parsing (_normalize below) from
publicly available fragments and general v3 API conventions, not by
calling the live endpoint with a real key. The endpoint paths and general
request shape (GET /livescores, /fixtures, api_token auth, include=...
parameter) are correct and documented publicly. The exact JSON field names
inside the response (e.g. state.short_name, scores[].description) may be
slightly off and need a one-time check against a real response once you
have an API key. If fields come back as "Unknown" or None, open your
Sportmonks dashboard's API tester, hit /livescores once, and adjust
_normalize() below to match what actually comes back — the surrounding
provider/toggle/fallback system does not need to change either way.
"""
from __future__ import annotations
import os
import httpx

from .base import LiveDataProvider, NormalizedFixture

BASE_URL = "https://api.sportmonks.com/v3/football"

STATUS_MAP = {
    "NS": "SCHEDULED",
    "LIVE": "LIVE",
    "HT": "LIVE",
    "FT": "FINISHED",
    "AET": "FINISHED",
    "PEN": "FINISHED",
    "POSTP": "POSTPONED",
    "CANC": "CANCELLED",
}


class SportmonksProvider(LiveDataProvider):
    key = "sportmonks"
    label = "Sportmonks"

    def __init__(self):
        self.api_key = os.environ.get("SPORTMONKS_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _normalize(self, raw: dict) -> NormalizedFixture:
        try:
            state = ((raw.get("state") or {}).get("short_name")) or "NS"
            participants = raw.get("participants", []) or []
            home = next((p for p in participants if (p.get("meta") or {}).get("location") == "home"), {})
            away = next((p for p in participants if (p.get("meta") or {}).get("location") == "away"), {})

            scores = raw.get("scores", []) or []
            home_score = away_score = None
            for s in scores:
                if s.get("description") == "CURRENT":
                    side = (s.get("score") or {}).get("participant")
                    if side == "home":
                        home_score = (s.get("score") or {}).get("goals")
                    elif side == "away":
                        away_score = (s.get("score") or {}).get("goals")

            periods = raw.get("periods")
            minute = periods.get("minutes") if isinstance(periods, dict) else None

            return NormalizedFixture(
                id=str(raw.get("id", "")),
                source=self.key,
                league=(raw.get("league") or {}).get("name", "Unknown"),
                home_team=home.get("name", "Unknown"),
                away_team=away.get("name", "Unknown"),
                utc_date=raw.get("starting_at", ""),
                status=STATUS_MAP.get(state, state),
                home_score=home_score,
                away_score=away_score,
                minute=minute,
            )
        except Exception:
            # A field-mapping mismatch (see module docstring) should degrade
            # to an "unparseable but present" fixture, never a 500 error.
            return NormalizedFixture(
                id=str(raw.get("id", "unknown")),
                source=self.key,
                league="Unknown",
                home_team="Unparsed fixture — check Sportmonks field mapping",
                away_team="",
                utc_date="",
                status="UNKNOWN",
            )

    async def _get(self, path: str, params: dict | None = None) -> list[dict]:
        params = dict(params or {})
        params["api_token"] = self.api_key
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BASE_URL}{path}", params=params)
            resp.raise_for_status()
            data = resp.json()
        return data.get("data", [])

    async def fetch_live_fixtures(self, competition: str | None = None) -> list[NormalizedFixture]:
        raw = await self._get("/livescores", {"include": "participants;scores;state;league;periods"})
        return [self._normalize(r) for r in raw]

    async def fetch_upcoming_fixtures(self, competition: str | None = None) -> list[NormalizedFixture]:
        raw = await self._get("/fixtures", {
            "include": "participants;scores;state;league",
            "filters": "fixtureStates:1",  # 1 = Not Started, per Sportmonks state IDs
        })
        return [self._normalize(r) for r in raw]
