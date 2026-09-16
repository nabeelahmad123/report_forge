# PFASuiki Demo Project — "Lab Intelligence Suite"
## Build Specification for Claude (or any coding agent)

---

## 0. Context: Why This Exists

**Target company:** PFASuiki (Oberhaching, near Munich) — climate-tech startup, TDK spin-out, ~11–50 employees. They build electrochemical oxidation (EO) systems that destroy PFAS ("forever chemicals") in contaminated water. Their product line is called **AquaHive**. Typical application: treating landfill leachate.

**The job I'm applying for:** Cloud & Data Engineering Intern / Working Student. Their stated tasks include:
- Maintain/optimize GCP + Firebase cloud infrastructure
- Expand their TypeScript/JavaScript laboratory data platform
- Build data pipelines connecting experimental data → databases → dashboards
- Translate scientific Python analysis into scalable web workflows
- **Identify and implement LLM/AI integrations for data synthesis, automated reporting, and environmental/industry intelligence**

**The goal of this demo:** Prove I can deliver their roadmap, not just talk about it. One deployed, clickable product that shows: Python data pipelines + LLM + TypeScript/JS frontend + GCP-style architecture. This document is the spec — build it fast, make it look production-grade, deploy it for free, and optimize for "wow in 60 seconds."

**Non-negotiables:**
- Deployed and live at a public URL (free tier is fine)
- Demo-able in <60 seconds without reading docs
- Fake data must look *scientifically plausible* (electrochemistry, PFAS analytics)
- Mirror PFASuiki's stack wherever reasonable: **TypeScript/JavaScript web frontend, Python analysis backend, GCP/Firebase services, dashboard UI**
- Total build time target: **3–5 days**. Treat 2–4 as the happy path; §13's Day 4 is buffer, not slack — if you're behind, cut RegWatch live-fetch (§8) entirely rather than compressing testing/deploy/README.
- Public repo names the company before any employment relationship exists — read §1's disclosure requirement as non-negotiable, not decoration, and be comfortable with that framing before publishing.

---

## 1. Product Overview

