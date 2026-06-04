# app.py
# The main Streamlit dashboard — this is what the user sees and interacts with.
# It ties together all the modules: parser, ratios, revenue schedule,
# budget vs actuals, and AI narrative.

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from modules.parser import parse_excel
from modules.flexible_parser import parse_flexible_excel
from modules.ratios import calculate_all_ratios, calculate_ratio_trends
from modules.revenue_schedule import analyze_revenue_schedule, build_forecast
from modules.budget_vs_actuals import analyze_budget_vs_actuals
from modules.ai_narrative import generate_narrative
from modules.pdf_export import generate_pdf

# ── PAGE CONFIG ───────────────────────────────────────────────────
# This must be the FIRST Streamlit command in the file
st.set_page_config(
    page_title="FP&A Assistant",
    page_icon="📊",
    layout="wide",           # use full browser width
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ────────────────────────────────────────────────────
# A little styling to make the dashboard look professional
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #0066cc;
    }
    .good  { color: #28a745; font-weight: bold; }
    .warning { color: #ffc107; font-weight: bold; }
    .poor  { color: #dc3545; font-weight: bold; }
    .narrative-box {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 20px;
        border-left: 4px solid #0066cc;
        font-size: 15px;
        line-height: 1.7;
    }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 FP&A Assistant")
    st.markdown("---")

    # Company name input
    company_name = st.text_input(
        "Company Name",
        value="Acme Corp",
        help="Enter the company name for the AI narrative"
    )

    # File uploader
    st.markdown("### Upload Financial Data")
    uploaded_file = st.file_uploader(
        "Upload Excel file (.xlsx)",
        type=["xlsx"],
        help="Upload a file with sheets: Income Statement, Balance Sheet, Cash Flow, Revenue Schedule, Budget vs Actuals"
    )

    # Option to use sample data
    use_sample = st.checkbox("Use sample data", value=True)

    st.markdown("---")
    st.markdown("### Compare a Second Company")
    uploaded_file2 = st.file_uploader(
        "Upload second company (.xlsx)",
        type=["xlsx"],
        help="Upload a second Excel file — use our template OR a file downloaded from Macrotrends / Stock Analysis",
        key="file2"
    )
    company_name2 = st.text_input(
        "Second Company Name",
        value="Rival Corp",
        help="Name for the second company"
    )
    file2_format = st.radio(
        "Second file format",
        ["Our template", "Downloaded (Macrotrends / Stock Analysis)"],
        help="Choose 'Downloaded' if you exported this file from a financial data site"
    )
    file2_units = st.selectbox(
        "Numbers reported in",
        ["Millions ($M)", "Thousands ($K)", "Full dollars"],
        help="Check the file header — most 10-K downloads report in millions"
    ) if file2_format == "Downloaded (Macrotrends / Stock Analysis)" else None

    st.markdown("---")
    st.markdown("**Sessions completed:** 10 of 10 ✅")
    st.markdown("Built with Python + Claude API")

# ── LOAD DATA ─────────────────────────────────────────────────────
# Decide whether to use uploaded file or sample data
data = None

if uploaded_file is not None:
    try:
        data = parse_excel(uploaded_file)
        st.sidebar.success("✅ File uploaded successfully!")
    except Exception as e:
        st.sidebar.error(f"❌ Error reading file: {e}")

elif use_sample:
    try:
        data = parse_excel("sample_data/sample_financials.xlsx")
    except Exception as e:
        st.error(f"Could not load sample data: {e}")

# ── LOAD SECOND FILE (COMPARISON) ────────────────────────────────
data2 = None
if uploaded_file2 is not None:
    try:
        if file2_format == "Downloaded (Macrotrends / Stock Analysis)":
            unit_map = {"Millions ($M)": 1_000_000, "Thousands ($K)": 1_000, "Full dollars": 1}
            multiplier = unit_map.get(file2_units, 1_000_000)
            data2 = parse_flexible_excel(uploaded_file2, unit_multiplier=multiplier)
        else:
            data2 = parse_excel(uploaded_file2)

        if not data2.get("financials") and not data2.get("balance"):
            st.sidebar.error("❌ Could not extract financial data. Check the file format.")
            data2 = None
        else:
            st.sidebar.success("✅ Second file loaded!")
    except Exception as e:
        st.sidebar.error(f"❌ Error reading second file: {e}")

# ── MAIN CONTENT ──────────────────────────────────────────────────
if data is None:
    # Show a welcome screen if no data is loaded
    st.title("📊 FP&A Assistant")
    st.markdown("### Welcome! Upload a financial Excel file or check 'Use sample data' to get started.")
    st.stop()

# Calculate all metrics once data is loaded
financials = data.get("financials", {})
balance    = data.get("balance", {})
ratios     = calculate_all_ratios(financials, balance)
ratio_trends = calculate_ratio_trends(
    data.get("income_statement", {}),
    data.get("balance_sheet", {})
) if "income_statement" in data and "balance_sheet" in data else {}
rs_data    = analyze_revenue_schedule(data.get("revenue_schedule"))
bva_data   = analyze_budget_vs_actuals(data.get("budget_vs_actuals"))

latest_year = financials.get("latest_year", "FY2024")

# ── HEADER ────────────────────────────────────────────────────────
st.title(f"📊 {company_name} — FP&A Dashboard")
st.caption(f"Financial analysis for {latest_year} | Powered by Claude AI")
st.markdown("---")

# ── TAB LAYOUT ────────────────────────────────────────────────────
# Organize content into tabs so the dashboard isn't overwhelming
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Overview",
    "⚖️ Ratios",
    "💰 Revenue Schedule",
    "🎯 Budget vs Actuals",
    "🤖 AI Narrative",
    "🔄 Compare"
])

# ════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ════════════════════════════════════════════════════════════════
with tab1:
    st.subheader(f"Financial Overview — {latest_year}")

    # Top KPI metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rev = financials.get("revenue", 0)
        rev_prior = financials.get("revenue_prior", 0)
        rev_growth = ((rev - rev_prior) / rev_prior * 100) if rev_prior else 0
        st.metric(
            label="Revenue",
            value=f"${rev/1e6:.1f}M",
            delta=f"{rev_growth:+.1f}% YoY"
        )

    with col2:
        ebitda = financials.get("ebitda", 0)
        ebitda_margin = (ebitda / rev * 100) if rev else 0
        st.metric(
            label="EBITDA",
            value=f"${ebitda/1e6:.1f}M",
            delta=f"{ebitda_margin:.1f}% margin"
        )

    with col3:
        ni = financials.get("net_income", 0)
        ni_prior = financials.get("net_income_prior", 0)
        ni_growth = ((ni - ni_prior) / ni_prior * 100) if ni_prior else 0
        st.metric(
            label="Net Income",
            value=f"${ni/1e6:.2f}M",
            delta=f"{ni_growth:+.1f}% YoY"
        )

    with col4:
        cash = balance.get("cash", 0)
        st.metric(
            label="Cash",
            value=f"${cash/1e6:.1f}M",
            delta="Net cash position" if balance.get("long_term_debt", 0) < cash else "Net debt"
        )

    st.markdown("---")

    # Income Statement table
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Income Statement Summary")
        if "income_statement" in data:
            df = data["income_statement"]
            year_cols = [c for c in df.columns if str(c).startswith("FY")]
            display_df = df[["Line Item"] + year_cols].copy()
            # Format numbers as $M
            for col in year_cols:
                display_df[col] = display_df[col].apply(
                    lambda x: f"${x/1e6:.2f}M" if pd.notna(x) else "-"
                )
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    with col_right:
        st.markdown("#### Balance Sheet Summary")
        if "balance_sheet" in data:
            df = data["balance_sheet"]
            year_cols = [c for c in df.columns if str(c).startswith("FY")]
            display_df = df[["Line Item"] + year_cols].copy()
            for col in year_cols:
                display_df[col] = display_df[col].apply(
                    lambda x: f"${x/1e6:.2f}M" if pd.notna(x) else "-"
                )
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Revenue trend chart
    st.markdown("#### Revenue & Net Income Trend")
    if "income_statement" in data:
        df = data["income_statement"]
        year_cols = [c for c in df.columns if str(c).startswith("FY")]
        rev_row = df[df["Line Item"] == "Revenue"]
        ni_row  = df[df["Line Item"] == "Net Income"]

        if not rev_row.empty and not ni_row.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=year_cols,
                y=[rev_row[y].values[0]/1e6 for y in year_cols],
                name="Revenue ($M)",
                marker_color="#0066cc"
            ))
            fig.add_trace(go.Scatter(
                x=year_cols,
                y=[ni_row[y].values[0]/1e6 for y in year_cols],
                name="Net Income ($M)",
                mode="lines+markers",
                line=dict(color="#28a745", width=3),
                yaxis="y2"
            ))
            fig.update_layout(
                yaxis=dict(title="Revenue ($M)"),
                yaxis2=dict(title="Net Income ($M)", overlaying="y", side="right"),
                legend=dict(x=0, y=1),
                height=350,
                margin=dict(l=0, r=0, t=20, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 2 — RATIOS
# ════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Financial Ratios")

    # Color-code based on status
    def status_badge(status):
        colors = {"good": "🟢", "warning": "🟡", "poor": "🔴"}
        return colors.get(status, "⚪")

    # Display ratios in 4 category columns
    categories = {
        "💧 Liquidity": ["current_ratio", "quick_ratio", "cash_ratio"],
        "📈 Profitability": ["gross_margin", "ebitda_margin", "net_margin", "roe", "roa"],
        "🏦 Leverage": ["debt_to_equity", "net_debt_ebitda", "interest_coverage", "debt_to_assets"],
        "⚙️ Efficiency & Growth": ["asset_turnover", "dso", "dpo", "inventory_days", "revenue_growth", "ni_growth"]
    }

    for category, keys in categories.items():
        st.markdown(f"#### {category}")
        cols = st.columns(len(keys))
        for i, key in enumerate(keys):
            r = ratios.get(key)
            if r:
                val = r["value"]
                fmt = r["format"]
                if fmt == "percent":
                    display = f"{val}%"
                elif fmt == "days":
                    display = f"{val}d"
                else:
                    display = f"{val}x"
                cols[i].metric(
                    label=f"{status_badge(r['status'])} {r['label']}",
                    value=display,
                    help=r["benchmark"]
                )
        st.markdown("---")

    # ── RATIO TREND CHARTS ────────────────────────────────────────
    if ratio_trends:
        st.markdown("#### 📉 Multi-Year Ratio Trends")
        st.caption("Showing how key ratios have moved across all available fiscal years.")

        # Group the trends into two rows of 3 charts each
        chart_groups = [
            ["Gross Margin (%)", "EBITDA Margin (%)", "Net Margin (%)"],
            ["ROE (%)",          "Current Ratio (x)", "Interest Coverage (x)"],
        ]

        for group in chart_groups:
            cols = st.columns(len(group))
            for i, metric_name in enumerate(group):
                trend_data = ratio_trends.get(metric_name, {})
                # Filter out None values (e.g. first year has no Revenue Growth)
                years_list  = [y for y, v in trend_data.items() if v is not None]
                values_list = [v for v in trend_data.values() if v is not None]

                if len(years_list) < 2:
                    cols[i].metric(metric_name, "Not enough data")
                    continue

                # Determine line color: green if improving, red if declining
                # "improving" depends on the metric
                higher_is_better = "Coverage" in metric_name or "Margin" in metric_name or "ROE" in metric_name or "ROA" in metric_name
                improving = values_list[-1] >= values_list[0]
                line_color = "#28a745" if (improving == higher_is_better) else "#dc3545"

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=years_list,
                    y=values_list,
                    mode="lines+markers+text",
                    text=[str(v) for v in values_list],
                    textposition="top center",
                    line=dict(color=line_color, width=3),
                    marker=dict(size=8),
                    showlegend=False
                ))
                fig.update_layout(
                    title=dict(text=metric_name, font=dict(size=13)),
                    height=220,
                    margin=dict(l=10, r=10, t=40, b=20),
                    yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
                    xaxis=dict(showgrid=False),
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                )
                cols[i].plotly_chart(fig, use_container_width=True)

        st.markdown("---")

