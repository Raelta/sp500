import argparse
import pandas as pd
import sys
import time
import os
from src.data_loader import load_data_uncached
from src.search_engine import GoalSeeker
from src.catalog import WindowCatalog
from src.catalog_search import CatalogSearcher
from src.data_validator import validate_dataset

def parse_args():
    description = "Goal Seek CLI for SP500 Bump & Slide Analysis"
    epilog = """
Examples:
  # Run with default settings (Lengths 3-6, Thresholds >= 3.0)
  python goal_seek_cli.py

  # Run with custom length ranges and higher thresholds
  python goal_seek_cli.py --bump-len-start 5 --bump-len-end 10 --min-bump-threshold 5.0

  # Run with minimum bumps filter
  python goal_seek_cli.py --min-bumps 10

Available Parameter Ranges:
  For LENGTH parameters [name], you can specify:
    --[name]-start: Start value of the range
    --[name]-end:   End value of the range (inclusive)
    --[name]-step:  Step size (set to 0 to lock at start value)

  Parameters:
    bump-len, slide-len       (Default: 3-6, step 1)
    
  Thresholds (Single Minimum Value):
    --min-bump-threshold      (Default: 3.0)
    --min-slide-threshold     (Default: 3.0)
    
  Other Ranges:
    bump-vol, slide-vol       (Default: Locked at 0)
    bump-up, slide-up         (Default: Locked at 0)

Output Columns:
  - total_hits:    Count of ALL overlapping pattern matches found.
  - true_hits:     Count of distinct patterns (best match per overlapping sequence).
  - best_hit_date: Date/Time of the single best match (highest slide change).
  - total_bumps:   Count of candidate bumps meeting criteria.
  - data_gap:      (Detailed only) True if gap > 1min exists between bump and slide.
"""
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global Config
    parser.add_argument("--data", default="spy_data.parquet", help="Path to data file")
    parser.add_argument("--min-bumps", type=int, default=0, help="Minimum Total Bumps Required")
    parser.add_argument("--top-n", type=int, default=20, help="Number of top results to display")
    parser.add_argument("--output", default="goal_seek_results.csv", help="Output CSV filename")
    parser.add_argument("--detailed", action="store_true", help="Output detailed matches (one row per match) in results CSV instead of summaries")
    
    # Catalog Options
    parser.add_argument("--build-catalog", action="store_true", help="Build the Window Catalog before searching")
    parser.add_argument("--use-catalog", action="store_true", help="Use pre-computed catalog for search")
    parser.add_argument("--catalog-max-len", type=int, default=360, help="Max Window Length for Catalog (default 360)")
    
    # Helper to add range args
    def add_range_args(name, default_start, default_end, default_step, help_text):
        group = parser.add_argument_group(f"{name} Parameters")
        group.add_argument(f"--{name}-start", type=float, default=default_start, help=f"Start {help_text}")
        group.add_argument(f"--{name}-end", type=float, default=default_end, help=f"End {help_text}")
        group.add_argument(f"--{name}-step", type=float, default=default_step, help=f"Step {help_text}")

    # Add parameters (Using defaults from UI/User Request)
    add_range_args("bump-len", 3, 6, 1, "Bump Length (min)")
    add_range_args("slide-len", 3, 6, 1, "Slide Length (min)")
    
    # Thresholds (Fixed Minimums)
    parser.add_argument("--min-bump-threshold", type=float, default=3.0, help="Minimum Bump Threshold")
    parser.add_argument("--min-slide-threshold", type=float, default=3.0, help="Minimum Slide Threshold")
    
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
        'bump-vol': ('min_bump_vol', int),
        'slide-vol': ('min_slide_vol', int),
        'bump-up': ('bump_up_pct', float),
        'slide-up': ('slide_up_pct', float),
    }
    
    # Add Fixed Thresholds
    grid['bump_threshold'] = [args.min_bump_threshold]
    grid['slide_threshold'] = [args.min_slide_threshold]
    
    import numpy as np
    
    for arg_name, (key, dtype) in mappings.items():
        start = getattr(args, f"{arg_name.replace('-', '_')}_start")
        end = getattr(args, f"{arg_name.replace('-', '_')}_end")
        step = getattr(args, f"{arg_name.replace('-', '_')}_step")
        
        if step <= 0:
            # Assume locked at start
            if dtype == int:
                vals = [int(start)]
            else:
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
    
    # Auto-detect catalog
    if not args.use_catalog and not args.build_catalog:
        if os.path.exists("catalog/metadata.npz") and os.path.exists("catalog/change_matrix.npy"):
            print("INFO: Pre-computed catalog found. Automatically enabling --use-catalog optimization.")
            args.use_catalog = True

    print(f"--- Goal Seek CLI ---")
    print(f"Data: {args.data}")
    print(f"Min Bumps: >={args.min_bumps}")
    
    # Handle Catalog Build
    if args.build_catalog:
        try:
            print("Loading data for catalog build...")
            df = load_data_uncached(args.data)
            print(f"Loaded {len(df)} rows.")
            
            # Clean Duplicates
            df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
            
            catalog = WindowCatalog()
            catalog.build(df, max_len=args.catalog_max_len)
            print("Catalog build completed successfully.")
            sys.exit(0)
        except Exception as e:
            print(f"Error building catalog: {e}")
            sys.exit(1)

    # Load Data (if not using catalog, or if needed)
    # If using catalog, we don't strictly need to load the dataframe unless we want to validate or use original columns not in catalog
    # But current GoalSeeker needs df. CatalogSearcher loads from disk.
    
    df = None
    if not args.use_catalog:
        try:
            df = load_data_uncached(args.data)
            print(f"Loaded {len(df)} rows.")
            
            # Clean Duplicates
            df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
                
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
    
    if args.use_catalog:
        print("Using Catalog Searcher...")
        seeker = CatalogSearcher()
    else:
        print("Using Standard GoalSeeker...")
        seeker = GoalSeeker(df)
    
    # Run Search
    try:
        results = seeker.search(
            params_grid, 
            fixed_params, 
            target_cr_min=0.0, # Ignored by search engine now
            min_bumps=args.min_bumps,
            progress_callback=progress,
            detailed=args.detailed
        )
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
    
    # Best Hits
    best_hits = results['total_hits'].max()
    print(f"Highest Total Hits Found: {best_hits}")
    
    # Sort by Total Hits Descending
    results_sorted = results.sort_values('total_hits', ascending=False)
    
    # Dump CSV (Top 1000)
    csv_limit = 1000
    results_to_save = results_sorted.head(csv_limit)
    results_to_save.to_csv(args.output, index=False)
    print(f"Top {len(results_to_save)} results saved to: {args.output}")
    
    # Print Top N
    print(f"\n--- Top {args.top_n} Results ---")
    top_n = results_sorted.head(args.top_n)
    
    # Select key columns for display
    cols = ['total_hits', 'true_hits', 'best_hit_date', 'total_bumps', 
            'bump_len', 'slide_len', 
            'bump_threshold', 'slide_threshold', 
            'min_bump_vol', 'min_slide_vol']
            
    if args.detailed:
        if 'bump_start_date' in top_n.columns:
            cols.insert(0, 'bump_start_date')
        if 'data_gap' in top_n.columns:
            cols.append('data_gap')
            
    # Format for printing
    # Ensure cols exist
    existing_cols = [c for c in cols if c in top_n.columns]
    print(top_n[existing_cols].to_string(index=False))

if __name__ == "__main__":
    main()
