# ClimaCred AI – Phase 2 Full-Stack Implementation + Gemini AI Layer

**Team:** TerraMind  
**Stack:** React + TypeScript + Vite + Tailwind + Framer Motion + Recharts + Lucide | FastAPI + MongoDB (PyMongo/Mongomock) + Pandas + NumPy + Scikit-learn

> **Core Principle:** ClimaCred AI is **NOT** a simple solar recommendation system. Solar is only one possible intervention. The platform multi-dimensionally evaluates Energy, Water, Waste, Emissions, Mobility, Materials, Operations to find the highest-impact inefficiencies for each business.

---

## Architecture

```
Frontend (React/Vite)  →  FastAPI REST API  →  Service Layer  →  Climate Intelligence Engine
                                                   ↓                ↓
                                              Calculation Engine  →  Recommendation Engine  →  MongoDB
                                                               ↘
                                                        Anomaly Detection / Forecasting (ML)
```

**Separation:**

- `api/routes` – HTTP handlers, validation, CORS, error handling
- `schemas` – Pydantic models (profile, assessment, scenario, report)
- `services` – Business logic, DB access, caching/invalidation
- `climate_engine` – `fingerprint.py`, `scoring.py`, `recommendations.py`, `simulations.py`, `emissions.py`, `anomaly_detection.py`, `forecasting.py`
- `database` – `mongodb.py`, `collections.py`
- `utils` – `calculations.py`, `validation.py`, `units.py`
- `config.py` – env, weights, emission factors (configurable, not hardcoded)

Frontend and backend are cleanly separated. All climate calculations live in backend services; frontend handles presentation.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/routes/{profile,assessment,fingerprint,solutions,scenarios,transformation,impact,reports}.py
│   │   ├── schemas/{profile,assessment,scenario,report}.py
│   │   ├── services/{profile_service,assessment_service,fingerprint_service,solution_service,scenario_service,transformation_service,impact_service,report_service}.py
│   │   ├── services/{ai_insight_service,ai_chat_service}.py   # Gemini layer (backend-only key)
│   │   ├── climate_engine/{fingerprint,scoring,recommendations,simulations,emissions,forecasting,anomaly_detection}.py
│   │   ├── database/{mongodb,collections}.py
│   │   └── utils/{calculations,validation,units}.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── seed.py                # developer-only sample data (needs --demo, never auto-run)
│   └── tests/{test_api.py,test_ai.py}
├── src/
│   ├── App.tsx
│   ├── components/{layout,common}
│   ├── components/chat/AIChatAssistant.tsx   # floating "ClimaCred AI Assistant"
│   ├── pages/{Dashboard,BusinessProfile,ClimateAssessment,ClimateFingerprint,Energy,Water,Waste,Emissions,Mobility,GreenSolutions,ScenarioSimulator,TransformationPlan,ImpactVerification,ClimateImpactReport}.tsx
│   ├── services/api.ts        # Centralized API client (live backend)
│   ├── services/defaults.ts   # Empty-state copy + formatting helpers
│   └── types/index.ts
├── frontend_smoke_test.cjs    # headless UI smoke test (empty DB + seeded)
└── vite.config.ts
```

---

## Environment Setup

### Prerequisites

- Node 18+, Python 3.11+, MongoDB 6+ (or use mongomock fallback for dev without MongoDB)

### Backend Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit MONGODB_URI if needed
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Env vars (`.env`):**

```
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=climacred
APP_ENV=development
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
ELECTRICITY_EMISSION_FACTOR_KG_PER_KWH=0.82
WATER_COST_PER_KL_INR=30
DIESEL_EMISSION_FACTOR_KG_PER_LITRE=2.68
PETROL_EMISSION_FACTOR_KG_PER_LITRE=2.31
NATURAL_GAS_EMISSION_FACTOR_KG_PER_KG=2.75
CALCULATION_VERSION=v1.0.0

