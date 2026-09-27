"""
Data loading and cleaning for ravenstack_support_tickets.csv.

Every cleaning step actually performed is recorded in `cleaning_log`, and every
data-quality number shown in the dashboard is measured from the raw file here -
none of it is hardcoded.
"""

import pandas as pd
import numpy as np


EXPECTED_COLUMNS = [
    "ticket_id",
    "account_id",
    "submitted_at",
    "closed_at",
    "resolution_time_hours",
    "priority",
    "first_response_time_minutes",
    "satisfaction_score",
    "escalation_flag",
]


def load_raw(path: str) -> pd.DataFrame:
    """Load the CSV exactly as provided."""
    return pd.read_csv(path)


def profile_raw(df: pd.DataFrame) -> dict:
    """Data-quality snapshot of the raw (uncleaned) dataframe."""
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "column_names": list(df.columns),
        "missing_by_column": df.isna().sum().to_dict(),
        "total_missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "missing_columns_vs_expected": [c for c in EXPECTED_COLUMNS if c not in df.columns],
    }


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Clean the raw ticket data. Returns (cleaned_df, cleaning_log).

    Nothing here invents values: satisfaction stays NaN where it was missing,
    rows with unparseable dates are dropped (and counted in the log) rather
    than silently kept, and no churn/plan/segment/region column is created
    because the source file has none.
    """
    log = []
    out = df.copy()
    start_rows = len(out)

    # 1. Standardize column names (defensive - source is already snake_case)
    out.columns = [c.strip().lower().replace(" ", "_") for c in out.columns]
    log.append("Standardized column names to snake_case.")

    # 2. Drop exact duplicate rows
    dupes = out.duplicated().sum()
    out = out.drop_duplicates()
    log.append(f"Removed {dupes} exact duplicate row(s).")

    # 3. Parse dates; drop rows where submitted_at cannot be parsed
    out["submitted_at"] = pd.to_datetime(out["submitted_at"], errors="coerce")
    out["closed_at"] = pd.to_datetime(out["closed_at"], errors="coerce")
    bad_dates = out["submitted_at"].isna().sum()
    out = out[out["submitted_at"].notna()].copy()
    log.append(f"Parsed submitted_at/closed_at to datetime; dropped {bad_dates} row(s) with an unparseable submitted_at.")

    # 4. Coerce numeric columns; invalid values become NaN rather than 0
    for col in ["resolution_time_hours", "first_response_time_minutes", "satisfaction_score"]:
        before_non_null = out[col].notna().sum()
        out[col] = pd.to_numeric(out[col], errors="coerce")
        after_non_null = out[col].notna().sum()
        if before_non_null != after_non_null:
            log.append(f"Coerced {col} to numeric ({before_non_null - after_non_null} non-numeric value(s) set to missing).")
    log.append(
        "satisfaction_score left as missing where absent (never imputed) so averages "
        "are computed only over rated tickets."
    )

    # 5. Normalize priority text
    out["priority"] = out["priority"].astype(str).str.strip().str.lower()
    valid_priorities = {"low", "medium", "high", "urgent"}
    unexpected = sorted(set(out["priority"].unique()) - valid_priorities)
    if unexpected:
        log.append(f"Found unexpected priority values: {unexpected} (kept as-is, not dropped).")
    else:
        log.append("Normalized priority to lowercase; all values fall within {low, medium, high, urgent}.")

    # 6. Normalize escalation_flag to boolean
    out["escalation_flag"] = out["escalation_flag"].map(
        lambda v: True if str(v).strip().lower() in ("true", "1", "yes") else
        (False if str(v).strip().lower() in ("false", "0", "no") else np.nan)
    )
    log.append("Normalized escalation_flag to boolean True/False.")

    # 7. Derived fields used throughout the app
    out["month"] = out["submitted_at"].dt.to_period("M").astype(str)
    out["is_rated"] = out["satisfaction_score"].notna()

    end_rows = len(out)
    log.append(f"Final cleaned dataset: {end_rows} of {start_rows} original rows retained.")

    # 8. Explicitly note what this dataset does NOT support, rather than guessing
    log.append(
        "No subscription/plan, account-status, signup-date, region, or segment column exists in "
        "the source file, so none of these are created or inferred during cleaning."
    )

    return out.reset_index(drop=True), log
