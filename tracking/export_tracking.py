"""
Export Tracking Data from Supabase

Pulls all report_events rows from Supabase using the service role key
and saves them to a CSV file.

Usage:
    python export_tracking.py

Requires:
    - SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables, or
      edit the constants below directly (never commit the service key).

Output:
    tracking/tracking_events.csv
"""

import os
import sys
import requests
import pandas as pd
from pathlib import Path


# ── Configuration ──────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://YOUR_PROJECT_ID.supabase.co")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "YOUR_SERVICE_KEY_HERE")

OUTPUT_PATH = Path(__file__).parent / "tracking_events.csv"


def main():
    if "YOUR_" in SUPABASE_URL or "YOUR_" in SERVICE_KEY:
        print("Error: Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables,")
        print("       or edit the constants in this script.")
        sys.exit(1)

    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
    }

    # Supabase REST API returns max 1000 rows by default; paginate if needed
    all_events = []
    offset = 0
    page_size = 1000

    while True:
        url = (
            f"{SUPABASE_URL}/rest/v1/report_events"
            f"?select=*&order=id.asc&offset={offset}&limit={page_size}"
        )
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        batch = response.json()
        if not batch:
            break

        all_events.extend(batch)
        offset += page_size

        if len(batch) < page_size:
            break

    if not all_events:
        print("No events found in the database.")
        return

    df = pd.DataFrame(all_events)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Exported {len(df)} events → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
