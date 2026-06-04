# ratios.py
# Calculates all standard FP&A ratios from the parsed financial data.
# Each function takes the dictionaries produced by parser.py and returns
# a dictionary of calculated ratios ready to display in the dashboard.

def calculate_all_ratios(financials: dict, balance: dict) -> dict:
    """
    Master function — calls all ratio groups and returns one
    combined dictionary with every ratio and its metadata.

    Each ratio entry contains:
      - value:       the calculated number
      - label:       human-readable name
      - format:      how to display it ("percent", "multiple", "days")
      - benchmark:   what a healthy number looks like
      - status:      "good", "warning", or "poor" based on benchmark
    """

    ratios = {}

    # Run all four ratio categories
    ratios.update(liquidity_ratios(financials, balance))
    ratios.update(profitability_ratios(financials, balance))
    ratios.update(leverage_ratios(financials, balance))
    ratios.update(efficiency_ratios(financials, balance))
    ratios.update(growth_ratios(financials))

    return ratios


# ── HELPER ────────────────────────────────────────────────────────
def safe_divide(numerator, denominator):
    """
    Divides two numbers safely.
    Returns 0 if the denominator is 0 (avoids crashing on division by zero).
    """
    if denominator == 0:
        return 0
    return numerator / denominator


def rate_status(value, good_above=None, good_below=None, warn_above=None, warn_below=None):
    """
    Returns "good", "warning", or "poor" based on thresholds.
    Used to color-code ratios in the dashboard (green/yellow/red).
    """
    if good_above is not None:
        if value >= good_above:
            return "good"
        elif warn_above is not None and value >= warn_above:
            return "warning"
        else:
            return "poor"
    if good_below is not None:
        if value <= good_below:
            return "good"
        elif warn_below is not None and value <= warn_below:
            return "warning"
        else:
            return "poor"
    return "warning"


# ── 1. LIQUIDITY RATIOS ───────────────────────────────────────────
def liquidity_ratios(f: dict, b: dict) -> dict:
    """
    Liquidity = can the company pay its short-term bills?
    Higher is generally better (but too high means idle cash).
    """

    # Current Ratio = Current Assets / Current Liabilities
    # Measures ability to cover short-term obligations
    # Healthy range: 1.5 – 3.0x
    current_ratio = safe_divide(b["current_assets"], b["current_liabilities"])

    # Quick Ratio = (Current Assets - Inventory) / Current Liabilities
    # Like current ratio but excludes inventory (harder to sell quickly)
    # Healthy range: 1.0 – 2.0x
    quick_ratio = safe_divide(
        b["current_assets"] - b["inventory"],
        b["current_liabilities"]
    )

    # Cash Ratio = Cash / Current Liabilities
    # Most conservative liquidity measure — cash only
    # Healthy range: 0.5+
    cash_ratio = safe_divide(b["cash"], b["current_liabilities"])

    return {
        "current_ratio": {
            "value": round(current_ratio, 2),
            "label": "Current Ratio",
            "format": "multiple",
            "benchmark": "Healthy: 1.5x – 3.0x",
            "status": rate_status(current_ratio, good_above=1.5, warn_above=1.0),
        },
        "quick_ratio": {
            "value": round(quick_ratio, 2),
            "label": "Quick Ratio",
            "format": "multiple",
            "benchmark": "Healthy: 1.0x – 2.0x",
            "status": rate_status(quick_ratio, good_above=1.0, warn_above=0.7),
        },
        "cash_ratio": {
            "value": round(cash_ratio, 2),
            "label": "Cash Ratio",
            "format": "multiple",
            "benchmark": "Healthy: 0.5x+",
            "status": rate_status(cash_ratio, good_above=0.5, warn_above=0.2),
        },
    }


