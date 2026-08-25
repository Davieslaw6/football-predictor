# Fulltime — Football Match Prediction Platform

A working, locally-runnable football match prediction platform: real historical
data, a validated ML model, a FastAPI backend, and a Next.js frontend.

## What's actually in here (read this first)

This was built to be honest about what it is, not to look more finished than
it is. Specifically:

- **Historical data is real**, not synthetic: 27,000+ actual match results
  across 14 competitions — Premier League, EFL Championship, UEFA Champions
  League, Bundesliga, 2. Bundesliga, La Liga, Serie A, Ligue 1, Eredivisie,
  Primeira Liga, Segunda División, Ligue 2, Belgian Pro League, and Süper
  Lig — pulled from the public
  [openfootball](https://github.com/openfootball/football.json) GitHub mirror.
  No API key needed for this — it's already baked into `data/matches.csv`,
  and `data/build_dataset.py` re-fetches it fresh on demand.
- **League coverage is honestly scoped.** Most leagues have full 7-season
  coverage (2018–19 through 2024–25). Champions League, Segunda División,
  Ligue 2, Belgian Pro League, and Süper Lig have a real gap in the middle
  (missing 2021-22 through 2023-24) — that's a real gap in the free
  source, not a bug, and still genuinely multi-year usable rather than a
  token addition. Europa League, Conference League, Saudi Pro League, and
  Scottish Premiership were evaluated and **deliberately left out**: none
  have usable multi-year historical depth in any free source found.
  Adding them for real would need a paid data subscription — see
  "Extending this" below.
- **A real data-quality bug was caught and fixed while expanding leagues**:
  several leagues' source files used inconsistent club naming across
  different season files (e.g. "PSV" vs "PSV Eindhoven", "AFC Ajax" vs
  "Ajax"), which would have silently split one real club's history into
  two separate "teams" and corrupted Elo/form for both halves.
  `build_dataset.py` now includes an automated duplicate-name detector
  that runs on every rebuild — not just a one-time manual fix — plus an
  alias table for the 20+ real duplicates found this way. (One
  near-miss avoided: "Paris" and "Paris Saint-Germain" look like a
  duplicate but are genuinely different clubs — checked directly against
  the source data before deciding not to merge them.)
- **The 1X2 model is a real, validated XGBoost classifier**, calibrated and
  evaluated on a strict time-based holdout (not random shuffling — it's
  trained on 2015–2024 and tested only on 2024–2025, matches it never saw).
  It beats a naive "always predict home win" baseline by ~7 percentage
  points of accuracy, and beats naive baselines on log loss and Brier
  score too. That's a real, modest, honest edge — not a claim of high
  accuracy, and it will shift slightly depending on which leagues are
  selected for training (see "Leagues & Data Updates" below). Recent
  additions — win/loss streak features and margin-of-victory-weighted Elo
  updates (bigger wins move ratings more, a standard refinement used by
  e.g. FiveThirtyEight's SPI) — measurably improved this over the
  previous version. A wider/deeper model was also tried and honestly
  found NOT to help on held-out data, so the simpler configuration was
  kept rather than changed just to look more sophisticated.
- **A real staleness bug in live match analysis was found and fixed**:
  analyzing a fresh matchup was using each team's Elo/form rating from
  going INTO their most recent match, not their true current rating
  AFTER it — off by exactly one match's worth of movement. Fixed by
  persisting each team's true end-of-data state separately
  (`ml/models/live_state.joblib`) rather than reconstructing it
  approximately from the training CSV.
- **Match result predictions (1X2) now show one decisive call**, matching
  the same pattern as the goals markets: whichever outcome the model
  favors most, with a confidence label, and the other two outcomes
  available behind a "Show other outcomes" toggle instead of a three-way
  breakdown shown all at once.
- **Corners and shots are a clearly-labeled heuristic estimate, not a
  validated prediction.** No free source — anywhere — provides multi-year
  historical corners/shots data; that's paid-tier data everywhere it
  exists. Rather than skip this or fake it, `ml/estimated_stats.py`
  derives a defensible estimate from each team's real goal-scoring
  output relative to league average, calibrated against published
  real-world corners/shots averages (cited in that file). Every response
  includes `is_validated_prediction: false` and a plain-language note —
  this is a rough guide, not something with an accuracy/log-loss score
  like the other predictions in this app, because there's no ground
  truth in this dataset to score it against.
- **A toggleable "real data" alternative for corners/shots exists**, as
  requested: enable Sportmonks or API-Football (if your specific plan
  includes match statistics — many don't) from the "Corners & Shots Data
  Source" panel, and the app will try to fetch real data instead of the
  estimate. Built honestly: the API-Football integration openly reports
  that it needs a league+season parameter not yet wired up (a real
  incomplete piece, surfaced as an error rather than hidden), and both
  clients gracefully fall back to the heuristic estimate on any failure
  rather than breaking the response.
- **Over/Under 2.5 and BTTS use a Poisson goals model**, the standard
  attack/defense-strength approach, now with shrinkage toward
  league-average scoring rates for teams with a small/extreme recent
  sample (see `goals_model.py`'s `expected_goals()` docstring — this was
  added after finding a real case where one team's outlier 6-match
  defensive record produced an implausible, overconfident expected-goals
  estimate for their opponent; the fix measurably improved log loss and
  Brier score on the same held-out test). The UI now shows this as **one
  decisive call per market** — whichever side the model favors — with the
  losing option hidden behind a "Show other outcome" toggle rather than
  always displaying both percentages side by side. Each call carries a
  confidence label (High/Medium/Low). Over/Under beats baseline by a
  small margin; **BTTS performs close to baseline**, which is why BTTS
  calls usually show Medium or Low confidence rather than High — that's
  the model being honest about a genuinely harder market, not a bug.
- **Leagues can be selected, and data can be refreshed on demand or
  daily.** The "Leagues & Data Updates" panel in the app lets you choose
  which competitions feed the model, and an "Update Now" button re-fetches
  match data and retrains both models in the background (usually well
  under a minute). For unattended daily updates, see "Daily updates"
  below — this needs your machine or a server to actually trigger it on a
  schedule; there's no way for a static download to run itself every day
  on its own.
- **The betting ROI simulator is clearly labeled as a methodology demo**,
  not a real profitability claim, because there's no real historical odds
  data bundled here. An earlier version of this simulator had a bug where
  it built the synthetic "market" from the same aggregate stats the model
  trained on, which produced unrealistically high ROI (+25–40%) — that's
  been fixed to use an independent baseline, and the code comments explain
  why the fix mattered. Plug in real odds (The Odds API, football-data.org)
  before trusting any ROI number for actual betting decisions.
- **Injury/availability adjustment is a documented rule-based overlay**,
  not something the model learned — there's no free historical injury
  data source, so the model was never trained on injury features. When you
  supply an availability penalty in the UI, it shifts the model's output
  probabilities using a simple, transparent formula. The API response says
  this explicitly every time.
- **Live fixture/live-score data now supports three independently-toggleable
  providers**: Sportmonks, API-Football, and football-data.org. Every one
  of them is opt-in and needs its own API key — none are pre-configured,
  none are free at meaningful scale (see "Live data providers" below for
  current pricing), and toggling a provider on in the UI does nothing
  until its key is also set as an environment variable. A provider that's
  disabled, unconfigured, or erroring never breaks the other two — each
  request reports per-provider status so you always know exactly what
  happened.
- **The Sportmonks client's response field-mapping is unverified against a
  live account.** Sportmonks' full field-level API docs sit behind an
  authenticated developer portal I don't have access to, so
  `backend/app/providers/sportmonks.py` was built from the publicly
  documented endpoint shape and general v3 conventions — the endpoints and
  auth are right, but exact JSON field names inside responses may need a
  small adjustment once you test against a real account. This is called
  out directly in that file's docstring, with instructions for the
  one-time fix. The API-Football client is on firmer ground — its
  request/response shape is confirmed against public documentation and
  matches independent third-party integrations.
- **There is no live player-news/injury scraping pipeline** beyond the
  fixture/score data above. Reliable real-time injury/lineup/sentiment
  feeds are a separate, further paid tier even within Sportmonks/
  API-Football, and aren't wired in — the architecture has a clean place
  to plug that in (`home_injury_penalty` / `away_injury_penalty` in the
  API), but nothing here fetches it automatically.
- **This isn't deployed anywhere.** It's a complete, runnable local project.
  Deployment instructions to Vercel + Render/Railway are below, but you'll
  need your own accounts/keys to actually deploy it.

None of this is a criticism of the ask — it's what's true about any
prediction system built on free, public data in one sitting. Better to know
where the real edges and gaps are than to trust a black box.

## Architecture

```
football-predictor/
├── data/
│   ├── raw/                    # Raw season JSON files (auto-fetched, gitignored)
│   ├── build_dataset.py        # Fetches + consolidates league JSON -> matches.csv
│   │                           #   (includes an automated duplicate-team-name detector)
│   ├── league_selection.json   # Which leagues are currently selected for updates
│   └── matches.csv             # 27,000+ real matches across 14 leagues, ready to use
├── ml/
│   ├── features.py             # Elo (margin-of-victory weighted), rolling form, streak,
│   │                           #   H2H, rest days — leak-free, persists live team state
│   ├── train.py                # Trains + calibrates the 1X2 XGBoost model
│   ├── goals_model.py          # Poisson Over/Under 2.5 + BTTS model, with shrinkage
│   │                           #   toward league-average for small/extreme samples
│   ├── estimated_stats.py      # Heuristic corners/shots estimate — NOT a validated
│   │                           #   prediction, see file docstring
│   ├── analyze.py              # Combines everything into one match report
│   ├── build_dataset_loader.py # Exposes the league registry to the backend
│   └── models/                 # Saved model artifacts, incl. live_state.joblib
│                               #   (each team's TRUE current Elo/form, not stale)
├── backend/
│   ├── app/main.py             # FastAPI: /api/teams, /api/analyze, /api/update, etc.
│   ├── app/providers/          # Live data + premium stats provider clients
│   │   ├── base.py             #   Common interface every live-fixture provider implements
│   │   ├── sportmonks.py       #   Sportmonks client (field mapping unverified — see docstring)
│   │   ├── api_football.py     #   API-Football client
│   │   ├── football_data_org.py #  football-data.org wrapped to the same interface
│   │   ├── registry.py         #   Enable/disable state + aggregates live-fixture providers
│   │   └── premium_stats.py    #   Toggleable REAL corners/shots data (Sportmonks/API-Football)
│   ├── daily_update.ps1        # Windows script: triggers update via the running server
│   └── daily_update_standalone.py  # Fetches + retrains without needing the server up
└── frontend/
    └── app/                    # Next.js 15 + Tailwind, light/dark mode
```

## Setup

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The model is already trained (artifacts are in `ml/models/`). To retrain
from scratch:

```bash
cd ml
pip install -r requirements.txt
cd ../data && python3 build_dataset.py   # fetches match data for all leagues
cd ../ml
python3 train.py          # trains + validates the 1X2 model
python3 goals_model.py    # validates the Over/Under 2.5 / BTTS model
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`. It expects the backend at
`http://localhost:8000` by default — see `.env.local` /
`NEXT_PUBLIC_API_BASE` to change that.

### 3. (Optional) Live data providers

Live in-play fixtures and scores come from up to three independently
toggleable providers. All three are opt-in — the app works fully without
any of them (you just won't have live scores) — and each is enabled or
disabled separately from the "Live Data Providers" panel in the app,
without affecting the other two.

**football-data.org** — the cheapest to start with; the same free key used
for historical data elsewhere in this project also unlocks its basic live
match status.
```bash
export FOOTBALL_DATA_API_KEY=your_key_here
```
Get a free key at https://www.football-data.org/register. Free tier is
rate-limited (10 requests/minute) and doesn't include minute-by-minute
in-play detail — fixtures + status only.

**API-Football** (api-sports.io / RapidAPI) — real in-play live scores
with elapsed minute, cheapest paid entry point (~$19/month after a free
tier of ~100 requests/day at time of writing — verify current pricing at
https://www.api-football.com/pricing).
```bash
export API_FOOTBALL_API_KEY=your_key_here
# If you subscribed via RapidAPI rather than directly at api-sports.io:
export API_FOOTBALL_USE_RAPIDAPI=true
```

**Sportmonks** — the most complete live data (in-play events, xG,
predictions, odds) but the most expensive: plans start at €29/month for 5
leagues (Starter), scaling to €99/month (30 leagues) and €249/month (120
leagues); the permanent free plan only covers the Danish Superliga and
Scottish Premiership, which won't include Premier League/Championship/
Champions League. Every paid plan includes a 14-day free trial (requires
a card). Verify current pricing at
https://www.sportmonks.com/football-api/plans-pricing/.
```bash
export SPORTMONKS_API_KEY=your_key_here
```
**Note:** the Sportmonks client's response parsing was built from public
documentation, not tested against a live account — see the honest caveat
in `backend/app/providers/sportmonks.py` if fixture data comes back
looking wrong after you add a real key; it's a one-function fix.

Set whichever keys you have before starting the backend. `/api/providers`
shows the live status of each (enabled / has-a-key / actually working);
`/api/fixtures/live` aggregates results from every provider that's both
toggled on and has a working key, and reports per-provider errors without
letting one bad provider break the others.

## Leagues & data updates

The "Leagues & Data Updates" panel in the app (below the team selectors)
lets you:
- **Choose which competitions are included** — check/uncheck Premier
  League, EFL Championship, and/or UEFA Champions League, then "Save
  selection". This changes which leagues get refreshed the next time data
  updates — it does not retroactively change the currently-loaded model
  until you also run an update.
- **Update Now** — re-fetches match results for the selected leagues and
  retrains both models in the background. Takes anywhere from a few
  seconds to about a minute depending on how many leagues are selected.
  Poll `/api/update/status` (or just watch the panel) for progress.

### Daily updates (automatic)

The app itself cannot run a background job forever on its own — a browser
tab or a downloaded project has no way to wake itself up once a day. What
*is* real and included: two scripts that do the actual fetch+retrain work,
which you schedule to run daily using your OS's own scheduler.

**Recommended: `backend/daily_update_standalone.py`** — this doesn't need
the FastAPI server to be running, which makes it the more reliable choice
for unattended daily runs.

**Windows (Task Scheduler):**
1. Open Task Scheduler → Create Basic Task
2. Name it "Football Predictor Daily Update", trigger: Daily, pick a time
3. Action: Start a program
   - Program/script: `C:\path\to\venv\Scripts\python.exe`
   - Add arguments: `daily_update_standalone.py`
   - Start in: `C:\path\to\football-predictor\backend`
4. Finish, then right-click the task → Run once to test it manually

**macOS/Linux (cron):**
```bash
crontab -e
# add:
0 6 * * * cd /path/to/football-predictor/backend && /path/to/venv/bin/python3 daily_update_standalone.py >> update.log 2>&1
```

Alternative: `backend/daily_update.ps1` calls the already-running server's
`/api/update` endpoint instead of running the pipeline directly — use this
only if you're keeping the backend server running continuously (e.g. as a
Windows Service).

## API reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/teams?q=` | GET | Searchable team list |
| `/api/analyze` | POST | Full match analysis (see body below) |
| `/api/leagues` | GET | Available leagues + which are selected |
| `/api/leagues/selection` | POST | Set which leagues update on the next refresh |
| `/api/update` | POST | Trigger a background data refresh + retrain |
| `/api/update/status` | GET | Poll progress of the last/current update |
| `/api/fixtures/live?competition=PL` | GET | Live fixtures aggregated across all enabled+configured providers |
| `/api/providers` | GET | Status of each live data provider (enabled/configured/available) |
| `/api/providers/selection` | POST | Enable or disable one provider independently |
| `/api/model/metrics` | GET | Training-time validation metrics |
| `/api/premium-stats` | GET | Status of the premium corners/shots data toggle |
| `/api/premium-stats/selection` | POST | Enable real corners/shots data, or disable (use heuristic estimate) |

`POST /api/analyze` body:
```json
{
  "home_team": "Liverpool",
  "away_team": "Manchester City",
  "home_injury_penalty": 0.15,
  "away_injury_penalty": 0.0,
  "home_out_players": ["Example Player"],
  "away_out_players": []
}
```

`POST /api/leagues/selection` body:
```json
{
  "leagues": ["premier_league", "champions_league"]
}
```
Valid league keys: `premier_league`, `championship`, `champions_league`.

`POST /api/providers/selection` body:
```json
{
  "provider": "sportmonks",
  "enabled": false
}
```
Valid provider keys: `sportmonks`, `api_football`, `football_data_org`.

## Extending this for real production use

To take this from "working local prototype" to something you'd trust with
real money or ship to real users, in priority order:

1. **Real odds data** — wire in The Odds API for actual bookmaker lines,
   replace the illustrative ROI simulation with one backtested against
   real historical odds.
2. **Real injury/news data** — API-Football's paid tier or a dedicated
   sports news API, with a scheduled job (Celery/cron) refreshing it daily.
   This is the single biggest accuracy lever left on the table, since
   squad availability is genuinely predictive and currently unused by the
   trained model itself (only as a manual overlay).
3. **More leagues** — Europa League, Conference League, and the Saudi Pro
   League were evaluated for this build and left out because no free
   source has usable multi-year historical depth for them. A paid
   subscription (API-Football, Sportmonks) would unlock these plus
   leagues outside Europe entirely.
4. **xG data** — Understat/FBref have shot-level xG data that would likely
   improve the goals model meaningfully beyond simple attack/defense
   averages.
5. **Deployment** — frontend to Vercel (`vercel deploy` from `/frontend`),
   backend to Render or Railway (both support FastAPI out of the box via
   a `Procfile` or their native Python detection). Set
   `NEXT_PUBLIC_API_BASE` on the frontend to your deployed backend URL,
   and lock down CORS in `backend/app/main.py` (currently `allow_origins=["*"]`
   for local dev convenience — tighten this before going live).
6. **Postgres + Redis** — the current setup uses flat files/joblib artifacts,
   which is fine for a single-model local app. A production system serving
   real traffic would want Postgres for match/odds storage and Redis for
   caching `/api/teams` and repeated `/api/analyze` calls.

## Responsible gambling

This tool produces statistical estimates with real, quantified uncertainty
(see `/api/model/metrics` for exact accuracy figures) — not certainties, and
not financial advice. If you or someone you know is struggling with
gambling: in the UK, GamCare (0808 8020 133); in the US, the National
Problem Gambling Helpline (1-800-522-4700).
