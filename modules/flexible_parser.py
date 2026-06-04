# flexible_parser.py
# Parses financial Excel files downloaded from sites like Macrotrends,
# Stock Analysis, or exported from financial databases.
# Unlike parser.py (which expects our exact template), this module tries
# to handle messy, real-world layouts by fuzzy-matching row labels.

import pandas as pd
import re
from io import BytesIO


# ── SYNONYM MAPS ──────────────────────────────────────────────────────────────
# Maps many possible row label variations → our internal standard label.
# Lower-cased for matching. Add more synonyms here as needed.

INCOME_SYNONYMS = {
    "revenue": [
        "revenue", "total revenue", "net revenue", "net sales",
        "total net revenue", "sales", "total sales", "revenues",
    ],
    "cost of goods sold": [
        "cost of goods sold", "cost of revenue", "cogs",
        "cost of sales", "cost of products", "cost of services",
    ],
    "gross profit": [
        "gross profit", "gross income", "gross margin dollar",
    ],
    "operating expenses": [
        "operating expenses", "total operating expenses",
        "selling general and administrative", "sg&a",
        "operating costs",
    ],
    "ebit": [
        "ebit", "operating income", "income from operations",
        "operating profit", "earnings before interest and taxes",
    ],
    "ebitda": [
        "ebitda",
        "earnings before interest taxes depreciation and amortization",
    ],
    "depreciation & amortization": [
        "depreciation & amortization", "depreciation and amortization",
        "d&a", "depreciation amortization", "depreciation",
    ],
    "interest expense": [
        "interest expense", "interest expense net", "interest and debt expense",
        "net interest expense", "interest costs",
    ],
    "tax expense": [
        "tax expense", "income tax expense", "provision for income taxes",
        "income taxes", "tax provision",
    ],
    "net income": [
        "net income", "net earnings", "net profit",
        "net income common stockholders", "net income applicable to common shares",
        "net income attributable to common shareholders",
        "earnings attributable to common shareholders",
    ],
}

BALANCE_SYNONYMS = {
    "cash & equivalents": [
        "cash & equivalents", "cash and cash equivalents",
        "cash and short-term investments", "cash cash equivalents",
        "cash and equivalents",
    ],
    "accounts receivable": [
        "accounts receivable", "net receivables", "trade receivables",
        "receivables", "accounts receivable net",
    ],
    "inventory": [
        "inventory", "inventories", "total inventory",
    ],
    "total current assets": [
        "total current assets", "current assets",
    ],
    "total assets": [
        "total assets", "assets total",
    ],
    "accounts payable": [
        "accounts payable", "trade payables", "payables",
    ],
    "short-term debt": [
        "short-term debt", "current portion of long term debt",
        "short term borrowings", "current debt",
        "notes payable", "commercial paper",
    ],
    "total current liabilities": [
        "total current liabilities", "current liabilities",
    ],
    "long-term debt": [
        "long-term debt", "long term debt", "long-term borrowings",
        "non-current debt", "long term borrowings",
    ],
    "total liabilities": [
        "total liabilities", "liabilities total",
        "total liabilities and equity",   # some sheets combine these — handled below
    ],
    "shareholders equity": [
        "shareholders equity", "stockholders equity", "total equity",
        "total stockholders equity", "shareholders equity total",
        "common stockholders equity", "total shareholders equity",
    ],
}


# ── NUMBER NORMALIZER ─────────────────────────────────────────────────────────

def clean_number(val, unit_multiplier=1_000_000):
    """
    Converts a messy cell value to a plain float in dollars.

    Handles:
      - Numbers already stored as int/float
      - Strings like "1,234.5", "(1,234.5)" [negative], "1.2B", "345M", "500K"
      - Blanks / dashes → 0

    unit_multiplier: multiply by this to convert to dollars.
      1_000_000 = file is in millions (most common for 10-Ks)
      1_000     = file is in thousands
      1         = file is already in dollars
    """
    if pd.isna(val) or val == "" or val == "-" or val == "—":
        return 0.0

    if isinstance(val, (int, float)):
        return float(val) * unit_multiplier

    s = str(val).strip().replace(",", "").replace(" ", "")

    # Handle parentheses for negatives: (1234) → -1234
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]

    # Handle suffix multipliers
    suffix_map = {"B": 1e9, "M": 1e6, "K": 1e3}
    for suffix, mult in suffix_map.items():
        if s.upper().endswith(suffix):
            try:
                num = float(s[:-1]) * mult
                return -num if negative else num
            except ValueError:
                return 0.0

    try:
        num = float(s) * unit_multiplier
        return -num if negative else num
    except ValueError:
        return 0.0


# ── YEAR COLUMN DETECTOR ──────────────────────────────────────────────────────