# --- Gemini AI intelligence layer (Phase 3) ---
# 👉 Put your Google AI Studio key here (this is the ONLY value you must add).
#    backend/.env  →  GEMINI_API_KEY=AIza...your-key...
#    Get a key: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
# Optional overrides
GEMINI_API_BASE=https://generativelanguage.googleapis.com/v1beta
GEMINI_TIMEOUT_SECONDS=25
AI_INSIGHT_CACHE_MINUTES=180
```

> Never hardcode credentials. Provide `.env.example`. All secrets via env.
> `GEMINI_API_KEY` is read **only by the FastAPI backend** — it is never sent to the browser, never returned
> by any endpoint, never stored in MongoDB and never committed (`.env` is git-ignored).

### Frontend Setup

```bash
npm install
# optional: set backend URL
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev    # http://localhost:5173
npm run build  # production single-file build
```

Vite proxies `/api` to `http://localhost:8000` for dev (see `vite.config.ts`).

### MongoDB Setup

- **Local:** `mongod --dbpath ./data/db`
- **Atlas:** set `MONGODB_URI=mongodb+srv://...`
- **Without MongoDB:** backend automatically falls back to `mongomock` in-memory (data not persisted across restarts, but app remains functional).
- **Nothing is inserted at startup.** A fresh database is genuinely empty; every figure in the UI comes from data you entered/imported, from MongoDB, or from backend calculations of that data.

Collections created on startup with indexes:

```
users, business_profiles, climate_assessments, climate_fingerprints, ai_insights,
green_solutions, scenarios, transformation_plans, impact_records, climate_reports
```

Each doc has `created_at`, `updated_at`, `user_id`.

---

## API Endpoints

Swagger at `http://localhost:8000/docs`

| Method | Path | Description |
|--------|------|-------------|
| GET/PATCH/POST | `/api/profile` | Business profile CRUD |
| POST | `/api/profile/reset` | Clear the stored profile (returns `null`) |
| GET/POST/PATCH | `/api/assessment` | Climate assessment CRUD |
| GET | `/api/climate-fingerprint` | Latest fingerprint |
| POST | `/api/climate-fingerprint/generate` | Generate from profile+assessment |
| GET | `/api/climate-fingerprint/analytics/energy` | Energy calc |
| GET | `/api/climate-fingerprint/analytics/water` | Water calc |
| GET | `/api/climate-fingerprint/analytics/waste` | Waste calc |
| GET | `/api/climate-fingerprint/analytics/emissions` | Emissions calc |
| GET | `/api/climate-fingerprint/analytics/mobility` | Mobility calc |
| GET | `/api/climate-fingerprint/analytics/data-quality` | Data quality |
| POST | `/api/climate-fingerprint/anomaly-detection` | IsolationForest or stats (needs history) |
| POST | `/api/climate-fingerprint/forecast` | LinearRegression forecast |
| GET | `/api/solutions` | Catalog (filter `?category=Energy`) |
| GET | `/api/solutions/recommendations?top_n=5` | Personalized recommendations |
| GET | `/api/solutions/{id}` | Single solution |
| POST | `/api/scenarios/simulate` | Simulate (`selected_solution_ids`, `adoption_scale_percent`) |
| GET | `/api/scenarios/history` | History |
| GET/POST | `/api/transformation-plan` | Get / generate plan |
| PATCH | `/api/transformation-plan/{id}` | Update status |
| GET/POST | `/api/impact` | Get / submit impact (`before`, `after`) |
| GET | `/api/impact/metrics` | Frontend-shaped metrics |
| GET/POST | `/api/reports/climate` | Get / generate report |
| GET | `/api/ai/dashboard-insights` | Gemini AI climate insight for the dashboard (auto-loaded, cached, `?refresh=true` to regenerate) |
| POST | `/api/ai/chat` | Floating AI chat assistant (`{message, history[]}`; context is built server-side) |
| GET | `/api/ai/chat/suggestions` | Starter questions for the chat assistant (`has_data` aware) |
| GET | `/api/ai/status` | AI layer status (`gemini_configured`, model, cache TTL) |

All also available under `/api/v1/...` for compatibility.

---

## Gemini AI Intelligence Layer (Phase 3)

