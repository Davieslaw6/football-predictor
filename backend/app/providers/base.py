"""
Common interface for live football data providers.

Every provider (Sportmonks, API-Football, football-data.org) implements
this same shape, so the rest of the app can ask for "live fixtures" or
"live scores" without caring which provider actually answers — and so
providers can be toggled on/off independently without touching any
calling code.

A provider is "enabled" when the app owner has both (a) flipped it on in
the provider selection settings, AND (b) supplied a real API key via
environment variable. Missing a key never crashes anything — it just
means that provider reports itself unavailable and is skipped.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class NormalizedFixture:
    """A fixture/match in a shape that's the same regardless of which
    provider it came from, so the frontend never needs to know."""
    id: str
    source: str  # "sportmonks" | "api_football" | "football_data_org"
    league: str
    home_team: str
    away_team: str
    utc_date: str
    status: str  # "SCHEDULED" | "LIVE" | "FINISHED" | etc (normalized)
    home_score: int | None = None
    away_score: int | None = None
    minute: int | None = None  # only meaningful when status == "LIVE"


@dataclass
class ProviderStatus:
    key: str
    label: str
    enabled: bool           # toggled on by the user
    configured: bool        # has an API key set
    available: bool         # enabled AND configured AND last call (if any) succeeded
    last_error: str | None = None


class LiveDataProvider(ABC):
    key: str
    label: str

    @abstractmethod
    def is_configured(self) -> bool:
        """True if an API key is present for this provider."""
        ...

    @abstractmethod
    async def fetch_live_fixtures(self, competition: str | None = None) -> list[NormalizedFixture]:
        """Currently in-progress matches, with live scores/minute where available."""
        ...

    @abstractmethod
    async def fetch_upcoming_fixtures(self, competition: str | None = None) -> list[NormalizedFixture]:
        """Scheduled, not-yet-started matches."""
        ...
