"""
Registry for live data providers. Handles:
  - which providers exist
  - which are toggled on/off (persisted to disk, like the league selection)
  - aggregating results across all enabled+configured providers
  - reporting per-provider status so the UI can show "Sportmonks: needs API key"
    vs "Sportmonks: disabled" vs "Sportmonks: active" distinctly

Providers are independent: disabling or misconfiguring one never affects
the others. If a provider is enabled but errors on a live call (bad key,
rate limit, network issue), that single provider's error is captured and
the rest still return normally — a partial-provider failure is never a
whole-endpoint failure.
"""
from __future__ import annotations
import json
from pathlib import Path

from .base import LiveDataProvider, NormalizedFixture, ProviderStatus
from .sportmonks import SportmonksProvider
from .api_football import ApiFootballProvider
from .football_data_org import FootballDataOrgProvider

SELECTION_FILE = Path(__file__).parent.parent.parent.parent / "data" / "provider_selection.json"

ALL_PROVIDERS: dict[str, LiveDataProvider] = {
    "sportmonks": SportmonksProvider(),
    "api_football": ApiFootballProvider(),
    "football_data_org": FootballDataOrgProvider(),
}


def _load_enabled() -> set[str]:
    if SELECTION_FILE.exists():
        try:
            return set(json.loads(SELECTION_FILE.read_text())["enabled"])
        except (json.JSONDecodeError, KeyError):
            pass
    return set(ALL_PROVIDERS.keys())  # default: all enabled (each still needs its own key)


def _save_enabled(enabled: set[str]):
    SELECTION_FILE.parent.mkdir(exist_ok=True)
    SELECTION_FILE.write_text(json.dumps({"enabled": sorted(enabled)}))


def get_provider_statuses() -> list[ProviderStatus]:
    enabled = _load_enabled()
    statuses = []
    for key, provider in ALL_PROVIDERS.items():
        is_enabled = key in enabled
        is_configured = provider.is_configured()
        statuses.append(ProviderStatus(
            key=key,
            label=provider.label,
            enabled=is_enabled,
            configured=is_configured,
            available=is_enabled and is_configured,
        ))
    return statuses


def set_provider_enabled(key: str, enabled: bool):
    if key not in ALL_PROVIDERS:
        raise ValueError(f"Unknown provider: {key}")
    current = _load_enabled()
    if enabled:
        current.add(key)
    else:
        current.discard(key)
    _save_enabled(current)


async def fetch_live_fixtures_all(competition: str | None = None) -> dict:
    """
    Queries every enabled+configured provider for live fixtures, in
    parallel-ish (sequential is fine here — this isn't a hot path), and
    returns both the combined fixture list and a per-provider status/error
    report so the UI can show exactly what happened with each source.
    """
    import asyncio

    enabled = _load_enabled()
    active = [(key, p) for key, p in ALL_PROVIDERS.items() if key in enabled and p.is_configured()]

    if not active:
        return {
            "fixtures": [],
            "provider_results": [
                {
                    "provider": key,
                    "label": p.label,
                    "enabled": key in enabled,
                    "configured": p.is_configured(),
                    "error": None if p.is_configured() else "No API key configured",
                }
                for key, p in ALL_PROVIDERS.items()
            ],
        }

    async def _fetch_one(key: str, provider: LiveDataProvider):
        try:
            fixtures = await provider.fetch_live_fixtures(competition)
            return key, fixtures, None
        except Exception as e:
            return key, [], str(e)

    results = await asyncio.gather(*[_fetch_one(k, p) for k, p in active])

    all_fixtures: list[NormalizedFixture] = []
    provider_results = []
    for key, fixtures, error in results:
        all_fixtures.extend(fixtures)
        provider_results.append({
            "provider": key,
            "label": ALL_PROVIDERS[key].label,
            "enabled": True,
            "configured": True,
            "fixture_count": len(fixtures),
            "error": error,
        })

    # Include disabled/unconfigured providers in the report too, for visibility
    for key, p in ALL_PROVIDERS.items():
        if key not in enabled or not p.is_configured():
            provider_results.append({
                "provider": key,
                "label": p.label,
                "enabled": key in enabled,
                "configured": p.is_configured(),
                "fixture_count": 0,
                "error": None if p.is_configured() else "No API key configured",
            })

    return {
        "fixtures": [vars(f) for f in all_fixtures],
        "provider_results": provider_results,
    }