def detect_year_columns(df):
    """
    Finds columns that look like fiscal years.
    Accepts: "FY2024", "2024", 2024, "Dec 2024", "FY 2024", etc.
    Returns a list of (original_col_name, "FY20XX") tuples, oldest first.
    """
    year_cols = []
    for col in df.columns:
        col_str = str(col).strip()
        # Look for a 4-digit year in the column name
        match = re.search(r"(20\d{2}|19\d{2})", col_str)
        if match:
            year = match.group(1)
            year_cols.append((col, f"FY{year}"))

    # Sort oldest → newest
    year_cols.sort(key=lambda x: x[1])
    return year_cols


# ── ROW LABEL MATCHER ─────────────────────────────────────────────────────────

def match_label(cell_value, synonym_map):
    """
    Given a cell value (row label), returns the standardized key if it matches
    any synonym. Returns None if no match found.
    """
    if pd.isna(cell_value):
        return None
    normalized = str(cell_value).strip().lower()
    # Remove trailing colons, asterisks, footnote markers
    normalized = re.sub(r"[\*\:†‡§¶]+$", "", normalized).strip()

    for standard_key, synonyms in synonym_map.items():
        if normalized in synonyms:
            return standard_key
    return None


# ── SHEET FINDER ──────────────────────────────────────────────────────────────

INCOME_SHEET_NAMES = [
    "income statement", "income statements", "profit and loss",
    "p&l", "consolidated statements of operations",
    "statements of operations", "operations",
]

BALANCE_SHEET_NAMES = [
    "balance sheet", "balance sheets", "consolidated balance sheets",
    "financial position", "statement of financial position",
]

def find_sheet(xl, candidates):
    """Returns the first sheet name that matches one of the candidate strings."""
    for sheet in xl.sheet_names:
        if sheet.strip().lower() in candidates:
            return sheet
    return None


# ── MAIN FLEXIBLE PARSE FUNCTION ─────────────────────────────────────────────

def parse_flexible_excel(file, unit_multiplier=1_000_000):
    """
    Parses a real-world financial Excel file and returns the same dict
    structure as parser.parse_excel(), so the rest of the app works unchanged.

    unit_multiplier:
      Pass 1_000_000 if the file reports in millions (default — most 10-Ks).
      Pass 1_000     if the file reports in thousands.
      Pass 1         if the file reports in full dollars.
    """
    xl = pd.ExcelFile(file)
    data = {}

    # ── INCOME STATEMENT ────────────────────────────────────────────
    is_sheet = find_sheet(xl, INCOME_SHEET_NAMES)
    if is_sheet:
        raw = xl.parse(is_sheet, header=None)
        is_df, is_years = _parse_statement(raw, INCOME_SYNONYMS, unit_multiplier)
        if is_df is not None:
            data["income_statement"] = is_df
            data["financials"] = _extract_income_figures(is_df, is_years)

    # ── BALANCE SHEET ────────────────────────────────────────────────
    bs_sheet = find_sheet(xl, BALANCE_SHEET_NAMES)
    if bs_sheet:
        raw = xl.parse(bs_sheet, header=None)
        bs_df, bs_years = _parse_statement(raw, BALANCE_SYNONYMS, unit_multiplier)
        if bs_df is not None:
            data["balance_sheet"] = bs_df
            data["balance"] = _extract_balance_figures(bs_df, bs_years)

    return data


# ── STATEMENT PARSER ──────────────────────────────────────────────────────────

def _parse_statement(raw_df, synonym_map, unit_multiplier):
    """
    Scans a raw sheet (no assumed header row) and builds a clean DataFrame
    with columns: ["Line Item", "FY20XX", "FY20XX", ...].

    Returns (clean_df, list_of_fy_col_names) or (None, []) on failure.
    """
    # Step 1: Find the header row — the row that contains year-like values
    header_row_idx = None
    year_cols_in_header = []

    for i, row in raw_df.iterrows():
        cols_found = detect_year_columns(pd.Series(row.values, name="tmp").rename(
            {j: raw_df.columns[j] for j in range(len(raw_df.columns))}
        ).to_frame().T.iloc[0])
        # detect_year_columns expects a DataFrame column, so do it differently:
        year_hits = []
        for j, cell in enumerate(row):
            cell_str = str(cell).strip()
            m = re.search(r"(20\d{2}|19\d{2})", cell_str)
            if m:
                year_hits.append((j, f"FY{m.group(1)}"))
        if len(year_hits) >= 2:
            header_row_idx = i
            year_cols_in_header = year_hits
            break

    if header_row_idx is None:
        return None, []

    # Sort year columns oldest → newest
    year_cols_in_header.sort(key=lambda x: x[1])

    # Step 2: Scan rows below the header, match labels, pull numbers
    rows = []
    seen_labels = set()

    for i in range(header_row_idx + 1, len(raw_df)):
        row = raw_df.iloc[i]

        # The label is usually in the first non-empty cell of the row
        label_cell = None
        for cell in row:
            if not pd.isna(cell) and str(cell).strip() not in ("", "-", "—"):
                label_cell = cell
                break

        standard_label = match_label(label_cell, synonym_map)
        if standard_label is None or standard_label in seen_labels:
            continue
        seen_labels.add(standard_label)

        # Pull numeric values for each year column
        row_data = {"Line Item": standard_label.title()}
        for col_idx, fy_label in year_cols_in_header:
            raw_val = row.iloc[col_idx] if col_idx < len(row) else None
            row_data[fy_label] = clean_number(raw_val, unit_multiplier)

        rows.append(row_data)

    if not rows:
        return None, []

    clean_df = pd.DataFrame(rows)
    fy_labels = [fy for _, fy in year_cols_in_header]

    # Standardize "Line Item" labels to match what the rest of the app expects
    label_corrections = {k.title(): k for k in synonym_map.keys()}
    label_corrections.update({
        "Cost Of Goods Sold": "Cost of Goods Sold",
        "Depreciation & Amortization": "Depreciation & Amortization",
        "Shareholders Equity": "Shareholders Equity",
        "Cash & Equivalents": "Cash & Equivalents",
        "Accounts Receivable": "Accounts Receivable",
        "Total Current Assets": "Total Current Assets",
        "Total Assets": "Total Assets",
        "Accounts Payable": "Accounts Payable",
        "Short-Term Debt": "Short-Term Debt",
        "Total Current Liabilities": "Total Current Liabilities",
        "Long-Term Debt": "Long-Term Debt",
        "Total Liabilities": "Total Liabilities",
        "Ebit": "EBIT",
        "Ebitda": "EBITDA",
        "Tax Expense": "Tax Expense",
        "Net Income": "Net Income",
        "Revenue": "Revenue",
        "Gross Profit": "Gross Profit",
        "Interest Expense": "Interest Expense",
        "Operating Expenses": "Operating Expenses",
        "Depreciation & Amortization": "Depreciation & Amortization",
    })
    clean_df["Line Item"] = clean_df["Line Item"].replace(label_corrections)

    return clean_df, fy_labels


