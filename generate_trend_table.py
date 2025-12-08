import pandas as pd
import argparse
import sys
import plotly.graph_objects as go
import webbrowser
import os
from load_data import load_spy_data

def get_input(prompt, default=None):
    if default:
        user_input = input(f"{prompt} [{default}]: ")
        return user_input if user_input else default
    return input(f"{prompt}: ")

def get_valid_year_input(prompt, default=None):
    while True:
        val = get_input(prompt, default)
        # Check for range format "YYYY-YYYY"
        if '-' in val:
            parts = val.split('-')
            if len(parts) == 2:
                try:
                    start = int(parts[0])
                    end = int(parts[1])
                    if start <= end:
                        return val
                    else:
                        print("Start year must be less than or equal to end year.")
                except ValueError:
                    print("Invalid range format. Use YYYY-YYYY.")
        else:
            try:
                # Check if single year
                int(val)
                return val
            except ValueError:
                print("Invalid input. Please enter a valid year or year range (YYYY-YYYY).")

def get_valid_int(prompt, default=None):
    while True:
        val = get_input(prompt, default)
        try:
            return int(val)
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def parse_years(year_input):
    """Parses year input string into a list of integer years."""
    if '-' in str(year_input):
        parts = str(year_input).split('-')
        start = int(parts[0])
        end = int(parts[1])
        return list(range(start, end + 1))
    else:
        return [int(year_input)]

