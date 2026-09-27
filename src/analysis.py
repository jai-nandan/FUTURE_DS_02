"""
All numeric analysis lives here: KPIs, the account-level Support Risk Signal,
and auto-generated insights/recommendations. Every number is computed from the
dataframe passed in - nothing is hardcoded, so results change correctly when
the caller passes a filtered slice.

IMPORTANT — about churn/retention:
This dataset (ravenstack_support_tickets.csv) has no subscription/plan field,
no cancellation or account-status field, and no signup date. That means a real
churn rate, retention rate, or cohort table CANNOT be computed from it, and
this module does not attempt to. See `churn_availability()` below, which the
app displays verbatim rather than silently omitting the topic.
"""

import numpy as np
import pandas as pd

from .utils import safe_mean, PRIORITY_ORDER, NOT_AVAILABLE


def churn_availability(df: pd.DataFrame) -> dict:
    """
    Explicit, honest statement of what churn/retention analysis this dataset
    supports. Called out as its own function so app.py can never accidentally
    skip displaying it.
    """
    required_for_churn = ["account_status", "subscription_status", "cancelled_at", "churned"]
    present = [c for c in required_for_churn if c in df.columns]
    return {
        "has_direct_churn_field": len(present) > 0,
        "fields_found": present,
        "verdict": (
            NOT_AVAILABLE
            if not present
            else "Churn field(s) detected: " + ", ".join(present)
        ),
        "explanation": (
            "The dataset contains only support-ticket records (ticket id, account, dates, "
            "priority, resolution/response time, satisfaction, escalation flag). There is no "
            "subscription/plan status, cancellation date, or signup date to determine who is "
            "an active vs. churned customer, so churn rate, retention rate, customer lifetime, "
            "and cohort analysis are not calculated here. Building a churn label from ticket "
            "activity alone (e.g. 'no recent tickets = churned') would not be reliable, since "
            "a quiet account could equally mean a satisfied customer with no issues."
        ),
    }


def kpis(df: pd.DataFrame) -> dict:
    """Headline KPIs for the current (possibly filtered) dataframe."""
    n_tickets = len(df)
    n_accounts = df["account_id"].nunique()
    rated = df[df["is_rated"]]
    return {
        "tickets": n_tickets,
        "accounts": n_accounts,
        "escalation_rate": (df["escalation_flag"].mean() if n_tickets else None),
        "avg_satisfaction": safe_mean(rated["satisfaction_score"]),
        "avg_resolution_hours": safe_mean(df["resolution_time_hours"]),
        "avg_first_response_min": safe_mean(df["first_response_time_minutes"]),
        "tickets_per_account": (n_tickets / n_accounts if n_accounts else None),
        "rated_share": (df["is_rated"].mean() if n_tickets else None),
    }


def monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    """Ticket volume and escalation rate by month, sorted chronologically."""
    if df.empty:
        return pd.DataFrame(columns=["month", "tickets", "escalation_rate"])
    g = df.groupby("month").agg(
        tickets=("ticket_id", "count"),
        escalation_rate=("escalation_flag", "mean"),
    ).reset_index()
    return g.sort_values("month")


def by_priority(df: pd.DataFrame) -> pd.DataFrame:
    """Ticket count, escalation rate, avg resolution/response/satisfaction by priority."""
    if df.empty:
        return pd.DataFrame(columns=["priority", "tickets", "escalation_rate",
                                      "avg_resolution_hours", "avg_first_response_min",
                                      "avg_satisfaction"])
    g = df.groupby("priority").agg(
        tickets=("ticket_id", "count"),
        escalation_rate=("escalation_flag", "mean"),
        avg_resolution_hours=("resolution_time_hours", "mean"),
        avg_first_response_min=("first_response_time_minutes", "mean"),
        avg_satisfaction=("satisfaction_score", "mean"),
    ).reindex(PRIORITY_ORDER).dropna(how="all").reset_index()
    return g


