import argparse
import pandas as pd
import sys
import time
from src.data_loader import load_data_uncached
from src.search_engine import GoalSeeker
from src.data_validator import validate_dataset

def parse_args():
    description = "Goal Seek CLI for SP500 Bump & Slide Analysis"
    epilog = """
Examples:
  # Run with default ranges (Bump/Slide Len 3-6, Threshold 3-10)
  python goal_seek_cli.py --target-cr 60

  # Run with custom ranges
  python goal_seek_cli.py --target-cr 75 --bump-len-start 5 --bump-len-end 10 --bump-thresh-start 5

Available Parameter Ranges:
  For each parameter [name], you can specify:
    --[name]-start: Start value of the range
    --[name]-end:   End value of the range (inclusive)
    --[name]-step:  Step size (set to 0 to lock at start value)

  Parameters:
    bump-len, slide-len       (Default: 3-6, step 1)
    bump-thresh, slide-thresh (Default: 3.0-10.0, step 0.5)
    bump-vol, slide-vol       (Default: Locked at 0)
    bump-up, slide-up         (Default: Locked at 0)
"""
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global Config
    parser.add_argument("--data", default="spy_data.parquet", help="Path to data file")
    parser.add_argument("--target-cr", type=float, default=50.0, help="Minimum Target Conversion Rate (Hit Ratio %%)")
    parser.add_argument("--top-n", type=int, default=20, help="Number of top results to display")
    parser.add_argument("--output", default="goal_seek_results.csv", help="Output CSV filename")
    
    # Helper to add range args
    def add_range_args(name, default_start, default_end, default_step, help_text):
        group = parser.add_argument_group(f"{name} Parameters")
        group.add_argument(f"--{name}-start", type=float, default=default_start, help=f"Start {help_text}")
        group.add_argument(f"--{name}-end", type=float, default=default_end, help=f"End {help_text}")
        group.add_argument(f"--{name}-step", type=float, default=default_step, help=f"Step {help_text}")

    # Add parameters (Using defaults from UI/User Request)
    add_range_args("bump-len", 3, 6, 1, "Bump Length (min)")
    add_range_args("slide-len", 3, 6, 1, "Slide Length (min)")
    
    add_range_args("bump-thresh", 3.0, 10.0, 0.5, "Bump Threshold")
    add_range_args("slide-thresh", 3.0, 10.0, 0.5, "Slide Threshold")
    
    # Volumes and Up% default to 0 (Locked)
    # If user wants to vary them, they can set start/end/step.
    # Default step 0 means locked? No, arange handles step. 
    # If start==end, it's locked.
    
    add_range_args("bump-vol", 0, 0, 10000, "Min Bump Size Vol")
    add_range_args("slide-vol", 0, 0, 10000, "Min Slide Size Vol")
    
    add_range_args("bump-up", 0, 0, 5.0, "Bump Up %%")
    add_range_args("slide-up", 0, 0, 5.0, "Slide Up %%")
    
    return parser.parse_args()

def generate_grid(args):
    grid = {}
    
    # Mapping arg names to internal keys
    mappings = {
        'bump-len': ('bump_len', int),
        'slide-len': ('slide_len', int),
        'bump-thresh': ('bump_threshold', float),
        'slide-thresh': ('slide_threshold', float),
        'bump-vol': ('min_bump_vol', int),
        'slide-vol': ('min_slide_vol', int),
        'bump-up': ('bump_up_pct', float),
        'slide-up': ('slide_up_pct', float),
    }
    
    import numpy as np
    
    for arg_name, (key, dtype) in mappings.items():
        start = getattr(args, f"{arg_name.replace('-', '_')}_start")
        end = getattr(args, f"{arg_name.replace('-', '_')}_end")
        step = getattr(args, f"{arg_name.replace('-', '_')}_step")
        
        if step <= 0:
            # Assume locked at start
            vals = [start]
        else:
            # Inclusive end
            if dtype == int:
                vals = np.arange(start, end + 0.0001, step).astype(int).tolist()
            else:
                vals = np.arange(start, end + 0.00001, step).tolist()
                vals = [round(x, 4) for x in vals]
        
        # If vals is empty (e.g. start > end), default to start
        if not vals:
            vals = [start]
            
        grid[key] = vals
        
    return grid

