# FP&A Assistant — Interview Talking Points

Use this when an interviewer asks about the project. Answer in plain English first,
then add technical detail only if they follow up. Finance people care about the "why,"
not the code.

---

## The 30-Second Pitch

> "I built an AI-powered FP&A dashboard in Python that takes a company's financial
> statements and produces a full analysis in seconds — ratio analysis, budget vs actuals,
> revenue scheduling, and an AI-written analyst memo. I used the Claude API for the
> narrative generation. It's the kind of tool an FP&A team could use to cut the time
> spent on routine variance commentary and focus on actual decisions."

---

## "Walk me through what it does."

Start with the output, not the code:

1. **You upload an Excel file** — Income Statement, Balance Sheet, Cash Flow, Revenue Schedule, Budget vs Actuals
2. **It calculates 17 financial ratios** automatically — current ratio, EBITDA margin, Net Debt/EBITDA, DSO, etc. — each benchmarked and color-coded green/yellow/red
3. **It shows multi-year trend charts** so you can see if margins are expanding or compressing
4. **Budget vs actuals tab** shows YTD variance by line item, which lines are favorable, and whether you're on track for the full year
5. **Revenue schedule tab** breaks down monthly actuals vs budget and lets you build a forward forecast with a growth rate slider
6. **AI narrative button** calls Claude and returns a 3-paragraph analyst memo written in proper FP&A language — basis points, coverage ratios, pacing
7. **PDF export** gives you a one-click professional report you could hand to a CFO

---

## "Why did you build this?"

> "I wanted to demonstrate that I understand what FP&A analysts actually do day-to-day —
> not just theory. Variance analysis, ratio benchmarking, and budget pacing are core to
> the role. I also wanted to show I could connect financial analysis to modern tools.
> The AI narrative piece came from noticing that a lot of junior analyst time goes into
> writing routine commentary — this automates the first draft so the analyst can focus
> on the insight, not the formatting."

---

## "What financial concepts does it cover?"

Be ready to explain any of these:

| Concept | What to say |
|---|---|
| **Current Ratio** | Current assets / current liabilities. Measures ability to pay short-term bills. Healthy above 1.5x. |
| **Net Debt / EBITDA** | How many years of operating profit needed to pay off net debt. Most important leverage metric in banking and PE. Below 3x is generally healthy. |
| **DSO** | Days Sales Outstanding — how long it takes to collect cash from customers. Lower is better for working capital. |
| **EBITDA Margin** | EBITDA / Revenue. Operating profitability before non-cash and financing items. Most widely used margin in deal work. |
| **Interest Coverage** | EBIT / Interest Expense. Can the company comfortably service its debt? Below 1.5x is a red flag. |
| **Budget vs Actuals** | YTD variance analysis — actual performance vs what was budgeted. Favorable = beat budget, Unfavorable = missed. |
| **Revenue Pacing** | Annualizing YTD actuals to project full-year revenue. If you're running at 48% of annual budget through June, you're on track. |

---

## "What was technically challenging?"

Pick one or two — don't list everything:

**Option 1 (parsing):**
> "The hardest part was building the flexible parser that handles real-world financial
> Excel files. Public company data from sites like Macrotrends uses different row labels
> than our template — 'Total Revenue' instead of 'Revenue', 'Net Income Common
> Stockholders' instead of 'Net Income'. I built a synonym mapper that normalizes
> hundreds of variations to a standard schema, and auto-detects the year columns
> regardless of how they're formatted."

**Option 2 (AI prompt engineering):**
> "Getting the AI narrative to sound like a real analyst took iteration. The first
> versions were too generic. I had to engineer the prompt carefully — specifying
> paragraph structure, requiring basis points language for margin changes, prohibiting
> bullet points, and feeding all the ratio context explicitly. The output now reads
> like something a senior analyst would actually write."

---

## "What would you add if you had more time?"

Shows you think like a product person:

- **Live data integration** — connect to an API (e.g. Financial Modeling Prep) so you can type a ticker and pull real financials automatically
- **Scenario modeling** — let users change assumptions (revenue growth, margin, capex) and see how ratios shift
- **Peer benchmarking** — compare a company's ratios against its sector median automatically
- **Streamlit Cloud deployment** — make it publicly accessible via URL, not just local

---

## On Your Resume

**Project line:**
> AI-Powered FP&A Assistant | Python, Streamlit, Claude API
> Built a financial analysis dashboard that automates ratio analysis (17 metrics),
> budget vs actuals variance, and AI-generated analyst narratives from uploaded
> financial statements. Features multi-year trend charts, company comparison,
> and one-click PDF export.

**Skills it demonstrates:**
- FP&A concepts (ratios, variance analysis, budget pacing, revenue scheduling)
- Python (pandas, data wrangling, modular code)
- API integration (Anthropic Claude)
- Data visualization (Plotly)
- Product thinking (built something a real team could use)

---

## On LinkedIn

Post a screenshot of the dashboard with this caption:

> "Built an AI-powered FP&A assistant from scratch using Python and the Claude API.
> It takes a company's financial statements and produces ratio analysis, budget variance,
> revenue trends, and a full analyst narrative — automatically.
> The kind of tool that turns hours of routine commentary into minutes.
> [screenshot] #FPA #Python #FinanceAndTech #AI"

---

*You built this. You understand every line of it. Talk about it with confidence.*
