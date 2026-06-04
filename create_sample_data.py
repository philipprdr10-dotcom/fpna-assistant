import pandas as pd

income_statement = pd.DataFrame({
    "Line Item": ["Revenue","Cost of Goods Sold","Gross Profit","Operating Expenses","EBITDA","Depreciation & Amortization","EBIT","Interest Expense","Pre-Tax Income","Tax Expense","Net Income"],
    "FY2022": [8500000,5100000,3400000,1800000,1600000,300000,1300000,150000,1150000,287500,862500],
    "FY2023": [9800000,5700000,4100000,2000000,2100000,320000,1780000,140000,1640000,410000,1230000],
    "FY2024": [11200000,6300000,4900000,2200000,2700000,340000,2360000,130000,2230000,557500,1672500]
})

balance_sheet = pd.DataFrame({
    "Line Item": ["Cash & Equivalents","Accounts Receivable","Inventory","Total Current Assets","Property Plant & Equipment","Total Assets","Accounts Payable","Short-Term Debt","Total Current Liabilities","Long-Term Debt","Total Liabilities","Shareholders Equity"],
    "FY2022": [1200000,950000,800000,2950000,3500000,6450000,600000,400000,1000000,1800000,2800000,3650000],
    "FY2023": [1500000,1100000,850000,3450000,3800000,7250000,700000,350000,1050000,1600000,2650000,4600000],
    "FY2024": [2100000,1250000,900000,4250000,4100000,8350000,750000,300000,1050000,1400000,2450000,5900000]
})

cash_flow = pd.DataFrame({
    "Line Item": ["Net Income","Depreciation & Amortization","Changes in Working Capital","Cash from Operations","Capital Expenditures","Cash from Investing","Debt Repayment","Cash from Financing","Net Change in Cash"],
    "FY2022": [862500,300000,-120000,1042500,-450000,-450000,-200000,-200000,392500],
    "FY2023": [1230000,320000,-150000,1400000,-600000,-600000,-200000,-200000,600000],
    "FY2024": [1672500,340000,-180000,1832500,-700000,-700000,-200000,-200000,932500]
})

revenue_schedule = pd.DataFrame({
    "Month": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
    "FY2024_Actual": [850000,880000,920000,910000,950000,980000,920000,940000,960000,970000,990000,930000],
    "FY2025_Budget": [950000,970000,1020000,1010000,1050000,1080000,1020000,1040000,1060000,1070000,1090000,1030000]
})

budget_vs_actuals = pd.DataFrame({
    "Line Item": ["Revenue","Cost of Goods Sold","Gross Profit","Operating Expenses","EBITDA","Net Income"],
    "FY2025_Budget": [12340000,6900000,5440000,2400000,3040000,1900000],
    "FY2025_Actual_YTD": [6100000,3500000,2600000,1150000,1450000,920000],
    "Budget_YTD": [6170000,3450000,2720000,1200000,1520000,950000]
})

with pd.ExcelWriter("sample_data/sample_financials.xlsx", engine="xlsxwriter") as writer:
    income_statement.to_excel(writer, sheet_name="Income Statement", index=False)
    balance_sheet.to_excel(writer, sheet_name="Balance Sheet", index=False)
    cash_flow.to_excel(writer, sheet_name="Cash Flow", index=False)
    revenue_schedule.to_excel(writer, sheet_name="Revenue Schedule", index=False)
    budget_vs_actuals.to_excel(writer, sheet_name="Budget vs Actuals", index=False)

print("✅ Sample data created: sample_data/sample_financials.xlsx")