# ════════════════════════════════════════════════════════════════
# TAB 3 — REVENUE SCHEDULE
# ════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Revenue Schedule Analysis")

    if rs_data:
        # Summary KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Actual", f"${rs_data['total_actual']/1e6:.2f}M")
        col2.metric("Total Budget", f"${rs_data['total_budget']/1e6:.2f}M")
        col3.metric("YoY Growth (Budgeted)", f"{rs_data['yoy_growth_pct']}%")
        col4.metric("Best Month", rs_data["best_month"])

        st.markdown("---")

        # Monthly chart
        st.markdown("#### Monthly Revenue: Actual vs Budget")
        monthly = rs_data["monthly_table"]
        actual_col = rs_data["actual_col"]
        budget_col = rs_data["budget_col"]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly["Month"],
            y=monthly[actual_col] / 1000,
            name="Actual ($K)",
            marker_color="#0066cc"
        ))
        fig.add_trace(go.Scatter(
            x=monthly["Month"],
            y=monthly[budget_col] / 1000,
            name="Budget ($K)",
            mode="lines+markers",
            line=dict(color="#dc3545", width=2, dash="dash")
        ))
        fig.update_layout(
            yaxis_title="Revenue ($K)",
            height=350,
            margin=dict(l=0, r=0, t=20, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Monthly variance table
        st.markdown("#### Monthly Variance Detail")
        display_cols = ["Month", actual_col, budget_col, "Variance ($)", "Variance (%)", "Status"]
        display_df = monthly[display_cols].copy()
        display_df[actual_col] = display_df[actual_col].apply(lambda x: f"${x:,.0f}")
        display_df[budget_col] = display_df[budget_col].apply(lambda x: f"${x:,.0f}")
        display_df["Variance ($)"] = display_df["Variance ($)"].apply(lambda x: f"${x:+,.0f}")
        display_df["Variance (%)"] = display_df["Variance (%)"].apply(lambda x: f"{x:+.1f}%")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Forecast builder
        st.markdown("---")
        st.markdown("#### 📐 Revenue Forecast Builder")
        growth_rate = st.slider(
            "Apply growth rate to build next year forecast (%)",
            min_value=-20, max_value=50, value=10, step=1
        )
        forecast_df = build_forecast(data.get("revenue_schedule"), growth_rate)
        if not forecast_df.empty:
            forecast_df["This Year Actual"] = forecast_df["This Year Actual"].apply(lambda x: f"${x:,.0f}")
            forecast_df["Forecast"] = forecast_df["Forecast"].apply(lambda x: f"${x:,.0f}")
            forecast_df["Growth ($)"] = forecast_df["Growth ($)"].apply(lambda x: f"${x:+,.0f}")
            st.dataframe(forecast_df, use_container_width=True, hide_index=True)
    else:
        st.info("No revenue schedule data found in the uploaded file.")

# ════════════════════════════════════════════════════════════════
# TAB 4 — BUDGET VS ACTUALS
# ════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Budget vs Actuals — YTD Variance Analysis")

    if bva_data:
        # Summary KPIs
        col1, col2, col3, col4 = st.columns(4)

        rev_var = bva_data["revenue_variance_usd"]
        ebitda_var = bva_data["ebitda_variance_usd"]

        col1.metric(
            "Revenue vs Budget",
            f"${rev_var/1e3:+.0f}K",
            delta=f"{bva_data['revenue_variance_pct']:+.1f}%",
            delta_color="normal"
        )
        col2.metric(
            "EBITDA vs Budget",
            f"${ebitda_var/1e3:+.0f}K",
            delta=f"{bva_data['ebitda_variance_pct']:+.1f}%",
            delta_color="normal"
        )
        col3.metric(
            "Favorable Lines",
            f"{bva_data['favorable_count']} / {bva_data['total_lines']}"
        )
        col4.metric(
            "Full Year On Track",
            "✅ Yes" if bva_data["on_track"] else "⚠️ At Risk"
        )

        st.markdown("---")

        # Variance chart
        st.markdown("#### YTD Variance by Line Item ($K)")
        vt = bva_data["variance_table"]
        fig = go.Figure(go.Bar(
            x=vt["Line Item"],
            y=vt["Variance ($)"] / 1000,
            marker_color=["#28a745" if v >= 0 else "#dc3545"
                         for v in vt["Variance ($)"]],
            text=[f"${v/1000:+.0f}K" for v in vt["Variance ($)"]],
            textposition="outside"
        ))
        fig.update_layout(
            yaxis_title="Variance ($K)",
            height=350,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Full variance table
        st.markdown("#### Detailed Variance Table")
        actual_col = bva_data["actual_ytd_col"]
        budget_col = bva_data["budget_ytd_col"]
        full_col   = bva_data["budget_full_col"]

        display_df = vt[["Line Item", actual_col, budget_col, full_col,
                          "Variance ($)", "Variance (%)", "% of Annual Budget", "Status"]].copy()

        for col in [actual_col, budget_col, full_col]:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")
        display_df["Variance ($)"] = display_df["Variance ($)"].apply(lambda x: f"${x:+,.0f}")
        display_df["Variance (%)"] = display_df["Variance (%)"].apply(lambda x: f"{x:+.1f}%")
        display_df["% of Annual Budget"] = display_df["% of Annual Budget"].apply(lambda x: f"{x:.1f}%")

        st.dataframe(display_df, use_container_width=True, hide_index=True)

    else:
        st.info("No budget vs actuals data found in the uploaded file.")

# ════════════════════════════════════════════════════════════════
# TAB 5 — AI NARRATIVE
# ════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("🤖 AI-Generated Analyst Narrative")
    st.markdown("Claude will write a professional FP&A memo based on all the financial data above.")

    if st.button("✍️ Generate Analyst Narrative", type="primary"):
        with st.spinner("Claude is analyzing the financials and writing the narrative... (10-15 seconds)"):
            narrative = generate_narrative(
                financials=financials,
                balance=balance,
                ratios=ratios,
                revenue_schedule_analysis=rs_data,
                budget_vs_actuals_analysis=bva_data,
                company_name=company_name
            )

        if narrative.startswith("❌"):
            st.error(narrative)
        else:
            st.markdown(f"""
<div class="narrative-box">
{narrative.replace(chr(10), '<br>')}
</div>
""", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### 📥 Export Report")

            # Two download buttons side by side
            dl_col1, dl_col2 = st.columns(2)

            # Button 1 — plain text narrative
            dl_col1.download_button(
                label="📄 Download Narrative (.txt)",
                data=narrative,
                file_name=f"{company_name}_FPnA_Narrative.txt",
                mime="text/plain",
                use_container_width=True
            )

            # Button 2 — full PDF report
            with dl_col2:
                with st.spinner("Building PDF..."):
                    pdf_bytes = generate_pdf(
                        company_name=company_name,
                        financials=financials,
                        balance=balance,
                        ratios=ratios,
                        narrative=narrative,
                        bva_data=bva_data,
                    )
                st.download_button(
                    label="📊 Download Full Report (.pdf)",
                    data=pdf_bytes,
                    file_name=f"{company_name}_FPnA_Report.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
    else:
        col_info, col_pdf = st.columns([2, 1])
        col_info.info("👆 Click the button above to generate the AI narrative. This uses the Claude API (~$0.01 per generation).")

        # Allow PDF export even without narrative
        with col_pdf:
            if st.button("📊 Export PDF (no narrative)", use_container_width=True):
                with st.spinner("Building PDF..."):
                    pdf_bytes = generate_pdf(
                        company_name=company_name,
                        financials=financials,
                        balance=balance,
                        ratios=ratios,
                    )
                st.download_button(
                    label="📥 Download Report (.pdf)",
                    data=pdf_bytes,
                    file_name=f"{company_name}_FPnA_Report.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )

# ════════════════════════════════════════════════════════════════
# TAB 6 — COMPARE TWO COMPANIES
# ════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("🔄 Side-by-Side Company Comparison")

    if data2 is None:
        st.info("👈 Upload a second Excel file in the sidebar to compare two companies side by side.")
        st.markdown("""
**How to use:**
1. The current file is **Company A** (shown in the sidebar as the first upload)
2. Upload a second Excel file using the **"Compare a Second Company"** uploader in the sidebar
3. This tab will show a ratio-by-ratio comparison with color coding

**Tip:** You can use two different versions of the sample data with different numbers to test this feature.
""")
    else:
        # Calculate ratios for company 2
        financials2 = data2.get("financials", {})
        balance2    = data2.get("balance", {})
        ratios2     = calculate_all_ratios(financials2, balance2)

        st.markdown(f"Comparing **{company_name}** vs **{company_name2}** — {latest_year}")
        st.markdown("---")

        # Build the comparison table rows
        # Each row: metric label, co1 value, co2 value, format, who wins
        comparison_metrics = [
            # (ratio_key, higher_is_better)
            ("gross_margin",       True),
            ("ebitda_margin",      True),
            ("net_margin",         True),
            ("roe",                True),
            ("roa",                True),
            ("current_ratio",      True),
            ("quick_ratio",        True),
            ("debt_to_equity",     False),
            ("net_debt_ebitda",    False),
            ("interest_coverage",  True),
            ("debt_to_assets",     False),
            ("asset_turnover",     True),
            ("dso",                False),
            ("dpo",                True),
            ("inventory_days",     False),
            ("revenue_growth",     True),
            ("ni_growth",          True),
        ]

        def fmt_value(r):
            """Format a ratio value for display."""
            if not r:
                return "N/A"
            val = r.get("value", 0)
            fmt = r.get("format", "multiple")
            if fmt == "percent":
                return f"{val}%"
            elif fmt == "days":
                return f"{val}d"
            else:
                return f"{val}x"

        # Summary score: how many ratios does each company win?
        co1_wins = 0
        co2_wins = 0

        rows = []
        for key, higher_is_better in comparison_metrics:
            r1 = ratios.get(key)
            r2 = ratios2.get(key)
            if not r1 or not r2:
                continue

            v1 = r1["value"]
            v2 = r2["value"]
            label = r1["label"]

            if higher_is_better:
                winner = 1 if v1 > v2 else (2 if v2 > v1 else 0)
            else:
                winner = 1 if v1 < v2 else (2 if v2 < v1 else 0)

            if winner == 1:
                co1_wins += 1
            elif winner == 2:
                co2_wins += 1

            rows.append({
                "Metric":        label,
                company_name:    fmt_value(r1),
                company_name2:   fmt_value(r2),
                "_winner":       winner,
                "_v1":           v1,
                "_v2":           v2,
            })

        # ── SCORECARD ──────────────────────────────────────────
        col1, col2, col3 = st.columns(3)
        col1.metric(f"🏆 {company_name} Wins", f"{co1_wins} ratios")
        col2.metric(f"🏆 {company_name2} Wins", f"{co2_wins} ratios")
        overall_winner = company_name if co1_wins > co2_wins else (company_name2 if co2_wins > co1_wins else "Tied")
        col3.metric("Overall Winner", overall_winner)

        st.markdown("---")

        # ── COMPARISON TABLE ───────────────────────────────────
        st.markdown("#### Detailed Ratio Comparison")
        st.caption("🟢 = better value for that metric")

        # Render each row with colored winner indicator
        header_cols = st.columns([3, 2, 2, 1])
        header_cols[0].markdown("**Metric**")
        header_cols[1].markdown(f"**{company_name}**")
        header_cols[2].markdown(f"**{company_name2}**")
        header_cols[3].markdown("**Edge**")

        for row in rows:
            w = row["_winner"]
            c1_indicator = "🟢" if w == 1 else ("🔴" if w == 2 else "⚪")
            c2_indicator = "🟢" if w == 2 else ("🔴" if w == 1 else "⚪")

            cols = st.columns([3, 2, 2, 1])
            cols[0].write(row["Metric"])
            cols[1].write(f"{c1_indicator} {row[company_name]}")
            cols[2].write(f"{c2_indicator} {row[company_name2]}")
            cols[3].write("—" if w == 0 else (f"→ {company_name}" if w == 1 else f"→ {company_name2}"))

        st.markdown("---")

        # ── BAR CHART — KEY MARGIN COMPARISON ─────────────────
        st.markdown("#### Margin Comparison")
        margin_keys = ["gross_margin", "ebitda_margin", "net_margin"]
        margin_labels = ["Gross Margin", "EBITDA Margin", "Net Margin"]

        v1s = [ratios.get(k, {}).get("value", 0) for k in margin_keys]
        v2s = [ratios2.get(k, {}).get("value", 0) for k in margin_keys]

        fig = go.Figure()
        fig.add_trace(go.Bar(name=company_name,  x=margin_labels, y=v1s, marker_color="#0066cc"))
        fig.add_trace(go.Bar(name=company_name2, x=margin_labels, y=v2s, marker_color="#ff6b35"))
        fig.update_layout(
            barmode="group",
            yaxis_title="(%)",
            height=320,
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(x=0, y=1)
        )
        st.plotly_chart(fig, use_container_width=True)