**Name (working title):** PFAS Lab Intelligence Suite (make clear in the UI it's an unsolicited demo by a candidate, not affiliated with PFASuiki)

**One-liner:** Upload electrochemical experiment data → get an AI-generated lab report in seconds + a weekly digest of PFAS regulatory news.

**Two modules:**

### Module A: AI Lab Report Generator ("ReportForge")
- Input: CSV of electrochemical PFAS degradation experiment(s)
- Processing: Python analysis pipeline → computes degradation metrics, anomalies, electrode efficiency trends
- Output: LLM-generated structured lab report (Markdown, downloadable as .md/.pdf), rendered in a clean web UI

### Module B: Regulatory Intelligence Feed ("RegWatch")
- A background job that fetches PFAS-related regulatory/environmental news (EU focus: ECHA, Umweltbundesamt, EPA if available via RSS)
- LLM summarizes each item into a structured digest card: headline, source, date, 2–3 sentence summary, relevance tag (Regulation / Litigation / Science / Industry)
- Displayed as a feed in the dashboard
- **Demo shortcut:** Since live scraping may be flaky on free tiers, ship with a pre-seeded snapshot of 6–8 realistic news items (clearly dated), with live-fetch as an optional enhancement. The button "Fetch latest" can attempt live fetch and fall back to the snapshot gracefully.

---

## 2. User Flow (the 60-second demo path)

1. Landing page → big hero: *"Turn electrochemical experiment data into reports in seconds"*
2. One-click **"Load demo dataset"** button (this is the key demo feature — no file hunting)
3. User sees: data preview table + auto-computed metrics (see §4)
4. User clicks **"Generate AI Report"**
5. Loading state (3–8 s, animated) → structured report renders in a reading pane
6. Sidebar/nav: **RegWatch** → feed of PFAS regulatory digest cards
7. Footer/banner: *"Unsolicited demo by [Name] — candidate for Cloud & Data Engineering. Built with TypeScript, Python, LLMs, GCP-ready architecture."* + GitHub link + email

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (deploy on Vercel/Netlify — free)             │
│  TypeScript + React + Vite + Tailwind                    │
│  Pages: Landing | Upload/Report | RegWatch feed          │
└──────────────┬──────────────────────────────────────────┘
               │ HTTPS / JSON
┌──────────────▼──────────────────────────────────────────┐
│  Backend API (deploy on Cloud Run — free tier)           │
│  Python 3.11, FastAPI                                    │
│  Endpoints:                                              │
│   POST /analyze     (CSV in → metrics + report JSON out) │
│   POST /report      (LLM call, streaming optional)       │
│   GET  /feed        (regulatory digest items)            │
│   POST /fetch-news  (trigger live fetch, optional)       │
└──────┬────────────────┬───────────────────────────────────┘
       │                │
┌──────▼───────┐  ┌─────▼──────────────┐
│ LLM Provider │  │ Firestore (or      │
│ OpenAI API or│  │ SQLite for demo)   │
│ Gemini API   │  │ - experiments      │
│ (env key)    │  │ - reports          │
└──────────────┘  │ - news items       │
                  └────────────────────┘
```

**GCP/Firebase mapping (state this explicitly in the README — it shows the demo mirrors their stack):**
- Frontend hosting → **Firebase Hosting** (or Vercel, note Firebase as the "GCP-standard" choice)
- Backend → **Cloud Run** container (Dockerfile required, shows Docker skills)
- DB → **Firestore** in production mode; for a zero-config demo, SQLite with a `FIRESTORE_EMULATOR` flag is acceptable — document the switch
- Auth: **skip** (demo doesn't need login; note Firebase Auth as the production path)

**Simplification clause:** If Cloud Run deployment becomes painful, fall back to: frontend on Vercel + backend on **Render/Railway free tier** + SQLite. A live demo beats architectural purity. Document both paths in README.

---

## 4. Data Model

### 4.1 Experiment CSV schema (what the user uploads / what demo data follows)

| Column | Type | Unit | Notes |
|---|---|---|---|
| `run_id` | string | — | e.g. `RUN-2026-014` |
| `timestamp` | datetime | — | ISO 8601, usually 30–90 min runs |
| `sample_id` | string | — | e.g. `LEACHATE-B12` |
| `pfas_compound` | string | — | PFOA / PFOS / PFHxS / PFNA |
| `concentration_ug_l` | float | µg/L | declining over time |
| `current_a` | float | A | ~5–50 A |
| `voltage_v` | float | V | ~5–20 V |
| `energy_kwh` | float | kWh | cumulative or per-interval |
| `flow_rate_l_min` | float | L/min | |
| `electrode_pair` | string | — | e.g. `BDD-#3` (boron-doped diamond) |
| `temperature_c` | float | °C | |
| `ph` | float | — | |

### 4.2 Computed metrics (Python analysis layer)

Must compute and display before/inside the report:
- **Degradation efficiency (%)** per compound: `(C0 - C_end) / C0 * 100`
- **Half-life estimate**: fit exponential decay `C(t) = C0 * exp(-k t)` → report `k` and `t_1/2`
- **Energy per order of magnitude (EEO), kWh/m³/order**: energy needed to reduce concentration by 90% — the standard figure of merit in EO water treatment
- **Electrode efficiency trend**: energy consumption per unit degradation across the run (drift = electrode wear signal — mirrors battery capacity fade, my Huawei thesis work). Make this callback explicit and visible, not just an internal metric: name it in the Electrode Health report section (§4.3.4) and in one README sentence ("the electrode-wear detection here uses the same drift-signal approach as capacity-fade analysis in my thesis work on Li-ion batteries at Huawei") — this is the single most distinctive credibility signal in the whole demo and should not be buried in code comments
- **Anomaly flags**: e.g., voltage spikes >2σ, pH out of 6–9 range, flow interruptions
- **Run comparison** (if multiple runs/compounds in one CSV): table + grouped bar chart

### 4.3 Report structure (LLM output contract)

The LLM must return structured Markdown with these exact sections:
1. **Executive Summary** — 3–4 sentences: what was tested, headline result, key concern
2. **Degradation Performance** — per-compound efficiency, half-life, comparison to typical EO benchmarks. **Do not rely on the LLM's general knowledge for benchmark numbers** — it will produce plausible-sounding but unverifiable figures. Instead hardcode 2–3 real published EO/PFAS degradation benchmark ranges (with citation) into `scripts/generate_demo_data.py` or a small `benchmarks.json`, pass them in the same structured JSON payload as the computed metrics, and instruct the model to compare only against those provided values
3. **Energy Analysis** — EEO values, cost implication hint
4. **Electrode Health** — efficiency trend interpretation, degradation signal
5. **Anomalies & Data Quality** — flagged events with timestamps
6. **Recommendations** — 3–5 concrete next steps (e.g., "RUN-014 shows EEO 18% above baseline — inspect BDD electrode pair #3 before next cycle")
7. **Appendix** — metric table

**Prompt engineering requirements:**
- System prompt: "You are a senior electrochemical water treatment engineer writing internal lab reports for PFAS degradation experiments. Be precise, quantitative, and honest about uncertainty. Never invent numbers — only use metrics and benchmark values provided in the JSON payload. Do not cite benchmark figures from memory."
- Pass metrics **and the hardcoded benchmark values (§4.3.2)** as a **structured JSON payload**, never raw CSV to the LLM (cost + reliability)
- Instruct the model to explicitly say "insufficient data" rather than hallucinate when a metric is missing
- Model choice: GPT-4o-mini / GPT-4.1-mini or Gemini Flash (cheap + fast); temperature 0.2

### 4.4 RegWatch item schema

| Field | Notes |
|---|---|
| `title` | news headline |
| `source` | e.g. ECHA, UBA, chemistryworld.com |
| `published_at` | date |
| `url` | link |
| `summary` | 2–3 LLM-written sentences |
| `category` | Regulation / Litigation / Science / Industry |
| `relevance_score` | 1–5, LLM-assessed (5 = direct impact on EO treatment operators) |

---

## 5. Frontend Requirements (TypeScript/React)

- **Stack:** React 18 + Vite + TypeScript + Tailwind CSS. Charts: **Recharts** (React-native feel) or Plotly.js.
- **Design language:** clean, scientific, dark-on-light, green/teal accents (climate-tech vibe). Look like a real R&D tool, not a hackathon project. Take visual cues from the PFASuiki site (teal/cyan, technical aesthetic) without copying branding.
- **Key screens:**
  1. **Landing:** hero + "Load demo dataset" CTA + short module descriptions
  2. **Report view:** left = metrics cards + charts (degradation curves, energy trend, comparison bars); right = rendered Markdown report + "Download .md" / "Copy" buttons
  3. **RegWatch:** card feed with category filter chips, relevance badges, source links
- **Loading states everywhere** — skeleton loaders, no blank screens.
- **Demo data seeding:** "Load demo dataset" fetches a pre-built CSV (3 runs × PFOA/PFOS/PFHxS, 90-min resolution, ~200 rows total) bundled with the frontend or served from backend `/demo-data`.

---

## 6. Backend Requirements (Python/FastAPI)

- `POST /analyze` — accepts CSV file or run_id of demo data → returns metrics JSON
- `POST /report` — accepts metrics JSON → returns Markdown report (LLM)
- `GET /feed` → returns digest items (newest first)
- `POST /fetch-news` → (optional, flag-gated) live RSS fetch of ECHA/UBA/EPA PFAS news + LLM summarization + upsert into DB
- Strict typing (pydantic models), docstrings, `/docs` (FastAPI auto) must be enabled
- **pytest suite:** at least 8 tests — metric calculations (2), decay fitting (2), API endpoints (3), report generation with mocked LLM (1). Include a GitHub Actions CI workflow (`.github/workflows/ci.yml`) — job post mentions CI/CD.
- `Dockerfile` for the backend (slim Python image), plus `docker-compose.yml` for one-command local run.

---

## 7. Demo Dataset Generation

Write a small script `scripts/generate_demo_data.py` that produces the demo CSV deterministically (seeded RNG):
- 3 runs: one "good" run (95%+ degradation, stable electrode), one "degraded electrode" run (efficiency drift + voltage noise), one "interrupted flow" run (anomaly: concentration plateaus mid-run)
- Exponential decay with realistic noise; voltage/current jitter; pH drift toward acidic as treatment progresses
- This dataset is the demo's hidden weapon: the report generator will *find and explain the anomalies*, which is the "wow" moment.

---

## 8. RegWatch Implementation

- **Primary (build this, it's the whole deliverable):** seed 6–8 realistic digest items as JSON (fabricated but plausible: e.g., "ECHA proposes PFHxS restriction amendment," "EU drinking water directive tightening," "US EPA new MCLs enforcement" — mark clearly as demo snapshot in the UI footer: *"Sample data — live feed available on request"*).
- **Stretch only (Day 4/5, skip without guilt if behind schedule):** RSS feeds from ECHA newsroom + UBA press + EPA news, fetch via `feedparser`, summarize with LLM, cache 24 h. Wrap in try/except; on failure return snapshot with a banner. **Do not let live fetch break the demo, and do not let it delay shipping the snapshot version.** The snapshot alone fully satisfies the acceptance criteria in §12 — live fetch adds polish, not correctness.

---

## 9. Deployment Checklist (in order)

1. Backend container → Cloud Run (or Render fallback); verify `/docs` loads
2. Frontend → Vercel/Netlify (or Firebase Hosting); wire `VITE_API_URL` env var
3. Seed demo data + RegWatch snapshot (one-time script or on startup)
4. Test full flow on mobile + desktop
5. **Public demo URL works with zero setup, zero login, zero API key required from the viewer**
6. GitHub repo: README with architecture diagram, screenshots/GIF of the demo, "Built as an unsolicited demo for PFASuiki" section, stack mapping table (§3), local dev instructions, test badge

---

## 10. Quality Bar — "Production-Grade Signals"

These small touches signal engineering maturity to a startup CTO:
- `.env.example` with every config variable documented
- `ruff`/`black` formatting + pre-commit config
- Structured logging (not `print`)
- Pydantic validation on all API boundaries
- Graceful LLM failure handling: if the LLM call fails, fall back to a template-generated report from metrics ("AI unavailable — showing template report") — never crash
- Rate limiting on `/report` (simple in-memory limiter is fine)
- Honest disclaimer in every LLM-generated report: *"Generated with AI assistance — verify before experimental decisions."*

---

## 11. What NOT to Do

- ❌ Don't build user auth/accounts — zero demo value, eats a day
- ❌ Don't fine-tune or RAG anything — overkill; good prompting + structured metrics is enough
- ❌ Don't use PFASuiki's actual logo/branding — "inspired by" aesthetic only, and label clearly as unofficial
- ❌ Don't make the demo require any file upload knowledge — "Load demo dataset" must work
- ❌ Don't spend >1 day on RegWatch live scraping — snapshot first
- ❌ Don't hardcode API keys anywhere — env vars only, `.env` gitignored

---

## 12. Acceptance Criteria (Claude: verify all before finishing)

- [ ] `docker compose up` runs the full stack locally in one command
- [ ] "Load demo dataset" → metrics render → "Generate AI Report" → full Markdown report appears, containing the pre-seeded anomalies (degraded electrode run, flow interruption) correctly identified
- [ ] RegWatch page shows digest cards with categories and sources
- [ ] All 8+ pytest tests pass in CI (GitHub Actions green badge)
- [ ] Backend deployed publicly, frontend deployed publicly, full flow works from the public URL on a phone
- [ ] LLM failure fallback path tested and documented in README
- [ ] README contains: architecture diagram, demo GIF, stack-mapping table, "why I built this for PFASuiki" note, contact info

---

## 13. Suggested Build Order (parallelizable where noted)

- **Day 1:** Project scaffolding (frontend + backend + compose) → demo data generator → `/analyze` endpoint + metric computations + tests
- **Day 2:** LLM report endpoint with prompt + structured payload (incl. hardcoded benchmarks, §4.3) → fallback template → frontend report view with charts
- **Day 3:** RegWatch snapshot mode → polish UI → Dockerfile/CI → deploy backend + frontend. **This is a shippable, criteria-complete demo — treat Day 3 end as the real deadline.**
- **Day 4 (buffer):** whatever slipped from Days 1–3 — tests, deploy flakiness, mobile check, README, demo GIF. Do not start Day 5 work until Day 4's core items are done.
- **Day 5 (optional stretch, only if Day 4 finished early):** RegWatch live news fetch. Skip entirely if it would cut into README/GIF/testing time.

---

*Spec author: candidate applying to PFASuiki. Build target: an interview-winning, 60-second demo of AI-powered lab reporting + regulatory intelligence for PFAS electrochemical treatment R&D.*
