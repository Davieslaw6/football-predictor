"""
Trains the match outcome model (Home/Draw/Away) with:
  - Time-based train/test split (no shuffling — respects chronology)
  - XGBoost multiclass classifier
  - Probability calibration (isotonic, via CalibratedClassifierCV)
  - Metrics: accuracy, log loss, Brier score
  - A simple flat-stake betting ROI simulation vs. naive market-implied odds
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV
from xgboost import XGBClassifier

from features import build_features

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

FEATURE_COLS = [
    "elo_home", "elo_away", "elo_diff", "elo_exp_home",
    "home_form_pts", "away_form_pts", "home_form_gd", "away_form_gd",
    "home_home_pts", "away_away_pts", "home_home_gd", "away_away_gd",
    "home_rest_days", "away_rest_days",
    "home_streak", "away_streak",
    "h2h_home_wins", "h2h_away_wins", "h2h_matches",
    "home_avail_penalty", "away_avail_penalty",
]

RESULT_MAP = {"H": 0, "D": 1, "A": 2}
RESULT_MAP_INV = {v: k for k, v in RESULT_MAP.items()}


def _elo_expected_local(r_a: float, r_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400))


def load_and_engineer() -> pd.DataFrame:
    matches = pd.read_csv(DATA_DIR / "matches.csv")
    feats = build_features(matches)
    feats = feats.dropna(subset=["result"]).reset_index(drop=True)
    return feats


def time_split(feats: pd.DataFrame, test_frac: float = 0.2):
    feats = feats.sort_values("date").reset_index(drop=True)
    split_idx = int(len(feats) * (1 - test_frac))
    train = feats.iloc[:split_idx]
    test = feats.iloc[split_idx:]
    return train, test


def train_model():
    print("Loading data and engineering features...")
    feats = load_and_engineer()
    print(f"Total labeled matches: {len(feats)}")

    train, test = time_split(feats, test_frac=0.2)
    print(f"Train: {len(train)} matches ({train['date'].min().date()} to {train['date'].max().date()})")
    print(f"Test:  {len(test)} matches ({test['date'].min().date()} to {test['date'].max().date()})")

    X_train = train[FEATURE_COLS]
    y_train = train["result"].map(RESULT_MAP)
    X_test = test[FEATURE_COLS]
    y_test = test["result"].map(RESULT_MAP)

    # Base XGBoost classifier
    base_model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=5,
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        random_state=42,
    )

    # Calibrate probabilities via isotonic regression, 5-fold CV on train set
    print("\nTraining + calibrating model...")
    model = CalibratedClassifierCV(base_model, method="isotonic", cv=5)
    model.fit(X_train, y_train)

    # --- Evaluate ---
    proba = model.predict_proba(X_test)
    preds = np.argmax(proba, axis=1)

    acc = accuracy_score(y_test, preds)
    ll = log_loss(y_test, proba, labels=[0, 1, 2])

    # Multiclass Brier score (mean over classes, one-vs-rest)
    y_test_onehot = np.eye(3)[y_test]
    brier = np.mean(np.sum((proba - y_test_onehot) ** 2, axis=1))

    print(f"\n=== TEST SET METRICS (time-based holdout) ===")
    print(f"Accuracy:        {acc:.4f}")
    print(f"Log loss:        {ll:.4f}  (lower is better; naive 3-class baseline ~1.099)")
    print(f"Brier score:     {brier:.4f}  (lower is better; naive baseline ~0.667)")

    # Baseline comparison: always predict most frequent class
    majority_class = y_train.mode()[0]
    baseline_acc = (y_test == majority_class).mean()
    print(f"\nBaseline (always predict '{RESULT_MAP_INV[majority_class]}'): {baseline_acc:.4f} accuracy")
    print(f"Model improvement over baseline: {(acc - baseline_acc) * 100:+.1f} pts")

    # --- Betting ROI simulation ---
    # IMPORTANT CAVEAT: this dataset has no real historical odds, so ROI here
    # is illustrative of the METHOD only, not a claim of real-world edge.
    # A previous version of this simulation derived "market odds" from the
    # same aggregate training-set frequencies the model was trained on,
    # which let the model trivially "beat" a market that was really just a
    # mirror of its own training distribution — inflating ROI to unrealistic
    # +25-40%. That was a methodology bug, not a genuine edge, and real
    # bookmaker lines are far more efficient than that.
    #
    # Fixed approach: build a PER-MATCH synthetic market price from a much
    # simpler Elo-only logistic proxy (no form/H2H/rest/news features the
    # main model uses), plus a realistic ~6% overround. This gives the ML
    # model something weaker-but-plausible to beat, which is the honest way
    # to sanity-check "does richer feature engineering add price-beating
    # value" without real odds data. Replace with genuine odds (The Odds
    # API / football-data.org) before trusting any ROI number for real money.
    print(f"\n=== SIMULATED BETTING ROI (flat stake, value-bet strategy) ===")
    print("CAVEAT: no real historical odds available — this uses a simple Elo-only")
    print("baseline as a stand-in 'market' to sanity-check the method. Do NOT treat")
    print("this ROI as a real-world profitability claim.\n")

    overround = 1.06

    def elo_only_market_probs(elo_home, elo_away):
        exp_home = _elo_expected_local(elo_home + 60, elo_away)
        # crude 3-way split: push a fixed draw mass, split remainder by exp_home
        p_draw = 0.24
        p_home = exp_home * (1 - p_draw)
        p_away = (1 - exp_home) * (1 - p_draw)
        return np.array([p_home, p_draw, p_away])

    for edge_threshold in [0.05, 0.08, 0.12]:
        stake = 1.0
        bankroll_delta = 0.0
        n_bets = 0
        for i in range(len(test)):
            row = test.iloc[i]
            market_p = elo_only_market_probs(row["elo_home"], row["elo_away"])
            market_p = market_p / market_p.sum()
            market_odds_row = (1 / market_p) / (1 / overround)  # apply overround to odds
            p = proba[i]
            actual = y_test.iloc[i]
            for cls in [0, 1, 2]:
                implied_p = 1 / market_odds_row[cls]
                if p[cls] - implied_p > edge_threshold:
                    n_bets += 1
                    if actual == cls:
                        bankroll_delta += stake * (market_odds_row[cls] - 1)
                    else:
                        bankroll_delta -= stake
        roi = (bankroll_delta / n_bets * 100) if n_bets else 0.0
        print(f"  Edge >{edge_threshold:.0%}: {n_bets} bets placed, ROI = {roi:+.2f}% per bet, "
              f"total P/L = {bankroll_delta:+.2f} units")

    # --- Save model + metadata ---
    joblib.dump(model, MODEL_DIR / "outcome_model.joblib")
    joblib.dump(FEATURE_COLS, MODEL_DIR / "feature_cols.joblib")
    feats.to_csv(MODEL_DIR / "engineered_features.csv", index=False)
    # live_state (each team's TRUE current Elo/form/streak, as of right
    # now rather than going into their last match) doesn't survive a CSV
    # round-trip, since .attrs isn't part of the CSV format — persist it
    # separately so analyze.py's live match analysis stays accurate.
    joblib.dump(feats.attrs.get("live_state", {}), MODEL_DIR / "live_state.joblib")

    metrics = {
        "accuracy": float(acc),
        "log_loss": float(ll),
        "brier_score": float(brier),
        "baseline_accuracy": float(baseline_acc),
        "train_matches": int(len(train)),
        "test_matches": int(len(test)),
        "test_date_range": [str(test["date"].min().date()), str(test["date"].max().date())],
    }
    joblib.dump(metrics, MODEL_DIR / "metrics.joblib")
    print(f"\nModel + metrics saved to {MODEL_DIR}")

    return model, metrics


if __name__ == "__main__":
    train_model()