# ── 2. PROFITABILITY RATIOS ───────────────────────────────────────
def profitability_ratios(f: dict, b: dict) -> dict:
    """
    Profitability = how efficiently does the company generate profit?
    Higher margins = better business economics.
    """

    # Gross Margin = Gross Profit / Revenue
    # What % of revenue is left after direct costs (COGS)
    gross_margin = safe_divide(f["gross_profit"], f["revenue"])

    # EBITDA Margin = EBITDA / Revenue
    # Operating profitability before non-cash/financing items
    # Most widely used margin in FP&A and deal work
    ebitda_margin = safe_divide(f["ebitda"], f["revenue"])

    # Net Profit Margin = Net Income / Revenue
    # Bottom-line profitability after everything
    net_margin = safe_divide(f["net_income"], f["revenue"])

    # Return on Equity (ROE) = Net Income / Shareholders Equity
    # How much profit generated per $1 of shareholder investment
    # Healthy range: 15%+
    roe = safe_divide(f["net_income"], b["shareholders_equity"])

    # Return on Assets (ROA) = Net Income / Total Assets
    # How efficiently assets are used to generate profit
    # Healthy range: 5%+
    roa = safe_divide(f["net_income"], b["total_assets"])

    return {
        "gross_margin": {
            "value": round(gross_margin * 100, 1),
            "label": "Gross Margin",
            "format": "percent",
            "benchmark": "Healthy: 30%+ (varies by industry)",
            "status": rate_status(gross_margin * 100, good_above=35, warn_above=20),
        },
        "ebitda_margin": {
            "value": round(ebitda_margin * 100, 1),
            "label": "EBITDA Margin",
            "format": "percent",
            "benchmark": "Healthy: 15%+ (varies by industry)",
            "status": rate_status(ebitda_margin * 100, good_above=15, warn_above=8),
        },
        "net_margin": {
            "value": round(net_margin * 100, 1),
            "label": "Net Profit Margin",
            "format": "percent",
            "benchmark": "Healthy: 10%+",
            "status": rate_status(net_margin * 100, good_above=10, warn_above=5),
        },
        "roe": {
            "value": round(roe * 100, 1),
            "label": "Return on Equity (ROE)",
            "format": "percent",
            "benchmark": "Healthy: 15%+",
            "status": rate_status(roe * 100, good_above=15, warn_above=8),
        },
        "roa": {
            "value": round(roa * 100, 1),
            "label": "Return on Assets (ROA)",
            "format": "percent",
            "benchmark": "Healthy: 5%+",
            "status": rate_status(roa * 100, good_above=5, warn_above=2),
        },
    }


# ── 3. LEVERAGE RATIOS ────────────────────────────────────────────
def leverage_ratios(f: dict, b: dict) -> dict:
    """
    Leverage = how much debt is the company carrying?
    Too much debt = financial risk. Key focus in credit/banking analysis.
    """

    # Debt-to-Equity = Total Debt / Shareholders Equity
    # How much of the company is financed by debt vs. equity
    # Healthy range: below 2.0x for most industries
    total_debt = b["short_term_debt"] + b["long_term_debt"]
    debt_to_equity = safe_divide(total_debt, b["shareholders_equity"])

    # Net Debt / EBITDA = (Total Debt - Cash) / EBITDA
    # Most important leverage metric in banking and PE
    # How many years of EBITDA needed to pay off net debt
    # Healthy range: below 3.0x
    net_debt = total_debt - b["cash"]
    net_debt_ebitda = safe_divide(net_debt, f["ebitda"])

    # Interest Coverage = EBIT / Interest Expense
    # Can the company comfortably pay its interest?
    # Healthy range: 3.0x+ (above 1.0x means it can cover interest at all)
    interest_coverage = safe_divide(f["ebit"], f["interest_expense"])

    # Debt-to-Assets = Total Liabilities / Total Assets
    # What % of assets are financed by debt
    # Healthy range: below 50%
    debt_to_assets = safe_divide(b["total_liabilities"], b["total_assets"])

    return {
        "debt_to_equity": {
            "value": round(debt_to_equity, 2),
            "label": "Debt-to-Equity",
            "format": "multiple",
            "benchmark": "Healthy: below 2.0x",
            "status": rate_status(debt_to_equity, good_below=1.0, warn_below=2.0),
        },
        "net_debt_ebitda": {
            "value": round(net_debt_ebitda, 2),
            "label": "Net Debt / EBITDA",
            "format": "multiple",
            "benchmark": "Healthy: below 3.0x",
            "status": rate_status(net_debt_ebitda, good_below=2.0, warn_below=3.5),
        },
        "interest_coverage": {
            "value": round(interest_coverage, 2),
            "label": "Interest Coverage",
            "format": "multiple",
            "benchmark": "Healthy: 3.0x+",
            "status": rate_status(interest_coverage, good_above=3.0, warn_above=1.5),
        },
        "debt_to_assets": {
            "value": round(debt_to_assets * 100, 1),
            "label": "Debt-to-Assets",
            "format": "percent",
            "benchmark": "Healthy: below 50%",
            "status": rate_status(debt_to_assets * 100, good_below=40, warn_below=60),
        },
    }


