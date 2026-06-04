# parser.py
# Reads the uploaded Excel file and extracts financial data from each sheet

import pandas as pd
from io import BytesIO

def parse_excel(file) -> dict:
    """
    Takes an Excel file and returns a dictionary containing
    one DataFrame per financial statement sheet.
    """
    xl = pd.ExcelFile(file)
    data = {}

    if "Income Statement" in xl.sheet_names:
        df = xl.parse("Income Statement")
        df.columns = df.columns.str.strip()
        df["Line Item"] = df["Line Item"].str.strip()
        data["income_statement"] = df
        data["financials"] = extract_key_figures(df)

    if "Balance Sheet" in xl.sheet_names:
        df = xl.parse("Balance Sheet")
        df.columns = df.columns.str.strip()
        df["Line Item"] = df["Line Item"].str.strip()
        data["balance_sheet"] = df
        data["balance"] = extract_balance_figures(df)

    if "Cash Flow" in xl.sheet_names:
        df = xl.parse("Cash Flow")
        df.columns = df.columns.str.strip()
        df["Line Item"] = df["Line Item"].str.strip()
        data["cash_flow"] = df

    if "Revenue Schedule" in xl.sheet_names:
        df = xl.parse("Revenue Schedule")
        df.columns = df.columns.str.strip()
        data["revenue_schedule"] = df

    if "Budget vs Actuals" in xl.sheet_names:
        df = xl.parse("Budget vs Actuals")
        df.columns = df.columns.str.strip()
        df["Line Item"] = df["Line Item"].str.strip()
        data["budget_vs_actuals"] = df

    return data


def get_value(df, line_item, column):
    """
    Looks up a specific number from a DataFrame.
    Returns 0 if not found — safer than crashing.
    """
    try:
        row = df[df["Line Item"].str.lower() == line_item.lower()]
        if row.empty:
            return 0
        return float(row[column].values[0])
    except:
        return 0


def extract_key_figures(df):
    """Pulls the most important income statement numbers."""
    year_cols = [c for c in df.columns if str(c).startswith("FY")]
    if not year_cols:
        return {}
    latest_year = year_cols[-1]
    prior_year  = year_cols[-2] if len(year_cols) > 1 else latest_year

    return {
        "latest_year":      latest_year,
        "prior_year":       prior_year,
        "revenue":          get_value(df, "Revenue", latest_year),
        "revenue_prior":    get_value(df, "Revenue", prior_year),
        "gross_profit":     get_value(df, "Gross Profit", latest_year),
        "ebitda":           get_value(df, "EBITDA", latest_year),
        "ebit":             get_value(df, "EBIT", latest_year),
        "interest_expense": get_value(df, "Interest Expense", latest_year),
        "net_income":       get_value(df, "Net Income", latest_year),
        "net_income_prior": get_value(df, "Net Income", prior_year),
        "da":               get_value(df, "Depreciation & Amortization", latest_year),
        "tax_expense":      get_value(df, "Tax Expense", latest_year),
        "cogs":             get_value(df, "Cost of Goods Sold", latest_year),
    }


def extract_balance_figures(df):
    """Pulls the most important balance sheet numbers."""
    year_cols = [c for c in df.columns if str(c).startswith("FY")]
    if not year_cols:
        return {}
    latest_year = year_cols[-1]
    prior_year  = year_cols[-2] if len(year_cols) > 1 else latest_year

    return {
        "latest_year":               latest_year,
        "cash":                      get_value(df, "Cash & Equivalents", latest_year),
        "accounts_receivable":       get_value(df, "Accounts Receivable", latest_year),
        "inventory":                 get_value(df, "Inventory", latest_year),
        "current_assets":            get_value(df, "Total Current Assets", latest_year),
        "total_assets":              get_value(df, "Total Assets", latest_year),
        "total_assets_prior":        get_value(df, "Total Assets", prior_year),
        "accounts_payable":          get_value(df, "Accounts Payable", latest_year),
        "current_liabilities":       get_value(df, "Total Current Liabilities", latest_year),
        "short_term_debt":           get_value(df, "Short-Term Debt", latest_year),
        "long_term_debt":            get_value(df, "Long-Term Debt", latest_year),
        "total_liabilities":         get_value(df, "Total Liabilities", latest_year),
        "shareholders_equity":       get_value(df, "Shareholders Equity", latest_year),
        "shareholders_equity_prior": get_value(df, "Shareholders Equity", prior_year),
    }