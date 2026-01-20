import pytest
from hypothesis import given, settings, strategies as st
from hypothesis.extra.pandas import data_frames, column, range_indexes
import pandas as pd
import numpy as np
from src.analyzer import find_bumps_and_slides

# Strategy for generating OHLCV dataframes
ohlcv_strategy = data_frames(
    columns=[
        column('date', elements=st.datetimes(min_value=pd.Timestamp('2020-01-01'), max_value=pd.Timestamp('2025-01-01'))),
        column('open', elements=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False)),
        column('high', elements=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False)),
        column('low', elements=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False)),
        column('close', elements=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False)),
        column('volume', elements=st.integers(min_value=0, max_value=1000000))
    ],
    index=range_indexes(min_size=50, max_size=200) # Ensure enough rows for windows
).map(lambda df: df.sort_values('date').reset_index(drop=True))

@settings(max_examples=50, deadline=None)
@given(df=ohlcv_strategy)
def test_analyzer_no_crash(df):
    """
    Property: The analyzer should never crash on valid float input, 
    even if the data makes no sense (e.g. High < Low).
    """
    # Ensure high/low consistency just to be nice, though analyzer relies mostly on Open/Close/Volume
    # We won't fix the data, we just test if it crashes.
    
    # Run with standard params
    try:
        results, stats = find_bumps_and_slides(
            df,
            bump_len=10, bump_threshold=0.01, bump_thresh_type="percent",
            slide_len=10, slide_threshold=0.01, slide_thresh_type="percent"
        )
    except Exception as e:
        pytest.fail(f"Analyzer crashed on random input: {e}")

    # Property 1: Results should be a DataFrame
    assert isinstance(results, pd.DataFrame)
    
    # Property 2: Stats should be a dict with keys
    assert 'hits' in stats
    assert 'total_bumps' in stats

@settings(max_examples=50, deadline=None)
@given(df=ohlcv_strategy)
def test_output_invariants(df):
    """
    Property: Result indices must be subset of input.
    """
    results, _ = find_bumps_and_slides(
        df,
        bump_len=5, bump_threshold=0.01, bump_thresh_type="percent",
        slide_len=5, slide_threshold=0.01, slide_thresh_type="percent"
    )
    
    if not results.empty:
        # Check that all result dates exist in original df
        assert results['date'].isin(df['date']).all()
        
        # Check that result index is valid
        # Note: analyzer preserves original index or resets? 
        # Looking at code: returns candidates[...] which preserves index.
        assert results.index.isin(df.index).all()
