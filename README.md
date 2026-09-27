# Customer Retention & Churn Analytics

**Future Interns — Data Science & Analytics Task 2 (2026)**

A Python/Streamlit dashboard analyzing customer support behavior in `ravenstack_support_tickets.csv`,
built to answer retention-relevant business questions honestly — including saying clearly where the
data does **not** support an answer, rather than fabricating one.

## Project overview

RavenStack's support-ticket log was analyzed to understand support activity, escalation and
satisfaction patterns, and to build a support-only proxy for account risk. The project follows a
standard analytics workflow: **Python → Data Cleaning → EDA → Support Analytics → Risk Analysis →
Visualization → Business Insights → Recommendations.**

## Business problem

RavenStack wants to understand which customer accounts are showing signs of support-driven friction
and what's driving it, so retention efforts can be targeted rather than blanket.

## Objectives

- Inspect and clean the raw ticket data.
- Calculate the KPIs the data actually supports (and say plainly which ones it doesn't).
- Analyze support activity: volume, priority, escalation, resolution time, response time, satisfaction.
- Build an explainable, support-only account risk score as a retention-risk leading indicator.
- Generate insights and recommendations computed from the data, not written generically.

## Dataset

`data/ravenstack_support_tickets.csv` — 2,000 support tickets across 492 accounts, Jan 2023–Dec 2024.

| Column | Type | Notes |
|---|---|---|
| `ticket_id` | string | unique per row |
| `account_id` | string | 492 unique accounts |
| `submitted_at` | date | ticket creation date |
| `closed_at` | datetime | ticket close timestamp |
| `resolution_time_hours` | number | submit → close, hours |
| `priority` | category | low / medium / high / urgent |
| `first_response_time_minutes` | number | time to first response |
| `satisfaction_score` | number | 3–5 scale; **41.3% missing** |
| `escalation_flag` | boolean | 4.75% of tickets |

### ⚠️ About churn and retention

**This dataset has no subscription/plan field, no cancellation or account-status field, and no
signup date.** That means **churn rate, retention rate, average customer lifetime, and cohort
analysis cannot be calculated from this file**, and this project does not invent them. The **Data
Quality & Scope** page in the app states this explicitly. What the project builds instead is a
support-ticket analysis plus a clearly-labeled **Support Risk Signal** — a proxy built only from
ticket volume, escalations, and satisfaction — offered as a leading indicator, not a churn model.

## Data cleaning

Performed in `src/data_cleaning.py`, and logged (and shown in-app) exactly as run:

- Standardize column names.
- Drop exact duplicate rows (0 found).
- Parse `submitted_at`/`closed_at` to datetime; drop rows with an unparseable `submitted_at` (0 found).
- Coerce numeric columns; invalid values become missing, never zero.
- Leave `satisfaction_score` as missing where absent — never imputed — so averages are computed only
  over rated tickets.
- Normalize `priority` to lowercase and validate against the expected 4 values.
- Normalize `escalation_flag` to boolean.
- No churn/plan/segment/region column is created, because none exists in the source file.

## Exploratory analysis / support analytics

- Monthly ticket volume and escalation-rate trend (24 months).
- Ticket distribution by priority (near-even split: 24–26% per level).
- Resolution time, first-response time, escalation rate, and satisfaction broken down by priority.
- Correlation check between resolution time and satisfaction.

## Churn analysis

Not performed — see "About churn and retention" above. The app's Data Quality & Scope page states
this rather than omitting the topic silently.

## Retention analysis / account risk

`src/analysis.py::account_risk_signal()` builds a 0–100 **Support Risk Signal** per account from three
explainable, support-data-only components:

- **Ticket volume** (up to 40 pts, relative to the busiest account in view)
- **Escalation rate** (up to 35 pts, share of that account's tickets escalated)
- **Satisfaction** (up to 25 pts, worse for a lower average rating; unrated accounts get the neutral
  midpoint rather than being penalized or rewarded)

Accounts are labeled Low / Medium / High risk from the score. This is explicitly a proxy, not a churn
model, and the dashboard says so wherever it's shown.

## Support analytics

Dedicated "Ticket Analytics" and "Account Risk Signals" pages cover tickets-over-time, priority/status
breakdowns, resolution and response time, satisfaction, tickets-per-account, and repeat-contact
concentration (what share of ticket volume comes from the most active accounts).

## Key insights (computed live, examples from the full dataset)

- Escalation rate is nearly flat across priority levels (4.5%–5.1%) — priority does not predict
  escalation in this data.
- Average satisfaction barely varies by priority (3.93–4.02) — priority is not a satisfaction driver here.
- Resolution time and satisfaction show almost no linear relationship (r ≈ 0.01).
- 78.9% of accounts have filed 3+ tickets; the busiest 20% of accounts account for a third of all
  ticket volume — support load is concentrated in a small group of repeat-contact accounts.
- 41.2% of tickets have no satisfaction score, so satisfaction-based conclusions cover a minority of
  tickets.

(All figures update live to whatever filters are active — the app computes them, they are not
hardcoded text.)

## Business recommendations

1. **Prioritize the High Support Risk Signal list** for proactive, retention-minded outreach.
2. **Investigate repeat-contact accounts** — recurring tickets usually mean an unresolved root cause.
3. **Close the satisfaction-data gap** by prompting for a rating on every ticket close.
4. **Add a real churn/status field** before drawing any retention conclusions — this dataset alone
   cannot support them.

## Dashboard features

- **Overview** — KPI cards, monthly volume, priority mix, escalation trend, satisfaction distribution.
- **Ticket Analytics** — priority breakdowns and a filterable ticket log.
- **Account Risk Signals** — top accounts by volume, ticket-count bands, ranked risk table.
- **Data Quality & Scope** — row/column counts, missing values, cleaning log, churn-availability statement.
- **Business Insights** — findings computed live from the filtered data.
- **Recommendations** — actions tied directly to the insights above.
- **Data Explorer** — search, summary statistics, and a "Download Filtered Data" button.
- Sidebar filters (priority, escalation, satisfaction-rated, date range) update every page dynamically.

## Technologies

Python · pandas · NumPy · Plotly · Streamlit

## Project structure

```
Customer-Retention-Churn-Analytics/
│
├── app.py
├── data/
│   └── ravenstack_support_tickets.csv
├── src/
│   ├── __init__.py
│   ├── data_cleaning.py
│   ├── analysis.py
│   ├── visualizations.py
│   └── utils.py
├── requirements.txt
├── README.md
└── screenshots/
```

## Installation

### 1. Clone/download project

```bash
git clone <repository-url>
cd Customer-Retention-Churn-Analytics
```

### 2. Create virtual environment

Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

Mac/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## How to run

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints, typically:

```
http://localhost:8501
```

The app reads the CSV via the relative path `data/ravenstack_support_tickets.csv` — no absolute
paths are used, so it runs the same way on any machine or host.

## Streamlit Community Cloud deployment

1. Push this folder to a public (or Streamlit-authorized private) GitHub repo, keeping the folder
   structure above intact.
2. On [share.streamlit.io](https://share.streamlit.io), create a new app pointing at the repo,
   branch, and `app.py`.
3. Streamlit Cloud installs `requirements.txt` automatically — no further configuration is needed
   since all paths are relative.

## Screenshots

Add screenshots of the running dashboard to `screenshots/` (e.g. `overview.png`, `risk_signals.png`)
before publishing this repo.

## Future improvements

- Join to a real customer/billing table (plan, status, signup date) to enable true churn and cohort analysis.
- Add ticket category/subject if it becomes available, to analyze churn/risk by issue type.
- Track Support Risk Signal over time per account rather than as a point-in-time score.
- Add authentication if this is ever deployed with real customer data.

## Limitations

- No churn, retention, plan, region, or segment analysis is possible from this dataset — see "About
  churn and retention" above.
- The Support Risk Signal is a proxy built only from support data; it has not been validated against
  actual churn outcomes, because no churn outcome exists in this dataset.
- 41.3% of tickets have no satisfaction score, limiting the reliability of satisfaction-based findings.
- The dataset has no ticket category/subject or channel field, so "tickets by category" and
  "support channel" analysis requested in the original brief could not be included — those columns
  simply aren't present in the source file.

## Author

Built for the Future Interns Data Science & Analytics Task 2 (2026) program.