The dashboard automatically asks the backend for an AI interpretation of the user's **already stored** data.
The user never pastes data, uploads reports or opens Gemini manually.

**Flow**

```
Dashboard mount
  → GET /api/ai/dashboard-insights
      → ai_insight_service.build_context()   (reuses the existing Phase 2 services:
                                              profile, assessment, fingerprint, analytics,
                                              recommendations, scenario engine, plan, impact)
      → data_signature(context)              (SHA-256 of the stored data state)
      → cache hit?  → return cached insight (no Gemini call)
      → cache miss? → Gemini generateContent → structured JSON → numeric audit → cache
      → Gemini missing/failing? → deterministic "calculated insight" + status notice
```

- **Endpoint:** `GET /api/ai/dashboard-insights` (also `/api/v1/ai/dashboard-insights`, `?refresh=true` bypasses the cache)
- **Service:** `backend/app/services/ai_insight_service.py` · **Route:** `backend/app/api/routes/ai.py`
- **Model:** `GEMINI_MODEL` (default `gemini-2.5-flash`) via the official REST API
  `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` with the `x-goog-api-key` header.
- **Response schema:** `summary`, `recent_changes[]`, `key_risk`, `focus_now`, `priority_action`, `forecast`,
  `expected_impact`, `confidence`, `details{data_used[], reasoning_summary, historical_comparison, main_risks[],
  recommended_actions[], related_recommendations[], expected_impact_detail, confidence_note, assumptions[],
  number_audit{verified, unsupported_values[]}}` plus `calculated` (Phase 2 source-of-truth values),
  `history`, `status`, `source` (`gemini` | `calculated`), `cached`, `disclaimer`.
- **Gemini never invents numbers:** the prompt is restricted to the calculated context and every numeric token
  returned is audited against the context (`number_audit`). Unmatched figures are flagged in the UI.
- **Forecast guardrail:** without earlier snapshots the forecast is forced to
  `"Insufficient historical data for a reliable forecast."`
- **Graceful degradation:** missing key / quota / timeout / bad JSON ⇒ `status: "unavailable" | "error"`,
  `source: "calculated"` and the notice *"AI insights unavailable — showing calculated insights."* —
  the dashboard and every Phase 2 endpoint keep working.
- **Caching:** insights are cached per data signature (default 180 min, `ai_insights` collection) and the
  browser keeps the last payload in `sessionStorage`; Gemini is only called again when stored data changes.
- **Dark mode:** navbar toggle (end of the header) with `localStorage` persistence (`climacred_theme`) and a
  class-based Tailwind v4 dark variant; the existing light palette is remapped in `src/index.css`.

### Floating AI chat assistant

- **UI:** `src/components/chat/AIChatAssistant.tsx` — compact FAB in the bottom-right corner, available on every
  page, titled *"ClimaCred AI Assistant"* with the subtitle *"Ask me about your climate data"*.
- **Endpoint:** `POST /api/ai/chat` with `{message, history[]}`; the backend rebuilds the structured context on
  every request (profile, latest assessment, fingerprint + history, analytics, recommendations, scenarios,
  transformation plan, impact, reports) — never a raw database dump — so follow-up questions in the same
  conversation keep their context.
- **Answer style:** short, business-friendly and action-oriented (Answer / Why / What to do next / Relevant number).
- **Numbers come from the calculation engine**, not from Gemini: the reply is numerically audited against the
  backend context and falls back to the deterministic calculated answer when the model is unavailable.
- **No data yet:** *"I don't have your business climate data yet."* + *"Complete your Climate Assessment and I'll
  analyze it for you."* General (non-business) questions are still answered, clearly separated from data analysis.
- **Errors:** missing/invalid key, quota, timeout or HTTP errors are logged server-side (model + reason) and the
  user only sees *"AI insights are temporarily unavailable."* — never a raw 404 and never an invented answer.

### Data authenticity

- No hardcoded business data ships with the app: `ABC Textile`, the demo assessment numbers and the
  frontend `mockData.ts` fallback are gone (deleted, not hidden).
