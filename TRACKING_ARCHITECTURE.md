# Tracking Infrastructure — Architecture Specification

## Goal

Deliver monthly inflation reports to consórcio survey respondents via personalized links, track their engagement (opens, time-on-page, downloads), and export clean data for econometric analysis. Each respondent sees only their own link — no shared access, no email exposure.

---

## Current Status (as of May 2026)

### Completed:
- [x] Supabase project created and SQL schema deployed
- [x] Supabase URL and anon key configured in `site/index.html`
- [x] GitHub repo created under org `pesquisa-inflacao` (public)
- [x] GitHub Pages enabled (source: `main` branch, `/ (root)`)
- [x] First report generated (`reports/2026-05.html`) and deployed to `site/reports/`
- [x] Viewer page (`site/index.html`) working with tracking + HTML download
- [x] Test tokens generated for 5 people — tracking confirmed working
- [x] Download button appears only after user scrolls to bottom

### Next Steps:
- [ ] Build bulk token generation + link distribution workflow from Qualtrics export
- [ ] Send personalized links to all opted-in respondents
- [ ] Monthly: update data → generate report → push → send links

---

## Live URLs

- **GitHub repo:** https://github.com/pesquisa-inflacao/inflation_report
- **Pages base:** https://pesquisa-inflacao.github.io/inflation_report/site/index.html
- **Report link format:** `https://pesquisa-inflacao.github.io/inflation_report/site/index.html?token=TOKEN&report=YYYY-MM`
- **Supabase project:** https://smawkkjarjcbqcaxpdoh.supabase.co

---

## System Overview

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  Qualtrics       │     │  GitHub Pages          │     │  Supabase            │
│  (survey export) │────▶│  (report viewer)       │────▶│  (tracking backend)  │
│                  │     │                        │     │                      │
│  emails +        │     │  - Reads token from URL │     │  - Logs open events  │
│  response IDs    │     │  - Renders report HTML  │     │  - Logs heartbeats   │
└────────┬─────────┘     │  - Tracks engagement   │     │  - Logs downloads    │
         │               │  - Offers HTML download │     │  - REST API (free)   │
         ▼               ��──────────────────────┘     └──────────┬──────────┘
┌─────────────────┐                                              │
│  Token Generator │                                              ▼
│  (Python script)  │                                   ┌─────────────────────┐
│                   │                                   │  Analysis            │
│  email → token    │                                   │  (Python script)     │
│  mapping CSV      │                                   │  merge tracking +    │
│                   │                                   │  Qualtrics data      │
└───────────────────┘                                   └─────────────────────┘
```

---

## Directory Structure

```
inflation_report/
├── REPORT_SPEC.md              # Report format specification (canonical reference)
├── TRACKING_ARCHITECTURE.md    # This file
├── data/
│   └── incc_report_input.xlsx  # Inflation data (update monthly)
├── reports/
│   └── 2026-05.html            # Monthly reports (Claude Code writes these)
├── site/                       # GitHub Pages deployment
│   ├── index.html              # Report viewer + tracking logic
│   └── reports/
│       └── 2026-05.html        # Copy of report for serving
├── tokens/
│   ├── generate_tokens.py      # Script: Qualtrics export → token mapping
│   └── test_token_map.csv      # Test tokens (5 people)
├── tracking/
│   ├── supabase_setup.sql      # SQL schema (already deployed)
│   └── export_tracking.py      # Script: pull tracking data from Supabase
├── analysis/
│   └── merge_data.py           # Script: join tracking + Qualtrics for analysis
└── .gitignore                  # Excludes PII, node_modules, secrets
```

---

## Components

### 1. Token Generation (`tokens/generate_tokens.py`)

**Purpose:** Takes a Qualtrics CSV export and generates a unique UUID4 token per respondent.

**Input:** Qualtrics CSV with at minimum: `ResponseId`, `email`

**Output:** `token_map.csv` with columns: `email`, `token`, `qualtrics_response_id`

**Usage:** `python generate_tokens.py <qualtrics_export.csv>`

**Security:** `token_map.csv` contains PII — gitignored, never pushed.

---

### 2. Supabase Backend

**Project:** `smawkkjarjcbqcaxpdoh` (São Paulo region)

**Table:** `report_events`

| Field              | Description                                          |
|--------------------|------------------------------------------------------|
| `token`            | Respondent's unique token (from URL)                 |
| `event_type`       | `opened`, `heartbeat`, or `downloaded`               |
| `report_month`     | Which report they accessed (e.g., `2026-05`)         |
| `timestamp`        | Server-side timestamp (UTC)                          |
| `duration_seconds` | Cumulative time on page at each heartbeat            |
| `user_agent`       | Browser/device string                                |
| `metadata`         | Reserved for future use (JSON)                       |

**Security:** RLS enabled. Anon key can INSERT only, never SELECT.

---

### 3. Report Viewer (`site/index.html`)

**URL format:** `https://pesquisa-inflacao.github.io/inflation_report/site/index.html?token=TOKEN&report=YYYY-MM`

