import pandas as pd
from src.search_engine import GoalSeeker
from src.data_loader import load_data_uncached

def main():
    df = load_data_uncached('spy_data_25yr.parquet')
    seeker = GoalSeeker(df)

    grid = {
        'bump_len': [3], 'slide_len': [3], 
        'bump_threshold': [0.5], 'slide_threshold': [0.5],
        'min_bump_vol': [0], 'min_slide_vol': [0],
        'bump_up_pct': [0], 'slide_up_pct': [0],
        'bump_thresh_type': ['percent'], 'slide_thresh_type': ['percent']
    }

    fixed_params = {
        'start_year': 2020,
        'end_year': 2020
    }

    print("Running with year filter...")
    res = seeker.search(grid, fixed_params=fixed_params)
    print("With year filter (2020-2020):", len(res), "results")
    if len(res) > 0:
        print("Scope:", res['scope_start'].iloc[0], "to", res['scope_end'].iloc[0])
        print("Best hit date:", res['best_hit_date'].iloc[0])

    print("\nRunning without year filter...")
    res2 = seeker.search(grid)
    print("Without year filter:", len(res2), "results")
    if len(res2) > 0:
        print("Scope:", res2['scope_start'].iloc[0], "to", res2['scope_end'].iloc[0])
        print("Best hit date:", res2['best_hit_date'].iloc[0])

if __name__ == '__main__':
    main()