def main():
    args = parse_args()
    
    print(f"--- Goal Seek CLI ---")
    print(f"Data: {args.data}")
    print(f"Target CR: >={args.target_cr}%")
    
    # Load Data
    try:
        df = load_data_uncached(args.data)
        print(f"Loaded {len(df)} rows.")
        print(f"Date Column Type: {df['date'].dtype}")
        
        # Validation Debug
        val_report = validate_dataset(df)
        dup_count = val_report['duplicates']['count']
        print(f"Validator found {dup_count} duplicates.")
        
        # Clean Duplicates (match app.py logic)
        initial_len = len(df)
        df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
        if len(df) < initial_len:
            print(f"Removed {initial_len - len(df)} duplicate rows. Analysis set: {len(df)} rows.")
        else:
            print("No duplicates removed by drop_duplicates.")
            
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)
        
    # Setup Grid
    params_grid = generate_grid(args)
    
    print("\nSearch Configuration:")
    # Calculate total combinations
    total = 1
    for k, v in params_grid.items():
        count = len(v)
        total *= count
        if count > 0:
            # Format nicely
            min_v = min(v)
            max_v = max(v)
            if count == 1:
                print(f"  {k}: {min_v} (Locked)")
            else:
                step_est = (max_v - min_v) / (count - 1) if count > 1 else 0
                print(f"  {k}: {min_v} to {max_v} (Step ~{step_est:.4f}, {count} values)")
        else:
            print(f"  {k}: Empty (0 values)")

    print(f"\nTotal Combinations to Search: {total}")
    
    # Setup Fixed Params (Types)
    # CLI assumes types are fixed for now (Percent/Value?). 
    # The UI defaults to Percent? 
    # Let's assume Percent for now or add args. 
    # The current `analyzer` uses `bump_thresh_type`.
    # I should add args for types or default them.
    # Defaulting to 'percent' as per typical use.
    
    fixed_params = {
        'bump_thresh_type': 'percent',
        'slide_thresh_type': 'percent',
        # Time range / Days could be added, defaulting to None (All)
    }
    
    # Setup Callback
    start_time = time.time()
    
    def progress(msg, pct):
        # Clear line and print
        sys.stdout.write(f"\r[{pct*100:.1f}%] {msg}")
        sys.stdout.flush()
        
    print("\nStarting Search...")
    
    seeker = GoalSeeker(df)
    
    # Run Search (target_cr_min=0 to get all results, then filter/sort)
    # Passing 0.0 allows us to see "Best CR" even if it's below target.
    try:
        results = seeker.search(params_grid, fixed_params, target_cr_min=0.0, progress_callback=progress)
        print("\n\nSearch Complete.")
    except KeyboardInterrupt:
        print("\nSearch interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during search: {e}")
        # traceback?
        sys.exit(1)
        
    elapsed = time.time() - start_time
    print(f"Time Taken: {elapsed:.2f} seconds")
    
    if results.empty:
        print("No results found (0 hits).")
        sys.exit(0)
        
    # --- Reporting ---
    
    # Best CR
    best_cr = results['conversion_rate'].max()
    print(f"Highest Conversion Rate Found: {best_cr:.2f}%")
    
    # Sort
    results_sorted = results.sort_values('conversion_rate', ascending=False)
    
    # Dump CSV (Top 1000)
    csv_limit = 1000
    results_to_save = results_sorted.head(csv_limit)
    results_to_save.to_csv(args.output, index=False)
    print(f"Top {len(results_to_save)} results saved to: {args.output}")
    
    # Print Top N
    print(f"\n--- Top {args.top_n} Configurations ---")
    top_n = results_sorted.head(args.top_n)
    
    # Select key columns for display
    cols = ['conversion_rate', 'hits', 'total_bumps', 
            'bump_len', 'slide_len', 
            'bump_threshold', 'slide_threshold', 
            'min_bump_vol', 'min_slide_vol']
            
    # Format for printing
    print(top_n[cols].to_string(index=False))

if __name__ == "__main__":
    main()
