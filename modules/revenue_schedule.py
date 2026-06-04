# revenue_schedule.py
# Analyzes the monthly revenue schedule — one of the core tools in FP&A.
# Takes the revenue schedule DataFrame from the parser and produces:
#   - Monthly actuals vs budget comparison
#   - Growth rates (month-over-month, year-over-year)
#   - Full-year forecast based on run rate
#   - Seasonality index (which months are strongest)

import pandas as pd

def analyze_revenue_schedule(df: pd.DataFrame) -> dict:
    """
    Master function for revenue schedule analysis.
    Takes the 'Revenue Schedule' sheet as a DataFrame.
    Returns a dictionary with all calculated metrics.
    """

    if df is None or df.empty:
        return {}

    result = {}

    # ── IDENTIFY COLUMNS ──────────────────────────────────────────
    # Find the actual and budget columns automatically
    # We look for columns containing "Actual" and "Budget"
    actual_col = next((c for c in df.columns if "Actual" in str(c)), None)
    budget_col = next((c for c in df.columns if "Budget" in str(c)), None)

    if not actual_col or not budget_col:
        return {}

    result["actual_col"] = actual_col
    result["budget_col"] = budget_col

    # ── TOTALS ────────────────────────────────────────────────────
    total_actual = df[actual_col].sum()
    total_budget = df[budget_col].sum()

    result["total_actual"]  = total_actual
    result["total_budget"]  = total_budget

    # ── VARIANCE ─────────────────────────────────────────────────
    # Variance = Actual - Budget (positive = beat budget)
    total_variance     = total_actual - total_budget
    total_variance_pct = (total_variance / total_budget * 100) if total_budget != 0 else 0

    result["total_variance"]     = total_variance
    result["total_variance_pct"] = round(total_variance_pct, 1)

    # ── MONTHLY VARIANCE TABLE ────────────────────────────────────
    # Build a clean month-by-month comparison table
    monthly = df[["Month", actual_col, budget_col]].copy()
    monthly["Variance ($)"]  = monthly[actual_col] - monthly[budget_col]
    monthly["Variance (%)"]  = (
        (monthly["Variance ($)"] / monthly[budget_col] * 100)
        .round(1)
        .fillna(0)
    )
    # Flag each month: did it beat or miss budget?
    monthly["Status"] = monthly["Variance ($)"].apply(
        lambda x: "✅ Beat" if x >= 0 else "⚠️ Miss"
    )

    result["monthly_table"] = monthly

    # ── GROWTH RATE (Actual vs Budget YoY) ───────────────────────
    # How much is next year's budget above this year's actuals?
    yoy_growth = (
        (total_budget - total_actual) / total_actual * 100
    ) if total_actual != 0 else 0

    result["yoy_growth_pct"] = round(yoy_growth, 1)

    # ── RUN RATE FORECAST ─────────────────────────────────────────
    # Run rate = annualize the average monthly actual
    # Useful for forecasting full-year if we only have partial data
    avg_monthly_actual  = total_actual / len(df)
    run_rate_annual     = avg_monthly_actual * 12

    result["avg_monthly_actual"] = avg_monthly_actual
    result["run_rate_annual"]    = run_rate_annual

    # ── SEASONALITY INDEX ─────────────────────────────────────────
    # Which months are above/below the annual average?
    # Index > 1.0 means that month is stronger than average
    # Example: December at 1.15 means 15% above average
    monthly["Seasonality"] = (
        monthly[actual_col] / avg_monthly_actual
    ).round(2)

    # Find the best and worst months
    best_month  = monthly.loc[monthly[actual_col].idxmax(), "Month"]
    worst_month = monthly.loc[monthly[actual_col].idxmin(), "Month"]

    result["best_month"]  = best_month
    result["worst_month"] = worst_month

    # ── MONTHS BEATING BUDGET ─────────────────────────────────────
    months_beating = (monthly["Variance ($)"] >= 0).sum()
    result["months_beating_budget"] = int(months_beating)
    result["total_months"]          = len(monthly)

    return result


def build_forecast(df: pd.DataFrame, growth_rate_pct: float) -> pd.DataFrame:
    """
    Builds a simple revenue forecast for next year based on a
    user-supplied growth rate applied to each month's actual.

    Example: growth_rate_pct = 10 means 10% growth on each month.
    Returns a DataFrame with Month, This Year Actual, and Forecast columns.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    actual_col = next((c for c in df.columns if "Actual" in str(c)), None)
    if not actual_col:
        return pd.DataFrame()

    forecast = df[["Month", actual_col]].copy()
    forecast.columns = ["Month", "This Year Actual"]

    # Apply the growth rate to each month
    growth_multiplier      = 1 + (growth_rate_pct / 100)
    forecast["Forecast"]   = (forecast["This Year Actual"] * growth_multiplier).round(0)
    forecast["Growth ($)"] = forecast["Forecast"] - forecast["This Year Actual"]

    return forecast