**Behavior:**
1. Reads `token` and `report` from URL params
2. Validates params (shows friendly error in Portuguese if missing)
3. Fetches `reports/YYYY-MM.html` and renders in page
4. Sends `opened` event to Supabase
5. Heartbeat every 30s (pauses when tab hidden, uses sendBeacon on unload)
6. Download button appears after user scrolls to bottom
7. On download click: sends `downloaded` event, triggers HTML file download

**Dependencies:** None external (html2pdf.js was removed; download is plain HTML).

---

### 4. GitHub Pages

- **Org:** `pesquisa-inflacao`
- **Repo:** `inflation_report` (public)
- **Pages source:** `main` branch, `/ (root)` — site lives at `/site/index.html`
- **Deploy:** Push to main → auto-deploys in ~1 minute

---

### 5. Data Export (`tracking/export_tracking.py`)

Pulls all events from Supabase using the service role key. Paginates (1000 rows/page). Outputs `tracking/tracking_events.csv`.

**Requires:** `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` env vars (or edit script directly).

---

### 6. Analysis Merge (`analysis/merge_data.py`)

Joins tracking events + token map + Qualtrics survey data → respondent × month panel dataset.

**Output variables:**

| Variable          | Description                                              |
|-------------------|----------------------------------------------------------|
| `opened`          | Binary: did they open this month's report?               |
| `downloaded`      | Binary: did they download it?                            |
| `total_seconds`   | Total time spent on page (from heartbeats)               |
| `num_visits`      | Number of times they opened the same report              |
| `report_month`    | Which report (panel dimension)                           |

---

## Monthly Workflow

1. **Update data:** Add new month's IPCA/INCC data to `data/incc_report_input.xlsx`
2. **Generate report:** Ask Claude Code to "write the [Month] [Year] report"
   - Claude reads xlsx, computes values, generates HTML, saves to `reports/` and `site/reports/`
3. **Push:** In GitHub Desktop — commit + push to main
4. **Send links:** Distribute links to respondents with `report=YYYY-MM` param (tokens stay the same)

---

## Security and Privacy Summary

| Concern                        | How it's handled                                            |
|--------------------------------|-------------------------------------------------------------|
| Respondents see each other     | No — each person has a unique token link, no shared access  |
| Token guessing                 | UUID4 tokens are 128-bit random — effectively unguessable   |
| Tracking data exposure         | Supabase RLS: anon key can insert only, never read          |
| PII in repo                    | `token_map.csv` is gitignored, never pushed                 |
| Report content                 | Public inflation data — not sensitive                       |
| Email exposure                 | Emails only exist in `token_map.csv` (local) and Qualtrics  |

---

## Next Implementation Task: Bulk Token Generation & Link Distribution

When we resume, the goal is to:
1. Take a full Qualtrics export CSV (with all opted-in respondents' emails)
2. Generate tokens for everyone (or append to existing token map without regenerating existing tokens)
3. Produce a ready-to-send list: one row per person with their name, email, and personalized link
4. Determine the best method to send links at scale (email API, mail merge, or manual)

This is where we stopped. The infrastructure is fully functional — the remaining work is operationalizing the distribution.
