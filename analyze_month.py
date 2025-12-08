import pandas as pd
import argparse
import sys
from load_data import load_spy_data

def parse_month(month_input):
    """
    Parses a month input (string or int) and returns the month number (1-12).
    Returns None if invalid.
    """
    month_input = str(month_input).strip().lower()
    
    # Map of name/abbr to number
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    # Check if it's a number
    if month_input.isdigit():
        val = int(month_input)
        if 1 <= val <= 12:
            return val
    
    # Check if it's a name
    return months.get(month_input)

def get_month_name(month_num):
    import calendar
    return calendar.month_name[month_num]

def analyze_month(target_month=None):
    # Get month from user if not provided
    if target_month is None:
        user_input = input("Enter the month you want to analyze (name or number): ")
        target_month = parse_month(user_input)
        if target_month is None:
            print(f"Error: '{user_input}' is not a valid month.")
            return

    month_name = get_month_name(target_month)
    print(f"\nAnalyzing data for: {month_name}...")

    # Load data
    df = load_spy_data()
    if df is None:
        print("Failed to load data.")
        return

    # Filter for the specific month
    # We use .dt.month accessor on the datetime column
    month_mask = df['date'].dt.month == target_month
    month_df = df[month_mask]

    if month_df.empty:
        print(f"No data found for {month_name}.")
        return

    # Group by Year and calculate average Open
    # We use .dt.year for grouping
    yearly_avg = month_df.groupby(month_df['date'].dt.year)['open'].mean()

    # Display results
    print(f"\n{'='*40}")
    print(f"   AVERAGE OPEN PRICE FOR {month_name.upper()}")
    print(f"{'='*40}")
    print(f"{'Year':<10} | {'Average Open':<15}")
    print(f"{'-'*10}-+-{'-'*15}")
    
    for year, avg_price in yearly_avg.items():
        print(f"{year:<10} | {avg_price:.2f}")

    print(f"{'='*40}")
    
    # Overall average for that month across all years
    overall_avg = month_df['open'].mean()
    print(f"Overall Average for {month_name} (2008-2021): {overall_avg:.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze SPY data for a specific month.")
    parser.add_argument("month", nargs="?", help="The month to analyze (e.g., 'January' or '1')")
    
    args = parser.parse_args()
    
    if args.month:
        month_num = parse_month(args.month)
        if month_num:
            analyze_month(month_num)
        else:
            print(f"Error: '{args.month}' is not a valid month.")
    else:
        analyze_month()
