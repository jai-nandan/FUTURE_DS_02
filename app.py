"""
Customer Retention & Churn Analytics — RavenStack Support Tickets
Future Interns — Data Science & Analytics Task 2 (2026)

Run with:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src.utils import DATA_PATH, fmt_pct, fmt_num
from src.data_cleaning import load_raw, profile_raw, clean
from src.analysis import (
    churn_availability, kpis, monthly_series, by_priority,
    account_risk_signal, account_ticket_bands, generate_insights, generate_recommendations,
)
from src.visualizations import (
    monthly_volume_chart, priority_donut_chart, escalation_trend_chart, satisfaction_histogram,
    bar_by_priority, top_accounts_chart, account_bands_chart, risk_distribution_chart,
)

st.set_page_config(
    page_title="RavenStack Retention & Support Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load + clean (cached so filters don't re-read/re-clean the CSV every time)
# ---------------------------------------------------------------------------
@st.cache_data
def get_data():
    raw = load_raw(DATA_PATH)
    raw_profile = profile_raw(raw)
    cleaned, log = clean(raw)
    return raw, raw_profile, cleaned, log

try:
    raw_df, raw_profile, df, cleaning_log = get_data()
except FileNotFoundError:
    st.error(f"Could not find `{DATA_PATH}`. Make sure the CSV is in the `data/` folder "
             f"next to app.py (relative path, no absolute paths used).")
    st.stop()

churn_info = churn_availability(df)

# ---------------------------------------------------------------------------
# Sidebar — navigation, dataset info, filters
# ---------------------------------------------------------------------------
st.sidebar.title("RavenStack Analytics")
st.sidebar.caption("Support & Retention-Risk Dashboard")

page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Ticket Analytics", "Account Risk Signals", "Data Quality & Scope",
     "Business Insights", "Recommendations", "Data Explorer"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Dataset**")
st.sidebar.markdown(
    f"- {raw_profile['rows']:,} raw rows, {raw_profile['columns']} columns\n"
    f"- {df['account_id'].nunique()} unique accounts (cleaned)\n"
    f"- {df['submitted_at'].min().date()} → {df['submitted_at'].max().date()}"
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Filters**")

priority_sel = st.sidebar.multiselect(
    "Priority", options=["low", "medium", "high", "urgent"], default=[]
)
escalation_sel = st.sidebar.selectbox("Escalation", ["All tickets", "Escalated only", "Not escalated"])
rated_sel = st.sidebar.selectbox("Satisfaction", ["All", "Rated only", "Unrated only"])

min_d, max_d = df["submitted_at"].min().date(), df["submitted_at"].max().date()
date_range = st.sidebar.date_input("Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)

if st.sidebar.button("Reset filters"):
    st.rerun()

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
fdf = df.copy()
if priority_sel:
    fdf = fdf[fdf["priority"].isin(priority_sel)]
if escalation_sel == "Escalated only":
    fdf = fdf[fdf["escalation_flag"] == True]
elif escalation_sel == "Not escalated":
    fdf = fdf[fdf["escalation_flag"] == False]
if rated_sel == "Rated only":
    fdf = fdf[fdf["is_rated"]]
elif rated_sel == "Unrated only":
    fdf = fdf[~fdf["is_rated"]]
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    fdf = fdf[(fdf["submitted_at"].dt.date >= start) & (fdf["submitted_at"].dt.date <= end)]

st.sidebar.caption(f"{len(fdf):,} of {len(df):,} tickets match current filters")

k = kpis(fdf)
risk_df = account_risk_signal(fdf)
mseries = monthly_series(fdf)
bp = by_priority(fdf)

SCOPE_NOTICE = (
    "**Dataset scope:** this file contains only support tickets (id, account, dates, priority, "
    "resolution time, first-response time, satisfaction, escalation flag). It has no "
    "subscription/plan field, no cancellation or status field, no signup date, and no "
    "segment/region field — so **true churn and retention rates cannot be calculated** and are "
    "not shown anywhere in this dashboard. What follows instead is a support-ticket analysis, "
    "plus a clearly-labeled **Support Risk Signal** derived only from escalation and satisfaction "
    "data, offered as a leading indicator — not a substitute for real churn data."
)

# ---------------------------------------------------------------------------
# OVERVIEW
# ---------------------------------------------------------------------------
if page == "Overview":
    st.title("Overview")
    st.info(SCOPE_NOTICE)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tickets in view", f"{k['tickets']:,}", f"of {len(df):,} total")
    c2.metric("Accounts in view", f"{k['accounts']:,}", f"of {df['account_id'].nunique()} total")
    c3.metric("Escalation rate", fmt_pct(k["escalation_rate"]))
    c4.metric("Avg. satisfaction", fmt_num(k["avg_satisfaction"], 2), "out of 5, rated only")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Avg. resolution time", fmt_num(k["avg_resolution_hours"], 1, "h"))
    c6.metric("Avg. first response", fmt_num(k["avg_first_response_min"], 0, "m"))
    c7.metric("Tickets / account", fmt_num(k["tickets_per_account"], 1))
    high_risk_n = int((risk_df["risk"] == "High").sum()) if not risk_df.empty else 0
    c8.metric("High-risk accounts", high_risk_n, "Support Risk Signal = High")

    col1, col2 = st.columns(2)
    with col1:
        if not mseries.empty:
            st.plotly_chart(monthly_volume_chart(mseries), use_container_width=True)
        else:
            st.warning("No tickets match the current filters.")
    with col2:
        if not bp.empty:
            st.plotly_chart(priority_donut_chart(bp), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        if not mseries.empty:
            st.plotly_chart(escalation_trend_chart(mseries), use_container_width=True)
    with col4:
        if fdf["is_rated"].any():
            st.plotly_chart(satisfaction_histogram(fdf), use_container_width=True)
        else:
            st.warning("No rated tickets in the current filter selection.")

# ---------------------------------------------------------------------------
# TICKET ANALYTICS
# ---------------------------------------------------------------------------
elif page == "Ticket Analytics":
    st.title("Ticket Analytics")
    st.caption("Ticket-level trends across priority, resolution and response time")

    if bp.empty:
        st.warning("No tickets match the current filters.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(bar_by_priority(bp, "avg_resolution_hours",
                             "Resolution time by priority (avg hours)"), use_container_width=True)
        with col2:
            st.plotly_chart(bar_by_priority(bp, "escalation_rate",
                             "Escalation rate by priority", y_fmt_pct=True), use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.plotly_chart(bar_by_priority(bp, "avg_first_response_min",
                             "First response time by priority (avg minutes)"), use_container_width=True)
        with col4:
            st.plotly_chart(bar_by_priority(bp, "avg_satisfaction",
                             "Satisfaction by priority (avg score)"), use_container_width=True)

    st.subheader("Ticket log")
    show_cols = ["ticket_id", "account_id", "submitted_at", "priority",
                 "resolution_time_hours", "first_response_time_minutes",
                 "satisfaction_score", "escalation_flag"]
    st.dataframe(
        fdf.sort_values("submitted_at", ascending=False)[show_cols].head(300),
        use_container_width=True, hide_index=True,
    )

# ---------------------------------------------------------------------------
# ACCOUNT RISK SIGNALS
# ---------------------------------------------------------------------------
elif page == "Account Risk Signals":
    st.title("Account Risk Signals")
    st.info(
        "**What this is:** since the dataset has no customer/subscription table, \"accounts\" "
        "here are built purely by grouping tickets on `account_id`. The **Support Risk Signal** "
        "below scores each account on three support-only factors — ticket volume, escalation "
        "count, and rated satisfaction — as a proxy for support-driven friction. It is **not** "
        "a churn prediction."
    )

    if risk_df.empty:
        st.warning("No tickets match the current filters.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(top_accounts_chart(risk_df), use_container_width=True)
        with col2:
            st.plotly_chart(account_bands_chart(account_ticket_bands(risk_df)), use_container_width=True)
            st.plotly_chart(risk_distribution_chart(risk_df), use_container_width=True)

        st.subheader("Highest Support Risk Signal accounts (top 25)")
        display = risk_df.head(25).copy()
        display["avg_satisfaction"] = display["avg_satisfaction"].round(2)
        display["avg_resolution_hours"] = display["avg_resolution_hours"].round(1)
        display["score"] = display["score"].round(1)
        st.dataframe(display, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# DATA QUALITY & SCOPE
# ---------------------------------------------------------------------------
elif page == "Data Quality & Scope":
    st.title("Data Quality & Scope")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Rows analyzed", f"{raw_profile['rows']:,}")
    c2.metric("Columns", raw_profile["columns"])
    c3.metric("Missing values", f"{raw_profile['total_missing_cells']:,}")
    c4.metric("Duplicate rows", raw_profile["duplicate_rows"])
    c5.metric("Data quality", "Good")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Columns detected")
        col_info = pd.DataFrame({
            "column": raw_profile["column_names"],
            "dtype": [raw_profile["dtypes"][c] for c in raw_profile["column_names"]],
            "missing": [raw_profile["missing_by_column"][c] for c in raw_profile["column_names"]],
        })
        col_info["missing_%"] = (col_info["missing"] / raw_profile["rows"] * 100).round(1)
        st.dataframe(col_info, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Cleaning steps actually performed")
        for step in cleaning_log:
            st.markdown(f"- {step}")

    st.subheader("Churn / retention availability")
    st.warning(f"**{churn_info['verdict']}**\n\n{churn_info['explanation']}")

# ---------------------------------------------------------------------------
# BUSINESS INSIGHTS
# ---------------------------------------------------------------------------
elif page == "Business Insights":
    st.title("💡 Business Insights")
    st.caption("Computed live from the filtered dataset — not pre-written")

    insights = generate_insights(fdf, risk_df)
    if not insights:
        st.warning("No tickets match the current filters.")
    else:
        icon = {"risk": "🔴", "pattern": "🔵", "opportunity": "🟢"}
        for ins in insights:
            st.markdown(f"{icon.get(ins['tag'], '•')} **{ins['tag'].capitalize()}.** {ins['text']}")

# ---------------------------------------------------------------------------
# RECOMMENDATIONS
# ---------------------------------------------------------------------------
elif page == "Recommendations":
    st.title("🎯 Retention Recommendations")
    st.caption("Actions logically supported by the findings in Business Insights")

    recs = generate_recommendations(fdf, risk_df)
    if not recs:
        st.warning("No tickets match the current filters.")
    else:
        cols = st.columns(2)
        for i, r in enumerate(recs):
            with cols[i % 2]:
                st.markdown(f"**{r['n']} · {r['title']}**")
                st.markdown(r["body"])
                st.markdown("")

# ---------------------------------------------------------------------------
# DATA EXPLORER
# ---------------------------------------------------------------------------
elif page == "Data Explorer":
    st.title("Data Explorer")
    st.caption("Browse and search the cleaned, filtered data; download it below.")

    search = st.text_input("Search ticket_id or account_id contains…")
    view = fdf.copy()
    if search:
        mask = view["ticket_id"].str.contains(search, case=False, na=False) | \
               view["account_id"].str.contains(search, case=False, na=False)
        view = view[mask]

    st.dataframe(view.sort_values("submitted_at", ascending=False), use_container_width=True, hide_index=True)

    st.subheader("Summary statistics (filtered numeric columns)")
    st.dataframe(view[["resolution_time_hours", "first_response_time_minutes", "satisfaction_score"]]
                 .describe().round(2), use_container_width=True)

    csv_bytes = view.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Filtered Data",
        data=csv_bytes,
        file_name="ravenstack_filtered_tickets.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption("RavenStack Support & Retention-Risk Analytics · Future Interns — Data Science & Analytics Task 2 (2026)")
