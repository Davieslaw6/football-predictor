"""
Feature engineering for football match prediction.

Computes, for every match in chronological order, features that were
KNOWN BEFORE KICKOFF ONLY (no leakage of the match's own result):
  - Elo ratings for both teams (updated after each match)
  - Rolling form (points per game, goals for/against) over last N matches
  - Home/away specific form splits
  - Head-to-head record between the two teams
  - Rest days since each team's last match (fatigue proxy)
  - News/availability adjustment (squad strength penalty), if provided
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from collections import defaultdict, deque
from datetime import datetime

FORM_WINDOW = 6          # matches for rolling form
ELO_K = 24                # Elo update speed
ELO_HOME_ADV = 60          # Elo points added to home team for expectancy
ELO_BASE = 1500


def _elo_expected(r_a: float, r_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400))


def build_features(matches: pd.DataFrame, news_penalties: dict[str, float] | None = None) -> pd.DataFrame:
    """
    matches: DataFrame with columns
        date, home_team, away_team, home_goals, away_goals, result, league
        sorted ascending by date.
    news_penalties: optional dict {team_name: strength_penalty 0-1}
        e.g. {"Arsenal": 0.15} means Arsenal is missing ~15% of squad strength
        (key injuries/suspensions). Applied only as a live-analysis time
        feature, not baked into historical training rows (those default to 0
        since we don't have historical injury data for this dataset).

    Returns matches with added feature columns, all computed using only
    information available strictly BEFORE that match's kickoff.
    """
    df = matches.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    elo = defaultdict(lambda: ELO_BASE)
    # rolling results, most recent first when popped
    recent_all = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    recent_home = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    recent_away = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    goals_for = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    goals_against = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    streak = defaultdict(int)  # positive = win streak, negative = loss streak, 0 = neutral/draw-broken
    last_played = {}  # team -> last match date
    h2h = defaultdict(lambda: deque(maxlen=10))  # (home,away) sorted key -> results

    feat_rows = []

    for _, row in df.iterrows():
        home, away = row["home_team"], row["away_team"]
        date = row["date"]

        # --- Elo (pre-match) ---
        elo_home = elo[home]
        elo_away = elo[away]
        elo_diff = elo_home - elo_away
        exp_home = _elo_expected(elo_home + ELO_HOME_ADV, elo_away)

        # --- Rolling form (pre-match), points per game & goal diff per game ---
        def form_stats(dq: deque) -> tuple[float, float]:
            if not dq:
                return 1.0, 0.0  # neutral prior: 1 ppg, 0 gd
            pts = sum(r[0] for r in dq) / len(dq)
            gd = sum(r[1] for r in dq) / len(dq)
            return pts, gd

        home_form_pts, home_form_gd = form_stats(recent_all[home])
        away_form_pts, away_form_gd = form_stats(recent_all[away])
        home_home_pts, home_home_gd = form_stats(recent_home[home])
        away_away_pts, away_away_gd = form_stats(recent_away[away])

        # --- Rolling goals for/against per game (for Poisson goals model) ---
        def avg_or_default(dq: deque, default: float) -> float:
            return (sum(dq) / len(dq)) if dq else default

        home_gf_avg = avg_or_default(goals_for[home], 1.3)
        home_ga_avg = avg_or_default(goals_against[home], 1.3)
        away_gf_avg = avg_or_default(goals_for[away], 1.1)
        away_ga_avg = avg_or_default(goals_against[away], 1.1)

        # --- Rest days (fatigue proxy) ---
        home_rest = (date - last_played[home]).days if home in last_played else 10
        away_rest = (date - last_played[away]).days if away in last_played else 10

        # --- Head-to-head (pre-match) ---
        key = tuple(sorted([home, away]))
        h2h_dq = h2h[key]
        if h2h_dq:
            home_h2h_wins = sum(1 for r in h2h_dq if r == home)
            away_h2h_wins = sum(1 for r in h2h_dq if r == away)
            h2h_matches = len(h2h_dq)
        else:
            home_h2h_wins = away_h2h_wins = h2h_matches = 0

        # --- News-driven availability penalty (live-analysis only; 0 for historical training) ---
        pen = news_penalties or {}
        home_penalty = pen.get(home, 0.0)
        away_penalty = pen.get(away, 0.0)

        # --- Current win/loss streak (pre-match) — more informative than
        # rolling points average alone, since a team on a 5-game win streak
        # plays differently than one that's 3W-2D-0L in the same window ---
        home_streak = streak[home]
        away_streak = streak[away]

        feat_rows.append({
            "date": date,
            "home_team": home,
            "away_team": away,
            "league": row.get("league", ""),
            "elo_home": elo_home,
            "elo_away": elo_away,
            "elo_diff": elo_diff,
            "elo_exp_home": exp_home,
            "home_form_pts": home_form_pts,
            "away_form_pts": away_form_pts,
            "home_form_gd": home_form_gd,
            "away_form_gd": away_form_gd,
            "home_home_pts": home_home_pts,
            "away_away_pts": away_away_pts,
            "home_home_gd": home_home_gd,
            "away_away_gd": away_away_gd,
            "home_gf_avg": home_gf_avg,
            "home_ga_avg": home_ga_avg,
            "away_gf_avg": away_gf_avg,
            "away_ga_avg": away_ga_avg,
            "home_rest_days": min(home_rest, 21),
            "away_rest_days": min(away_rest, 21),
            "home_streak": max(-5, min(5, home_streak)),
            "away_streak": max(-5, min(5, away_streak)),
            "h2h_home_wins": home_h2h_wins,
            "h2h_away_wins": away_h2h_wins,
            "h2h_matches": h2h_matches,
            "home_avail_penalty": home_penalty,
            "away_avail_penalty": away_penalty,
            # targets (only valid for historical rows with a played result)
            "home_goals": row.get("home_goals"),
            "away_goals": row.get("away_goals"),
            "result": row.get("result"),
        })

        # --- Update state AFTER recording pre-match features ---
        hg, ag = row.get("home_goals"), row.get("away_goals")
        if pd.notna(hg) and pd.notna(ag):
            hg, ag = int(hg), int(ag)
            if hg > ag:
                res_h, res_a = 3, 0
                h2h[key].append(home)
                streak[home] = max(1, streak[home] + 1)
                streak[away] = min(-1, streak[away] - 1)
            elif hg < ag:
                res_h, res_a = 0, 3
                h2h[key].append(away)
                streak[home] = min(-1, streak[home] - 1)
                streak[away] = max(1, streak[away] + 1)
            else:
                res_h, res_a = 1, 1
                streak[home] = 0
                streak[away] = 0

            recent_all[home].append((res_h, hg - ag))
            recent_all[away].append((res_a, ag - hg))
            recent_home[home].append((res_h, hg - ag))
            recent_away[away].append((res_a, ag - hg))
            goals_for[home].append(hg)
            goals_against[home].append(ag)
            goals_for[away].append(ag)
            goals_against[away].append(hg)

            # Elo update with margin-of-victory scaling: a standard,
            # well-established refinement over vanilla Elo (used by e.g.
            # FiveThirtyEight's SPI) — a 4-0 win moves rating more than a
            # 1-0 win against the same opponent, since it's stronger
            # evidence of a real strength gap rather than a close margin.
            actual_home = 1.0 if hg > ag else (0.5 if hg == ag else 0.0)
            goal_margin = abs(hg - ag)
            mov_multiplier = 1.0 if goal_margin <= 1 else (1.0 + 0.30 * (goal_margin - 1)) ** 0.5
            elo[home] = elo_home + ELO_K * mov_multiplier * (actual_home - exp_home)
            elo[away] = elo_away + ELO_K * mov_multiplier * ((1 - actual_home) - (1 - exp_home))

            last_played[home] = date
            last_played[away] = date

    result_df = pd.DataFrame(feat_rows)

    # Live end-of-data state for every team — used by get_team_snapshot()
    # to give live/current-day match analysis each team's TRUE latest
    # rating (as of right now, after their most recent match), rather
    # than their pre-match rating going INTO their last match, which is
    # one match's worth of Elo/form movement stale.
    def _form_stats(dq: deque) -> tuple[float, float]:
        if not dq:
            return 1.0, 0.0
        pts = sum(r[0] for r in dq) / len(dq)
        gd = sum(r[1] for r in dq) / len(dq)
        return pts, gd

    all_teams = set(elo.keys())
    live_state = {}
    for team in all_teams:
        form_pts, form_gd = _form_stats(recent_all[team])
        gf_avg = (sum(goals_for[team]) / len(goals_for[team])) if goals_for[team] else 1.2
        ga_avg = (sum(goals_against[team]) / len(goals_against[team])) if goals_against[team] else 1.2
        live_state[team] = {
            "elo": elo[team],
            "form_pts": form_pts,
            "form_gd": form_gd,
            "gf_avg": gf_avg,
            "ga_avg": ga_avg,
            "streak": max(-5, min(5, streak[team])),
        }

    result_df.attrs["live_state"] = live_state
    return result_df


def get_team_snapshot(features_df: pd.DataFrame, team: str) -> dict:
    """
    Latest known Elo/form/streak snapshot for a team, for live match
    analysis. Prefers the true current state attached via
    build_features()'s .attrs (accurate as of right now, including their
    most recent match's result) — falls back to the old pre-match-of-last-
    row approach only if that live state isn't available, e.g. when
    features_df was loaded fresh from a saved CSV that doesn't carry
    DataFrame .attrs across a save/load round trip.
    """
    live_state = features_df.attrs.get("live_state")
    if live_state and team in live_state:
        return live_state[team]

    team_rows = features_df[
        (features_df["home_team"] == team) | (features_df["away_team"] == team)
    ].sort_values("date")
    if team_rows.empty:
        return {"elo": ELO_BASE, "form_pts": 1.0, "form_gd": 0.0, "gf_avg": 1.2, "ga_avg": 1.2, "streak": 0}
    last = team_rows.iloc[-1]
    if last["home_team"] == team:
        return {
            "elo": last["elo_home"], "form_pts": last["home_form_pts"], "form_gd": last["home_form_gd"],
            "gf_avg": last["home_gf_avg"], "ga_avg": last["home_ga_avg"], "streak": last.get("home_streak", 0),
        }
    else:
        return {
            "elo": last["elo_away"], "form_pts": last["away_form_pts"], "form_gd": last["away_form_gd"],
            "gf_avg": last["away_gf_avg"], "ga_avg": last["away_ga_avg"], "streak": last.get("away_streak", 0),
        }