# ── 4. EFFICIENCY RATIOS ──────────────────────────────────────────
def efficiency_ratios(f: dict, b: dict) -> dict:
    """
    Efficiency = how well does the company use its assets?
    Important for working capital management — core FP&A territory.
    """

    # Asset Turnover = Revenue / Total Assets
    # How much revenue generated per $1 of assets
    # Higher = more efficient use of assets
    asset_turnover = safe_divide(f["revenue"], b["total_assets"])

    # Days Sales Outstanding (DSO) = (Accounts Receivable / Revenue) x 365
    # How many days on average to collect payment from customers
    # Lower = faster collections = better cash flow
    # Healthy range: below 45 days
    dso = safe_divide(b["accounts_receivable"], f["revenue"]) * 365

    # Days Payable Outstanding (DPO) = (Accounts Payable / COGS) x 365
    # How many days the company takes to pay its suppliers
    # Higher = company keeps cash longer = better for cash flow
    dpo = safe_divide(b["accounts_payable"], f["cogs"]) * 365

    # Inventory Days = (Inventory / COGS) x 365
    # How many days inventory sits before being sold
    # Lower = faster moving inventory = more efficient
    inventory_days = safe_divide(b["inventory"], f["cogs"]) * 365

    return {
        "asset_turnover": {
            "value": round(asset_turnover, 2),
            "label": "Asset Turnover",
            "format": "multiple",
            "benchmark": "Healthy: 0.5x+ (varies by industry)",
            "status": rate_status(asset_turnover, good_above=0.8, warn_above=0.4),
        },
        "dso": {
            "value": round(dso, 1),
            "label": "Days Sales Outstanding (DSO)",
            "format": "days",
            "benchmark": "Healthy: below 45 days",
            "status": rate_status(dso, good_below=45, warn_below=60),
        },
        "dpo": {
            "value": round(dpo, 1),
            "label": "Days Payable Outstanding (DPO)",
            "format": "days",
            "benchmark": "Healthy: 30 – 60 days",
            "status": rate_status(dpo, good_above=30, warn_above=15),
        },
        "inventory_days": {
            "value": round(inventory_days, 1),
            "label": "Inventory Days",
            "format": "days",
            "benchmark": "Healthy: below 60 days",
            "status": rate_status(inventory_days, good_below=45, warn_below=75),
        },
    }


