import pandas as pd
import argparse
import sys
import matplotlib.pyplot as plt
from load_data import load_spy_data

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

def generate_trend_table(year, column_name, start_sample, end_sample, trend_direction, generate_chart=False):
    trend_direction = trend_direction.lower()
    if trend_direction not in ['increase', 'decrease']:
        print(f"Error: Trend direction must be 'increase' or 'decrease'. Got '{trend_direction}'.")
        return

    print(f"Analyzing Year: {year}, Column: '{column_name}', Sample Range: {start_sample}-{end_sample}, Trend: {trend_direction}...")
    
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

    values = year_df[column_name].values
    n_rows = len(values)
    
    # Header format updated to include new column
    # % Continuation = (Matches & Cont) / Matches * 100
    
    print(f"\n{'='*125}")
    print(f"   TREND ANALYSIS TABLE: {column_name} ({trend_direction.upper()}) - Year {year}")
    print(f"   Continuation Size: 1")
    print(f"{'='*125}")
    print(f"{'Sample Size':<12} | {'Total Samples':<14} | {'Matches':<12} | {'Matches & Cont':<14} | {'% Increasing':<12} | {'% Inc & Cont':<12} | {'% Continuation':<14}")
    print(f"{'-'*12}-+-{'-'*14}-+-{'-'*12}-+-{'-'*14}-+-{'-'*12}-+-{'-'*12}-+-{'-'*14}")

    results_data = []

    for sample_size in range(start_sample, end_sample + 1):
        total_samples = 0
        match_count = 0
        continued_count = 0
        
        # Iterate through chunks
        for i in range(0, n_rows, sample_size):
            chunk_end = i + sample_size
            if chunk_end > n_rows:
                break # Incomplete chunk at end
                
            chunk = values[i : chunk_end]
            
            # Check trend
            matches_trend = True
            for j in range(sample_size - 1):
                if trend_direction == 'increase':
                    if chunk[j] >= chunk[j+1]:
                        matches_trend = False
                        break
                else: # decrease
                    if chunk[j] <= chunk[j+1]:
                        matches_trend = False
                        break
            
            total_samples += 1
            
            if matches_trend:
                match_count += 1
                
                # Check continuation (next value)
                if chunk_end < n_rows:
                    next_val = values[chunk_end]
                    last_val = chunk[-1]
                    
                    if trend_direction == 'increase':
                        if last_val < next_val:
                            continued_count += 1
                    else: # decrease
                        if last_val > next_val:
                            continued_count += 1
        
        # Calculate percentages
        if total_samples > 0:
            pct_increasing = (match_count / total_samples * 100)
            pct_continued_total = (continued_count / total_samples * 100)
        else:
            pct_increasing = 0
            pct_continued_total = 0
            
        # Calculate % Continuation (Relative to matches)
        if match_count > 0:
            pct_continuation_relative = (continued_count / match_count * 100)
        else:
            pct_continuation_relative = 0
        
        print(f"{sample_size:<12} | {total_samples:<14} | {match_count:<12} | {continued_count:<14} | {pct_increasing:<11.2f}% | {pct_continued_total:<11.2f}% | {pct_continuation_relative:<13.2f}%")
        
        results_data.append({
            'sample_size': sample_size,
            'total_samples': total_samples,
            'match_count': match_count,
            'continued_count': continued_count,
            'pct_continuation_relative': pct_continuation_relative
        })

    if generate_chart and results_data:
        print("\nGenerating bar chart...")
        try:
            x = [r['sample_size'] for r in results_data]
            y = [r['pct_continuation_relative'] for r in results_data]
            
            plt.figure(figsize=(12, 8)) # Increased size for annotations
            plt.bar(x, y, color='lightgreen')
            plt.xlabel('Sample Size')
            plt.ylabel("% Continuation (Relative to Matches)")
            plt.title(f'Trend Continuation Probability by Sample Size\nYear: {year} (Total Rows: {n_rows}), Column: {column_name}, Trend: {trend_direction}')
            plt.xticks(x)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # Add annotations
            # We want to show Tot, Mat, Cont
            for i, r in enumerate(results_data):
                label = f"{y[i]:.1f}%\n\nTot: {r['total_samples']}\nMat: {r['match_count']}\nCont: {r['continued_count']}"
                plt.text(x[i], y[i] + 1, label, ha='center', va='bottom', fontsize=9)
            
            # Adjust y limit to fit text
            plt.ylim(0, max(y) * 1.3) # Add 30% headroom
            
            filename = f"trend_chart_{year}_{column_name}_{trend_direction}.png"
            plt.savefig(filename)
            print(f"Chart saved to '{filename}'")
            plt.close()
        except Exception as e:
            print(f"Error generating chart: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a trend analysis table for a range of sample sizes.")
    parser.add_argument("year", nargs="?", help="Year to analyze (e.g., 2010)")
    parser.add_argument("column", nargs="?", help="Column to check (e.g., 'open')")
    parser.add_argument("start_sample", nargs="?", help="Start sample size (e.g., 3)")
    parser.add_argument("end_sample", nargs="?", help="End sample size (e.g., 10)")
    parser.add_argument("trend", nargs="?", help="Trend direction ('increase' or 'decrease')")
    parser.add_argument("--chart", "-c", action="store_true", help="Generate a bar chart")
    
    args = parser.parse_args()
    
    year = args.year
    column = args.column
    start_sample = args.start_sample
    end_sample = args.end_sample
    trend = args.trend
    generate_chart = args.chart

    # Interactive prompts if args missing
    if not year:
        year = get_valid_int("Enter Year (e.g., 2010)")
    
    if not column:
        column = get_input("Enter Column Name (e.g., open)", "open")
        
    if not start_sample:
        start_sample = get_valid_int("Enter Start Sample Size (e.g., 3)", 3)
        
    if not end_sample:
        end_sample = get_valid_int("Enter End Sample Size (e.g., 10)", 10)
        
    if not trend:
        trend = get_input("Enter Trend Direction (increase/decrease)", "increase")
        
    if args.year is None: # Interactive mode
        chart_input = get_input("Generate Bar Chart? (y/n)", "n")
        if chart_input.lower().startswith('y'):
            generate_chart = True

    # Normalize trend input
    if trend.lower().startswith('inc'):
        trend = 'increase'
    elif trend.lower().startswith('dec'):
        trend = 'decrease'

    # Ensure start <= end
    if int(start_sample) > int(end_sample):
        print("Warning: Start sample size is greater than end sample size. Swapping.")
        start_sample, end_sample = end_sample, start_sample

    generate_trend_table(year, column, int(start_sample), int(end_sample), trend, generate_chart)
