"""
Shared constants and small helpers used across the app.
"""

import pandas as pd

DATA_PATH = "data/ravenstack_support_tickets.csv"

PRIORITY_ORDER = ["low", "medium", "high", "urgent"]

PRIORITY_COLORS = {
    "low": "#1d8a5b",
    "medium": "#1f5eff",
    "high": "#b8791a",
    "urgent": "#c23b3b",
}

RISK_COLORS = {"Low": "#1d8a5b", "Medium": "#b8791a", "High": "#c23b3b"}

NOT_AVAILABLE = "Not available from the current dataset."


def fmt_pct(x, decimals=1):
    """Format a 0-1 fraction as a percentage string, or a placeholder if missing."""
    if x is None or pd.isna(x):
        return "–"
    return f"{x * 100:.{decimals}f}%"


def fmt_num(x, decimals=1, suffix=""):
    if x is None or pd.isna(x):
        return "–"
    return f"{x:.{decimals}f}{suffix}"


def safe_mean(series):
    """Mean of a pandas Series, ignoring NaN, returning None if empty."""
    s = series.dropna()
    return float(s.mean()) if len(s) else None
