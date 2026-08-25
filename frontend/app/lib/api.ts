import { AnalysisResult, ModelMetrics } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function fetchTeams(query?: string): Promise<string[]> {
  const url = new URL(`${API_BASE}/api/teams`);
  if (query) url.searchParams.set("q", query);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to fetch teams");
  const data = await res.json();
  return data.teams as string[];
}

export async function analyzeMatch(params: {
  home_team: string;
  away_team: string;
  home_injury_penalty?: number;
  away_injury_penalty?: number;
  home_out_players?: string[];
  away_out_players?: string[];
}): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Analysis failed");
  }
  return res.json();
}

export async function fetchModelMetrics(): Promise<ModelMetrics> {
  const res = await fetch(`${API_BASE}/api/model/metrics`);
  if (!res.ok) throw new Error("Failed to fetch model metrics");
  return res.json();
}

export interface LeagueInfo {
  key: string;
  label: string;
  competition_type: "domestic" | "continental";
  seasons_available: string[];
  selected: boolean;
}

export async function fetchLeagues(): Promise<LeagueInfo[]> {
  const res = await fetch(`${API_BASE}/api/leagues`);
  if (!res.ok) throw new Error("Failed to fetch leagues");
  const data = await res.json();
  return data.leagues as LeagueInfo[];
}

export async function setLeagueSelection(leagues: string[]): Promise<void> {
  const res = await fetch(`${API_BASE}/api/leagues/selection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ leagues }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to save league selection");
  }
}

export interface UpdateStatus {
  status: "idle" | "running" | "success" | "error";
  started_at: number | null;
  finished_at: number | null;
  log: string;
  error: string | null;
}

export async function triggerUpdate(): Promise<{ message: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/update`, { method: "POST" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to trigger update");
  }
  return res.json();
}

export async function fetchUpdateStatus(): Promise<UpdateStatus> {
  const res = await fetch(`${API_BASE}/api/update/status`);
  if (!res.ok) throw new Error("Failed to fetch update status");
  return res.json();
}

export interface LiveFixture {
  id: string;
  source: string;
  league: string;
  home_team: string;
  away_team: string;
  utc_date: string;
  status: string;
  home_score: number | null;
  away_score: number | null;
  minute: number | null;
}

export interface ProviderResult {
  provider: string;
  label: string;
  enabled: boolean;
  configured: boolean;
  fixture_count?: number;
  error: string | null;
}

export interface LiveFixturesResponse {
  configured: boolean;
  message: string | null;
  fixtures: LiveFixture[];
  provider_results: ProviderResult[];
}

export async function fetchLiveFixtures(competition?: string): Promise<LiveFixturesResponse> {
  const url = new URL(`${API_BASE}/api/fixtures/live`);
  if (competition) url.searchParams.set("competition", competition);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to fetch fixtures");
  return res.json();
}

export interface ProviderStatus {
  key: string;
  label: string;
  enabled: boolean;
  configured: boolean;
  available: boolean;
}

export async function fetchProviders(): Promise<ProviderStatus[]> {
  const res = await fetch(`${API_BASE}/api/providers`);
  if (!res.ok) throw new Error("Failed to fetch providers");
  const data = await res.json();
  return data.providers as ProviderStatus[];
}

export async function setProviderEnabled(provider: string, enabled: boolean): Promise<void> {
  const res = await fetch(`${API_BASE}/api/providers/selection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, enabled }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to update provider");
  }
}


export interface DataSourceStatus {
  prediction_source: "local" | "api";
  prediction_source_label: string;
  dataset_available: boolean;
  dataset_last_updated: string | null;
  api_providers_configured: string[];
  note: string;
}

export async function fetchDataSourceStatus(): Promise<DataSourceStatus> {
  const res = await fetch(`${API_BASE}/api/data-source`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch data source status");
  return res.json();
}