# ── FIGURE EXTRACTORS ─────────────────────────────────────────────────────────

def _get(df, label, col):
    """Pull a value from the clean DataFrame by label and year column."""
    try:
        row = df[df["Line Item"] == label]
        if row.empty:
            return 0.0
        return float(row[col].values[0])
    except:
        return 0.0


def _extract_income_figures(df, year_cols):
    """Build the financials dict from the clean income statement DataFrame."""
    if not year_cols:
        return {}

    latest = year_cols[-1]
    prior  = year_cols[-2] if len(year_cols) > 1 else latest

    revenue     = _get(df, "Revenue", latest)
    gross_p     = _get(df, "Gross Profit", latest)
    ebit        = _get(df, "EBIT", latest)
    ebitda      = _get(df, "EBITDA", latest)
    da          = _get(df, "Depreciation & Amortization", latest)
    interest    = _get(df, "Interest Expense", latest)
    net_income  = _get(df, "Net Income", latest)
    cogs        = _get(df, "Cost of Goods Sold", latest)

    # Derive missing figures if not directly available
    if gross_p == 0 and revenue and cogs:
        gross_p = revenue - cogs
    if ebitda == 0 and ebit:
        ebitda = ebit + da
    if ebit == 0 and ebitda:
        ebit = ebitda - da

    return {
        "latest_year":      latest,
        "prior_year":       prior,
        "revenue":          revenue,
        "revenue_prior":    _get(df, "Revenue", prior),
        "gross_profit":     gross_p,
        "ebitda":           ebitda,
        "ebit":             ebit,
        "interest_expense": interest,
        "net_income":       net_income,
        "net_income_prior": _get(df, "Net Income", prior),
        "da":               da,
        "tax_expense":      _get(df, "Tax Expense", latest),
        "cogs":             cogs,
    }


def _extract_balance_figures(df, year_cols):
    """Build the balance dict from the clean balance sheet DataFrame."""
    if not year_cols:
        return {}

    latest = year_cols[-1]
    prior  = year_cols[-2] if len(year_cols) > 1 else latest

    total_assets = _get(df, "Total Assets", latest)
    total_liab   = _get(df, "Total Liabilities", latest)
    equity       = _get(df, "Shareholders Equity", latest)

    # Derive equity if not listed (Assets - Liabilities)
    if equity == 0 and total_assets and total_liab:
        equity = total_assets - total_liab

    return {
        "latest_year":               latest,
        "cash":                      _get(df, "Cash & Equivalents", latest),
        "accounts_receivable":       _get(df, "Accounts Receivable", latest),
        "inventory":                 _get(df, "Inventory", latest),
        "current_assets":            _get(df, "Total Current Assets", latest),
        "total_assets":              total_assets,
        "total_assets_prior":        _get(df, "Total Assets", prior),
        "accounts_payable":          _get(df, "Accounts Payable", latest),
        "current_liabilities":       _get(df, "Total Current Liabilities", latest),
        "short_term_debt":           _get(df, "Short-Term Debt", latest),
        "long_term_debt":            _get(df, "Long-Term Debt", latest),
        "total_liabilities":         total_liab,
        "shareholders_equity":       equity,
        "shareholders_equity_prior": _get(df, "Shareholders Equity", prior),
    }
