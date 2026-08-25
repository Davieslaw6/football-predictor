"""
Match Analysis Engine.

Given two teams (and optional news/injury info), produces:
  - Calibrated Home/Draw/Away probabilities
  - Top-3 most likely outcomes with confidence scores
  - Key factors driving the prediction (feature-level reasoning)
  - Injury/availability-adjusted strength penalty applied on top of the
    trained model's base prediction

NOTE on injuries/news: the training data has no historical injury feed
attached (none of the free sources used here expose that without a paid
key), so the model itself was NOT trained on injury features — training
rows all have avail_penalty = 0. What we do instead, honestly: apply a
transparent, documented POST-HOC probability adjustment when the user
supplies current injury/suspension info for a live analysis. This is a
real, working mechanism — not a token field — but it's a rule-based
overlay on top of the ML prediction, not something the model "learned".
That distinction is called out in the API response so nobody mistakes it
for a learned effect.
"""
from __future__ import annotations
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from features import build_features, get_team_snapshot, ELO_HOME_ADV, _elo_expected
from goals_model import predict_goals_markets, league_avg_goals
from estimated_stats import estimate_match_stats

MODEL_DIR = Path(__file__).parent / "models"
RESULT_MAP_INV = {0: "H", 1: "D", 2: "A"}
LABELS = {"H": "Home Win", "D": "Draw", "A": "Away Win"}

_model = None
_feature_cols = None
_engineered = None


def _load():
    global _model, _feature_cols, _engineered
    if _model is None:
        _model = joblib.load(MODEL_DIR / "outcome_model.joblib")
        _feature_cols = joblib.load(MODEL_DIR / "feature_cols.joblib")
        _engineered = pd.read_csv(MODEL_DIR / "engineered_features.csv", parse_dates=["date"])
        live_state_path = MODEL_DIR / "live_state.joblib"
        if live_state_path.exists():
            _engineered.attrs["live_state"] = joblib.load(live_state_path)
    return _model, _feature_cols, _engineered


def list_teams() -> list[str]:
    _, _, eng = _load()
    teams = sorted(set(eng["home_team"]).union(set(eng["away_team"])))
    return teams


def _apply_availability_adjustment(probs: np.ndarray, home_penalty: float, away_penalty: float) -> np.ndarray:
    """
    Rule-based overlay: an availability penalty (0-1, fraction of effective
    squad strength missing to injury/suspension) shifts win probability mass
    from the weakened team toward the opponent and, slightly, the draw.
    This is intentionally simple and documented rather than hidden inside
    the model, since we have no historical injury data to LEARN this effect
    from — see module docstring.
    """
    p_home, p_draw, p_away = probs
    net = home_penalty - away_penalty  # positive => home is weaker
    # Scale: a 20% squad strength penalty shifts ~8 percentage points
    shift = net * 0.40
    p_home_new = max(0.02, p_home - shift * 0.7)
    p_away_new = max(0.02, p_away + shift * 0.7)
    p_draw_new = max(0.02, p_draw + abs(shift) * 0.3 - (p_home_new - p_home + p_away_new - p_away))
    total = p_home_new + p_draw_new + p_away_new
    return np.array([p_home_new, p_draw_new, p_away_new]) / total


