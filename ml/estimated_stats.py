"""
Estimated match statistics: corners and shots per team.

IMPORTANT — READ BEFORE USING THIS MODULE'S OUTPUT AS A "PREDICTION":

This is a HEURISTIC ESTIMATE, not a trained, validated model like the 1X2
or goals-market predictions elsewhere in this app. The historical dataset
this app uses (openfootball) contains only match results — final score,
date, teams. It does NOT contain corners, shots, or any other in-match
event data. No free source I found provides multi-year historical
corners/shots data; that's paid-tier data (Sportmonks, API-Football,
Opta/StatsBomb-derived products).

What this module does instead: it derives a plausible estimate from each
team's attacking output (goals scored/conceded, which the model DOES have
real historical data for) using published real-world relationships between
goal-scoring intensity and corners/shots — teams that score/concede more
also generate/concede more shots and corners, a relationship documented in
sports analytics research (see README for the specific sources cited when
this was built). The baseline rates used below (~5.1 corners per team per
match, ~12-13 shots per team per match) are real published averages, not
invented numbers.

This is NOT the same as a model trained on and validated against actual
historical corners/shots outcomes — there IS no ground truth in this
dataset to validate against, so there is no accuracy/log-loss/Brier score
reported for this module, unlike every other prediction in this app. Every
API response and UI surface using this data says so explicitly.

If you enable a premium data provider (Sportmonks or API-Football) with a
plan that includes match statistics, `premium_stats.py` can supply REAL
historical corners/shots instead of this estimate — see that module and
the "Match Statistics Provider" toggle in the app.
"""
from __future__ import annotations

# Published real-world baselines (see module docstring for context):
# ~5.13 corners per team per match (BeSoccer analysis of EPL 2010/11,
# corroborated by FootyStats' 8-11 total corners per match across leagues),
# ~12-13 shots per team per match (typical across top-5 European leagues
# per multiple sports-analytics studies).
BASELINE_CORNERS_PER_TEAM = 5.1
BASELINE_SHOTS_PER_TEAM = 12.5

# How strongly attacking output (goals for/against rate) shifts the
# estimate away from the league baseline. Deliberately conservative —
# this is a heuristic, not a fitted coefficient, so it shouldn't swing
# wildly based on a small sample of recent goals.
ATTACK_SENSITIVITY = 0.35


def estimate_match_stats(
    home_gf_avg: float, home_ga_avg: float,
    away_gf_avg: float, away_ga_avg: float,
    league_avg_home_goals: float, league_avg_away_goals: float,
) -> dict:
    """
    Estimates corners and shots for both teams from their recent
    goal-scoring rates relative to league average. A team that scores
    more than average is assumed to also generate more shots/corners than
    average (and a team that concedes more than average is assumed to
    concede more shots/corners than average too) — see module docstring
    for why this is a defensible heuristic, not a fabricated number.
    """
    def attack_ratio(gf: float, league_avg: float) -> float:
        if league_avg <= 0:
            return 1.0
        return gf / league_avg

    def defense_ratio(ga: float, league_avg: float) -> float:
        if league_avg <= 0:
            return 1.0
        return ga / league_avg

    home_attack = attack_ratio(home_gf_avg, league_avg_home_goals)
    home_concede = defense_ratio(home_ga_avg, league_avg_away_goals)
    away_attack = attack_ratio(away_gf_avg, league_avg_away_goals)
    away_concede = defense_ratio(away_ga_avg, league_avg_home_goals)

    # A team's estimated attacking-stat output scales with its own attack
    # strength AND the opponent's defensive weakness (how much they concede).
    def scaled(base: float, own_attack: float, opp_concede: float) -> float:
        factor = 1.0 + ATTACK_SENSITIVITY * ((own_attack - 1.0) + (opp_concede - 1.0))
        return max(base * 0.5, base * factor)  # floor at half baseline, avoid absurd low estimates

    home_corners = scaled(BASELINE_CORNERS_PER_TEAM, home_attack, away_concede)
    away_corners = scaled(BASELINE_CORNERS_PER_TEAM, away_attack, home_concede)
    home_shots = scaled(BASELINE_SHOTS_PER_TEAM, home_attack, away_concede)
    away_shots = scaled(BASELINE_SHOTS_PER_TEAM, away_attack, home_concede)

    return {
        "home_corners_estimate": round(home_corners, 1),
        "away_corners_estimate": round(away_corners, 1),
        "total_corners_estimate": round(home_corners + away_corners, 1),
        "home_shots_estimate": round(home_shots, 1),
        "away_shots_estimate": round(away_shots, 1),
        "total_shots_estimate": round(home_shots + away_shots, 1),
        "is_validated_prediction": False,
        "methodology_note": (
            "Heuristic estimate derived from each team's goal-scoring rate relative "
            "to league average — not a trained model, since no free historical corners/"
            "shots data exists to validate against. Treat as a rough guide, not a "
            "calibrated probability like the 1X2 or goals-market predictions. Enable a "
            "premium data provider with match-statistics access for real historical data."
        ),
    }