- Every displayed value is user-entered/imported data, MongoDB data, or a backend calculation of it;
  Gemini only ever *interprets* those values.
- An empty database renders clean empty states — missing values are never replaced with zeros.

---

## Database Collections

Documents are structured, with timestamps and indexes. Example `business_profiles`:

```json
{
  "user_id": "default",
  "business_name": "<name you entered>",
  "industry": "<industry you selected>",
  "employees": 0,
  "created_at": "2026-09-23T...",
  "updated_at": "2026-09-23T..."
}
```

The shape above is the schema only — the values are whatever the user actually submitted.
`backend/seed.py` (developer utility) contains the full field-by-field shapes and refuses to run
without an explicit `--demo` flag.

---

## Climate Scoring Methodology

**Decision-support metric, not official certification.**

- Six dimensions scored 0–100 (100 = best / Low impact, 0 = Very High opportunity)
- **Weights (configurable in `config.py`):** Energy 20%, Water 20%, Waste 15%, Emissions 20%, Mobility 10%, Operations 15% (sum 1.0)
- **Impact levels:** Low 80–100, Moderate 65–79, High 40–64, Very High 0–39
- **Overall Climate Readiness:** weighted sum, labels: Leadership ≥80, Accelerated ≥65, Transition ≥45, At-Risk <45, percentile derived vs. textile benchmark.

**Transparent per-dimension logic (examples):**

- *Energy:* penalty for high kWh/employee (>250 → -18), low efficiency equipment ((100-eff%)*0.25), zero solar -12, diesel hours >40 -10, cost/kWh >10 -8. Bonus for solar ≥30 kWp.
- *Water:* 480k L/mo → -22, litres/employee >2500 → -7, no recycling -18, no rainwater -8, leakage Monthly -9, wastewater Primary -6, groundwater -7. Scores clamped 0–100.
- *Waste:* total >3000 kg → -16, recycling <25% → -14, no segregation -12, textile >2000 kg → -10.
- *Emissions:* total tonnes >30 → -20, diesel >1500 L → -12, primary fuel Diesel/Coal -10, air control None -14.
- *Mobility:* fuel/vehicle >220 → -14, fuel >1200 L → -7, EV 0% → -12, fuel type Diesel -8.
- *Operations:* base 50 + 7 per green practice, ≤1 practice -10, high operating hours + few practices -8.

Each returns `{score, impact_level, current_status, primary_cause, improvement_opportunity, potential_reduction, confidence, metrics_used}`.

Fingerprint generation steps: retrieve profile → assessment → validate → calc dimensions → weighted overall → identify top 3 worst → generate explanations → save → return. Includes `weights_used`, `methodology`, `data_quality`, `calculation_version`, `generated_at`.

---

## Calculation Assumptions

All metrics document assumptions.

- **Energy:** `annual = monthly*12`, `monthly_emissions = monthly_kwh * electricity_factor /1000` (factor configurable, default 0.82 India CEA, stored with `factor, unit, source_label, timestamp, version`; not certified).
- **Water:** `annual = monthly*12`, `potential saving = annual * (recycling_factor + leakage_factor*0.5)` capped 70%; recycling 65% if no system else 20%, leakage Frequent 8% etc. Labeled assumptions.
- **Waste:** `total = sum streams`, `recyclable = total * recycling%`, `recovery opportunity = total * (segregation_bonus + recycling_gap*0.5)` capped 60%.
- **Emissions:** sum per fuel `litres * factor /1000` (diesel 2.68, petrol 2.31, gas 2.75, electricity 0.82), each factor stored with metadata; not verified carbon accounting.
- **Mobility:** `monthly_emissions = fuel * fuel_factor /1000` (fuel_type map), `ev adoption %` derived, potential saving 30% of non-EV fuel.
- **Data Quality:** High >85%, Medium 60–85%, Low <60% completeness; missing fields listed; improves with better inputs.

Every estimated metric exposes `assumptions[]`; every calculated environmental metric retains `factor, unit, source_label, calculation_timestamp`.

