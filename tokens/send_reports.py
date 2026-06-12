"""
send_reports.py
---------------
Sends each subscriber their personalized, trackable inflation-report link by
email, via the Resend API.

How it works
  1. Reads the subscriber list (../data/mailinglist.xlsx) and token_map.csv,
     and joins them on email so every recipient gets their stable token.
  2. Builds the personalized link:
         {BASE_URL}?token={TOKEN}&report={YYYY-MM}
  3. Renders a short Brazilian-Portuguese email and sends it through Resend.
  4. Records every send in tokens/send_log.csv and skips anyone already sent
     this month's report (so it's safe to re-run).

Safety
  - DRY RUN BY DEFAULT: with no flags it sends nothing. It writes a preview
    CSV (tokens/preview_<report>.csv) with name, email, link and subject so you
    can eyeball everything first.
  - Pass --send to actually deliver the emails.

Configuration (inflation_report/.env  — gitignored; see .env.example)
    RESEND_API_KEY   your Resend API key
    FROM_EMAIL       verified sender, e.g. relatorios@yourdomain.org
    FROM_NAME        display name, e.g. "Pesquisa Inflação"
    REPLY_TO         optional reply-to (e.g. your @stanford.edu address)
    BASE_URL         report viewer base (defaults to the GitHub Pages URL)

Usage
    python send_reports.py --report 2026-06              # dry run + preview
    python send_reports.py --report 2026-06 --send       # actually send
    python send_reports.py --report 2026-06 --send --resend-failures
"""

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

TOKENS_DIR = Path(__file__).parent
ROOT = TOKENS_DIR.parent
ENV_PATH = ROOT / ".env"
MAILING_LIST = ROOT / "data" / "mailinglist.xlsx"
TOKEN_MAP = TOKENS_DIR / "token_map.csv"
SEND_LOG = TOKENS_DIR / "send_log.csv"

DEFAULT_BASE_URL = ("https://pesquisa-inflacao.github.io/"
                    "inflation_report/site/index.html")
RESEND_ENDPOINT = "https://api.resend.com/emails"

MONTHS_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
    7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro",
    12: "dezembro",
}


# --------------------------------------------------------------------------- #
# config / io helpers
# --------------------------------------------------------------------------- #
def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def month_label_pt(report: str) -> str:
    dt = datetime.strptime(report, "%Y-%m")
    return f"{MONTHS_PT[dt.month]} de {dt.year}"


def load_recipients() -> pd.DataFrame:
    if not MAILING_LIST.exists():
        raise SystemExit(f"Missing mailing list: {MAILING_LIST}")
    if not TOKEN_MAP.exists():
        raise SystemExit(
            f"Missing {TOKEN_MAP}. Run generate_tokens.py first.")

    ml = pd.read_excel(MAILING_LIST, dtype=str)
    tm = pd.read_csv(TOKEN_MAP, dtype=str)
    ml["_e"] = ml["email"].astype(str).str.strip().str.lower()
    tm["_e"] = tm["email"].astype(str).str.strip().str.lower()

    merged = ml.merge(tm[["_e", "token"]], on="_e", how="left")
    missing = merged[merged["token"].isna()]
    if len(missing):
        emails = ", ".join(missing["email"].astype(str).tolist())
        raise SystemExit(
            "These mailing-list emails have no token (run generate_tokens.py): "
            + emails)

    # prefer the mailing-list name; fall back to token map handled upstream
    merged["name"] = merged["name"].fillna("").astype(str).str.strip()
    return merged[["name", "email", "token"]].reset_index(drop=True)


def already_sent(report: str) -> set:
    if not SEND_LOG.exists():
        return set()
    log = pd.read_csv(SEND_LOG, dtype=str)
    ok = log[(log["report_month"] == report) & (log["status"] == "sent")]
    return set(ok["email"].astype(str).str.strip().str.lower())


def append_log(rows: list):
    new = not SEND_LOG.exists()
    with SEND_LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["report_month", "email", "token",
                        "status", "resend_id", "timestamp"])
        w.writerows(rows)


