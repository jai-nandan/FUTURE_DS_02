"""
Plotly figure builders. Each function takes already-aggregated data (from
analysis.py) and returns a `go.Figure` / `px` figure - no analysis happens here,
just presentation, so charts can never silently diverge from the numbers shown
in KPI cards and tables.
"""

import plotly.express as px
import plotly.graph_objects as go

from .utils import PRIORITY_COLORS, RISK_COLORS

TEMPLATE = "plotly_white"


def _style(fig, height=320):
    fig.update_layout(
        template=TEMPLATE,
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(size=12),
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def monthly_volume_chart(monthly_df):
    fig = px.line(monthly_df, x="month", y="tickets", markers=True,
                   title="Monthly ticket volume")
    fig.update_traces(line_color="#1f5eff")
    return _style(fig)


def priority_donut_chart(bp_df):
    fig = px.pie(bp_df, names="priority", values="tickets", hole=0.55,
                  title="Tickets by priority",
                  color="priority", color_discrete_map=PRIORITY_COLORS)
    return _style(fig)


def escalation_trend_chart(monthly_df):
    fig = px.line(monthly_df, x="month", y="escalation_rate", markers=True,
                   title="Escalation rate by month")
    fig.update_traces(line_color="#c23b3b")
    fig.update_yaxes(tickformat=".0%")
    return _style(fig)


def satisfaction_histogram(df):
    rated = df[df["is_rated"]]
    fig = px.histogram(rated, x="satisfaction_score", nbins=3,
                        title="Satisfaction score distribution (rated tickets only)")
    fig.update_traces(marker_color="#1f5eff")
    return _style(fig)


def bar_by_priority(bp_df, y_col, title, y_fmt_pct=False):
    fig = px.bar(bp_df, x="priority", y=y_col, title=title,
                  color="priority", color_discrete_map=PRIORITY_COLORS)
    if y_fmt_pct:
        fig.update_yaxes(tickformat=".0%")
    fig.update_layout(showlegend=False)
    return _style(fig)


def top_accounts_chart(risk_df, n=15):
    top = risk_df.sort_values("tickets", ascending=False).head(n).sort_values("tickets")
    fig = px.bar(top, x="tickets", y="account_id", orientation="h",
                 title=f"Top {n} accounts by ticket volume")
    fig.update_traces(marker_color="#1f5eff")
    return _style(fig, height=max(320, n * 22))


def account_bands_chart(bands_df):
    fig = px.bar(bands_df, x="band", y="accounts",
                 title="Accounts by ticket-count band")
    fig.update_traces(marker_color="#1f5eff")
    return _style(fig)


def risk_distribution_chart(risk_df):
    counts = risk_df["risk"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0).reset_index()
    counts.columns = ["risk", "accounts"]
    fig = px.bar(counts, x="risk", y="accounts", title="Accounts by Support Risk Signal",
                 color="risk", color_discrete_map=RISK_COLORS)
    fig.update_layout(showlegend=False)
    return _style(fig)