---

## ML Methodology

**Lightweight, explainable. No deep learning.**

- **Anomaly detection:** `IsolationForest(contamination=0.15)` if ≥12 historical points; else statistical Z-score >2.0 if ≥6 points; else returns `{"status":"insufficient_data","message":"Insufficient historical data for reliable anomaly detection."}` – never fabricates.
- **Forecasting:** `LinearRegression` on time index if ≥8 points; outputs `predicted_value, lower_bound, upper_bound (±1 std), trend_slope, r_squared, assumptions`; else `insufficient_data` message.
- **Location:** `climate_engine/anomaly_detection.py`, `forecasting.py`; tested via `/analytics/anomaly-detection` and `/forecast`.

---

## How to Run Locally

```bash
# Terminal 1 – Backend
cd backend
pip install -r requirements.txt
cp .env.example .env     # add GEMINI_API_KEY=... (optional; AI layer degrades gracefully without it)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# The API starts with an EMPTY database - no demo business is created.

# Terminal 2 – Frontend
npm install
npm run dev
# Open http://localhost:5173  → Dashboard now shows live backend data (proxy /api)
```

**Verify:**

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/profile
curl http://localhost:8000/api/climate-fingerprint
curl -X POST http://localhost:8000/api/scenarios/simulate -H "Content-Type: application/json" -d '{"selected_solution_ids":["sol-solar","sol-water-ro"]}'
```

---

## Developer-Only Sample Data (optional)

The normal app never creates sample data. If you want a throwaway business to click through the UI:

```bash
cd backend
python seed.py --demo      # refuses to run without an explicit flag
```

It writes a clearly-labelled illustrative business (profile, assessment, fingerprint, plan, report).
The backend never calls this module, so a normal `uvicorn app.main:app` start leaves the database empty.
Never point it at a production database.

---

## How to Enter Your Own Data (normal flow)

The app works only with what you enter, import, or what the backend calculates from it.

1. Update **Business Profile** page → PATCH `/api/profile` (employees, facilityArea, etc.)
2. Complete **Climate Assessment** wizard (6 steps) → POST `/api/assessment` (validates non-negative, % 0–100, EV ≤ vehicles, etc.)
3. Click **Analyze My Business** → POST `/api/climate-fingerprint/generate` (recalculates the current fingerprint; earlier snapshots are kept as history and used for the trend/change comparison)
4. View **Climate Fingerprint** – new scores, top gaps, AI insights personalized: e.g., “Water is highest opportunity because monthly consumption high relative to activity and no recycling recorded.”
5. **Green Solutions** now shows personalized recommendations (not generic solar). Recommendation Score = Impact (30%) + Financial (25%) + Environmental (20%) + Feasibility (15%) + Business Relevance (10%) – weights configurable, transparent breakdown per solution.
6. **Scenario Simulator**: select e.g., `Solar + VFD` or `Water RO + Leak Sensors`, set scale 50–100%, POST `/api/scenarios/simulate` – combined outcomes capped to avoid double counting, assumptions listed.
7. **Transformation Plan**: POST `/api/transformation-plan/generate` – prioritized 4 phases based on actual fingerprint; update status via PATCH.
8. **Impact Verification**: POST `/api/impact` with `{before:{energy_kwh:10000,…}, after:{…}}` → calculates `absolute_change, percentage_change, estimated_impact` with terminology “observed change”, “estimated environmental impact”, “reported implementation outcome” (never “verified carbon reduction” unless verified).
9. **Climate Report**: POST `/api/reports/climate/generate` → structured report with Business Profile, Readiness, Fingerprint, all analyses, priorities, solutions, scenario, plan, impact, assumptions, methodology, data quality, `generated_at, data_period, calculation_version`, distinguishing measured vs calculated vs estimated vs AI insights.

---

## Frontend–Backend Integration

- **Centralized client:** `src/services/api.ts` handles the base URL (`VITE_API_URL` when set, otherwise the same origin plus the Vite `/api` proxy), timeouts, JSON and validation errors. Missing data returns `null`/`[]` — it never falls back to sample business data.
- **API functions:** `getBusinessProfile`, `saveBusinessProfile`, `getClimateAssessment`, `saveClimateAssessment`, `getClimateFingerprint`, `getGreenSolutions`, `runScenarioSimulation`, `getTransformationPlan`, `updateTransformationItemStatus`, `getImpactVerification`, `submitImpactVerification`, `getClimateReport`, plus analytics/anomaly/forecast helpers.
- **Keeps UI:** No redesign – pages, components, animations, charts, navigation, styling preserved; now retrieve real data.
- **Handles states:** loading spinners, success toasts, validation errors (e.g., “EV count cannot exceed total”), server errors, network timeouts (8s), empty states (“No solutions match”).
- **Validation:** frontend + backend (required, non-negative, 0–100%, reasonable ranges, units). Example: `energyEfficientEquipmentPercent 0–100`, `EV count ≤ vehicles`.
- **Performance:** service-layer separation, async, Mongomock fallback, fingerprints/reports cached with timestamps; the current fingerprint is recalculated when the assessment changes, while earlier real snapshots are kept for trends and change comparison.

---

## Testing

```bash
cd backend
python -m pytest tests -v          # 88 tests (50 API + 38 AI layer), Gemini mocked - no network needed
python audit_e2e.py                # optional: 99-check live end-to-end audit (needs the backend running)