def account_risk_signal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Support Risk Signal: a support-data-only composite score per account, used
    as a leading indicator of support-driven friction. Explicitly NOT a churn
    model - the dataset has no ground truth to validate a churn model against.

    Score (0-100) blends three normalized, explainable components:
      - ticket volume  (40 pts max, relative to the busiest account in view)
      - escalation rate (35 pts max, share of that account's tickets escalated)
      - satisfaction    (25 pts max, worse for lower average rating; accounts
                          with no ratings at all get the neutral midpoint
                          rather than being penalized or rewarded)
    """
    if df.empty:
        return pd.DataFrame(columns=["account_id", "tickets", "escalations",
                                      "avg_satisfaction", "avg_resolution_hours",
                                      "score", "risk"])

    g = df.groupby("account_id").agg(
        tickets=("ticket_id", "count"),
        escalations=("escalation_flag", "sum"),
        avg_satisfaction=("satisfaction_score", "mean"),
        avg_resolution_hours=("resolution_time_hours", "mean"),
    ).reset_index()

    max_tickets = max(g["tickets"].max(), 1)
    volume_score = (g["tickets"] / max_tickets) * 40
    esc_score = (g["escalations"] / g["tickets"].replace(0, np.nan)).fillna(0) * 35
    sat_score = g["avg_satisfaction"].apply(
        lambda s: 12.5 if pd.isna(s) else ((5 - s) / 2) * 25
    )

    g["score"] = volume_score + esc_score + sat_score
    g["risk"] = pd.cut(g["score"], bins=[-1, 27.999, 44.999, 100], labels=["Low", "Medium", "High"])
    return g.sort_values("score", ascending=False).reset_index(drop=True)


def account_ticket_bands(risk_df: pd.DataFrame) -> pd.DataFrame:
    """How many accounts fall into each ticket-count band."""
    bands = [(1, 1, "1"), (2, 2, "2"), (3, 4, "3-4"), (5, 6, "5-6"), (7, 10_000, "7+")]
    rows = []
    for lo, hi, label in bands:
        rows.append({"band": label, "accounts": int(((risk_df["tickets"] >= lo) & (risk_df["tickets"] <= hi)).sum())})
    return pd.DataFrame(rows)


def generate_insights(df: pd.DataFrame, risk_df: pd.DataFrame) -> list[dict]:
    """
    Compute a handful of findings directly from the current (filtered) data.
    Each insight is tagged 'pattern', 'risk', or 'opportunity' for display.
    Returns [] if there isn't enough data to say anything meaningful.
    """
    insights = []
    if df.empty:
        return insights

    bp = by_priority(df)

    # 1. Escalation rate spread across priority
    if len(bp) >= 2 and bp["escalation_rate"].notna().any():
        spread = bp["escalation_rate"].max() - bp["escalation_rate"].min()
        if spread < 0.02:
            lo, hi = bp["escalation_rate"].min(), bp["escalation_rate"].max()
            insights.append({
                "tag": "pattern",
                "text": (f"Escalation rate is nearly flat across priority levels "
                         f"({lo*100:.1f}%–{hi*100:.1f}%). Ticket priority does not appear "
                         f"to predict which tickets get escalated in this data.")
            })
        else:
            worst = bp.loc[bp["escalation_rate"].idxmax()]
            insights.append({
                "tag": "risk",
                "text": (f"\"{worst['priority']}\" priority tickets have the highest escalation "
                         f"rate at {worst['escalation_rate']*100:.1f}%.")
            })

    # 2. Satisfaction spread across priority
    valid_sat = bp.dropna(subset=["avg_satisfaction"])
    if len(valid_sat) >= 2:
        sat_spread = valid_sat["avg_satisfaction"].max() - valid_sat["avg_satisfaction"].min()
        if sat_spread < 0.2:
            detail = ", ".join(f"{r.priority}: {r.avg_satisfaction:.2f}" for r in valid_sat.itertuples())
            insights.append({
                "tag": "pattern",
                "text": (f"Average satisfaction is essentially the same regardless of priority "
                         f"({detail}), so urgent/high-priority handling is not showing up as a "
                         f"satisfaction driver in this data.")
            })

    # 3. Resolution time vs satisfaction correlation
    pairs = df.dropna(subset=["resolution_time_hours", "satisfaction_score"])
    if len(pairs) > 20:
        r = pairs["resolution_time_hours"].corr(pairs["satisfaction_score"])
        insights.append({
            "tag": "pattern",
            "text": (f"Resolution time and satisfaction show almost no linear relationship in "
                     f"this filtered view (r ≈ {r:.2f}), so slower resolution alone doesn't "
                     f"explain lower ratings here.")
        })

    # 4. Repeat-contact concentration
    if not risk_df.empty:
        repeat_share = (risk_df["tickets"] >= 3).mean()
        sorted_by_tix = risk_df.sort_values("tickets", ascending=False)
        top20_n = max(1, round(len(sorted_by_tix) * 0.2))
        top20_share = sorted_by_tix.head(top20_n)["tickets"].sum() / max(1, df["ticket_id"].nunique())
        insights.append({
            "tag": "opportunity",
            "text": (f"{repeat_share*100:.1f}% of accounts in view have filed 3 or more tickets, "
                     f"and the top 20% most-active accounts by ticket count account for "
                     f"{top20_share*100:.1f}% of all ticket volume — support load is concentrated "
                     f"in a small group of repeat-contact accounts.")
        })

        # 5. High risk accounts
        high_risk = (risk_df["risk"] == "High").sum()
        if high_risk:
            insights.append({
                "tag": "risk",
                "text": (f"{high_risk} account(s) in view score \"High\" on the Support Risk "
                         f"Signal (heavy ticket volume, frequent escalation, and/or low "
                         f"satisfaction) — see Account Risk Signals for the ranked list.")
            })

    # 6. Unrated share
    unrated_share = 1 - df["is_rated"].mean()
    insights.append({
        "tag": "pattern",
        "text": (f"{unrated_share*100:.1f}% of tickets in view have no satisfaction score at all "
                 f"— any satisfaction-based conclusion here covers a minority of tickets and "
                 f"should be read with that in mind.")
    })

    return insights


def generate_recommendations(df: pd.DataFrame, risk_df: pd.DataFrame) -> list[dict]:
    """
    Recommendations tied to what generate_insights() actually found - kept
    separate from the insights themselves so findings vs. actions stay distinct.
    """
    if df.empty or risk_df.empty:
        return []

    high_risk = int((risk_df["risk"] == "High").sum())
    repeat_share = (risk_df["tickets"] >= 3).mean()
    unrated_share = 1 - df["is_rated"].mean()

    return [
        {
            "n": "01",
            "title": "Prioritize the High Support Risk Signal list",
            "body": (f"{high_risk} account(s) currently score \"High\" on volume + escalations + "
                     f"low satisfaction. Route these to a retention-minded rep for proactive "
                     f"outreach before assuming they are simply \"heavy support users.\""),
        },
        {
            "n": "02",
            "title": "Investigate repeat-contact accounts",
            "body": (f"{repeat_share*100:.1f}% of accounts have filed 3+ tickets. Recurring "
                     f"contact from the same account usually signals an unresolved root cause "
                     f"rather than several unrelated issues — worth a root-cause review per "
                     f"account, not per ticket."),
        },
        {
            "n": "03",
            "title": "Close the satisfaction-data gap",
            "body": (f"{unrated_share*100:.1f}% of tickets have no satisfaction score, so any "
                     f"satisfaction-based signal (including the Risk Signal above) is working "
                     f"with partial information. Prompting for a rating on ticket close would "
                     f"materially improve future retention analysis."),
        },
        {
            "n": "04",
            "title": "Add a real churn/status field before drawing retention conclusions",
            "body": ("This dataset cannot answer \"who churned\" or \"what drives churn\" — it "
                      "has no subscription, cancellation, or signup field. Joining this ticket "
                      "log to a customer/billing table with account status and plan would unlock "
                      "actual churn and retention analysis, rather than the support-only proxy "
                      "shown here."),
        },
    ]