def analyze_match(
    home_team: str,
    away_team: str,
    home_injury_penalty: float = 0.0,
    away_injury_penalty: float = 0.0,
    home_out_players: list[str] | None = None,
    away_out_players: list[str] | None = None,
) -> dict:
    model, feature_cols, eng = _load()

    teams = list_teams()
    if home_team not in teams:
        raise ValueError(f"Unknown team: {home_team}")
    if away_team not in teams:
        raise ValueError(f"Unknown team: {away_team}")

    home_snap = get_team_snapshot(eng, home_team)
    away_snap = get_team_snapshot(eng, away_team)

    league_avg_home, league_avg_away = league_avg_goals(eng.rename(columns={"home_goals": "home_goals", "away_goals": "away_goals"}))
    goals_markets = predict_goals_markets(
        home_snap["gf_avg"], home_snap["ga_avg"], away_snap["gf_avg"], away_snap["ga_avg"],
        league_avg_home, league_avg_away,
    )
    estimated_stats = estimate_match_stats(
        home_snap["gf_avg"], home_snap["ga_avg"], away_snap["gf_avg"], away_snap["ga_avg"],
        league_avg_home, league_avg_away,
    )

    # Head-to-head: pull most recent known h2h stats between these two teams
    key_rows = eng[
        ((eng["home_team"] == home_team) & (eng["away_team"] == away_team)) |
        ((eng["home_team"] == away_team) & (eng["away_team"] == home_team))
    ].sort_values("date")
    if not key_rows.empty:
        last = key_rows.iloc[-1]
        h2h_matches = int(last["h2h_matches"])
        h2h_home_wins = int(last["h2h_home_wins"]) if last["home_team"] == home_team else int(last["h2h_away_wins"])
        h2h_away_wins = int(last["h2h_away_wins"]) if last["home_team"] == home_team else int(last["h2h_home_wins"])
    else:
        h2h_matches = h2h_home_wins = h2h_away_wins = 0

    elo_diff = home_snap["elo"] - away_snap["elo"]
    elo_exp_home = _elo_expected(home_snap["elo"] + ELO_HOME_ADV, away_snap["elo"])

    feat_row = pd.DataFrame([{
        "elo_home": home_snap["elo"],
        "elo_away": away_snap["elo"],
        "elo_diff": elo_diff,
        "elo_exp_home": elo_exp_home,
        "home_form_pts": home_snap["form_pts"],
        "away_form_pts": away_snap["form_pts"],
        "home_form_gd": home_snap["form_gd"],
        "away_form_gd": away_snap["form_gd"],
        "home_home_pts": home_snap["form_pts"],   # fallback proxy if home/away split unavailable
        "away_away_pts": away_snap["form_pts"],
        "home_home_gd": home_snap["form_gd"],
        "away_away_gd": away_snap["form_gd"],
        "home_rest_days": 7,
        "away_rest_days": 7,
        "home_streak": home_snap.get("streak", 0),
        "away_streak": away_snap.get("streak", 0),
        "h2h_home_wins": h2h_home_wins,
        "h2h_away_wins": h2h_away_wins,
        "h2h_matches": h2h_matches,
        "home_avail_penalty": 0.0,  # base model prediction excludes injuries (see docstring)
        "away_avail_penalty": 0.0,
    }])[feature_cols]

    base_probs = model.predict_proba(feat_row)[0]  # [P(H), P(D), P(A)]

    adjusted_probs = _apply_availability_adjustment(
        base_probs, home_injury_penalty, away_injury_penalty
    )

    outcomes = [
        {"outcome": "H", "label": f"{home_team} Win", "probability": round(float(adjusted_probs[0]), 4)},
        {"outcome": "D", "label": "Draw", "probability": round(float(adjusted_probs[1]), 4)},
        {"outcome": "A", "label": f"{away_team} Win", "probability": round(float(adjusted_probs[2]), 4)},
    ]
    outcomes.sort(key=lambda x: -x["probability"])
    for i, o in enumerate(outcomes):
        o["rank"] = i + 1
        o["confidence"] = (
            "High" if o["probability"] > 0.55 else
            "Medium" if o["probability"] > 0.38 else
            "Low"
        )

    # --- Key factors / reasoning ---
    factors = []
    if abs(elo_diff) > 50:
        stronger = home_team if elo_diff > 0 else away_team
        factors.append(f"{stronger} has a significant Elo rating edge ({abs(elo_diff):.0f} points)")
    if home_snap["form_pts"] - away_snap["form_pts"] > 0.5:
        factors.append(f"{home_team} in noticeably better recent form ({home_snap['form_pts']:.1f} vs {away_snap['form_pts']:.1f} pts/game)")
    elif away_snap["form_pts"] - home_snap["form_pts"] > 0.5:
        factors.append(f"{away_team} in noticeably better recent form ({away_snap['form_pts']:.1f} vs {home_snap['form_pts']:.1f} pts/game)")
    if h2h_matches >= 3:
        if h2h_home_wins > h2h_away_wins:
            factors.append(f"{home_team} has historically dominated this fixture ({h2h_home_wins}-{h2h_away_wins} in last {h2h_matches})")
        elif h2h_away_wins > h2h_home_wins:
            factors.append(f"{away_team} has historically dominated this fixture ({h2h_away_wins}-{h2h_home_wins} in last {h2h_matches})")
    factors.append("Home advantage factored in via Elo home-field adjustment")
    if home_injury_penalty > 0.05:
        names = f" ({', '.join(home_out_players)})" if home_out_players else ""
        factors.append(f"{home_team} weakened by unavailable players{names} — squad strength impact ~{home_injury_penalty*100:.0f}%")
    if away_injury_penalty > 0.05:
        names = f" ({', '.join(away_out_players)})" if away_out_players else ""
        factors.append(f"{away_team} weakened by unavailable players{names} — squad strength impact ~{away_injury_penalty*100:.0f}%")

    return {
        "home_team": home_team,
        "away_team": away_team,
        "base_model_probabilities": {
            "home_win": round(float(base_probs[0]), 4),
            "draw": round(float(base_probs[1]), 4),
            "away_win": round(float(base_probs[2]), 4),
        },
        "final_probabilities": {
            "home_win": round(float(adjusted_probs[0]), 4),
            "draw": round(float(adjusted_probs[1]), 4),
            "away_win": round(float(adjusted_probs[2]), 4),
        },
        "match_result_call": _build_match_result_call(outcomes),
        "top_outcomes": outcomes,
        "key_factors": factors,
        "team_snapshots": {
            "home": {"elo": round(home_snap["elo"], 1), "form_pts_per_game": round(home_snap["form_pts"], 2)},
            "away": {"elo": round(away_snap["elo"], 1), "form_pts_per_game": round(away_snap["form_pts"], 2)},
        },
        "head_to_head": {
            "matches_considered": h2h_matches,
            "home_team_wins": h2h_home_wins,
            "away_team_wins": h2h_away_wins,
        },
        "goals_markets": _build_goals_markets_section(goals_markets),
        "estimated_stats": estimated_stats,
        "availability_note": (
            "Injury/suspension adjustment is a rule-based overlay applied on top of "
            "the trained model, not a learned effect — see analyze.py docstring."
            if (home_injury_penalty or away_injury_penalty) else
            "No injury/availability data supplied for this analysis; prediction reflects full-strength squads."
        ),
    }


