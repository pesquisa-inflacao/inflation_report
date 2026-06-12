"""
Token Generator for Inflation Report Distribution
--------------------------------------------------
Assigns a STABLE, unique UUID4 token to every subscriber so we can build
personalized, trackable report links.

Idempotent by design: it loads any existing token_map.csv, keeps the token
already assigned to each known email, and only mints new tokens for emails it
has never seen. Re-running it every month therefore preserves longitudinal
tracking (a person's token never changes; only the `report=YYYY-MM` URL param
changes between months).

Input (default): ../data/mailinglist.xlsx  (the report opt-in subscribers)
    May also be a .csv. Override with --input PATH.
    The input must contain an `email` column; `name` and `response_id`
    (or `ResponseId`) are used if present.

Output: tokens/token_map.csv
    columns: email, token, name, qualtrics_response_id, source, date_added

Security: token_map.csv contains PII (emails) — it is gitignored, never pushed.

Usage:
    python generate_tokens.py                  # uses ../data/mailinglist.xlsx
    python generate_tokens.py --input list.csv
"""

import argparse
import uuid
from datetime import date
from pathlib import Path

import pandas as pd

TOKENS_DIR = Path(__file__).parent
DEFAULT_INPUT = TOKENS_DIR.parent / "data" / "mailinglist.xlsx"
TOKEN_MAP = TOKENS_DIR / "token_map.csv"

OUT_COLUMNS = ["email", "token", "name", "qualtrics_response_id",
               "source", "date_added"]


def _read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str)


def _norm_email(value) -> str:
    return str(value).strip().lower()


def main():
    ap = argparse.ArgumentParser(description="Generate / update report tokens.")
    ap.add_argument("--input", default=str(DEFAULT_INPUT),
                    help="subscriber list (.xlsx or .csv) with an 'email' column")
    args = ap.parse_args()

    src = _read_any(Path(args.input))
    if "email" not in src.columns:
        raise SystemExit("Error: input must contain an 'email' column.")

    # Normalize helper columns that may or may not be present.
    name_col = "name" if "name" in src.columns else None
    rid_col = next((c for c in ("response_id", "ResponseId", "qualtrics_response_id")
                    if c in src.columns), None)
    src_col = "source" if "source" in src.columns else None

    src = src[src["email"].notna()].copy()
    src["email_norm"] = src["email"].map(_norm_email)
    src = src[src["email_norm"] != ""]
    src = src.drop_duplicates(subset="email_norm", keep="first")

    # Load existing map to preserve tokens.
    if TOKEN_MAP.exists():
        existing = pd.read_csv(TOKEN_MAP, dtype=str)
        existing["email_norm"] = existing["email"].map(_norm_email)
        token_by_email = dict(zip(existing["email_norm"], existing["token"]))
        existing_rows = {r["email_norm"]: r for _, r in existing.iterrows()}
    else:
        token_by_email = {}
        existing_rows = {}

    today = date.today().isoformat()
    rows = []
    n_new = 0
    for _, r in src.iterrows():
        em = r["email_norm"]
        if em in token_by_email:
            token = token_by_email[em]
            date_added = existing_rows.get(em, {}).get("date_added", today)
        else:
            token = str(uuid.uuid4())
            date_added = today
            n_new += 1
        rows.append({
            "email": str(r["email"]).strip(),
            "token": token,
            "name": (str(r[name_col]).strip() if name_col else ""),
            "qualtrics_response_id": (str(r[rid_col]).strip() if rid_col else ""),
            "source": (str(r[src_col]).strip() if src_col else ""),
            "date_added": date_added,
        })

    # Carry over any prior entries no longer in the input (don't drop people).
    current = {row["email"].strip().lower() for row in rows}
    for em, r in existing_rows.items():
        if em not in current:
            rows.append({c: r.get(c, "") for c in OUT_COLUMNS})

    out = pd.DataFrame(rows, columns=OUT_COLUMNS)
    out.to_csv(TOKEN_MAP, index=False)

    print(f"token_map.csv: {len(out)} total tokens "
          f"({n_new} newly minted, {len(out) - n_new} preserved)")
    print(f"written: {TOKEN_MAP}")


if __name__ == "__main__":
    main()