def generate_trend_table(year_input, column_name, start_sample, end_sample, trend_direction, generate_chart=False):
    trend_direction = trend_direction.lower()
    if trend_direction not in ['increase', 'decrease']:
        print(f"Error: Trend direction must be 'increase' or 'decrease'. Got '{trend_direction}'.")
        return

    years = parse_years(year_input)
    print(f"Analyzing Years: {years}, Column: '{column_name}', Sample Range: {start_sample}-{end_sample}, Trend: {trend_direction}...")
    
    # Load data ONCE
    df = load_spy_data()
    if df is None:
        print("Failed to load data.")
        return
    
    if column_name not in df.columns:
        print(f"Column '{column_name}' not found in dataset.")
        return

    all_years_data = []

    for year in years:
        # Filter for the specific year
        try:
            year_mask = df['date'].dt.year == int(year)
            year_df = df[year_mask].copy()
        except Exception as e:
            print(f"Error filtering for year {year}: {e}")
            continue

        if year_df.empty:
            print(f"No data found for year {year}.")
            continue

        values = year_df[column_name].values
        n_rows = len(values)
        
        print(f"\n{'='*125}")
        print(f"   TREND ANALYSIS TABLE: {column_name} ({trend_direction.upper()}) - Year {year}")
        print(f"   Continuation Size: 1")
        print(f"{'='*125}")
        print(f"{'Sample Size':<12} | {'Total Samples':<14} | {'Matches':<12} | {'Matches & Cont':<14} | {'% Increasing':<12} | {'% Inc & Cont':<12} | {'% Continuation':<14}")
        print(f"{'-'*12}-+-{'-'*14}-+-{'-'*12}-+-{'-'*14}-+-{'-'*12}-+-{'-'*12}-+-{'-'*14}")

        for sample_size in range(start_sample, end_sample + 1):
            total_samples = 0
            match_count = 0
            continued_count = 0
            
            # Iterate through chunks
            for i in range(0, n_rows, sample_size):
                chunk_end = i + sample_size
                if chunk_end > n_rows:
                    break 
                    
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
                    
                    # Check continuation
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
            
            # Round to 2 decimal places for display and storage
            pct_increasing = round(pct_increasing, 2)
            pct_continued_total = round(pct_continued_total, 2)
            pct_continuation_relative = round(pct_continuation_relative, 2)

            print(f"{sample_size:<12} | {total_samples:<14} | {match_count:<12} | {continued_count:<14} | {pct_increasing:<11.2f}% | {pct_continued_total:<11.2f}% | {pct_continuation_relative:<13.2f}%")
            
            all_years_data.append({
                'year': year,
                'total_rows': n_rows,
                'sample_size': sample_size,
                'total_samples': total_samples,
                'matches': match_count,
                'continued': continued_count,
                'pct_inc_and_cont': pct_continued_total,
                'pct_continuation': pct_continuation_relative
            })

    if generate_chart and all_years_data:
        print("\nGenerating interactive multi-year chart...")
        try:
            df_chart = pd.DataFrame(all_years_data)
            
            # Create figure
            fig = go.Figure()
            
            unique_years = sorted(df_chart['year'].unique())
            
            for i, year in enumerate(unique_years):
                year_data = df_chart[df_chart['year'] == year]
                
                # Construct hover text manually
                # Added % Inc & Cont to tooltip
                hover_text = [
                    f"Sample Size: {ss}<br>% Continuation: {pct:.2f}%<br>% Inc & Cont: {pct_ic:.2f}%"
                    for ss, pct, pct_ic in zip(year_data['sample_size'], year_data['pct_continuation'], year_data['pct_inc_and_cont'])
                ]
                
                # Construct bar text (annotation on top)
                bar_text = [
                    f"Tot: {t}<br>Mat: {m}<br>Cont: {c}"
                    for t, m, c in zip(year_data['total_samples'], year_data['matches'], year_data['continued'])
                ]
                
                visible = (i == 0) # Only first year visible initially
                
                fig.add_trace(go.Bar(
                    x=year_data['sample_size'],
                    y=year_data['pct_continuation'],
                    name=str(year),
                    visible=visible,
                    marker_color='#2c3e50', # Professional dark blue/grey
                    text=bar_text,
                    textposition='outside', # Place text above bar
                    hoverinfo='text',
                    hovertext=hover_text
                ))

            # Create dropdown menu
            buttons = []
            for i, year in enumerate(unique_years):
                # Create visibility list: [False, False, ..., True, ..., False]
                visibility = [False] * len(unique_years)
                visibility[i] = True
                
                n_rows = df_chart[df_chart['year'] == year]['total_rows'].iloc[0]
                
                # Use "title.text" to ensure title is updated correctly without removing it
                buttons.append(dict(
                    label=str(year),
                    method="update",
                    args=[{"visible": visibility},
                          {"title.text": f"Trend Continuation Probability ({year})<br>Total Rows: {n_rows} | Column: {column_name} | Trend: {trend_direction}"}]
                ))
            
            # Initial Title
            initial_year = unique_years[0]
            initial_rows = df_chart[df_chart['year']==initial_year]['total_rows'].iloc[0]
            initial_title = f"Trend Continuation Probability ({initial_year})<br>Total Rows: {initial_rows} | Column: {column_name} | Trend: {trend_direction}"

            fig.update_layout(
                updatemenus=[dict(
                    active=0,
                    buttons=buttons,
                    x=1.0,         # Right justified
                    xanchor='right',
                    y=1.15
                )],
                title=dict(text=initial_title),
                xaxis_title="Sample Size",
                yaxis_title="% Continuation (Relative to Matches)",
                yaxis=dict(range=[0, df_chart['pct_continuation'].max() * 1.3]), # Headroom for text
                xaxis=dict(type='category'),
                template="plotly_white"
            )

            filename = f"trend_chart_multiyear_{column_name}_{trend_direction}.html"
            fig.write_html(filename)
            print(f"Interactive chart saved to '{filename}'")
            
            try:
                webbrowser.open('file://' + os.path.realpath(filename))
                print("Opening chart in browser...")
            except:
                print("Could not automatically open browser.")
                
        except Exception as e:
            print(f"Error generating chart: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a trend analysis table for a range of sample sizes.")
    parser.add_argument("year", nargs="?", help="Year or Year Range (e.g., 2010 or 2010-2015)")
    parser.add_argument("column", nargs="?", help="Column to check (e.g., 'open')")
    parser.add_argument("start_sample", nargs="?", help="Start sample size (e.g., 3)")
    parser.add_argument("end_sample", nargs="?", help="End sample size (e.g., 10)")
    parser.add_argument("trend", nargs="?", help="Trend direction ('increase' or 'decrease')")
    parser.add_argument("--chart", "-c", action="store_true", help="Generate a bar chart")
    
    args = parser.parse_args()
    
    year_input = args.year
    column = args.column
    start_sample = args.start_sample
    end_sample = args.end_sample
    trend = args.trend
    generate_chart = args.chart

    # Interactive prompts
    if not year_input:
        year_input = get_valid_year_input("Enter Year or Range (e.g., 2010 or 2010-2012)")
    
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

    if trend.lower().startswith('inc'):
        trend = 'increase'
    elif trend.lower().startswith('dec'):
        trend = 'decrease'

    if int(start_sample) > int(end_sample):
        print("Warning: Start sample size is greater than end sample size. Swapping.")
        start_sample, end_sample = end_sample, start_sample

    generate_trend_table(year_input, column, int(start_sample), int(end_sample), trend, generate_chart)
