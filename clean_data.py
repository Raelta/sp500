import pandas as pd
from src.data_loader import load_data_uncached
from src.data_validator import get_yearly_duplicate_summary

def main():
    input_file = "spy_data.parquet"
    output_file = "spy_data_clean.parquet"
    
    print(f"Loading data from {input_file}...")
    try:
        df = load_data_uncached(input_file)
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    initial_count = len(df)
    print(f"Initial row count: {initial_count}")
    
    # Identify duplicates
    if 'date' not in df.columns:
        print("Error: 'date' column missing from data.")
        return

    dups_mask = df.duplicated('date', keep='first')
    dups_df = df[dups_mask].copy()
    duplicates_count = len(dups_df)
    
    if duplicates_count == 0:
        print("No duplicates found. Data is already clean.")
        # We might still want to save it to the new filename for consistency if the user expects it
        # But technically no change needed.
        # Let's save it anyway so the user has the "clean" file.
    else:
        print(f"\nFound {duplicates_count} duplicate rows.")
        
        # Yearly summary of duplicates
        yearly_summary = get_yearly_duplicate_summary(dups_df)
        print("\nDuplicates removed by year:")
        for year, count in yearly_summary.items():
            print(f"  {year}: {count}")
            
        # Remove duplicates
        df_clean = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
        final_count = len(df_clean)
        
        print(f"\nCleaning complete.")
        print(f"Final row count: {final_count}")
        print(f"Removed {initial_count - final_count} rows.")
        
        df = df_clean

    print(f"\nSaving clean data to {output_file}...")
    df.to_parquet(output_file)
    print("Done.")

if __name__ == "__main__":
    main()
