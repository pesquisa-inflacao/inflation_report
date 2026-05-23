# Inflation Report Specification

## Overview

Monthly inflation report for participants in a consórcio (Brazilian group-purchasing system) administered by **Servopa**. Part of an RCT — some survey respondents opted in to receive it. Must be informative, visually appealing, and accessible to a non-specialist audience of all backgrounds.

## Output

- **Format:** A single self-contained HTML file with all CSS inline (no external stylesheets or scripts).
- **Language:** Brazilian Portuguese.
- **Naming convention:** `reports/YYYY-MM.html` — the file is named for the **publication month** (e.g., `reports/2026-05.html` for the May 2026 edition), even though the most recent data may be from the prior month.
- **Self-contained:** No external dependencies (fonts, images, scripts). Everything inline.
- **After writing:** Copy the file to `site/reports/YYYY-MM.html` for GitHub Pages serving.

## Data Source

The input data lives at `data/incc_report_input.xlsx`. It contains two sheets:

### Sheet: `ipca`
IPCA (Índice Nacional de Preços ao Consumidor Amplo) — Brazil's official consumer price index, used to adjust consórcio installments for **vehicles and other movable goods** (bens móveis).

### Sheet: `incc`
INCC (Índice Nacional de Custo da Construção) — the construction cost index, used to adjust consórcio installments for **real estate** (bens imóveis).

### Column structure (both sheets identical):
| Column      | Description                                      |
|-------------|--------------------------------------------------|
| `month`     | Reference month (Excel serial date, first day)   |
| `index`     | Cumulative index value                           |
| `month_1`   | Monthly variation (%, e.g., 0.54 means 0.54%)   |
| `ytd`       | Year-to-date accumulated variation (%)           |
| `past_year` | Trailing 12-month accumulated variation (%)      |

The data runs from January 2008 through the most recent available month.

## Report Structure (Current Design — May 2026)

The report uses colored full-width section banners as dividers between content blocks. The body background is dark (`#1a2b3c`), making the white content areas feel like separate "pages."

### 1. Header Block (white)
- Title: **"Relatório Mensal de Inflação"** (30px, bold)
- Month: **"[Month in Portuguese] [Year]"** (22px, blue)
- Attribution: "Elaborado por pesquisadores e direcionado aos clientes do consórcio Servopa"
- Data note: "Dados mais recentes disponíveis: [month of latest data] de [year]"
- **Intro list** — concise bullet points:
  - Inflação nos últimos 12 meses — o quanto os índices de preços subiram no último ano
  - Inflação nos últimos 6 meses — o quanto os índices de preços subiram no último semestre
  - Simulador de Reajuste — quanto sua parcela pode aumentar com a inflação atual
- **Navigation cards** — two clickable cards side by side:
  - ���� Bens Móveis (veículos, motos, caminhões) — blue border
  - 🏠 Bens Imóveis (casas, apartamentos, terrenos) — orange border

### 2. Section Banner: Bens Móveis (blue `#1a5276` background)
- Title + subtitle in white

### 3. IPCA Content Block (white)
- **Stat boxes** (side by side):
  - Large box (flex: 2): 12-month accumulated (`past_year`) — 42px bold number
  - Smaller box (flex: 1): 6-month accumulated (computed) — 28px bold number
- **Context line**: "↑ Este índice subiu em relação ao mês anterior (era X,XX%) — acelerando/desacelerando"
  - Use red (`#c0392b`) for "acelerando", green (`#2ecc71`) for "desacelerando"
- **Line chart** (inline SVG, viewBox 600×200):
  - Last 30 months of `past_year` values
  - Title: "Inflação acumulada em 12 meses" (no time range in title)
  - Y-axis range: choose appropriate min/max to show the data well
  - X-axis labels: every ~6 months
  - Line color: `#1a5276`
  - End-point dot and label with current value

### 4. Section Banner: Bens Imóveis (orange `#e67e22` background)
- Title + subtitle in white

### 5. INCC Content Block (white)
- Same structure as IPCA, but:
  - Border accents use orange (`#e67e22`)
  - Chart line color: `#e67e22`

### 6. Section Banner: Simulador de Reajuste (dark slate `#2c3e50` background)
- Title + subtitle in white

