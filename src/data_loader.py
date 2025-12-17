import pandas as pd
import streamlit as st
from src.data_validator import validate_dataset

def load_data_uncached(filepath="spy_data.parquet"):
    """
    Loads the parquet data without caching.
    """
    df = pd.read_parquet(filepath)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
    return df

@st.cache_data
def load_data_cached(filepath="spy_data.parquet"):
    """
    Loads the parquet data with Streamlit caching and pre-calculates validation.
    Returns (df, val_report)
    """
    df = load_data_uncached(filepath)
    val_report = validate_dataset(df)
    return df, val_report
