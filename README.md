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

# --- Gemini (backend only) ---
# The ONLY value you must add. Create a key at https://aistudio.google.com/apikey
GEMINI_API_KEY=
# Optional. Empty = auto-select a model the Gemini API reports for YOUR key and that
# passes a live generateContent probe. Set a model (e.g. one from GET /api/ai/status ->
# available_models) to pin it; it is verified the same way before it is used.
GEMINI_MODEL=
# Optional overrides
GEMINI_API_BASE=https://generativelanguage.googleapis.com/v1beta
GEMINI_TIMEOUT_SECONDS=60
GEMINI_STATUS_CACHE_SECONDS=300
GEMINI_STATUS_ERROR_CACHE_SECONDS=30
AI_INSIGHT_CACHE_MINUTES=180
# Removes the legacy "ABC Textile" demo documents older builds auto-inserted (exact signature only)
PURGE_LEGACY_DEMO_DATA=true
```

> Never hardcode credentials. Provide `.env.example`. All secrets via env.
> `GEMINI_API_KEY` is read **only by the FastAPI backend** from `backend/.env` (resolved relative to the backend
> folder, so it works from any working directory). It is never sent to the browser, never put in a `VITE_*`
> variable, never returned by any endpoint, never stored in MongoDB and never committed (`.env` is git-ignored).
> Restart the backend after editing `backend/.env`.

### Frontend Setup

```bash
npm install
# optional: set backend URL (never put GEMINI_API_KEY in any frontend .env / VITE_* variable)
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev    # http://localhost:5173
npm run build  # production single-file build
```

Vite proxies `/api` to `http://localhost:8000` for dev (see `vite.config.ts`).

### MongoDB Setup

- **Local:** `mongod --dbpath ./data/db`
- **Atlas:** set `MONGODB_URI=mongodb+srv://...`
- **Without MongoDB:** backend automatically falls back to `mongomock` in-memory (data not persisted across restarts, but app remains functional).
- **Nothing is inserted at startup, on connect, or on first page load.** A fresh database is genuinely empty;
  every figure in the UI comes from data you entered, from MongoDB, or from backend calculations of that data.
- **Legacy cleanup at startup:** the only data operation at startup *removes* documents that match the exact
  signature of the "ABC Textile" demo that builds up to commit `a9db8ba` auto-inserted (see below).
  Inspect a database read-only with `python -m app.database.legacy_demo` (from `backend/`), remove with `--apply`.

Indexes are ensured at startup for:

```
business_profiles, climate_assessments, climate_fingerprints, scenarios, transformation_plans,
impact_records, climate_reports, ai_insights, ai_conversations, green_solutions
```

Each doc has `created_at`, `updated_at`, `user_id`.

---

## API Endpoints

Swagger at `http://localhost:8000/docs`

| Method | Path | Description |
|--------|------|-------------|
| GET/PATCH/POST | `/api/profile` | Business profile CRUD |
| POST | `/api/profile/reset` | Development reset: deletes **all** stored data of the current user (profile, assessment, fingerprints, plans, scenarios, reports, impact, AI caches, chat memory) → `{"has_data": false, "data": null, "deleted": {...}}` |
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
| GET | `/api/ai/status` | Real Gemini connection check (verified model + live `generateContent`, cached briefly; `?refresh=true`) |
| POST | `/api/ai/chat` | `{message, conversation_id?}` → `{answer, provider: "gemini", model, conversation_id, status, ...}` |
| DELETE | `/api/ai/chat/{conversation_id}` | Clear a conversation's server-side memory ("Clear chat") |
| GET | `/api/ai/chat/suggestions` | The four starter questions + `has_data` |
| GET | `/api/ai/dashboard-insights` | Gemini dashboard insight (auto-loaded, cached per data signature, `?refresh=true`) |

All also available under `/api/v1/...` for compatibility.

---

## Gemini AI Layer

### Root cause of the old "Gemini API error 404" (fixed)

