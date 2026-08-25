"""
Goals market model: Over/Under 2.5 and Both Teams To Score (BTTS).

Approach: independent Poisson model for home/away expected goals (lambda),
derived from each team's rolling attack/defense rates adjusted by a league-
average baseline (standard "attack strength x opponent defense weakness x
league average" method used in Dixon-Coles style models). From the two
Poisson lambdas we compute the full scoreline probability matrix, then sum
over it for Over/Under 2.5 and BTTS probabilities. This is more principled
than training a separate classifier per market on a dataset this size,
and it stays consistent with the 1X2 model's Elo/form inputs.

Validated the same way as the 1X2 model: time-based split, log loss,
Brier score, and accuracy against actual Over/Under and BTTS outcomes.

Includes shrinkage toward league-average scoring rates (see
expected_goals() docstring) — added after finding a real case where a
team's 6-match rolling window happened to contain an extreme outlier
(a very low goals-conceded rate) and produced an overconfident,
implausible expected-goals estimate for their opponent. Shrinkage measurably
improved log loss and Brier score on the same held-out test set. A
further improvement not yet implemented: the shrinkage strength currently
assumes a full 6-match sample for every team; dynamically passing each
team's ACTUAL match count (fewer early in a season, or for a team new to
a league) would shrink correctly. See expected_goals()'s
sample_size parameters, which predict_goals_markets() does not yet
supply — currently defaults to 6.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import poisson
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss

from features import build_features

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = Path(__file__).parent / "models"

MAX_GOALS = 8  # scoreline matrix truncation


def league_avg_goals(df: pd.DataFrame) -> tuple[float, float]:
    """Average home and away goals per match across the training window."""
    return df["home_goals"].mean(), df["away_goals"].mean()


def expected_goals(
    home_gf, home_ga, away_gf, away_ga, league_avg_home, league_avg_away,
    home_sample_size: int = 6, away_sample_size: int = 6,
) -> tuple[float, float]:
    """
    Standard attack/defense-strength expected goals formula:
      home_attack_strength = home_gf_avg / league_avg_home_goals
      away_defense_weakness = away_ga_avg / league_avg_home_goals
      home_lambda = home_attack_strength * away_defense_weakness * league_avg_home_goals
    (and symmetric for away)

    With shrinkage toward the league-average rate based on sample size: the
    rolling window feeding gf/ga averages is only 6 matches (see
    features.FORM_WINDOW), which is a genuinely small sample — a team that
    happened to concede very little in exactly those 6 games can otherwise
    produce an extreme, overconfident expected-goals swing for the
    opponent. This shrinks each rate partway back toward the league
    average, more so for smaller samples, which is a standard technique
    (empirical Bayes / James-Stein-style shrinkage) for taming small-sample
    noise rather than trusting a thin window at full strength.
    """
    SHRINKAGE_PRIOR_WEIGHT = 4  # "worth" of league-average matches blended in

    def shrink(rate: float, league_avg: float, n: int) -> float:
        n = max(n, 1)
        return (rate * n + league_avg * SHRINKAGE_PRIOR_WEIGHT) / (n + SHRINKAGE_PRIOR_WEIGHT)

    home_gf = shrink(home_gf, league_avg_home, home_sample_size)
    home_ga = shrink(home_ga, league_avg_away, home_sample_size)
    away_gf = shrink(away_gf, league_avg_away, away_sample_size)
    away_ga = shrink(away_ga, league_avg_home, away_sample_size)

    home_attack = home_gf / league_avg_home if league_avg_home > 0 else 1.0
    away_defense = away_ga / league_avg_home if league_avg_home > 0 else 1.0
    home_lambda = max(0.15, home_attack * away_defense * league_avg_home)

    away_attack = away_gf / league_avg_away if league_avg_away > 0 else 1.0
    home_defense = home_ga / league_avg_away if league_avg_away > 0 else 1.0
    away_lambda = max(0.15, away_attack * home_defense * league_avg_away)

    return home_lambda, away_lambda


def scoreline_matrix(lambda_home: float, lambda_away: float) -> np.ndarray:
    home_probs = poisson.pmf(np.arange(MAX_GOALS + 1), lambda_home)
    away_probs = poisson.pmf(np.arange(MAX_GOALS + 1), lambda_away)
    return np.outer(home_probs, away_probs)  # [home_goals, away_goals]


def market_probs_from_matrix(matrix: np.ndarray) -> dict:
    total_goals_grid = np.add.outer(np.arange(MAX_GOALS + 1), np.arange(MAX_GOALS + 1))
    over_2_5 = matrix[total_goals_grid > 2.5].sum()
    under_2_5 = 1 - over_2_5

    btts_yes = matrix[1:, 1:].sum()  # both scored at least 1
    btts_no = 1 - btts_yes

    return {
        "over_2_5": float(over_2_5),
        "under_2_5": float(under_2_5),
        "btts_yes": float(btts_yes),
        "btts_no": float(btts_no),
    }


def predict_goals_markets(home_gf, home_ga, away_gf, away_ga, league_avg_home, league_avg_away) -> dict:
    lam_h, lam_a = expected_goals(home_gf, home_ga, away_gf, away_ga, league_avg_home, league_avg_away)
    matrix = scoreline_matrix(lam_h, lam_a)
    markets = market_probs_from_matrix(matrix)
    markets["expected_home_goals"] = round(float(lam_h), 2)
    markets["expected_away_goals"] = round(float(lam_a), 2)

    # Most likely exact scorelines (top 3)
    flat_idx = np.dstack(np.unravel_index(np.argsort(-matrix, axis=None), matrix.shape))[0][:3]
    top_scores = [
        {"score": f"{int(h)}-{int(a)}", "probability": round(float(matrix[h, a]), 4)}
        for h, a in flat_idx
    ]
    markets["most_likely_scorelines"] = top_scores
    return markets


def validate_goals_model():
    """Time-based holdout validation for Over/Under 2.5 and BTTS."""
    matches = pd.read_csv(DATA_DIR / "matches.csv")
    feats = build_features(matches)
    feats = feats.dropna(subset=["result"]).reset_index(drop=True)
    feats["date"] = pd.to_datetime(feats["date"])
    feats = feats.sort_values("date").reset_index(drop=True)

    split_idx = int(len(feats) * 0.8)
    train, test = feats.iloc[:split_idx], feats.iloc[split_idx:]

    league_avg_home, league_avg_away = league_avg_goals(train)
    print(f"League average goals — Home: {league_avg_home:.2f}, Away: {league_avg_away:.2f}")

    over_probs, over_actuals = [], []
    btts_probs, btts_actuals = [], []

    for _, row in test.iterrows():
        markets = predict_goals_markets(
            row["home_gf_avg"], row["home_ga_avg"], row["away_gf_avg"], row["away_ga_avg"],
            league_avg_home, league_avg_away,
        )
        total_goals = row["home_goals"] + row["away_goals"]
        actual_over = 1 if total_goals > 2.5 else 0
        actual_btts = 1 if (row["home_goals"] > 0 and row["away_goals"] > 0) else 0

        over_probs.append(markets["over_2_5"])
        over_actuals.append(actual_over)
        btts_probs.append(markets["btts_yes"])
        btts_actuals.append(actual_btts)

    over_probs = np.array(over_probs)
    btts_probs = np.array(btts_probs)

    print(f"\n=== OVER/UNDER 2.5 GOALS — TEST SET ({len(test)} matches) ===")
    over_preds = (over_probs > 0.5).astype(int)
    print(f"Accuracy:    {accuracy_score(over_actuals, over_preds):.4f}")
    print(f"Log loss:    {log_loss(over_actuals, over_probs):.4f}")
    print(f"Brier score: {brier_score_loss(over_actuals, over_probs):.4f}")
    baseline_over = max(np.mean(over_actuals), 1 - np.mean(over_actuals))
    print(f"Baseline (majority class): {baseline_over:.4f}")

    print(f"\n=== BOTH TEAMS TO SCORE — TEST SET ({len(test)} matches) ===")
    btts_preds = (btts_probs > 0.5).astype(int)
    print(f"Accuracy:    {accuracy_score(btts_actuals, btts_preds):.4f}")
    print(f"Log loss:    {log_loss(btts_actuals, btts_probs):.4f}")
    print(f"Brier score: {brier_score_loss(btts_actuals, btts_probs):.4f}")
    baseline_btts = max(np.mean(btts_actuals), 1 - np.mean(btts_actuals))
    print(f"Baseline (majority class): {baseline_btts:.4f}")

    import joblib
    joblib.dump({"league_avg_home": league_avg_home, "league_avg_away": league_avg_away}, MODEL_DIR / "goals_model_params.joblib")
    print(f"\nGoals model params saved to {MODEL_DIR / 'goals_model_params.joblib'}")


if __name__ == "__main__":
    validate_goals_model()
