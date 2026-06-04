# budget_vs_actuals.py
# Budget vs Actuals variance analysis — the most common FP&A deliverable.
# Real analysts spend significant time on this every month-end close.
#
# This module takes the "Budget vs Actuals" sheet and produces:
#   - Line-by-line variance ($ and %)
#   - Favorable vs unfavorable flags
#   - Summary KPIs (how many lines beat budget, overall variance)
#   - A "management commentary" data package for the AI narrative

import pandas as pd

def analyze_budget_vs_actuals(df: pd.DataFrame) -> dict:
    """
    Master function for budget vs actuals analysis.
    Takes the 'Budget vs Actuals' DataFrame from the parser.
    Returns a complete variance analysis dictionary.
    """

    if df is None or df.empty:
        return {}

    result = {}

    # ── IDENTIFY COLUMNS ──────────────────────────────────────────
    # Find the columns for full-year budget, YTD actuals, and YTD budget
    budget_full_col  = next((c for c in df.columns if "Budget" in str(c) and "YTD" not in str(c)), None)
    actual_ytd_col   = next((c for c in df.columns if "Actual" in str(c)), None)
    budget_ytd_col   = next((c for c in df.columns if "Budget" in str(c) and "YTD" in str(c)), None)

    if not all([budget_full_col, actual_ytd_col, budget_ytd_col]):
        return {}

    result["budget_full_col"] = budget_full_col
    result["actual_ytd_col"]  = actual_ytd_col
    result["budget_ytd_col"]  = budget_ytd_col

    # ── BUILD VARIANCE TABLE ──────────────────────────────────────
    # Core output: line-by-line comparison of YTD actuals vs YTD budget
    bva = df[["Line Item", actual_ytd_col, budget_ytd_col, budget_full_col]].copy()

    # Variance in dollars
    bva["Variance ($)"] = bva[actual_ytd_col] - bva[budget_ytd_col]

    # Variance in percent
    bva["Variance (%)"] = (
        bva.apply(
            lambda row: round(
                (row["Variance ($)"] / abs(row[budget_ytd_col]) * 100), 1
            ) if row[budget_ytd_col] != 0 else 0,
            axis=1
        )
    )

    # % of full-year budget already achieved (YTD actuals / full-year budget)
    bva["% of Annual Budget"] = (
        bva.apply(
            lambda row: round(
                (row[actual_ytd_col] / row[budget_full_col] * 100), 1
            ) if row[budget_full_col] != 0 else 0,
            axis=1
        )
    )

    # ── FAVORABLE / UNFAVORABLE FLAGS ────────────────────────────
    # For revenue lines: higher actuals = favorable (F)
    # For cost lines:    lower actuals  = favorable (F)
    # We detect cost lines by checking if "Cost" or "Expense" is in the name
    def flag_variance(row):
        is_cost = any(word in row["Line Item"] for word in
                      ["Cost", "Expense", "Operating"])
        variance = row["Variance ($)"]
        if is_cost:
            # For costs, spending LESS than budget is favorable
            return "✅ Favorable" if variance <= 0 else "⚠️ Unfavorable"
        else:
            # For revenue/profit, being ABOVE budget is favorable
            return "✅ Favorable" if variance >= 0 else "⚠️ Unfavorable"

    bva["Status"] = bva.apply(flag_variance, axis=1)

    result["variance_table"] = bva

    # ── SUMMARY KPIs ──────────────────────────────────────────────
    # Pull out the key lines for the summary cards at the top of the dashboard

    def get_line(line_item):
        """Helper to get a specific row by Line Item name."""
        row = bva[bva["Line Item"].str.lower() == line_item.lower()]
        if row.empty:
            return None
        return row.iloc[0]

    revenue_row  = get_line("Revenue")
    ebitda_row   = get_line("EBITDA")
    ni_row       = get_line("Net Income")

    result["revenue_variance_usd"] = float(revenue_row["Variance ($)"]) if revenue_row is not None else 0
    result["revenue_variance_pct"] = float(revenue_row["Variance (%)"]) if revenue_row is not None else 0
    result["ebitda_variance_usd"]  = float(ebitda_row["Variance ($)"])  if ebitda_row  is not None else 0
    result["ebitda_variance_pct"]  = float(ebitda_row["Variance (%)"])  if ebitda_row  is not None else 0
    result["ni_variance_usd"]      = float(ni_row["Variance ($)"])      if ni_row      is not None else 0
    result["ni_variance_pct"]      = float(ni_row["Variance (%)"])      if ni_row      is not None else 0

    # Count favorable vs unfavorable lines
    favorable_count   = (bva["Status"] == "✅ Favorable").sum()
    unfavorable_count = (bva["Status"] == "⚠️ Unfavorable").sum()

    result["favorable_count"]   = int(favorable_count)
    result["unfavorable_count"] = int(unfavorable_count)
    result["total_lines"]       = len(bva)

    # ── FULL YEAR PACING ──────────────────────────────────────────
    # Are we on track to hit the full-year budget?
    # Simple approach: annualize YTD actuals and compare to full-year budget
    revenue_actual_ytd  = float(revenue_row[actual_ytd_col])  if revenue_row is not None else 0
    revenue_budget_full = float(revenue_row[budget_full_col]) if revenue_row is not None else 0
    revenue_ytd_budget  = float(revenue_row[budget_ytd_col])  if revenue_row is not None else 0

    # Implied full year = scale up YTD actuals proportionally
    ytd_completion = (revenue_ytd_budget / revenue_budget_full) if revenue_budget_full != 0 else 0
    implied_full_year = (revenue_actual_ytd / ytd_completion) if ytd_completion != 0 else 0
    full_year_gap = implied_full_year - revenue_budget_full

    result["ytd_completion_pct"]  = round(ytd_completion * 100, 1)
    result["implied_full_year"]   = round(implied_full_year, 0)
    result["full_year_gap"]       = round(full_year_gap, 0)
    result["on_track"]            = full_year_gap >= 0

    return result