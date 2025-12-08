import pandas as pd
import argparse
import sys
from load_data import load_spy_data

def check_trend(year, column_name, sample_value, trend_direction, continuation_size):
    trend_direction = trend_direction.lower()
    if trend_direction not in ['increase', 'decrease']:
        print(f"Error: Trend direction must be 'increase' or 'decrease'. Got '{trend_direction}'.")
        return

    print(f"Analyzing Year: {year}, Column: '{column_name}', Sample Size: {sample_value}, Trend: {trend_direction}, Continuation Samples: {continuation_size}...")
    
    # Load data
    df = load_spy_data()
    if df is None:
        print("Failed to load data.")
        return

    # Filter for the specific year
    try:
        year_mask = df['date'].dt.year == int(year)
    except ValueError:
        print(f"Error: Year '{year}' must be a valid number.")
        return
        
    year_df = df[year_mask].copy()

    if year_df.empty:
        print(f"No data found for year {year}.")
        return

    if column_name not in year_df.columns:
        print(f"Column '{column_name}' not found in dataset.")
        return

    # Create chunks
    total_rows = len(year_df)
    results = []

    # Reset index to make chunking easier by integer position
    year_df = year_df.reset_index(drop=True)

    try:
        sample_size = int(sample_value)
        if sample_size <= 0:
            raise ValueError
        
        cont_size = int(continuation_size)
        if cont_size <= 0:
            raise ValueError("Continuation size must be positive")
            
    except ValueError as e:
        print(f"Error: {e}")
        return

    print(f"\nProcessing {total_rows} rows in chunks of {sample_size}...")
    
    for i in range(0, total_rows, sample_size):
        chunk = year_df.iloc[i : i + sample_size]
        
        # We need at least 2 values to check for trend
        if len(chunk) < 2:
            continue
            
        start_date = chunk['date'].iloc[0]
        end_date = chunk['date'].iloc[-1]
        
        values = chunk[column_name].values
        
        # Check trend within the sample
        if trend_direction == 'increase':
            match_trend = all(values[j] < values[j+1] for j in range(len(values)-1))
        else:
            match_trend = all(values[j] > values[j+1] for j in range(len(values)-1))
            
        # Check if trend continues over next N samples
        continues_trend = False
        next_start_idx = i + sample_size
        next_end_idx = next_start_idx + cont_size
        
        if next_end_idx <= len(year_df):
            # Get the continuation window
            next_chunk = year_df.iloc[next_start_idx : next_end_idx]
            next_values = next_chunk[column_name].values
            
            # Combine last value of sample with next values to ensure continuity
            combined_sequence = [values[-1]] + list(next_values)
            
            if trend_direction == 'increase':
                # Check if combined sequence is strictly increasing
                continues_trend = all(combined_sequence[j] < combined_sequence[j+1] for j in range(len(combined_sequence)-1))
            else:
                # Check if strictly decreasing
                continues_trend = all(combined_sequence[j] > combined_sequence[j+1] for j in range(len(combined_sequence)-1))
        
        results.append({
            'start_date': start_date,
            'end_date': end_date,
            'matches_trend': match_trend,
            'continues_trend': continues_trend,
            'trend_type': trend_direction,
            'start_val': values[0],
            'end_val': values[-1]
        })

    # Create results dataframe for display
    results_df = pd.DataFrame(results)

    if results_df.empty:
        print("No results generated (dataset might be smaller than sample size).")
        return

    # Save to CSV
    output_filename = f"trend_analysis_{year}_{column_name}_{sample_size}_{trend_direction}_cont{cont_size}.csv"
    results_df.to_csv(output_filename, index=False)
    print(f"\nFull results saved to '{output_filename}'")

    # Display Output
    print(f"\n{'='*95}")
    print(f"   TREND ANALYSIS: {column_name} ({trend_direction.upper()}) - Year {year}")
    print(f"{'='*95}")
    print(f"{'Start Date':<25} | {'End Date':<25} | {'Matches?':<10} | {'Continues?':<10}")
    print(f"{'-'*25}-+-{'-'*25}-+-{'-'*10}-+-{'-'*10}")

    # Count true matches
    true_count = results_df['matches_trend'].sum()
    total_count = len(results_df)
    
    # Count how many matched AND continued
    continued_count = len(results_df[results_df['matches_trend'] & results_df['continues_trend']])
    
    print(f"\nTotal Windows Checked: {total_count}")
    print(f"Windows Matching Trend: {true_count} ({(true_count/total_count)*100:.2f}%)")
    if true_count > 0:
        print(f"Of matches, continued for {cont_size} samples: {continued_count} ({(continued_count/true_count)*100:.2f}%)")
    
    if true_count > 0:
        print(f"\nShowing first 10 windows where trend is {trend_direction.upper()}:")
        print(f"{'Start Date':<25} | {'End Date':<25} | {'Matches?':<10} | {'Continues?':<10}")
        print(f"{'-'*25}-+-{'-'*25}-+-{'-'*10}-+-{'-'*10}")
        
        matching_rows = results_df[results_df['matches_trend']].head(10)
        for _, row in matching_rows.iterrows():
            print(f"{str(row['start_date']):<25} | {str(row['end_date']):<25} | {str(row['matches_trend']):<10} | {str(row['continues_trend']):<10}")
    else:
        print(f"\nNo windows found with strictly {trend_direction} trend.")

def get_input(prompt, default=None):
    if default:
        user_input = input(f"{prompt} [{default}]: ")
        return user_input if user_input else default
    return input(f"{prompt}: ")

def get_valid_int(prompt, default=None):
    while True:
        val = get_input(prompt, default)
        try:
            return int(val)
        except ValueError:
            print("Invalid input. Please enter a valid number.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check for increasing/decreasing trends in data chunks.")
    parser.add_argument("year", nargs="?", help="Year to analyze (e.g., 2010)")
    parser.add_argument("column", nargs="?", help="Column to check (e.g., 'open')")
    parser.add_argument("sample", nargs="?", help="Sample size (number of rows per window)")
    parser.add_argument("trend", nargs="?", help="Trend direction ('increase' or 'decrease')")
    parser.add_argument("continuation", nargs="?", help="Number of samples to check for continuation")
    
    args = parser.parse_args()
    
    year = args.year
    column = args.column
    sample = args.sample
    trend = args.trend
    cont = args.continuation

    # Interactive prompts if args missing
    if not year:
        year = get_valid_int("Enter Year (e.g., 2010)")
    
    if not column:
        column = get_input("Enter Column Name (e.g., open)", "open")
        
    if not sample:
        sample = get_valid_int("Enter Sample Size (e.g., 5)", 5)
        
    if not trend:
        trend = get_input("Enter Trend Direction (increase/decrease)", "increase")
        
    if not cont:
        cont = get_valid_int("Enter Continuation Samples (e.g., 1)", 1)

    # Normalize trend input
    if trend.lower().startswith('inc'):
        trend = 'increase'
    elif trend.lower().startswith('dec'):
        trend = 'decrease'

    check_trend(year, column, sample, trend, cont)
