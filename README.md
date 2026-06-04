# 📊 FP&A Assistant

An AI-powered financial analysis dashboard built with Python, Streamlit, and the Claude API.
Designed to demonstrate real FP&A skills: ratio analysis, budget variance, revenue scheduling, and AI-generated analyst narratives.

---

## What It Does

Upload a company's financial statements (Excel) and the app instantly:

- **Calculates 17 financial ratios** across liquidity, profitability, leverage, efficiency, and growth — each color-coded against industry benchmarks
- **Shows multi-year ratio trends** with line charts across FY2022–FY2024
- **Analyzes the revenue schedule** — monthly actuals vs budget, best/worst months, variance detail, and a forecast builder with adjustable growth rates
- **Runs a budget vs actuals analysis** — YTD variance by line item, full-year pacing, and on-track status
- **Generates a professional FP&A narrative** via the Claude API — written like a senior analyst memo, not a bullet list
- **Compares two companies side by side** — ratio-by-ratio with a scorecard and margin comparison chart
- **Exports a full PDF report** — KPIs, ratio table, BvA summary, and AI narrative in one clean document

---

## Tech Stack

| Layer | Tool |
|---|---|
| Frontend / UI | Streamlit |
| Data processing | pandas |
| Charts | Plotly |
| AI narrative | Anthropic Claude API (claude-sonnet) |
| Excel parsing | openpyxl, flexible synonym mapper |
| PDF generation | ReportLab |
| Environment | Python 3.13, venv |

---

## Project Structure

```
fpna_assistant/
├── app.py                        # Main Streamlit dashboard
├── modules/
│   ├── parser.py                 # Parses our standard Excel template
│   ├── flexible_parser.py        # Parses real-world 10-K Excel downloads
│   ├── ratios.py                 # 17 financial ratios + multi-year trends
│   ├── revenue_schedule.py       # Monthly revenue analysis + forecast builder
│   ├── budget_vs_actuals.py      # YTD variance analysis
│   ├── ai_narrative.py           # Claude API integration
│   └── pdf_export.py             # PDF report generator
├── sample_data/
│   └── sample_financials.xlsx    # 3-year sample data (IS, BS, CFS, Rev, BvA)
├── create_sample_data.py         # Script to regenerate sample data
├── requirements.txt
└── .env                          # API key (not committed to git)
```

---

## How to Run

```bash
# 1. Clone the repo and navigate to the folder
cd fpna_assistant

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Anthropic API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# 5. Launch the app
./venv/bin/streamlit run app.py
```

Then open http://localhost:8501 in your browser.

---

## Using Your Own Data

**Option A — Fill in the template:**
Open `sample_data/sample_financials.xlsx` and replace the numbers with real company data.
Sheet names and row labels must stay the same.

**Option B — Upload a downloaded file:**
Export financials from a site like Stock Analysis or Macrotrends.
In the sidebar, select **"Downloaded (Macrotrends / Stock Analysis)"** and choose the correct unit (millions/thousands).
The flexible parser auto-detects year columns and maps common row label variations.

---

## Key Ratios Calculated

| Category | Ratios |
|---|---|
| Liquidity | Current Ratio, Quick Ratio, Cash Ratio |
| Profitability | Gross Margin, EBITDA Margin, Net Margin, ROE, ROA |
| Leverage | Debt/Equity, Net Debt/EBITDA, Interest Coverage, Debt/Assets |
| Efficiency | Asset Turnover, DSO, DPO, Inventory Days |
| Growth | Revenue Growth YoY, Net Income Growth YoY |

---

Built as a portfolio project to demonstrate FP&A, Python, and AI integration skills.
