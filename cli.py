import argparse
import pandas as pd
from datetime import datetime, time
from src.data_loader import load_data_uncached
from src.analyzer import find_bumps_and_slides
from src.data_validator import validate_dataset, get_yearly_duplicate_summary

def parse_time(s):
    try:
        return datetime.strptime(s, "%H:%M").time()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid time format: {s}. Use HH:MM")

def main():
    parser = argparse.ArgumentParser(description="SP500 Bump & Slide Analysis CLI")
    
    parser.add_argument("--bump-len", type=int, default=5, help="Bump length in minutes (3-20)")
    parser.add_argument("--bump-thresh", type=float, default=0.05, help="Bump threshold")
    parser.add_argument("--bump-type", choices=["percent", "value"], default="percent", help="Bump threshold type")
    
    parser.add_argument("--slide-len", type=int, default=3, help="Slide length in minutes")
    parser.add_argument("--slide-thresh", type=float, default=0.05, help="Slide threshold")
    parser.add_argument("--slide-type", choices=["percent", "value"], default="percent", help="Slide threshold type")
    
    parser.add_argument("--min-bump-vol", type=int, default=0, help="Minimum volume during bump")
    parser.add_argument("--min-slide-vol", type=int, default=0, help="Minimum volume during slide")
    
    parser.add_argument("--start-time", type=parse_time, default="09:30", help="Filter start time (HH:MM)")
    parser.add_argument("--end-time", type=parse_time, default="16:00", help="Filter end time (HH:MM)")
    
    parser.add_argument("--days", nargs="+", default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], 
                        help="List of days to include (e.g. Monday Tuesday)")
    
    parser.add_argument("--file", default="spy_data.parquet", help="Path to parquet file")
    
    args = parser.parse_args()
    
    print(f"Loading data from {args.file}...")
    try:
        df = load_data_uncached(args.file)
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Data Validation
    print("Validating data quality...")
    val = validate_dataset(df)
    issues_found = False
    
    if val['duplicates']['count'] > 0:
        print(f"⚠️  WARNING: Found {val['duplicates']['count']} duplicate timestamps.")
        
        # Yearly Summary
        summary = get_yearly_duplicate_summary(val['duplicates']['data'])
        print("   Duplicates per year:")
        for year, count in summary.items():
            print(f"   {year}: {count}")
            
        # Clean Duplicates
        print("   🧹 Cleaning duplicates (keeping first instance)...")
        original_len = len(df)
        df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
        print(f"   Removed {original_len - len(df)} rows. Analysis will run on {len(df)} unique rows.")
        issues_found = True
        
    if val['missing_values']['count'] > 0:
        print(f"⚠️  WARNING: Found {val['missing_values']['count']} rows with missing values.")
        print(val['missing_values']['summary'])
        issues_found = True
        
    if val['intraday_gaps']['count'] > 0:
        print(f"⚠️  WARNING: Found {val['intraday_gaps']['count']} intraday gaps (> 1 min).")
        print(val['intraday_gaps']['data'].head(3).to_string(index=False))
        issues_found = True
            
    if not issues_found:
        print("✅ Data validation passed.")

    print("Running analysis...")
    print(f"Parameters: Bump={args.bump_len}m ({args.bump_thresh} {args.bump_type}), Slide={args.slide_len}m ({args.slide_thresh} {args.slide_type})")
    
    results = find_bumps_and_slides(
        df,
        args.bump_len, args.bump_thresh, args.bump_type,
        args.slide_len, args.slide_thresh, args.slide_type,
        args.min_bump_vol, args.min_slide_vol,
        (args.start_time, args.end_time),
        args.days
    )
    
    print(f"\nFound {len(results)} matches.")
    if not results.empty:
        print("\nTop 5 Matches:")
        print(results[['date', 'bump_change', 'slide_change', 'bump_vol', 'slide_vol']].head().to_string())
        print("\n(Use the Streamlit app for full visualization)")

if __name__ == "__main__":
    main()