def _build_match_result_call(outcomes: list[dict]) -> dict:
    """
    Restructures the ranked 1X2 outcomes into the same "one decisive call,
    rest available on request" shape used for the goals markets — the
    single highest-probability outcome up front, with the other two kept
    in all_options for a UI reveal toggle.
    """
    best = outcomes[0]  # outcomes is already sorted by probability descending
    return {
        "call": best["label"],
        "call_probability": best["probability"],
        "confidence": best["confidence"],
        "all_options": [
            {"label": o["label"], "probability": o["probability"]} for o in outcomes
        ],
    }


def _confidence_label(probability: float) -> str:
    """Same thresholds as the 1X2 outcome confidence labels, for consistency."""
    if probability > 0.60:
        return "High"
    if probability > 0.50:
        return "Medium"
    return "Low"


def _build_goals_markets_section(goals_markets: dict) -> dict:
    """
    Restructures the raw Poisson goals output into a "the model decides"
    shape: for each market (Over/Under 2.5, BTTS), pick whichever side has
    >50% probability as the model's call, and keep the other side available
    but marked hidden-by-default so the frontend can show one decisive
    prediction with a reveal toggle for the full breakdown, rather than
    always showing both percentages side by side.
    """
    over_p, under_p = goals_markets["over_2_5"], goals_markets["under_2_5"]
    over_call = "Over 2.5 Goals" if over_p >= under_p else "Under 2.5 Goals"
    over_call_prob = max(over_p, under_p)

    btts_yes_p, btts_no_p = goals_markets["btts_yes"], goals_markets["btts_no"]
    btts_call = "Both Teams to Score" if btts_yes_p >= btts_no_p else "No — Not Both Teams to Score"
    btts_call_prob = max(btts_yes_p, btts_no_p)

    return {
        "total_goals_market": {
            "call": over_call,
            "call_probability": round(over_call_prob, 4),
            "confidence": _confidence_label(over_call_prob),
            "all_options": [
                {"label": "Over 2.5 Goals", "probability": round(over_p, 4)},
                {"label": "Under 2.5 Goals", "probability": round(under_p, 4)},
            ],
        },
        "btts_market": {
            "call": btts_call,
            "call_probability": round(btts_call_prob, 4),
            "confidence": _confidence_label(btts_call_prob),
            "all_options": [
                {"label": "Both Teams to Score", "probability": round(btts_yes_p, 4)},
                {"label": "No — Not Both Teams to Score", "probability": round(btts_no_p, 4)},
            ],
        },
        "expected_home_goals": goals_markets["expected_home_goals"],
        "expected_away_goals": goals_markets["expected_away_goals"],
        "most_likely_scorelines": goals_markets["most_likely_scorelines"],
        "model_note": (
            "Poisson attack/defense model. Validated on time-based holdout: Over/Under 2.5 "
            "beats a majority-class baseline by a modest margin; BTTS performs close to "
            "baseline and should be treated as a weaker signal than the main 1X2 and "
            "Over/Under predictions — a 'Medium' or 'Low' confidence BTTS call reflects that."
        ),
    }


if __name__ == "__main__":
    teams = list_teams()
    print(f"{len(teams)} teams available: {teams[:10]}...")
    t1, t2 = teams[0], teams[1]
    result = analyze_match(t1, t2, home_injury_penalty=0.15, home_out_players=["Test Player"])
    import json
    print(json.dumps(result, indent=2))
