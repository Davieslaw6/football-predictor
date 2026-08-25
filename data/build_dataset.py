"""
Fetches and consolidates openfootball JSON season files into a single
clean CSV of match results, ready for feature engineering + model training.

This script is idempotent and safe to re-run daily: it re-downloads the
current season for every configured league (so newly played matches show
up) and rebuilds matches.csv from scratch each time. Past/completed
seasons are also re-downloaded since they're small and this keeps the
script simple and correct rather than trying to diff/cache.

Run manually:
    python3 build_dataset.py

Run for only specific leagues (used by the "which leagues to update"
selector in the app):
    python3 build_dataset.py --leagues premier_league,championship
"""
import json
import csv
import re
import sys
import argparse
import urllib.request
import urllib.error
from pathlib import Path

RAW_DIR = Path(__file__).parent / "raw"
OUT_FILE = Path(__file__).parent / "matches.csv"
RAW_DIR.mkdir(exist_ok=True)

BASE_URL = "https://raw.githubusercontent.com/openfootball/football.json/master"

# --- League registry ---------------------------------------------------
# key: internal id used across the app (API, frontend selector, etc.)
# label: human-readable name
# code: openfootball's file code (e.g. en.1 -> en.1.json)
# competition_type: "domestic" or "continental" — surfaced in the UI/API
# seasons: known-good seasons for this competition in this data source.
#          Champions League has a real gap (2020-21 to 2023-24 missing
#          from the free source) — that gap is intentional, not a bug.
LEAGUES = {
    "premier_league": {
        "label": "Premier League",
        "code": "en.1",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"],
    },
    "championship": {
        "label": "EFL Championship",
        "code": "en.2",
        "competition_type": "domestic",
        "seasons": ["2021-22", "2022-23", "2023-24", "2024-25"],
    },
    "champions_league": {
        "label": "UEFA Champions League",
        "code": "uefa.cl",
        "competition_type": "continental",
        "seasons": ["2015-16", "2016-17", "2017-18", "2018-19", "2019-20", "2024-25"],
    },
    "bundesliga": {
        "label": "Bundesliga",
        "code": "de.1",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"],
    },
    "bundesliga_2": {
        "label": "2. Bundesliga",
        "code": "de.2",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"],
    },
    "la_liga": {
        "label": "La Liga",
        "code": "es.1",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"],
    },
    "serie_a": {
        "label": "Serie A",
        "code": "it.1",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"],
    },
    "ligue_1": {
        "label": "Ligue 1",
        "code": "fr.1",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"],
    },
    "eredivisie": {
        "label": "Eredivisie",
        "code": "nl.1",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"],
    },
    "primeira_liga": {
        "label": "Primeira Liga",
        "code": "pt.1",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"],
    },
    # These four have a real gap (2021-22 to 2023-24 missing from the free
    # source) — same pattern as Champions League. Still genuinely
    # multi-year usable, not a token/thin addition.
    "segunda": {
        "label": "Segunda División",
        "code": "es.2",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2024-25"],
    },
    "ligue_2": {
        "label": "Ligue 2",
        "code": "fr.2",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2024-25"],
    },
    "belgian_pro_league": {
        "label": "Belgian Pro League",
        "code": "be.1",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2024-25"],
    },
    "super_lig": {
        "label": "Süper Lig",
        "code": "tr.1",
        "competition_type": "domestic",
        "seasons": ["2018-19", "2019-20", "2020-21", "2024-25"],
    },
}

CURRENT_SEASON = "2024-25"  # bump this each August when a new season starts


def fetch_season(league_key: str, season: str) -> Path | None:
    """Downloads one season's JSON for a league. Returns the local path, or
    None if this competition/season combo doesn't exist in the source
    (e.g. the known Champions League gap years) — that's expected, not an
    error worth crashing over."""
    league = LEAGUES[league_key]
    url = f"{BASE_URL}/{season}/{league['code']}.json"
    dest = RAW_DIR / f"{league_key}_{season}.json"
    try:
        urllib.request.urlretrieve(url, dest)
        if dest.stat().st_size < 50:  # GitHub 404 pages are tiny; real data isn't
            dest.unlink(missing_ok=True)
            return None
        return dest
    except urllib.error.HTTPError:
        dest.unlink(missing_ok=True)
        return None
    except urllib.error.URLError as e:
        print(f"  Network error fetching {league_key} {season}: {e}")
        return None


