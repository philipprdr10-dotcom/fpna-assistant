# ai_narrative.py
# Connects to the Claude API and generates a professional FP&A analyst narrative.
# Takes all the calculated financial data and returns a written memo.

import anthropic
import os
from dotenv import load_dotenv

# Load the API key from the .env file (local development)
load_dotenv()

# Also support Streamlit Cloud secrets (deployment)
try:
    import streamlit as st
    if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

def generate_narrative(
    financials: dict,
    balance: dict,
    ratios: dict,
    revenue_schedule_analysis: dict = None,
    budget_vs_actuals_analysis: dict = None,
    company_name: str = "the company"
) -> str:
    """
    Sends financial data to Claude and returns a written analyst narrative.

    The narrative covers:
    1. Financial health overview (revenue, margins, profitability)
    2. Balance sheet strength and liquidity
    3. FP&A focus: revenue trends, budget performance, key risks
    """

    # ── BUILD THE DATA SUMMARY FOR CLAUDE ────────────────────────
    # We format all the numbers into a clear text block
    # so Claude has everything it needs to write intelligently

    latest_year = financials.get("latest_year", "Latest Year")
    prior_year  = financials.get("prior_year", "Prior Year")

    # Format key income statement figures
    income_summary = f"""
INCOME STATEMENT ({latest_year} vs {prior_year}):
- Revenue: ${financials.get('revenue', 0):,.0f} vs ${financials.get('revenue_prior', 0):,.0f} prior year
- Gross Profit: ${financials.get('gross_profit', 0):,.0f}
- EBITDA: ${financials.get('ebitda', 0):,.0f}
- Net Income: ${financials.get('net_income', 0):,.0f} vs ${financials.get('net_income_prior', 0):,.0f} prior year
- Interest Expense: ${financials.get('interest_expense', 0):,.0f}
"""

    # Format key balance sheet figures
    balance_summary = f"""
BALANCE SHEET ({latest_year}):
- Cash: ${balance.get('cash', 0):,.0f}
- Total Current Assets: ${balance.get('current_assets', 0):,.0f}
- Total Assets: ${balance.get('total_assets', 0):,.0f}
- Total Current Liabilities: ${balance.get('current_liabilities', 0):,.0f}
- Short-Term Debt: ${balance.get('short_term_debt', 0):,.0f}
- Long-Term Debt: ${balance.get('long_term_debt', 0):,.0f}
- Shareholders Equity: ${balance.get('shareholders_equity', 0):,.0f}
"""

    # Format key ratios
    def fmt_ratio(r):
        """Helper to format a ratio value nicely."""
        if not r:
            return "N/A"
        val = r.get("value", 0)
        fmt = r.get("format", "multiple")
        if fmt == "percent":
            return f"{val}%"
        elif fmt == "days":
            return f"{val} days"
        else:
            return f"{val}x"

    ratios_summary = f"""
KEY RATIOS:
LIQUIDITY:
- Current Ratio: {fmt_ratio(ratios.get('current_ratio'))} (benchmark: 1.5-3.0x)
- Quick Ratio: {fmt_ratio(ratios.get('quick_ratio'))}

PROFITABILITY:
- Gross Margin: {fmt_ratio(ratios.get('gross_margin'))}
- EBITDA Margin: {fmt_ratio(ratios.get('ebitda_margin'))}
- Net Margin: {fmt_ratio(ratios.get('net_margin'))}
- ROE: {fmt_ratio(ratios.get('roe'))}
- ROA: {fmt_ratio(ratios.get('roa'))}

LEVERAGE:
- Debt-to-Equity: {fmt_ratio(ratios.get('debt_to_equity'))}
- Net Debt/EBITDA: {fmt_ratio(ratios.get('net_debt_ebitda'))}
- Interest Coverage: {fmt_ratio(ratios.get('interest_coverage'))}

EFFICIENCY:
- Asset Turnover: {fmt_ratio(ratios.get('asset_turnover'))}
- DSO: {fmt_ratio(ratios.get('dso'))}
- DPO: {fmt_ratio(ratios.get('dpo'))}
- Inventory Days: {fmt_ratio(ratios.get('inventory_days'))}

GROWTH:
- Revenue Growth (YoY): {fmt_ratio(ratios.get('revenue_growth'))}
- Net Income Growth (YoY): {fmt_ratio(ratios.get('ni_growth'))}
"""

    # Format revenue schedule analysis if available
    revenue_summary = ""
    if revenue_schedule_analysis:
        rs = revenue_schedule_analysis
        revenue_summary = f"""
REVENUE SCHEDULE ANALYSIS:
- Total Annual Revenue (Actual): ${rs.get('total_actual', 0):,.0f}
- Total Annual Revenue (Budget): ${rs.get('total_budget', 0):,.0f}
- YoY Budgeted Growth: {rs.get('yoy_growth_pct', 0)}%
- Best Month: {rs.get('best_month', 'N/A')}
- Worst Month: {rs.get('worst_month', 'N/A')}
- Run Rate (Annualized): ${rs.get('run_rate_annual', 0):,.0f}
- Months Beating Budget: {rs.get('months_beating_budget', 0)} of {rs.get('total_months', 12)}
"""

    # Format budget vs actuals if available
    bva_summary = ""
    if budget_vs_actuals_analysis:
        bva = budget_vs_actuals_analysis
        bva_summary = f"""
BUDGET VS ACTUALS (YTD):
- Revenue: Actual ${bva.get('revenue_variance_usd', 0):+,.0f} vs YTD Budget ({bva.get('revenue_variance_pct', 0):+.1f}%)
- EBITDA: Actual ${bva.get('ebitda_variance_usd', 0):+,.0f} vs YTD Budget ({bva.get('ebitda_variance_pct', 0):+.1f}%)
- Net Income: Actual ${bva.get('ni_variance_usd', 0):+,.0f} vs YTD Budget ({bva.get('ni_variance_pct', 0):+.1f}%)
- Favorable Lines: {bva.get('favorable_count', 0)} of {bva.get('total_lines', 0)}
- On Track for Full Year: {bva.get('on_track', False)}
- Implied Full Year Revenue: ${bva.get('implied_full_year', 0):,.0f}
"""

    # ── BUILD THE PROMPT ──────────────────────────────────────────
    # This is the instruction we give Claude — the more specific,
    # the better the output
    prompt = f"""You are a senior FP&A analyst writing an internal financial review memo for {company_name}.

Based on the financial data below, write a professional analyst narrative with exactly 3 paragraphs:

PARAGRAPH 1 — FINANCIAL PERFORMANCE OVERVIEW:
Summarize revenue growth, profitability trends (gross margin, EBITDA margin, net income), and year-over-year changes. Use specific numbers. Be direct and analytical.

PARAGRAPH 2 — BALANCE SHEET & FINANCIAL HEALTH:
Comment on liquidity position (current ratio, cash), leverage (debt levels, interest coverage, net debt/EBITDA), and return metrics (ROE, ROA). Note any strengths or concerns.

PARAGRAPH 3 — FP&A FOCUS (BUDGET, REVENUE TRENDS & RISKS):
Discuss budget vs actuals performance, revenue schedule trends, seasonality, and full-year pacing. Identify the top 2-3 risks or areas requiring management attention. End with a brief outlook.

FINANCIAL DATA:
{income_summary}
{balance_summary}
{ratios_summary}
{revenue_summary}
{bva_summary}

WRITING STYLE REQUIREMENTS:
- Write like a real FP&A analyst, not an AI
- Use precise financial language (e.g. "EBITDA margin expanded 240bps", not "profit improved")
- Each paragraph should be 4-6 sentences
- Do NOT use bullet points — this is flowing prose only
- Do NOT start with "I" or "As an AI"
- Start directly with the analysis
"""

    # ── CALL THE CLAUDE API ───────────────────────────────────────
    try:
        # Initialize the Anthropic client
        # It automatically reads ANTHROPIC_API_KEY from the .env file
        client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        # Send the prompt to Claude and get a response
        message = client.messages.create(
            model="claude-sonnet-4-5",       # Best model for analytical writing
            max_tokens=1024,                  # Enough for 3 solid paragraphs
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract the text from the response
        narrative = message.content[0].text
        return narrative

    except anthropic.AuthenticationError:
        return "❌ API Key Error: Please check your ANTHROPIC_API_KEY in the .env file."
    except anthropic.RateLimitError:
        return "❌ Rate Limit: Too many requests. Please wait a moment and try again."
    except Exception as e:
        return f"❌ Error generating narrative: {str(e)}"