# --------------------------------------------------------------------------- #
# email content
# --------------------------------------------------------------------------- #
def build_email(name: str, link: str, report: str):
    label = month_label_pt(report)
    first = (name.split()[0] if name.strip() else "").strip()
    greeting = f"Olá, {first}!" if first else "Olá!"
    subject = f"📊 Seu relatório de inflação — {label.capitalize()}"

    html = f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;
            color:#1a2b3c;line-height:1.55;font-size:15px;">
  <p>{greeting}</p>
  <p>Seu relatório mensal de inflação referente a <strong>{label}</strong> já
     está disponível. Ele resume a evolução do IPCA e do INCC e mostra, de forma
     simples, como esses índices podem afetar o reajuste das suas parcelas.</p>
  <p style="text-align:center;margin:28px 0;">
    <a href="{link}"
       style="background:#1a2b3c;color:#ffffff;text-decoration:none;
              padding:12px 26px;border-radius:6px;font-weight:bold;
              display:inline-block;">Acessar meu relatório</a>
  </p>
  <p style="font-size:13px;color:#555;">Se o botão não funcionar, copie e cole
     este link no seu navegador:<br>
     <a href="{link}" style="color:#1a73e8;word-break:break-all;">{link}</a></p>
  <p style="font-size:13px;color:#555;">Este link é pessoal e foi gerado
     exclusivamente para você.</p>
  <p>Atenciosamente,<br>Equipe de Pesquisa</p>
</div>"""

    text = (
        f"{greeting}\n\n"
        f"Seu relatório mensal de inflação referente a {label} já está "
        f"disponível. Ele resume a evolução do IPCA e do INCC e mostra como "
        f"esses índices podem afetar o reajuste das suas parcelas.\n\n"
        f"Acesse seu relatório: {link}\n\n"
        f"Este link é pessoal e foi gerado exclusivamente para você.\n\n"
        f"Atenciosamente,\nEquipe de Pesquisa"
    )
    return subject, html, text


def send_one(env, to_email, subject, html, text):
    headers = {
        "Authorization": f"Bearer {env['RESEND_API_KEY']}",
        "Content-Type": "application/json",
    }
    from_name = env.get("FROM_NAME", "").strip()
    from_email = env["FROM_EMAIL"].strip()
    sender = f"{from_name} <{from_email}>" if from_name else from_email
    payload = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if env.get("REPLY_TO"):
        payload["reply_to"] = env["REPLY_TO"].strip()

    resp = requests.post(RESEND_ENDPOINT, headers=headers,
                         data=json.dumps(payload), timeout=30)
    if resp.status_code in (200, 201):
        return True, resp.json().get("id", "")
    return False, f"HTTP {resp.status_code}: {resp.text[:200]}"


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Send personalized report links.")
    ap.add_argument("--report", required=True, help="report month, e.g. 2026-06")
    ap.add_argument("--send", action="store_true",
                    help="actually send (default is a dry run / preview only)")
    ap.add_argument("--resend-failures", action="store_true",
                    help="also retry recipients whose last send failed")
    args = ap.parse_args()

    # validate report format early
    month_label_pt(args.report)

    env = load_env(ENV_PATH)
    base_url = env.get("BASE_URL", DEFAULT_BASE_URL).rstrip()

    recips = load_recipients()
    recips["link"] = recips["token"].map(
        lambda t: f"{base_url}?token={t}&report={args.report}")

    sent_set = set() if args.resend_failures else already_sent(args.report)
    to_process = recips[~recips["email"].str.strip().str.lower().isin(sent_set)]
    skipped = len(recips) - len(to_process)

    # always write a preview
    preview_path = TOKENS_DIR / f"preview_{args.report}.csv"
    preview = to_process.copy()
    preview["subject"] = preview.apply(
        lambda r: build_email(r["name"], r["link"], args.report)[0], axis=1)
    preview.to_csv(preview_path, index=False)

    print("=" * 60)
    print(f"REPORT SEND  —  {args.report}  ({month_label_pt(args.report)})")
    print(f"  recipients on list : {len(recips)}")
    print(f"  already sent (skip): {skipped}")
    print(f"  to send            : {len(to_process)}")
    print(f"  mode               : {'SEND' if args.send else 'DRY RUN (no emails)'}")
    print(f"  preview written    : {preview_path}")
    print("=" * 60)

    if not args.send:
        print("\nDry run only. Review the preview CSV, then re-run with --send.")
        return

    # sending requires complete config
    for key in ("RESEND_API_KEY", "FROM_EMAIL"):
        if not env.get(key):
            raise SystemExit(f"Missing {key} in {ENV_PATH} (see .env.example).")

    ts = datetime.now(timezone.utc).isoformat()
    log_rows, ok, fail = [], 0, 0
    for _, r in to_process.iterrows():
        subject, html, text = build_email(r["name"], r["link"], args.report)
        success, info = send_one(env, r["email"], subject, html, text)
        status = "sent" if success else "failed"
        log_rows.append([args.report, r["email"], r["token"], status,
                         info if success else "", ts])
        if success:
            ok += 1
        else:
            fail += 1
            print(f"  FAILED {r['email']}: {info}")

    append_log(log_rows)
    print(f"\nDone. sent={ok}  failed={fail}  (logged to {SEND_LOG})")


if __name__ == "__main__":
    main()