The previous code sent `generateContent` requests blindly to a hardcoded chain
`gemini-2.5-flash → gemini-2.0-flash → gemini-1.5-flash`. As of September 2026:

- `gemini-1.5-*` models are shut down (404 for everyone),
- `gemini-2.0-flash` was shut down on **2026-06-01** (404 for everyone),
- `gemini-2.5-*` models are limited by Google to projects that used them before; keys from newer projects get
  `404 "This model models/gemini-2.5-flash is no longer available to new users"`.

So every candidate could answer 404 and the UI showed "Gemini API error 404". The URL format and the
`x-goog-api-key` header were correct; the model names were not usable. There is no hardcoded model chain any more.

### How the backend talks to Gemini (`backend/app/services/gemini_client.py`)

- Official REST API `https://generativelanguage.googleapis.com/v1beta` — `models.list`, `models.get`,
  `models.generateContent` — authenticated with the `x-goog-api-key` header (works for standard and the new
  authorization keys; the key never appears in a URL, log line, response or the database).
- **Model verification before use:** a configured `GEMINI_MODEL` must exist for the key, list `generateContent` in
  `supportedGenerationMethods` (models.get) **and** answer a tiny real `generateContent` probe. With `GEMINI_MODEL`
  empty, the newest stable Flash-family model that `models.list` reports for the key is probed and used.
- Requests follow current Gemini 3 guidance: no temperature override (default 1.0), generous `maxOutputTokens`
  (thinking tokens share the budget), `responseMimeType` JSON for insights / text for chat, thought parts skipped.
- Failures are classified (invalid/unauthorised key, API disabled, model not found, model not available to the
  project, quota, timeout, unreachable) into a **safe** message; raw provider text is only logged server-side.

### `GET /api/ai/status`

```json
{"provider":"Google Gemini","configured":true,"authenticated":true,"model":"<verified model>","status":"connected"}
{"provider":"Google Gemini","configured":false,"authenticated":false,"model":null,"status":"not_configured","message":"GEMINI_API_KEY is not set in backend/.env."}
{"provider":"Google Gemini","configured":true,"authenticated":false,"model":null,"status":"error","message":"Gemini rejected the API key (HTTP 400 ... API_KEY_INVALID) ..."}
{"provider":"Google Gemini","configured":true,"authenticated":false,"model":null,"status":"unreachable","message":"Could not reach the Gemini API ..."}
```

`connected` is reported **only** after a verified model answered a real `generateContent` request — a key that merely
exists is not "connected". Results are cached (5 min when connected, 30 s after an error; `?refresh=true` re-checks)
and every real chat/insight call updates the status. Model errors also return `available_models` for the key.

**Navbar indicator** (`src/components/layout/GeminiStatusIndicator.tsx`, next to the Dark Mode toggle):
`● Gemini Connected` / `● Gemini Not Connected` (no key or API unreachable) / `● Gemini Checking...` /
`● Gemini Error`. Clicking it shows *Gemini · Status · Model · Last checked* plus the reason and "Re-check now".

### Dashboard insight — `GET /api/ai/dashboard-insights`

```
Dashboard mount → build_context()  (stored profile, latest assessment, fingerprint, 5 resource analytics,
                                    recommendations, current-assessment scenario runs, plan, impact, history)
                → data_signature → cache hit? return it : Gemini generateContent (JSON) → number audit → cache
```

- Sections: **What Changed · Key Risk · What To Do Next · Trend / Forecast · Expected Impact** (+ "More Info").
- `status`: `no_data` (nothing stored → no AI call, `insight: null`) · `ok` (`source: "gemini"`, verified `model`) ·
  `not_configured` / `unreachable` / `error` (`insight: null` + safe `message`). There is **no template insight**
  pretending to be AI; the dashboard's calculated metrics (`calculated`) are always the source of truth.