### 7. Simulator Content Block (white)
- **Two tables** (one for Bens Móveis/IPCA, one for Bens Imóveis/INCC)
- Columns: Parcela atual | Reajuste semestral (6M %) | Reajuste anual (12M %)
- Rows: R$ 1.000, R$ 2.000, R$ 3.000, R$ 4.000, R$ 5.000
- Values: `round(parcela * rate)`
- Disclaimer: "Valores aproximados para fins ilustrativos..."
- **Carta de crédito reminder** (grey box): "Lembre-se: a sua carta de crédito também é corrigida por esses mesmos índices enquanto você não for contemplado. Ou seja, o valor que você terá direito a receber acompanha a inflação."

### 8. Footer (light grey background)
- "Relatório informativo. Não constitui recomendação financeira. Dados: IBGE (IPCA) e FGV (INCC)."

## Computing the 6-Month Accumulated Inflation

The 6-month figure is NOT in the spreadsheet — it must be computed:

```
6M = (1 + m1/100) × (1 + m2/100) × ... × (1 + m6/100) - 1
```

Where m1...m6 are the `month_1` values for the last 6 months (including the current one).

## Chart Coordinate Calculation

For line charts:
- **X**: `x = 50 + i * (530 / (N-1))` where i is the point index (0-based) and N is total points (30)
- **Y**: `y = y_bottom - ((value - y_min) * (y_bottom - y_top) / (y_max - y_min))`
  - Use `y_top = 20`, `y_bottom = 164` (gives 144px of vertical space)
  - Choose `y_min` and `y_max` to frame the data well (round to nice numbers)

## Visual Design

- **Color palette:**
  - Primary blue: `#1a5276` (IPCA/Bens Móveis)
  - Orange: `#e67e22` (INCC/Bens Imóveis)
  - Red: `#c0392b` (acceleration indicator)
  - Green: `#2ecc71` (deceleration indicator)
  - Dark background: `#1a2b3c` (body, between sections)
  - Dark slate: `#2c3e50` (simulator banner)
  - Text: `#333333` (body), `#1a2b3c` (headers), `#888` (secondary), `#aaa` (tertiary)
  - Backgrounds: `#ffffff` (content), `#f8f9fa` (stat boxes, callouts)
- **Typography:** `'Helvetica Neue', Helvetica, Arial, sans-serif`
- **Mobile-friendly:** `max-width: 700px; margin: 0 auto;` on each content block

## Tone and Language

- **Accessible:** Write for someone who is not an economist. Avoid jargon.
- **Neutral and factual:** No editorializing.
- **Practical:** Connect data back to what it means for installments.
- **Concise:** Minimal text. Let the numbers and visuals do the work.
- **Friendly:** Use "você" and conversational Portuguese.

## How to Generate a New Monthly Report

When it's time to write the next month's report (e.g., "write the June 2026 report"):

1. **Check data:** Read `data/incc_report_input.xlsx`. Verify the latest month is present. If not, flag it — do not invent numbers.
2. **Extract values:**
   - Current month `past_year` (12M) for both IPCA and INCC
   - Previous month `past_year` for both (for the context line)
   - Last 6 `month_1` values for both (to compute 6M accumulated)
   - Last 30 `past_year` values for both (for charts)
3. **Compute:**
   - 6M accumulated for IPCA and INCC
   - Table values: `round(parcela * rate)` for each combination
   - Chart coordinates using the formulas above
4. **Determine acceleration/deceleration:** Compare current `past_year` to previous month's `past_year`.
5. **Generate HTML** using `reports/2026-05.html` as the template. Update:
   - Month name in title and header
   - Data note (which month the data goes up to)
   - All numbers (stat boxes, context lines, chart points, tables)
   - Chart Y-axis range if needed (pick nice min/max for the data)
6. **Save** to `reports/YYYY-MM.html`
7. **Copy** to `site/reports/YYYY-MM.html`
8. **Remind user** to commit and push via GitHub Desktop

## Important Notes

- **Do not fabricate data.** Only use values from the spreadsheet.
- **Publication month vs. data month:** The report is named for the publication month. The data may lag by one month. Always note this in the header.
- **Each report is standalone.** A reader should understand any single report without prior context.
- **Use `reports/2026-05.html` as the canonical template** for all future reports.