cd ..
npx tsc --noEmit                   # type check
npm run build                      # production single-file build (dist/index.html)
npm run preview                    # then, with the backend running:
node frontend_smoke_test.cjs            # 27/27 - empty DB, all pages, no fake data
node frontend_smoke_test.cjs --with-data # 28/28 - same plus a real business seeded through the API
```

Covers:

- Profile creation/patch/validation (negative, range, EV count)
- Assessment validation (negative, 100% recycling, zero consumption, incomplete)
- Fingerprint calculation (dimensions, levels, confidence)
- Energy/water/waste/emissions/mobility calculations & data quality
- Edge: missing data, zero, 100% recycling, no historical data, multiple interventions, incomplete assessment
- Recommendation engine (personalized, not all solar)
- Scenario simulation (single, multiple no double-counting, empty)
- Transformation plan (phases, update status)
- Impact (before/after calc, missing data, terminology)
- Report (distinct data types, metadata)
- Anomaly/forecast insufficient data messages
- AI layer (`tests/test_ai.py`): missing key fallback, Gemini success, prompt contains stored data only,
  numeric audit (unsupported values flagged), forecast forced when no history, quota/transport/JSON failures,
  404 model fallback chain, cache prevents repeated Gemini calls, `?refresh=true`, history included when snapshots exist,
  chat context/follow-ups, chat never ships invented numbers, provider errors never exposed to users
- Data authenticity: no `ABC Textile`/mock/demo literals in code or bundles; empty DB returns empty states;
  the API key never appears in any response

**88 tests, all passing.** UI smoke test: **27/27** on an empty database, **28/28** with real submitted data.

---

## Security & Trust

- Env vars, no hardcoded secrets, `.env.example`
- Input validation (Pydantic + custom), sanitizes Mongo queries (strips `$`)
- CORS configured via `CORS_ORIGINS`
- Structured logging, error handlers (400 validation, 500 generic, never leaks secrets)
- Never fabricates environmental data, never claims government certification / carbon credits / guaranteed savings or financing; every estimate exposes assumptions; calculated metrics retain inputs.

---

## Known Notes

- Mongomock fallback means data resets on backend restart without real MongoDB – for production use real MongoDB.
- Empty database ⇒ clean empty states everywhere (dashboard, analytics pages, chat). Zeros are shown only when a stored value really is zero.
- Fingerprint history: each assessment change stores a new snapshot; the older real snapshots are retained so trends and change comparisons have data. (Transformation plans and generated reports are still regenerated on assessment change.)
- No frontend sample/demo data module exists any more — `src/services/mockData.ts` was removed, not hidden.

---

## License

Built for TerraMind – educational project.