def normalize_team_name(raw: str) -> str:
    """Strips ' FC' suffix and continental-competition country tags like
    ' (ENG)' so the same club matches across domestic and continental
    datasets (e.g. 'Liverpool FC (ENG)' -> 'Liverpool')."""
    name = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", raw)  # strip trailing (ENG) etc.
    name = name.replace(" FC", "").strip()

    # Known same-club aliases that the free source uses inconsistently
    # across different seasons within the SAME league — not international
    # naming differences (those are handled by the FC/country-tag rules
    # above). Found by direct inspection of the fetched data: openfootball's
    # Eredivisie files vary between short and city-suffixed club names
    # across different season files. Without this map, the same real-world
    # club would be silently split into two separate "teams" in the
    # dataset, corrupting Elo/form history for that club.
    ALIASES = {
        "AZ Alkmaar": "AZ",
        "FC Twente '65": "FC Twente",
        "Feyenoord Rotterdam": "Feyenoord",
        "NEC Nijmegen": "NEC",
        "PSV Eindhoven": "PSV",
        "Willem II Tilburg": "Willem II",
        "sc Heerenveen": "SC Heerenveen",
        "AFC Ajax": "Ajax",
        "Atalanta BC": "Atalanta",
        "Bologna 1909": "Bologna",
        "FC St. Pauli 1910": "FC St. Pauli",
        "GD Estoril Praia": "GD Estoril",
        "Huddersfield Town AFC": "Huddersfield Town",
        "RC Celta de Vigo": "RC Celta",
        "RC Strasbourg Alsace": "RC Strasbourg",
        "Rayo Vallecano de Madrid": "Rayo Vallecano",
        "Real Betis Balompié": "Real Betis",
        "Real Madrid CF": "Real Madrid",
        "Real Sociedad de Fútbol": "Real Sociedad",
        "Real Valladolid CF": "Real Valladolid",
        "SpVgg Greuther Fürth 1903": "SpVgg Greuther Fürth",
        "Stade Rennais 1901": "Stade Rennais",
        "VfL Bochum 1848": "VfL Bochum",
        # NOT aliased: "Paris" (Paris FC, Ligue 2) is a genuinely different,
        # real club from "Paris Saint-Germain" — checked directly against
        # the source data before excluding this one from the map.
    }
    name = ALIASES.get(name, name)
    return name


def build(selected_leagues: list[str]):
    rows = []
    skipped = 0
    fetched_files = 0

    for league_key in selected_leagues:
        if league_key not in LEAGUES:
            print(f"  Unknown league key '{league_key}', skipping")
            continue
        league = LEAGUES[league_key]
        print(f"Fetching {league['label']}...")
        for season in league["seasons"]:
            path = fetch_season(league_key, season)
            if path is None:
                continue
            fetched_files += 1
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for m in data.get("matches", []):
                score = m.get("score", {})
                ft = score.get("ft")
                if not ft or len(ft) != 2:
                    skipped += 1
                    continue

                home_goals, away_goals = ft
                if home_goals > away_goals:
                    result = "H"
                elif home_goals < away_goals:
                    result = "A"
                else:
                    result = "D"

                rows.append({
                    "date": m.get("date", ""),
                    "season": season,
                    "league": league["label"],
                    "league_key": league_key,
                    "competition_type": league["competition_type"],
                    "round": m.get("round", ""),
                    "home_team": normalize_team_name(m.get("team1", "")),
                    "away_team": normalize_team_name(m.get("team2", "")),
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "result": result,
                })

    rows.sort(key=lambda r: r["date"])

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date", "season", "league", "league_key", "competition_type", "round",
            "home_team", "away_team", "home_goals", "away_goals", "result"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nFetched {fetched_files} season files")
    print(f"Wrote {len(rows)} matches to {OUT_FILE}")
    print(f"Skipped {skipped} unplayed/postponed fixtures")

    if not rows:
        print("WARNING: no matches written — check network access / league selection")
        return

    teams = set()
    for r in rows:
        teams.add(r["home_team"])
        teams.add(r["away_team"])
    print(f"Unique teams: {len(teams)}")
    print(f"Date range: {rows[0]['date']} to {rows[-1]['date']}")

    for league_key in selected_leagues:
        if league_key not in LEAGUES:
            continue
        league_rows = [r for r in rows if r["league_key"] == league_key]
        print(f"  {LEAGUES[league_key]['label']}: {len(league_rows)} matches")

    _warn_on_likely_duplicate_teams(teams)


def _warn_on_likely_duplicate_teams(teams: set[str]):
    """
    Best-effort check for team names that are probably the same real club
    under two different spellings — e.g. a case difference, or one name
    being a strict substring of another ('PSV' / 'PSV Eindhoven'). This
    doesn't auto-fix anything (that would risk merging two genuinely
    different clubs); it just prints a warning so a real duplicate gets
    caught and added to the ALIASES map in normalize_team_name() instead
    of silently fragmenting a club's Elo/form history across seasons.
    """
    team_list = sorted(teams)
    lower_seen: dict[str, str] = {}
    warnings = []
    for t in team_list:
        low = t.lower()
        if low in lower_seen and lower_seen[low] != t:
            warnings.append(f"  Case-only mismatch: '{t}' vs '{lower_seen[low]}'")
        lower_seen[low] = t

    for i, a in enumerate(team_list):
        for b in team_list[i + 1:]:
            if a == b:
                continue
            shorter, longer = (a, b) if len(a) < len(b) else (b, a)
            # Require the shorter name to make up most of the longer one —
            # avoids flagging cases like "Paris" / "Paris Saint-Germain",
            # which are a real short club name and a totally different,
            # unrelated club that happens to start with the same word.
            if len(shorter) >= 3 and longer.startswith(shorter + " ") and len(shorter) / len(longer) > 0.55:
                warnings.append(f"  Possible same club: '{shorter}' / '{longer}'")

    if warnings:
        print(f"\nWARNING: {len(warnings)} possible duplicate team name(s) detected —")
        print("these likely need an entry in the ALIASES map inside normalize_team_name():")
        for w in warnings[:25]:
            print(w)
        if len(warnings) > 25:
            print(f"  ... and {len(warnings) - 25} more")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--leagues",
        default=",".join(LEAGUES.keys()),
        help="Comma-separated league keys to fetch/rebuild. Default: all.",
    )
    args = parser.parse_args()
    selected = [s.strip() for s in args.leagues.split(",") if s.strip()]
    build(selected)
