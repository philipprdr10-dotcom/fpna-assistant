# pdf_10k_parser.py
# Extracts financial data from 10-K PDFs using two approaches:
# 1. pdfplumber table extraction (finds actual table structures)
# 2. Falls back to text extraction + Claude if tables not found

import pdfplumber
import anthropic
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

try:
    import streamlit as st
    if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass


# ── FINANCIAL STATEMENT KEYWORDS ─────────────────────────────────────────────

INCOME_MARKERS = [
    'net revenue', 'net revenues', 'net sales', 'total revenue',
    'total revenues', 'merchandise costs', 'cost of sales',
    'selling, general', 'operating income', 'net income',
]

BALANCE_MARKERS = [
    'total assets', 'total liabilities', 'stockholders', 'shareholders',
    'total current assets', 'total current liabilities', 'cash and cash',
]


# ── STEP 1: EXTRACT TEXT FROM ALL PAGES ──────────────────────────────────────

def extract_all_pages(file) -> list:
    """Extract (page_num, text) for every page in the PDF."""
    pages = []
    with pdfplumber.open(file) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and len(text.strip()) > 30:
                pages.append((i + 1, text.strip()))
    return pages


# ── STEP 2: FIND FINANCIAL STATEMENT PAGES ───────────────────────────────────

def is_financial_statement_page(text: str) -> bool:
    """
    Returns True if this page looks like an actual financial statement table.
    Requirements:
    - Contains financial statement keywords
    - Has multiple large numbers (millions range: X,XXX or XX,XXX or XXX,XXX)
    - NOT just prose text mentioning financials
    """
    t = text.lower()

    # Check for financial keywords
    has_income_kw  = sum(1 for k in INCOME_MARKERS  if k in t) >= 2
    has_balance_kw = sum(1 for k in BALANCE_MARKERS if k in t) >= 2

    if not (has_income_kw or has_balance_kw):
        return False

    # Count numbers that look like financial statement data
    # Pattern: number with comma separator (1,234 or 12,345 or 123,456 or 1,234,567)
    fin_numbers = re.findall(r'\b\d{1,3}(?:,\d{3})+\b', text)

    # Must have at least 8 such numbers to be a real financial table
    return len(fin_numbers) >= 8


def find_financial_pages(pages: list) -> list:
    """
    Returns the subset of pages that contain actual financial statements.
    Searches the entire document, returns up to 20 consecutive pages
    starting from the first financial statement page found.
    """
    for i, (page_num, text) in enumerate(pages):
        if is_financial_statement_page(text):
            # Found the start — grab this page + next 19
            return pages[i: i + 20]

    return []


# ── STEP 3: BUILD TEXT BLOCK FOR CLAUDE ──────────────────────────────────────

def build_financial_text(pages: list, all_pages: list) -> str:
    """
    Combines the financial statement pages into one text block.
    If no financial pages found, falls back to second half of document.
    """
    if pages:
        combined = "\n\n".join([text for _, text in pages])
        return combined[:14000]

    # Fallback: second half of the document
    mid = len(all_pages) // 2
    combined = "\n\n".join([text for _, text in all_pages[mid:]])
    return combined[:14000]


# ── STEP 4: CLAUDE EXTRACTS NUMBERS ──────────────────────────────────────────

def extract_with_claude(financial_text: str, company_name: str) -> dict:
    """
    Sends financial statement text to Claude for structured extraction.
    """

    prompt = f"""You are a financial data extraction expert analyzing a 10-K annual report for {company_name}.

The text below is extracted from the financial statements section of the 10-K.
The text may be messy due to PDF extraction — numbers and labels may be on separate lines.

CRITICAL INSTRUCTIONS:
1. Return ONLY valid JSON — no explanation, no markdown fences
2. Convert ALL numbers to FULL DOLLARS:
   - If you see "(amounts in millions)" → multiply each number by 1,000,000
   - If you see "(in thousands)" → multiply by 1,000
   - Look carefully for the unit disclosure near the top of the statements
3. Extract the TWO most recent fiscal years
4. For missing values, derive them:
   - Gross Profit = Revenue - Cost of Goods Sold
   - EBIT = Operating Income (if EBIT not listed)
   - EBITDA = EBIT + Depreciation & Amortization
5. Interest expense must be positive
6. If you truly cannot find a value after careful reading, use 0

JSON format to return:
{{
  "company_name": "{company_name}",
  "latest_year": "FY20XX",
  "prior_year": "FY20XX",
  "unit": "millions/thousands/dollars",
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

FINANCIAL STATEMENTS TEXT:
{financial_text}"""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*',     '', raw)
    raw = re.sub(r'\s*```$',     '', raw)

    return json.loads(raw)


