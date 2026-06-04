# pdf_10k_parser.py
# Parses a real 10-K PDF by:
# 1. Extracting raw text using pdfplumber
# 2. Finding the financial statement pages (IS, BS)
# 3. Sending those sections to Claude to extract structured numbers
# 4. Returning the same dict format as parser.py so the dashboard works unchanged

import pdfplumber
import anthropic
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

# Also support Streamlit Cloud secrets
try:
    import streamlit as st
    if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass


# ── TEXT EXTRACTION ───────────────────────────────────────────────────────────

def extract_text_from_pdf(file) -> str:
    """
    Extracts all text from a PDF file.
    Returns the full text as a single string.
    """
    full_text = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
    return "\n".join(full_text)


def find_financial_sections(full_text: str) -> dict:
    """
    Searches the extracted text for the income statement and balance sheet
    sections by looking for common 10-K section headers.
    Returns a dict with 'income_statement' and 'balance_sheet' text chunks.
    """

    # Common headers for income statement in 10-Ks
    income_keywords = [
        "CONSOLIDATED STATEMENTS OF OPERATIONS",
        "CONSOLIDATED STATEMENTS OF INCOME",
        "CONSOLIDATED STATEMENTS OF EARNINGS",
        "STATEMENTS OF OPERATIONS",
        "STATEMENTS OF INCOME",
        "INCOME STATEMENT",
    ]

    # Common headers for balance sheet
    balance_keywords = [
        "CONSOLIDATED BALANCE SHEETS",
        "CONSOLIDATED BALANCE SHEET",
        "BALANCE SHEETS",
        "BALANCE SHEET",
        "CONSOLIDATED STATEMENTS OF FINANCIAL POSITION",
        "STATEMENTS OF FINANCIAL POSITION",
    ]

    text_upper = full_text.upper()
    sections = {}

    # Find income statement section
    for kw in income_keywords:
        idx = text_upper.find(kw)
        if idx != -1:
            # Take 3000 characters after the header — enough for the full statement
            sections["income_statement"] = full_text[idx: idx + 3000]
            break

    # Find balance sheet section
    for kw in balance_keywords:
        idx = text_upper.find(kw)
        if idx != -1:
            sections["balance_sheet"] = full_text[idx: idx + 3000]
            break

    # If we couldn't find specific sections, take the middle chunk of the doc
    # (financial statements usually appear in the middle of a 10-K)
    if not sections:
        mid = len(full_text) // 2
        sections["income_statement"] = full_text[mid: mid + 4000]
        sections["balance_sheet"]    = full_text[mid + 2000: mid + 6000]

    return sections


# ── CLAUDE EXTRACTION ─────────────────────────────────────────────────────────

def extract_financials_with_claude(sections: dict, company_name: str = "the company") -> dict:
    """
    Sends the financial statement text to Claude and asks it to extract
    key numbers as structured JSON.
    Returns a dict in our standard format (same as parser.py output).
    """

    income_text  = sections.get("income_statement", "")
    balance_text = sections.get("balance_sheet", "")

    prompt = f"""You are a financial data extraction assistant. I will give you raw text extracted from a 10-K annual report for {company_name}.

Your job is to extract the key financial figures and return them as a JSON object.

IMPORTANT RULES:
- Return ONLY valid JSON, no other text
- All numbers should be in FULL DOLLARS (if the report says "in millions", multiply by 1,000,000)
- If a value is not found, use 0
- Extract the two most recent fiscal years available
- For the income statement, look for the most recent year and the prior year
- Use negative numbers for expenses if they appear that way in the source

Return this exact JSON structure:
{{
  "company_name": "string",
  "latest_year": "FY20XX",
  "prior_year": "FY20XX",
  "income_statement": {{
    "revenue": 0,
    "revenue_prior": 0,
    "cost_of_goods_sold": 0,
    "gross_profit": 0,
    "operating_expenses": 0,
    "ebit": 0,
    "depreciation_amortization": 0,
    "ebitda": 0,
    "interest_expense": 0,
    "tax_expense": 0,
    "net_income": 0,
    "net_income_prior": 0
  }},
  "balance_sheet": {{
    "cash": 0,
    "accounts_receivable": 0,
    "inventory": 0,
    "total_current_assets": 0,
    "total_assets": 0,
    "accounts_payable": 0,
    "short_term_debt": 0,
    "total_current_liabilities": 0,
    "long_term_debt": 0,
    "total_liabilities": 0,
    "shareholders_equity": 0
  }}
}}

INCOME STATEMENT TEXT:
{income_text}

BALANCE SHEET TEXT:
{balance_text}

Return only the JSON object, nothing else."""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()

    # Sometimes Claude adds ```json ... ``` fences — strip them
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*",     "", raw)
    raw = re.sub(r"\s*```$",     "", raw)

    return json.loads(raw)


# ── DATA FORMATTER ────────────────────────────────────────────────────────────