- Numbers: Gemini may only reuse numbers present in the context; every number is audited (`number_audit`) and
  unmatched figures are flagged. Without stored history the forecast is forced to *"Insufficient historical data
  for a reliable forecast."* Missing values must be written as *"Insufficient data."*

### Floating chat — `POST /api/ai/chat`

```json
// request
{"message": "What's my biggest climate risk?", "conversation_id": "optional"}
// response
{"answer": "...", "provider": "gemini", "model": "<verified model>", "conversation_id": "...", "status": "ok",
 "has_data": true, "number_audit": {"verified": true, "unsupported_values": []}}
```

- Every answer is generated by Gemini. If Gemini cannot answer, `answer` is `null` and `status`/`message` explain
  why — the UI shows *"No answer from Gemini. <reason>"*. No canned chatbot answers exist in backend or frontend.
- Context is gathered server-side from stored data only (compact, never a DB dump). With no stored data the
  context says so and Gemini is instructed to answer *"I don't have your business climate data yet. Complete your
  Climate Assessment and I'll analyze your actual data."* (greetings and product questions are answered normally).
- **Follow-ups:** conversation memory is stored server-side (`ai_conversations`) under `conversation_id`, so
  "How can I reduce it?" resolves "it". Cost questions use scenario / catalog investment data from the context,
  otherwise *"The application does not currently have that value."* "Clear chat" deletes the memory.
- Unverified numbers trigger one corrective retry; if any remain, the answer is shown with those values flagged.
- UI: `src/components/chat/AIChatAssistant.tsx` — bottom-right "ClimaCred AI" FAB, *"ClimaCred AI Assistant"*,
  *"Ask me about your climate data"*, the four suggestions, loading / error states, Clear chat, dark + light mode.
  Nothing is written to browser storage.

### Troubleshooting Gemini

| `GET /api/ai/status` says | Fix |
|---|---|
| `not_configured` | Put `GEMINI_API_KEY=...` in `backend/.env`, restart the backend. |
| `error` · `auth` (400 API_KEY_INVALID / 401 / 403) | Create a new key in Google AI Studio (standard/unrestricted keys are being rejected in 2026), enable the Gemini API for the project, update `backend/.env`. |
| `error` · `model_not_found` / `model_unavailable` (404) | Leave `GEMINI_MODEL` empty (auto-select) or set one of `available_models`. |
| `error` · `quota` (429) | Wait / check plan & billing of the key's project. |
| `unreachable` | The server cannot reach `generativelanguage.googleapis.com` (network, proxy, firewall). |

## Fake Data: Root Cause & Removal

**Fake data source found at:** the MongoDB database `climacred` (collections `business_profiles`,
`climate_assessments`, `climate_fingerprints`, user_id `default`). Builds up to commit `a9db8ba` auto-**inserted** an
"ABC Textile Manufacturing Ltd." business the first time `GET /api/profile` / `GET /api/assessment` found no document
(`profile_service.get_profile` / `assessment_service.get_assessment` wrote hardcoded defaults: Tirupur, 145
employees, 38,000 sq.ft, 38,500 kWh, 480,000 L, 3,600 kg textile scrap, 1,950 L fleet fuel), and
`GET /api/climate-fingerprint` stored a fingerprint calculated from it (47.5/100). `seed.py --demo` wrote the same
values. The current code no longer inserted anything, but those documents stayed in MongoDB and were served as real
data; the 36.5 t CO₂e was calculated live from them (38,500×0.82 + 1,620×2.68 + 240×2.31 = 36.47 t). The old
`POST /api/profile/reset` deleted only the profile, so the assessment, fingerprint and emissions survived a reset.

**Removed by:**

- startup purge of documents matching the exact legacy signature (`app/database/legacy_demo.py`): pure demo
  documents are deleted; where a user edited the auto-inserted demo, their edits are kept and only leftover demo
  values are removed; results derived from demo inputs (fingerprints, plans, reports, scenarios, AI caches) are
  removed and recalculated on demand; user-entered data is never touched;
