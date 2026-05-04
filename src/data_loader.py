import os
import pickle
from datetime import time

import pandas as pd

from src.data_validator import validate_dataset

try:
    import streamlit as st
except ImportError:
    st = None

# Regular-hours window for NYSE (ET): 09:30 to 16:00 inclusive = 391 1-min bars/day,
# matching SPY's 08:30–15:00 CT window.
REGULAR_HOURS_START = time(9, 30)
REGULAR_HOURS_END = time(16, 0)
REGULAR_HOURS_MINUTES = 391

DATASETS = {
    "SPY": {
        "path": "spy_data_25yr.parquet",
        "label": "SPY (S&P 500 ETF, 1-min, ~25y)",
        "expected_minutes_per_day": 391,
        "has_extended_hours": False,
    },
    "NVDA": {
        "path": "nvda_data_6yr.parquet",
        "label": "NVDA (NVIDIA, 1-min, ~6y)",
        # Extended hours is 04:01–20:00 ET → ~960 bars/day.
        "expected_minutes_per_day": 960,
        "has_extended_hours": True,
    },
}

DEFAULT_SYMBOL = "SPY"


def get_dataset_info(symbol):
    if symbol not in DATASETS:
        raise ValueError(f"Unknown symbol: {symbol}. Available: {list(DATASETS)}")
    return DATASETS[symbol]


def _validation_pickle_path(symbol, include_extended_hours):
    info = DATASETS.get(symbol, {})
    if info.get("has_extended_hours") and not include_extended_hours:
        return f"validation_report_{symbol}_regular.pkl"
    return f"validation_report_{symbol}.pkl"


def _filter_regular_hours(df):
    if df.empty or "date" not in df.columns:
        return df
    t = df["date"].dt.time
    mask = (t >= REGULAR_HOURS_START) & (t <= REGULAR_HOURS_END)
    return df[mask].reset_index(drop=True)


def _compute_yearly_size_vol(df):
    if df.empty:
        return {}
    size_vol = df["volume"] * (df["close"] - df["open"]).abs()
    return size_vol.groupby(df["date"].dt.year).median().to_dict()


def load_data_uncached(symbol_or_path=DEFAULT_SYMBOL, include_extended_hours=False):
    """
    Loads parquet data without caching.

    Accepts either a symbol ("SPY", "NVDA") registered in DATASETS, or a raw
    parquet path for backward compatibility. For symbols flagged with
    has_extended_hours, the dataframe is filtered to regular trading hours
    unless include_extended_hours=True.
    """
    if symbol_or_path in DATASETS:
        info = DATASETS[symbol_or_path]
        filepath = info["path"]
        has_extended = info.get("has_extended_hours", False)
    else:
        filepath = symbol_or_path
        has_extended = False  # Path-based loads are treated as already-prepared.

    df = pd.read_parquet(filepath)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

    if has_extended and not include_extended_hours:
        df = _filter_regular_hours(df)

    return df


def _expected_minutes(symbol, include_extended_hours):
    info = DATASETS.get(symbol, {})
    if info.get("has_extended_hours") and not include_extended_hours:
        return REGULAR_HOURS_MINUTES
    return info.get("expected_minutes_per_day", REGULAR_HOURS_MINUTES)


def _load_with_validation(symbol, include_extended_hours):
    df = load_data_uncached(symbol, include_extended_hours=include_extended_hours)
    expected = _expected_minutes(symbol, include_extended_hours)

    report_path = _validation_pickle_path(symbol, include_extended_hours)
    if os.path.exists(report_path):
        try:
            with open(report_path, "rb") as f:
                return df, pickle.load(f)
        except Exception as e:
            print(f"Warning: Failed to load pre-computed report {report_path}: {e}")

    val_report = validate_dataset(df, expected_minutes_per_day=expected)
    val_report["yearly_size_vol"] = _compute_yearly_size_vol(df)
    return df, val_report


if st:
    @st.cache_data
    def load_data_cached(symbol=DEFAULT_SYMBOL, include_extended_hours=False):
        """
        Loads data with Streamlit caching, keyed by (symbol, include_extended_hours).
        Returns (df, val_report).
        """
        return _load_with_validation(symbol, include_extended_hours)
else:
    def load_data_cached(symbol=DEFAULT_SYMBOL, include_extended_hours=False):
        print("Warning: Streamlit not installed. Using uncached loader.")
        return _load_with_validation(symbol, include_extended_hours)