# ── STEP 5: FORMAT FOR DASHBOARD ─────────────────────────────────────────────

def format_for_dashboard(extracted: dict, financial_text: str) -> dict:
    import pandas as pd

    latest = extracted.get("latest_year", "FY2024")
    prior  = extracted.get("prior_year",  "FY2023")
    inc    = extracted.get("income_statement", {})
    bal    = extracted.get("balance_sheet", {})

    revenue  = inc.get("revenue", 0)
    cogs     = inc.get("cost_of_goods_sold", 0)
    gross_p  = inc.get("gross_profit", 0) or (revenue - cogs if cogs else 0)
    ebit     = inc.get("ebit", 0)
    da       = inc.get("depreciation_amortization", 0)
    ebitda   = inc.get("ebitda", 0) or (ebit + da)
    interest = abs(inc.get("interest_expense", 0))
    ni       = inc.get("net_income", 0)

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
        "interest_expense": interest,
        "net_income":       ni,
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

    is_rows = [
        {"Line Item": "Revenue",                     latest: revenue,  prior: inc.get("revenue_prior", 0)},
        {"Line Item": "Cost of Goods Sold",          latest: cogs,     prior: 0},
        {"Line Item": "Gross Profit",                latest: gross_p,  prior: 0},
        {"Line Item": "EBITDA",                      latest: ebitda,   prior: 0},
        {"Line Item": "EBIT",                        latest: ebit,     prior: 0},
        {"Line Item": "Net Income",                  latest: ni,       prior: inc.get("net_income_prior", 0)},
        {"Line Item": "Interest Expense",            latest: interest, prior: 0},
        {"Line Item": "Depreciation & Amortization", latest: da,       prior: 0},
    ]

    bs_rows = [
        {"Line Item": "Cash & Equivalents",        latest: bal.get("cash", 0),                   prior: 0},
        {"Line Item": "Accounts Receivable",       latest: bal.get("accounts_receivable", 0),    prior: 0},
        {"Line Item": "Inventory",                 latest: bal.get("inventory", 0),               prior: 0},
        {"Line Item": "Total Current Assets",      latest: bal.get("total_current_assets", 0),   prior: 0},
        {"Line Item": "Total Assets",              latest: total_assets,                          prior: 0},
        {"Line Item": "Accounts Payable",          latest: bal.get("accounts_payable", 0),       prior: 0},
        {"Line Item": "Short-Term Debt",           latest: bal.get("short_term_debt", 0),         prior: 0},
        {"Line Item": "Total Current Liabilities", latest: bal.get("total_current_liabilities", 0), prior: 0},
        {"Line Item": "Long-Term Debt",            latest: bal.get("long_term_debt", 0),          prior: 0},
        {"Line Item": "Total Liabilities",         latest: total_liab,                            prior: 0},
        {"Line Item": "Shareholders Equity",       latest: equity,                                prior: 0},
    ]

    return {
        "financials":       financials,
        "balance":          balance,
        "income_statement": pd.DataFrame(is_rows),
        "balance_sheet":    pd.DataFrame(bs_rows),
        "extracted_json":   extracted,
        "_debug_sections":  {"financial_text_sent": financial_text},
    }


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────────────

def parse_10k_pdf(file, company_name: str = "the company") -> dict:
    """Full pipeline: PDF → financial pages → Claude → dashboard dict."""

    # Step 1: Extract all pages
    all_pages = extract_all_pages(file)
    if not all_pages:
        raise ValueError("No text could be extracted. This PDF may be a scanned image.")

    # Step 2: Find financial statement pages
    fin_pages = find_financial_pages(all_pages)

    # Step 3: Build text block
    financial_text = build_financial_text(fin_pages, all_pages)

    if len(financial_text) < 100:
        raise ValueError("Could not find financial statements in this PDF.")

    # Step 4: Claude extracts the numbers
    extracted = extract_with_claude(financial_text, company_name)

    # Step 5: Format for dashboard
    return format_for_dashboard(extracted, financial_text)