- `POST /api/profile/reset` (Settings → "Reset All Stored Data") now deletes **every** per-user collection;
- derived documents are never served without the real profile + assessment they came from (no orphans);
- the dashboard Waste card now shows the backend's total of all waste streams (it used to show only the textile
  field — the old "3,600 kg");
- the frontend removes stale `sessionStorage`/`localStorage` keys left by older builds (AI insight / chat
  transcript caches) and keeps only `climacred_theme` and `climacred_preferences`. IndexedDB was never used.

Only two data states exist: **no data** → clean empty states everywhere; **real data** → real backend calculations
+ Gemini interpretation.

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
cp .env.example .env     # then set GEMINI_API_KEY=... in backend/.env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# The API starts with an EMPTY database - nothing is seeded; legacy demo documents are removed.

# Terminal 2 – Frontend
npm install
npm run dev
# Open http://localhost:5173  → Dashboard now shows live backend data (proxy /api)
```

**Verify:**

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/ai/status            # "connected" only after a live generateContent call
curl -X POST http://localhost:8000/api/ai/chat -H "Content-Type: application/json" -d '{"message":"Hello"}'
curl -X POST http://localhost:8000/api/profile/reset # development reset -> empty app
curl http://localhost:8000/api/profile
curl http://localhost:8000/api/climate-fingerprint
curl -X POST http://localhost:8000/api/scenarios/simulate -H "Content-Type: application/json" -d '{"selected_solution_ids":["sol-solar","sol-water-ro"]}'
```

---

## Developer-Only Sample Data (optional)

The normal app never creates sample data. If you want a throwaway business to click through the UI:

```bash
cd backend
python seed.py --demo            # refuses without the flag, and refuses if real user data exists
python seed.py --demo --force    # overwrite the stored data of user "default"
```

It writes a clearly-labelled illustrative business (profile, assessment, fingerprint, plan, report, impact),
tagged `data_origin="developer_seed_script"`. The application never imports or runs this module, so a normal
`uvicorn app.main:app` start leaves the database empty. Remove it with `POST /api/profile/reset`.
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
python -m pytest tests -v          # 104 tests (54 API + 39 Gemini layer + 11 legacy-data), Gemini API faked - no network needed
python audit_e2e.py                # optional: 99-check live end-to-end audit (needs the backend running)

cd ..
npx tsc --noEmit                   # type check
npm run build                      # production single-file build (dist/index.html)
npm run preview                    # then, with the backend running:
NODE_PATH=... node frontend_smoke_test.cjs            # 33/33 - empty DB, indicator, chat, all pages, no fake data
NODE_PATH=... node frontend_smoke_test.cjs --with-data # 34/34 - same plus a real business seeded through the API
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
- Gemini layer (`tests/test_ai.py`, fake Gemini REST API): status not_configured / connected only after a live
  generateContent / auto-selection skipping models restricted to existing projects / retired configured model
  detected without blind calls / invalid key / 403 / 429 / unreachable / caching; chat contract, conversation
  memory, clear chat, no canned answers, stored-data-only context, backend numbers for budget & scenarios,
  unverified numbers retried then flagged; insights no_data / ok / explicit errors / cache / audit
- Legacy data (`tests/test_legacy_demo.py`): real dumps produced by the old code (`tests/fixtures/`) are removed at
  startup, user data and user edits are preserved, derived demo snapshots are removed, nothing is seeded
- Data authenticity: no `ABC Textile`/mock/demo literals in code or bundles; empty DB returns empty states;
  the API key never appears in any response

**104 tests, all passing.** UI smoke test: **33/33** on an empty database, **34/34** with real submitted data.
Live audit: **99/99**.

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
- Gemini models change quickly (2.0 shut down 2026-06-01; 2.5 restricted for new projects). Leave `GEMINI_MODEL`
  empty to use the newest verified model, or pin one from `GET /api/ai/status` → `available_models`.

---

## License

Built for TerraMind – educational project.

