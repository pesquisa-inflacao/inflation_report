"""
Token Generator for Inflation Report Distribution

Takes a Qualtrics survey export (CSV) and generates a unique UUID4 token
for each respondent who opted in and provided an email address.

Usage:
    python generate_tokens.py <qualtrics_export.csv>

Output:
    tokens/token_map.csv — columns: email, token, qualtrics_response_id
"""

import sys
import uuid
import pandas as pd
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_tokens.py <qualtrics_export.csv>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = Path(__file__).parent
    output_path = output_dir / "token_map.csv"

    # Read Qualtrics export
    df = pd.read_csv(input_path)

    # Check that required columns exist
    if "email" not in df.columns:
        print("Error: CSV must contain an 'email' column.")
        sys.exit(1)
    if "ResponseId" not in df.columns:
        print("Error: CSV must contain a 'ResponseId' column.")
        sys.exit(1)

    # Filter to respondents who provided a valid email
    df = df[df["email"].notna() & (df["email"].str.strip() != "")]
    df = df.copy()

    # Generate unique tokens
    df["token"] = [str(uuid.uuid4()) for _ in range(len(df))]

    # Select and rename columns
    result = df[["email", "token", "ResponseId"]].rename(
        columns={"ResponseId": "qualtrics_response_id"}
    )

    # Save
    result.to_csv(output_path, index=False)
    print(f"Generated {len(result)} tokens → {output_path}")


if __name__ == "__main__":
    main()
