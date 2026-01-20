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
    assert 'conversion_rate' in results.columns
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
