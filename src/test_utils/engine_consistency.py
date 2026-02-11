import pandas as pd
import numpy as np
import os
import sys
from src.search_engine import GoalSeeker
from src.catalog_search import CatalogSearcher
from src.catalog import WindowCatalog
from src.data_loader import load_data_uncached

def check_engines():
    DATA_PATH = "spy_data_25yr.parquet"
    CATALOG_DIR = "catalog"
    
    if not os.path.exists(DATA_PATH):
        print(f"❌ Source data {DATA_PATH} not found.")
        return

    print(f"Loading data from {DATA_PATH}...")
    df = load_data_uncached(DATA_PATH)
    df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
    
    # Define a test grid
    params_grid = {
        'bump_len': [5],
        'slide_len': [5],
        'bump_threshold': [0.5],
        'slide_threshold': [0.5],
        'min_bump_vol': [0],
        'min_slide_vol': [0],
        'bump_up_pct': [0],
        'slide_up_pct': [0]
    }
    
    # Explicitly set types to ensure percent calculation
    fixed_params = {
        'bump_thresh_type': 'percent',
        'slide_thresh_type': 'percent'
    }
    
    print("\n--- Running GoalSeeker (Local Engine) ---")
    seeker = GoalSeeker(df)
    res_local = seeker.search(params_grid, fixed_params=fixed_params)
    
    print("\n--- Running CatalogSearcher (Optimized Engine) ---")
    cat_seeker = CatalogSearcher(catalog_dir=CATALOG_DIR)
    res_cat = cat_seeker.search(params_grid, fixed_params=fixed_params)
    
    print("\n--- Comparison Results ---")
    print(f"Local hits: {res_local.iloc[0]['total_hits'] if not res_local.empty else 0}")
    print(f"Catalog hits: {res_cat.iloc[0]['total_hits'] if not res_cat.empty else 0}")

    if not res_local.empty and not res_cat.empty:
        diff = res_local.iloc[0]['total_hits'] - res_cat.iloc[0]['total_hits']
        if diff == 0:
            print("✅ SUCCESS: Engines matched perfectly.")
        else:
            print(f"❌ FAILURE: Mismatch by {diff} hits.")

if __name__ == "__main__":
    check_engines()
