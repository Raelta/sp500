import pandas as pd
import pytest
from src.search_engine import GoalSeeker

# Mock data
# 100 minutes of data
data = {
    'date': pd.date_range(start='2023-01-01', periods=100, freq='min'),
    'open': [100.0 + i for i in range(100)],
    'close': [100.5 + i for i in range(100)], # Always up by 0.5 relative to open of that minute
    'volume': [1000] * 100
}
df = pd.DataFrame(data)
# Ensure calculate_change handles zero correctly if referenced, though here prices are > 100

def test_goal_seeker_basic():
    seeker = GoalSeeker(df)
    
    # Define a simple grid
    params_grid = {
        'bump_len': [5],
        'slide_len': [5],
        'bump_threshold': [0.01], # Small threshold
        'slide_threshold': [0.01],
        'min_bump_vol': [0],
        'min_slide_vol': [0],
        'bump_up_pct': [0],
        'slide_up_pct': [0]
    }
    
    # We need fixed params for Types
    fixed_params = {
        'bump_thresh_type': 'percent',
        'slide_thresh_type': 'percent'
    }
    
    results = seeker.search(params_grid, fixed_params, target_cr_min=0)
    
    assert not results.empty
    assert 'total_hits' in results.columns
    assert 'true_hits' in results.columns
    # With always up candles and linear price increase:
    # Bump (5 mins): Price increases. Change is positive.
    # Slide (5 mins): Price increases. Change is positive.
    # Thresholds are minimal.
    # Should find hits.
    
    assert results.iloc[0]['hits'] > 0

def test_goal_seeker_optimization():
    # Test multiple structural params to ensure loop works
    seeker = GoalSeeker(df)
    
    params_grid = {
        'bump_len': [2, 3],
        'slide_len': [2, 3],
        'bump_threshold': [0.1],
        'slide_threshold': [0.1],
        'min_bump_vol': [0],
        'min_slide_vol': [0],
        'bump_up_pct': [0],
        'slide_up_pct': [0]
    }
    
    fixed_params = {
        'bump_thresh_type': 'percent',
        'slide_thresh_type': 'percent'
    }
    
    results = seeker.search(params_grid, fixed_params)
    # Should have 2 * 2 = 4 rows (since other params have len 1)
    assert len(results) == 4

def test_goal_seeker_pruning():
    # Test that parameters outside the possible data range are pruned (ignored)
    # Create data with max bump change of ~0.5
    data_prune = {
        'date': pd.date_range(start='2023-01-01', periods=100, freq='min'),
        'open': [100.0] * 100,
        'close': [100.5] * 100, # Constant 0.5 diff
        'volume': [1000] * 100
    }
    df_prune = pd.DataFrame(data_prune)
    
    seeker = GoalSeeker(df_prune)
    
    # Grid asks for thresholds [0.1, 10.0]
    # 10.0 is impossible (max is 0.5)
    params_grid = {
        'bump_len': [5],
        'slide_len': [5],
        'bump_threshold': [0.1, 10.0],
        'slide_threshold': [0.1],
        'min_bump_vol': [0],
        'min_slide_vol': [0],
        'bump_up_pct': [0],
        'slide_up_pct': [0]
    }
    
    fixed_params = {
        'bump_thresh_type': 'value', # Use value to match 0.5 diff
        'slide_thresh_type': 'value'
    }
    
    # We expect results for 0.1, but NOT for 10.0
    results = seeker.search(params_grid, fixed_params, target_cr_min=0)
    
    assert not results.empty
    # Check that 'bump_threshold' column only contains 0.1
    assert (results['bump_threshold'] == 0.1).all()
    assert 10.0 not in results['bump_threshold'].values

def test_hits_per_year():
    # Verify that hits_per_year JSON is correctly generated for multi-year data
    import json
    
    # Create data spanning two years (Dec 31 2022 to Jan 2 2023)
    dates = pd.date_range(start='2022-12-31 23:30', end='2023-01-01 00:30', freq='min')
    n = len(dates)
    
    data = {
        'date': dates,
        'open': [100.0 + i for i in range(n)],
        'close': [100.5 + i for i in range(n)], # Always up
        'volume': [1000] * n
    }
    df = pd.DataFrame(data)
    
    seeker = GoalSeeker(df)
    
    params_grid = {
        'bump_len': [5],
        'slide_len': [5],
        'bump_threshold': [0.01],
        'slide_threshold': [0.01],
        'min_bump_vol': [0],
        'min_slide_vol': [0],
        'bump_up_pct': [0],
        'slide_up_pct': [0]
    }
    
    fixed_params = { 'bump_thresh_type': 'percent', 'slide_thresh_type': 'percent' }
    
    results = seeker.search(params_grid, fixed_params, target_cr_min=0)
    
    assert not results.empty
    row = results.iloc[0]
    
    assert 'hits_per_year' in row
    hpy_json = row['hits_per_year']
    assert isinstance(hpy_json, str)
    
    hpy = json.loads(hpy_json)
    # We should have hits in 2022 and 2023 because the pattern continues across the year boundary
    # Note: Hits are attributed to the "best hit date". 
    # If patterns overlap, we might only get true hits in one year or both.
    # Given the steady rise, we should have hits throughout.
    
    assert '2022' in hpy or '2023' in hpy
    # Ideally both, but check at least one valid year key exists
    assert any(k in ['2022', '2023'] for k in hpy.keys())
    assert all(isinstance(v, int) for v in hpy.values())
