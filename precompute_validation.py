import pandas as pd
import pickle
import os
import sys

# Ensure src is in path
sys.path.append(os.getcwd())

from src.data_loader import load_data_uncached
from src.data_validator import validate_dataset

def main():
    print("Starting pre-computation of data validation report...")
    
    # Load data
    try:
        df = load_data_uncached("spy_data_25yr.parquet")
        print(f"Loaded {len(df)} rows.")
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

    # Validate
    print("Running validation (this may take a while)...")
    val_report = validate_dataset(df)
    
    # Add yearly size vol (as done in loader)
    if not df.empty:
        size_vol = df['volume'] * (df['close'] - df['open']).abs()
        yearly_avgs = size_vol.groupby(df['date'].dt.year).median().to_dict()
        val_report['yearly_size_vol'] = yearly_avgs
    else:
        val_report['yearly_size_vol'] = {}

    # Save
    output_file = "validation_report.pkl"
    with open(output_file, "wb") as f:
        pickle.dump(val_report, f)
        
    print(f"Validation report saved to {output_file}")

if __name__ == "__main__":
    main()
