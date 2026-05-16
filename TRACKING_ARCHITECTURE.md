# Tracking Infrastructure — Architecture Specification

## Goal

Deliver monthly inflation reports to consórcio survey respondents via personalized links, track their engagement (opens, time-on-page, downloads), and export clean data for econometric analysis. Each respondent sees only their own link — no shared access, no email exposure.

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
         │               │  - Offers PDF download  │     │  - REST API (free)   │
         ▼               └──────────────────────┘     └──────────┬──────────┘
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

All files live inside `C:\Users\otavi\Dropbox\jmp_inflation_rct\inflation_report\`.

```
inflation_report/
├── REPORT_SPEC.md              # Instructions for writing reports (already exists)
├── TRACKING_ARCHITECTURE.md    # This file
├── data/
│   └── incc_report_input.xlsx  # Inflation data (already exists)
├── reports/
│   └── 2026-04.html            # Monthly reports (Claude Code writes these)
├── site/                       # GitHub Pages deployment folder
│   ├── index.html              # Report viewer + tracking logic
│   └── reports/                # Copy of report HTML files for serving
│       └── 2026-04.html
├── tokens/
│   ├── generate_tokens.py      # Script: Qualtrics export → token mapping
│   └── token_map.csv           # Output: email, token, qualtrics_response_id
├── tracking/
│   ├── supabase_setup.sql      # SQL to create the tracking table
│   └── export_tracking.py      # Script: pull tracking data from Supabase
└── analysis/
    └── merge_data.py           # Script: join tracking + Qualtrics for analysis
```

---

## Components

### 1. Token Generation (`tokens/generate_tokens.py`)

**Purpose:** Takes the Qualtrics survey export (CSV) and generates a unique, unguessable token for each respondent who opted in to receive reports.

**Input:**
- Qualtrics CSV export containing at minimum: `ResponseId`, `email` (the field where respondents entered their email at the end of the survey).

**Output:**
- `token_map.csv` with columns: `email`, `token`, `qualtrics_response_id`

**Token format:** UUID4 (e.g., `a3f8b2c1-7d4e-4f9a-b6c8-1e2d3f4a5b6c`). These are unguessable and unique.

**Logic:**
```python
import pandas as pd
import uuid

# Read Qualtrics export
df = pd.read_csv("qualtrics_export.csv")

# Filter to respondents who opted in and provided an email
df = df[df["email"].notna() & (df["email"].str.strip() != "")]

# Generate tokens
df["token"] = [str(uuid.uuid4()) for _ in range(len(df))]

