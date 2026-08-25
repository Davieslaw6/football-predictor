export interface Outcome {
  outcome: "H" | "D" | "A";
  label: string;
  probability: number;
  rank: number;
  confidence: "High" | "Medium" | "Low";
}

export interface TeamSnapshot {
  elo: number;
  form_pts_per_game: number;
}

export interface HeadToHead {
  matches_considered: number;
  home_team_wins: number;
  away_team_wins: number;
}

export interface Scoreline {
  score: string;
  probability: number;
}

export interface MarketCall {
  call: string;
  call_probability: number;
  confidence: "High" | "Medium" | "Low";
  all_options: Array<{ label: string; probability: number }>;
}

export interface GoalsMarkets {
  total_goals_market: MarketCall;
  btts_market: MarketCall;
  expected_home_goals: number;
  expected_away_goals: number;
  most_likely_scorelines: Scoreline[];
  model_note: string;
}

export interface EstimatedStats {
  home_corners_estimate: number;
  away_corners_estimate: number;
  total_corners_estimate: number;
  home_shots_estimate: number;
  away_shots_estimate: number;
  total_shots_estimate: number;
  is_validated_prediction: boolean;
  methodology_note: string;
  premium_data_available?: boolean;
  premium_source?: string;
  premium_error?: string;
}

export interface AnalysisResult {
  home_team: string;
  away_team: string;
  base_model_probabilities: { home_win: number; draw: number; away_win: number };
  final_probabilities: { home_win: number; draw: number; away_win: number };
  match_result_call: MarketCall;
  top_outcomes: Outcome[];
  key_factors: string[];
  team_snapshots: { home: TeamSnapshot; away: TeamSnapshot };
  head_to_head: HeadToHead;
  goals_markets: GoalsMarkets;
  estimated_stats: EstimatedStats;
  availability_note: string;
}

export interface ModelMetrics {
  accuracy: number;
  log_loss: number;
  brier_score: number;
  baseline_accuracy: number;
  train_matches: number;
  test_matches: number;
  test_date_range: [string, string];
}
