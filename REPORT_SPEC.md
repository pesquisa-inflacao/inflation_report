# Inflation Report Specification

## Overview

You are writing a monthly inflation report for participants in a consórcio (a Brazilian group-purchasing system) administered by **Servopa**. This report is part of a research experiment (RCT) — some survey respondents opted in to receive it. The report must be informative, visually appealing, and accessible to a non-specialist audience.

## Output

- **Format:** A single self-contained HTML file with all CSS inline (no external stylesheets or scripts).
- **Language:** Brazilian Portuguese.
- **Naming convention:** `reports/YYYY-MM.html` (e.g., `reports/2026-07.html`).
- **Self-contained:** No external dependencies (fonts, images, scripts). Everything inline.

## Data Source

The input data lives at `data/incc_report_input.xlsx`. It contains two sheets:

### Sheet: `incc`
INCC (Índice Nacional de Custo da Construção) — the construction cost index, used to adjust consórcio installments for **real estate** (bens imóveis).

### Sheet: `ipca`
IPCA (Índice Nacional de Preços ao Consumidor Amplo) — Brazil's official consumer price index, used to adjust consórcio installments for **vehicles and other movable goods** (bens móveis).

### Column structure (both sheets are identical):
| Column      | Description                                      |
|-------------|--------------------------------------------------|
| `month`     | Reference month (datetime, first day of month)   |
| `index`     | Cumulative index value                           |
| `month.1`   | Monthly variation (%, e.g., 0.54 means 0.54%)    |
| `ytd`       | Year-to-date accumulated variation (%)           |
| `past_year` | Trailing 12-month accumulated variation (%)      |

The data runs from January 2008 through the most recent available month. When writing a report for month YYYY-MM, use data up to and including that month.

## Report Structure

Each monthly report should follow this structure. Keep it concise — the target reading time is **5 to 10 minutes**.

### 1. Header
- Title: **"Relatório Mensal de Inflação — [Month in Portuguese] [Year]"**
  - Example: "Relatório Mensal de Inflação — Julho 2026"
- Subtitle: "Preparado para participantes de consórcio Servopa"
- Date of publication

### 2. Resumo Executivo (Executive Summary)
- 2-3 sentences summarizing the key takeaway for the month.
- Example tone: "A inflação medida pelo IPCA acelerou em julho, atingindo X,XX% no mês. Para quem tem consórcio de veículos, isso significa que o reajuste anual das parcelas tende a ser maior. Já o INCC desacelerou, trazendo alívio para quem tem consórcio de imóveis."

### 3. IPCA — O que aconteceu?
- Report the **monthly variation** and **trailing 12-month variation**.
- Compare to the previous month's values (is it accelerating or decelerating?).
- Show a simple trend: provide a visual (inline SVG chart or HTML/CSS bar chart) of the **last 12 monthly variations** of IPCA.
- **Plain-language explanation** of what this means for consórcio installments of **bens móveis** (vehicles, motorcycles, trucks).
- Include a concrete example: "Se sua parcela atual é de R$ 1.000, um reajuste anual de X,XX% representaria um aumento de R$ XX,XX por mês."

### 4. INCC — O que aconteceu?
- Same structure as the IPCA section, but for INCC.
- Explain relevance to **bens imóveis** (houses, apartments, land, renovations).
- Include the same type of concrete installment example.

### 5. Comparativo: IPCA vs. INCC
- A side-by-side comparison (table or visual) of the two indices for the current month and trailing 12 months.
- Brief note on which type of consórcio is facing more pressure from inflation right now.

### 6. Olhando para Frente (Looking Ahead)
- A brief, cautious forward-looking paragraph. Do NOT make predictions — instead, describe the recent trend direction and what it *could* mean if it continues.
- Use hedging language: "Caso a tendência de aceleração se mantenha...", "Se o ritmo atual continuar..."
- You may reference publicly known information (e.g., Banco Central targets, Selic trajectory) but keep it general. Do not cite specific forecasts.

### 7. Glossário Rápido (Quick Glossary)
- Short definitions (1-2 sentences each) for: IPCA, INCC, variação mensal, variação acumulada em 12 meses, reajuste de parcela.
- This should appear at the bottom of every report so new readers always have it.

## Visual Design Guidelines

- **Color palette:** Use a professional, clean palette. Suggested:
  - Primary blue: `#1a5276` (headers, chart accents)
  - Secondary teal: `#2ecc71` (positive/deceleration highlights)
  - Alert orange: `#e67e22` (acceleration highlights)
  - Text: `#333333` (body), `#1a2b3c` (headers)
  - Background: `#ffffff` (main), `#f8f9fa` (callout boxes)
- **Typography:** Use system fonts: `'Helvetica Neue', Helvetica, Arial, sans-serif`.
- **Charts:** Use inline SVG for any charts. Keep them simple — bar charts for monthly variations, no 3D effects, no excessive decoration. Label axes clearly. Charts should be responsive (use viewBox).
- **Callout boxes:** Use the same visual language as the survey (left-border accent, light background, rounded corners). Example:
  ```html
  <div style="background-color: #f8f9fa; border-left: 4px solid #2ecc71; padding: 12px 15px; border-radius: 4px;">
      <p style="font-size: 16px; margin: 0; color: #555; line-height: 1.5;">
          Content here
      </p>
  </div>
  ```
- **Installment examples:** Highlight these in a distinct callout box so they stand out. Use a calculator emoji (🧮) as a visual anchor.
- **Mobile-friendly:** The report will be viewed on phones. Use responsive widths (`max-width: 700px; margin: 0 auto;`), adequate font sizes (minimum 15px body text), and ensure charts scale down gracefully.

## Tone and Language

- **Accessible:** Write for someone who is not an economist. Avoid jargon without explanation.
- **Neutral and factual:** Do not editorialize or make value judgments about government policy, the Banco Central, etc.
- **Practical:** Always connect the data back to what it means for the reader's consórcio installments. This is the core value proposition.
- **Concise:** Respect the reader's time. Every paragraph should earn its place.

## How to Generate a Report

When asked to write a report for a specific month (e.g., "write the July 2026 report"):

1. Read the data from `data/incc_report_input.xlsx`.
2. Filter to the relevant month and extract the needed values (current month, previous month, last 12 months for charts).
3. Compute any derived values (e.g., change in monthly variation vs. prior month, installment impact examples).
4. Generate the HTML file following the structure and design guidelines above.
5. Save to `reports/YYYY-MM.html`.

## Important Notes

- **Do not fabricate data.** Only use values that exist in the spreadsheet. If the requested month is not in the data, say so.
- **Do not make forecasts.** The "Looking Ahead" section describes trends, not predictions.
- **Update the data file first.** Before writing a new report, check if the xlsx has been updated with the latest month's data. If it hasn't, flag this rather than inventing numbers.
- **Each report is standalone.** A reader should be able to understand any single report without having read previous ones.