# Save mapping
df[["email", "token", "ResponseId"]].rename(
    columns={"ResponseId": "qualtrics_response_id"}
).to_csv("token_map.csv", index=False)
```

**Security note:** The `token_map.csv` file contains PII (emails). Do NOT commit it to a public GitHub repo. Keep it local or in a private location. The `.gitignore` must exclude it.

---

### 2. Supabase Backend (`tracking/supabase_setup.sql`)

**Why Supabase:** Free tier includes a full Postgres database, REST API out of the box, and easy CSV export. No server to manage. The free tier allows up to 500MB of storage and 50,000 monthly API requests — more than enough for a few hundred respondents accessing monthly reports.

**Setup steps:**
1. Create a free account at [supabase.com](https://supabase.com).
2. Create a new project (any region; São Paulo is available).
3. Run the SQL below in the Supabase SQL Editor to create the tracking table.
4. In Project Settings → API, copy:
   - **Project URL** (e.g., `https://xxxx.supabase.co`)
   - **`anon` public key** (safe to use in client-side JS — it's rate-limited and can only insert, not read, thanks to RLS policies below)

**SQL schema:**
```sql
-- Create the tracking table
CREATE TABLE report_events (
    id BIGSERIAL PRIMARY KEY,
    token TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('opened', 'heartbeat', 'downloaded')),
    report_month TEXT NOT NULL,          -- e.g., '2026-04'
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    duration_seconds INTEGER,            -- cumulative seconds on page (for heartbeats)
    user_agent TEXT,                      -- browser info (mobile vs desktop)
    metadata JSONB                       -- any extra info
);

-- Index for fast lookups by token
CREATE INDEX idx_report_events_token ON report_events(token);

-- Row Level Security: allow anonymous inserts only, no reads
ALTER TABLE report_events ENABLE ROW LEVEL SECURITY;

-- Policy: anyone can insert (tracking events from the viewer page)
CREATE POLICY "Allow anonymous inserts"
    ON report_events
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- Policy: no one can read via the public API (only you via the dashboard or service key)
-- This means even if someone inspects the JS, they can't read other people's events.
```

**What gets logged:**

| Field              | Description                                          |
|--------------------|------------------------------------------------------|
| `token`            | Respondent's unique token (from URL)                 |
| `event_type`       | `opened`, `heartbeat`, or `downloaded`               |
| `report_month`     | Which report they accessed (e.g., `2026-07`)         |
| `timestamp`        | Server-side timestamp (UTC)                          |
| `duration_seconds` | Cumulative time on page at each heartbeat            |
| `user_agent`       | Browser/device string                                |
| `metadata`         | Reserved for future use (JSON)                       |

---

### 3. Report Viewer (`site/index.html`)

**Purpose:** A single-page site hosted on GitHub Pages that:
1. Reads the `token` and `report` parameters from the URL.
2. Loads the corresponding report HTML.
3. Renders it in the page.
4. Tracks engagement (open, time-on-page, download) by sending events to Supabase.

**URL format:**
```
https://<your-github-username>.github.io/inflation-report/?token=abc123&report=2026-04
```

**Core behavior:**

```
Page Load
  ├── Read token + report from URL params
  ├── Validate token exists (if missing, show error)
  ├── Fetch reports/<report>.html
  ├── Render report content in page
  ├── Send "opened" event to Supabase
  ├── Start heartbeat timer (every 30 seconds)
  │     └── Send "heartbeat" event with cumulative duration
  └── Show download button
        └── On click: send "downloaded" event, then trigger file download
```

**Key implementation details:**

- **Report loading:** Use `fetch()` to load the report HTML from the `site/reports/` directory and inject it into a container div. This way the viewer page is always the same — only the report content changes.
- **Download button:** Generate a Blob from the report HTML, create a temporary download link, and trigger it. Track the click before initiating the download.
- **Heartbeat:** Use `setInterval` every 30 seconds. Stop heartbeats when the page is hidden (`document.visibilityState === 'hidden'`) and resume when visible — this avoids inflating time-on-page when the tab is in the background.
- **Error handling:** If the token or report param is missing, show a friendly error message in Portuguese: "Link inválido. Por favor, use o link que foi enviado para o seu email."
- **No authentication:** The token *is* the authentication. No login flow needed.

**Supabase client-side call (vanilla JS, no SDK needed):**
```javascript
async function trackEvent(eventType, durationSeconds = null) {
    const SUPABASE_URL = "https://xxxx.supabase.co";
    const SUPABASE_ANON_KEY = "your-anon-key-here";

    await fetch(`${SUPABASE_URL}/rest/v1/report_events`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": `Bearer ${SUPABASE_ANON_KEY}`
        },
        body: JSON.stringify({
            token: TOKEN,
            event_type: eventType,
            report_month: REPORT_MONTH,
            duration_seconds: durationSeconds,
            user_agent: navigator.userAgent
        })
    });
}
```

**Important:** The `anon` key is safe to expose in client-side JavaScript. The RLS policies above ensure it can only insert rows, never read them. An attacker could spam fake events, but they can't see other respondents' data. For your scale this is fine; you can filter spam events in analysis by checking against valid tokens.

---

### 4. GitHub Pages Setup

**Repository structure:**
- Create a repository (e.g., `inflation-report`) on GitHub.
- The `site/` folder is the deployment root.
- In the repo settings, set GitHub Pages source to the `site/` directory (or use the root and move files accordingly).
- **CRITICAL:** The repo must be **public** for free GitHub Pages hosting. This is fine because the reports themselves are not sensitive — they contain public inflation data. The token mapping CSV is NOT in this repo.

**`.gitignore` (in repo root):**
```
tokens/token_map.csv
tokens/qualtrics_export.csv
.env
```

**Deployment workflow:**
1. Claude Code writes a new report to `reports/2026-MM.html`.
2. You copy it to `site/reports/2026-MM.html`.
3. Commit and push.
4. GitHub Pages auto-deploys within a minute.
5. Respondents accessing their links now see the new report.

This copy step could be automated with a simple script, but doing it manually is fine given it's monthly.

---

### 5. Data Export (`tracking/export_tracking.py`)

**Purpose:** Pull all tracking events from Supabase and export to CSV for analysis.

**Approach:** Use the Supabase **service role key** (NOT the anon key) to read all rows. The service key bypasses RLS and should never be exposed in client-side code — only use it locally.

```python
import requests
import pandas as pd

SUPABASE_URL = "https://xxxx.supabase.co"
SERVICE_KEY = "your-service-role-key"  # Keep secret, never commit

response = requests.get(
    f"{SUPABASE_URL}/rest/v1/report_events?select=*",
    headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}"
    }
)

events = pd.DataFrame(response.json())
events.to_csv("tracking_events.csv", index=False)
```

**Output:** `tracking_events.csv` with one row per event.

---

### 6. Analysis Merge (`analysis/merge_data.py`)

**Purpose:** Join the tracking data with the Qualtrics survey data to create the analysis dataset.

**Logic:**
```python
import pandas as pd

# Load data
tokens = pd.read_csv("tokens/token_map.csv")
events = pd.read_csv("tracking/tracking_events.csv")
qualtrics = pd.read_csv("qualtrics_export.csv")

# Merge token → events
events_with_id = events.merge(tokens[["token", "qualtrics_response_id"]], on="token")

# Construct engagement variables per respondent per report
engagement = events_with_id.groupby(["qualtrics_response_id", "report_month"]).agg(
    opened=("event_type", lambda x: (x == "opened").any()),
    downloaded=("event_type", lambda x: (x == "downloaded").any()),
    total_seconds=("duration_seconds", "max"),  # max heartbeat = total time
    num_visits=("event_type", lambda x: (x == "opened").sum())
).reset_index()

# Merge with Qualtrics
panel = qualtrics.merge(engagement, on="qualtrics_response_id", how="left")
panel.to_csv("analysis/analysis_panel.csv", index=False)
```

**Output variables for analysis:**

| Variable          | Description                                              |
|-------------------|----------------------------------------------------------|
| `opened`          | Binary: did they open this month's report?               |
| `downloaded`      | Binary: did they download it?                            |
| `total_seconds`   | Total time spent on page (from heartbeats)               |
| `num_visits`      | Number of times they opened the same report              |
| `report_month`    | Which report (panel dimension)                           |

This gives you a respondent × month panel dataset ready for analysis.

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

## Setup Checklist

1. [ ] Create Supabase project and run `tracking/supabase_setup.sql`
2. [ ] Copy Supabase URL and anon key into `site/index.html`
3. [ ] Copy Supabase service key into `tracking/export_tracking.py` (local only)
4. [ ] Create GitHub repo and enable GitHub Pages on `site/` directory
5. [ ] Generate first report with Claude Code → copy to `site/reports/`
6. [ ] Export Qualtrics emails → run `tokens/generate_tokens.py`
7. [ ] Send personalized links to respondents (method TBD)
8. [ ] After each month: write new report, copy to `site/reports/`, push to GitHub
9. [ ] At end of experiment: run `tracking/export_tracking.py` → `analysis/merge_data.py`

---

## Asking Claude Code to Build This

Once this file and `REPORT_SPEC.md` are in the project root, you can tell Claude Code:

> "Read TRACKING_ARCHITECTURE.md. Build the tracking infrastructure: create the site/index.html viewer page, the token generation script, the export script, the merge script, and the .gitignore. Use placeholder values for the Supabase URL and keys — I'll fill those in after creating the project."

Claude Code will have everything it needs to scaffold the full system.