def format_for_dashboard(extracted: dict) -> dict:
    """
    Takes the JSON returned by Claude and converts it into the exact
    dict format that app.py expects (same as parser.py output).
    """

    latest = extracted.get("latest_year", "FY2024")
    prior  = extracted.get("prior_year",  "FY2023")
    inc    = extracted.get("income_statement", {})
    bal    = extracted.get("balance_sheet", {})

    # Derive EBITDA if not provided
    ebit   = inc.get("ebit", 0)
    da     = inc.get("depreciation_amortization", 0)
    ebitda = inc.get("ebitda", 0) or (ebit + da)

    # Derive gross profit if not provided
    revenue = inc.get("revenue", 0)
    cogs    = inc.get("cost_of_goods_sold", 0)
    gross_p = inc.get("gross_profit", 0) or (revenue - cogs if cogs else 0)

    # Derive equity if not provided
    total_assets = bal.get("total_assets", 0)
    total_liab   = bal.get("total_liabilities", 0)
    equity       = bal.get("shareholders_equity", 0) or (total_assets - total_liab)

    financials = {
        "latest_year":      latest,
        "prior_year":       prior,
        "revenue":          revenue,
        "revenue_prior":    inc.get("revenue_prior", 0),
        "gross_profit":     gross_p,
        "ebitda":           ebitda,
        "ebit":             ebit,
        "interest_expense": abs(inc.get("interest_expense", 0)),  # always positive
        "net_income":       inc.get("net_income", 0),
        "net_income_prior": inc.get("net_income_prior", 0),
        "da":               da,
        "tax_expense":      inc.get("tax_expense", 0),
        "cogs":             cogs,
    }

    balance = {
        "latest_year":               latest,
        "cash":                      bal.get("cash", 0),
        "accounts_receivable":       bal.get("accounts_receivable", 0),
        "inventory":                 bal.get("inventory", 0),
        "current_assets":            bal.get("total_current_assets", 0),
        "total_assets":              total_assets,
        "total_assets_prior":        0,
        "accounts_payable":          bal.get("accounts_payable", 0),
        "current_liabilities":       bal.get("total_current_liabilities", 0),
        "short_term_debt":           bal.get("short_term_debt", 0),
        "long_term_debt":            bal.get("long_term_debt", 0),
        "total_liabilities":         total_liab,
        "shareholders_equity":       equity,
        "shareholders_equity_prior": 0,
    }

    # Build minimal income statement DataFrame for trend charts
    import pandas as pd
    is_rows = [
        {"Line Item": "Revenue",          latest: revenue,          prior: inc.get("revenue_prior", 0)},
        {"Line Item": "Cost of Goods Sold", latest: cogs,            prior: 0},
        {"Line Item": "Gross Profit",     latest: gross_p,          prior: 0},
        {"Line Item": "EBITDA",           latest: ebitda,           prior: 0},
        {"Line Item": "EBIT",             latest: ebit,             prior: 0},
        {"Line Item": "Net Income",       latest: inc.get("net_income", 0), prior: inc.get("net_income_prior", 0)},
        {"Line Item": "Interest Expense", latest: abs(inc.get("interest_expense", 0)), prior: 0},
        {"Line Item": "Depreciation & Amortization", latest: da,   prior: 0},
    ]
    income_df = pd.DataFrame(is_rows)

    bs_rows = [
        {"Line Item": "Cash & Equivalents",         latest: bal.get("cash", 0),                  prior: 0},
        {"Line Item": "Accounts Receivable",        latest: bal.get("accounts_receivable", 0),   prior: 0},
        {"Line Item": "Inventory",                  latest: bal.get("inventory", 0),              prior: 0},
        {"Line Item": "Total Current Assets",       latest: bal.get("total_current_assets", 0),  prior: 0},
        {"Line Item": "Total Assets",               latest: total_assets,                         prior: 0},
        {"Line Item": "Accounts Payable",           latest: bal.get("accounts_payable", 0),      prior: 0},
        {"Line Item": "Short-Term Debt",            latest: bal.get("short_term_debt", 0),        prior: 0},
        {"Line Item": "Total Current Liabilities",  latest: bal.get("total_current_liabilities", 0), prior: 0},
        {"Line Item": "Long-Term Debt",             latest: bal.get("long_term_debt", 0),         prior: 0},
        {"Line Item": "Total Liabilities",          latest: total_liab,                           prior: 0},
        {"Line Item": "Shareholders Equity",        latest: equity,                               prior: 0},
    ]
    balance_df = pd.DataFrame(bs_rows)

    return {
        "financials":       financials,
        "balance":          balance,
        "income_statement": income_df,
        "balance_sheet":    balance_df,
        "extracted_json":   extracted,   # keep raw for debugging
    }


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────────────

def parse_10k_pdf(file, company_name: str = "the company") -> dict:
    """
    Full pipeline: PDF → text → Claude → dashboard-ready dict.
    Call this from app.py.

    Returns a dict with 'financials', 'balance', 'income_statement', 'balance_sheet'
    OR raises an exception with an error message.
    """
    # Step 1: Extract text
    full_text = extract_text_from_pdf(file)
    if len(full_text) < 500:
        raise ValueError("Could not extract text from this PDF. It may be a scanned image — try a text-based PDF.")

    # Step 2: Find financial statement sections
    sections = find_financial_sections(full_text)

    # Step 3: Claude extracts the numbers
    extracted = extract_financials_with_claude(sections, company_name)

    # Step 4: Format for dashboard
    return format_for_dashboard(extracted)