# ── 0. MULTI-YEAR TREND CALCULATOR ───────────────────────────
def calculate_ratio_trends(income_df, balance_df) -> dict:
    """
    Calculates key ratios for every FY year column found in the data.
    Returns a dict like:
      { "Gross Margin (%)": {"FY2022": 40.0, "FY2023": 42.1, "FY2024": 43.8}, ... }
    Used to draw trend charts in the Ratios tab.
    """
    from modules.parser import get_value

    # Find all year columns that exist in both sheets
    is_years  = [c for c in income_df.columns  if str(c).startswith("FY")]
    bs_years  = [c for c in balance_df.columns if str(c).startswith("FY")]
    years = [y for y in is_years if y in bs_years]  # only years present in both

    trends = {
        "Gross Margin (%)":     {},
        "EBITDA Margin (%)":    {},
        "Net Margin (%)":       {},
        "ROE (%)":              {},
        "ROA (%)":              {},
        "Current Ratio (x)":    {},
        "Debt/Equity (x)":      {},
        "Interest Coverage (x)": {},
        "Revenue Growth (%)":   {},
    }

    prev_revenue = None

    for year in years:
        # Income statement figures
        revenue    = get_value(income_df, "Revenue",                    year)
        gross_p    = get_value(income_df, "Gross Profit",               year)
        ebitda     = get_value(income_df, "EBITDA",                     year)
        ebit       = get_value(income_df, "EBIT",                       year)
        net_income = get_value(income_df, "Net Income",                 year)
        interest   = get_value(income_df, "Interest Expense",           year)

        # Balance sheet figures
        curr_assets = get_value(balance_df, "Total Current Assets",     year)
        curr_liab   = get_value(balance_df, "Total Current Liabilities",year)
        total_assets= get_value(balance_df, "Total Assets",             year)
        equity      = get_value(balance_df, "Shareholders Equity",      year)
        st_debt     = get_value(balance_df, "Short-Term Debt",          year)
        lt_debt     = get_value(balance_df, "Long-Term Debt",           year)
        total_debt  = st_debt + lt_debt

        trends["Gross Margin (%)"][year]      = round(safe_divide(gross_p,    revenue)    * 100, 1)
        trends["EBITDA Margin (%)"][year]     = round(safe_divide(ebitda,     revenue)    * 100, 1)
        trends["Net Margin (%)"][year]        = round(safe_divide(net_income, revenue)    * 100, 1)
        trends["ROE (%)"][year]               = round(safe_divide(net_income, equity)     * 100, 1)
        trends["ROA (%)"][year]               = round(safe_divide(net_income, total_assets) * 100, 1)
        trends["Current Ratio (x)"][year]     = round(safe_divide(curr_assets, curr_liab), 2)
        trends["Debt/Equity (x)"][year]       = round(safe_divide(total_debt, equity),    2)
        trends["Interest Coverage (x)"][year] = round(safe_divide(ebit, interest),        2)

        if prev_revenue and prev_revenue > 0:
            trends["Revenue Growth (%)"][year] = round((revenue - prev_revenue) / prev_revenue * 100, 1)
        else:
            trends["Revenue Growth (%)"][year] = None  # no prior year to compare

        prev_revenue = revenue

    return trends


# ── 5. GROWTH RATIOS ──────────────────────────────────────────────
def growth_ratios(f: dict) -> dict:
    """
    Growth = is the business expanding?
    Year-over-year comparisons — key for forecasting and budgeting.
    """

    # Revenue Growth = (Revenue_Current - Revenue_Prior) / Revenue_Prior
    revenue_growth = safe_divide(
        f["revenue"] - f["revenue_prior"],
        f["revenue_prior"]
    )

    # Net Income Growth = (NetIncome_Current - NetIncome_Prior) / NetIncome_Prior
    ni_growth = safe_divide(
        f["net_income"] - f["net_income_prior"],
        f["net_income_prior"]
    )

    return {
        "revenue_growth": {
            "value": round(revenue_growth * 100, 1),
            "label": "Revenue Growth (YoY)",
            "format": "percent",
            "benchmark": "Healthy: 5%+",
            "status": rate_status(revenue_growth * 100, good_above=10, warn_above=3),
        },
        "ni_growth": {
            "value": round(ni_growth * 100, 1),
            "label": "Net Income Growth (YoY)",
            "format": "percent",
            "benchmark": "Healthy: 5%+",
            "status": rate_status(ni_growth * 100, good_above=10, warn_above=3),
        },
    }