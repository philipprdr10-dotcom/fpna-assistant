# pdf_10k_parser.py
# Smart 10-K PDF parser.
# Strategy: extract all text from the financial statements section of the PDF,
# then send it directly to Claude and let Claude find the numbers.
# Claude is far better at reading messy PDF text than any regex approach.

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


# ── STEP 1: EXTRACT TEXT ──────────────────────────────────────────────────────

def extract_text_from_pdf(file) -> list:
    """
    Extracts text from every page of the PDF.
    Returns list of (page_number, text) tuples.
    Only includes pages with meaningful text (skips blank/image pages).
    """
    pages = []
    with pdfplumber.open(file) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and len(text.strip()) > 30:
                pages.append((i + 1, text.strip()))
    return pages


# ── STEP 2: FIND ITEM 8 (FINANCIAL STATEMENTS SECTION) ───────────────────────

def find_financial_text(pages: list) -> str:
    """
    Finds the financial statements section of the 10-K.
    In every US 10-K, financial statements are in Item 8.
    Returns a large text block containing the actual financial tables.
    """

    # First: find the page where Item 8 begins
    item8_page_idx = None
    for i, (page_num, text) in enumerate(pages):
        t = text.upper()
        # Look for Item 8 header — must mention financial statements
        if re.search(r'ITEM\s*8[\.\s]', t) and 'FINANCIAL' in t:
            item8_page_idx = i
            break

    if item8_page_idx is not None:
        # Take everything from Item 8 onwards (up to 30 pages)
        relevant_pages = pages[item8_page_idx: item8_page_idx + 30]
    else:
        # Fallback: take the last 40% of the document
        start = int(len(pages) * 0.6)
        relevant_pages = pages[start:]

    # Combine all the relevant text
    combined = "\n\n--- PAGE BREAK ---\n\n".join([text for _, text in relevant_pages])

    # Return up to 12,000 characters — enough for IS + BS + some notes
    return combined[:12000]


# ── STEP 3: CLAUDE EXTRACTS THE NUMBERS ──────────────────────────────────────

def extract_with_claude(financial_text: str, company_name: str) -> dict:
    """
    Sends the financial statement text to Claude.
    Claude is smart enough to handle messy PDF text, column misalignment,
    and different number formats (thousands, millions, etc).
    Returns structured JSON.
    """

    prompt = f"""You are a financial data extraction expert. Below is raw text extracted from a 10-K annual report (SEC filing) for {company_name}.

The text may be messy due to PDF extraction — columns may be misaligned, numbers may appear on separate lines from their labels. Use your financial expertise to correctly identify and match numbers to their line items.

IMPORTANT RULES:
1. Return ONLY valid JSON — no explanation, no markdown, no code fences
2. Convert ALL numbers to FULL DOLLARS:
   - If the report says "in millions", multiply each number by 1,000,000
   - If the report says "in thousands", multiply by 1,000
   - Look for a note near the top of the statements like "(in millions)" or "(dollars in thousands)"
3. Extract the TWO most recent fiscal years
4. Use 0 only if you genuinely cannot find the value after careful reading
5. For EBITDA: if not stated directly, calculate as Operating Income + Depreciation & Amortization
6. For EBIT: use Operating Income if EBIT is not listed separately
7. Interest expense should always be a positive number

Return this exact JSON:
{{
  "company_name": "{company_name}",
  "latest_year": "FY20XX",
  "prior_year": "FY20XX",
  "unit": "millions or thousands or dollars",
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

10-K FINANCIAL STATEMENTS TEXT:
{financial_text}"""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*',     '', raw)
    raw = re.sub(r'\s*```$',     '', raw)

    return json.loads(raw)


# ── STEP 4: FORMAT FOR DASHBOARD ──────────────────────────────────────────────

def format_for_dashboard(extracted: dict) -> dict:
    """
    Converts Claude's JSON into the dict format app.py expects.
    """
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
        {"Line Item": "Cash & Equivalents",        latest: bal.get("cash", 0),                  prior: 0},
        {"Line Item": "Accounts Receivable",       latest: bal.get("accounts_receivable", 0),   prior: 0},
        {"Line Item": "Inventory",                 latest: bal.get("inventory", 0),              prior: 0},
        {"Line Item": "Total Current Assets",      latest: bal.get("total_current_assets", 0),  prior: 0},
        {"Line Item": "Total Assets",              latest: total_assets,                         prior: 0},
        {"Line Item": "Accounts Payable",          latest: bal.get("accounts_payable", 0),      prior: 0},
        {"Line Item": "Short-Term Debt",           latest: bal.get("short_term_debt", 0),        prior: 0},
        {"Line Item": "Total Current Liabilities", latest: bal.get("total_current_liabilities", 0), prior: 0},
        {"Line Item": "Long-Term Debt",            latest: bal.get("long_term_debt", 0),         prior: 0},
        {"Line Item": "Total Liabilities",         latest: total_liab,                           prior: 0},
        {"Line Item": "Shareholders Equity",       latest: equity,                               prior: 0},
    ]

    return {
        "financials":       financials,
        "balance":          balance,
        "income_statement": pd.DataFrame(is_rows),
        "balance_sheet":    pd.DataFrame(bs_rows),
        "extracted_json":   extracted,
        "_debug_sections":  {"financial_text_sent": financial_text_cache},
    }


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────────────

financial_text_cache = ""  # Store for debug panel

def parse_10k_pdf(file, company_name: str = "the company") -> dict:
    """
    Full pipeline: PDF → text → Claude → dashboard dict.
    """
    global financial_text_cache

    # Step 1: Extract all text from PDF
    pages = extract_text_from_pdf(file)
    if not pages:
        raise ValueError("No text could be extracted. This PDF may be a scanned image.")

    # Step 2: Find the financial statements section
    financial_text = find_financial_text(pages)
    financial_text_cache = financial_text

    if len(financial_text) < 200:
        raise ValueError("Could not find financial statements in this PDF.")

    # Step 3: Claude extracts numbers from the text
    extracted = extract_with_claude(financial_text, company_name)

    # Step 4: Format for dashboard
    return format_for_dashboard(extracted)
