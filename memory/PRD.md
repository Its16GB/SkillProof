# SkillProof — Product Requirements

## Original Problem Statement
> "A web app that lets a candidate know what skills he needs to have for a
> particular role in a particular region anywhere in the world based on the
> experience. The result has to be job-posting based, proof it has to show
> like out of 50 job postings these are the common skills required for a
> person with these many years of experience. Can be any role anywhere in
> the world. It has to be deployable and easily maintained for future
> versions."

## User Choices (confirmed)
- Job source: **Adzuna (live postings)** + AI-suggested gap skills
- Skills extraction: **AI (Claude Sonnet 4.6 via Anthropic API)**
- Inputs: role/title, country, city (optional), years of experience
- Outputs: skill frequency, grouped skills, salary insights, top companies,
  top titles, sample proof postings, AI-suggested gap skills
- Auth: **none** (open-source, public tool)

## Architecture
- **Backend** — FastAPI (`/app/backend/server.py`)
  - `GET /api/countries` → 19 Adzuna-supported countries
  - `POST /api/analyze` → fetch up to 50 Adzuna postings, run Claude
    Sonnet 4.6, aggregate salary/companies/titles, persist to Mongo
  - `GET /api/recent?limit=1..50` → recent analyses
- **Frontend** — React 19 + Tailwind + Shadcn/UI + Recharts
  - Single page (`/app/frontend/src/pages/Analyzer.jsx`)
  - Components: `SearchForm`, `LoadingPanel`, `ResultsDashboard`
- **Data** — Mongo `analyses` collection (persistence, non-critical)
- **Env keys** (`backend/.env`): `MONGO_URL`, `DB_NAME`, `ADZUNA_APP_ID`,
  `ADZUNA_APP_KEY`, `ANTHROPIC_API_KEY`

## Users
- **Candidate** — figures out which skills to add to CV for a target role
- **Career coach / HR analyst** — sees objective, posting-backed evidence

## Implemented (Feb 2026)
- Adzuna live job fetch (up to 50 postings)
- Claude Sonnet 4.6 skills extraction, batch analysis of descriptions
- Frequency + categorised skills (technical/tools/soft/certification)
- AI-suggested gap skills badge
- Salary aggregation (min/max/avg)
- Top hiring companies, top titles
- Evidence panel with live sample postings linking to Adzuna
- Responsive Swiss/high-contrast dashboard UI (DM Serif Display + IBM Plex
  Sans + JetBrains Mono)
- Testing agent 100% frontend, 92% backend on first pass; fixes applied for
  `/api/recent` validation, uppercase country codes and category coercion

## Backlog / Next steps
- **P0** — none blocking (MVP done)
- **P1**
  - Result caching (TTL on role+country+years) to save LLM credits
  - Migrate `@app.on_event` to FastAPI lifespan
  - Share link / permalink for a saved analysis
- **P2**
  - "Compare two roles" side-by-side view
  - CV upload → gap report vs. desired role
  - Export as PDF / Notion-friendly Markdown
