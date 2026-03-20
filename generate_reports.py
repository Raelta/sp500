import subprocess
import pandas as pd
import os

events = [
    {
        "id": "flash_crash",
        "title": "The 2010 Flash Crash (Microsecond Reversals)",
        "command": [
            "python", "goal_seek_cli.py", "--start-year", "2010", "--end-year", "2010",
            "--bump-len-start", "5", "--bump-len-end", "40", "--bump-len-step", "5",
            "--slide-len-start", "5", "--slide-len-end", "40", "--slide-len-step", "5",
            "--min-bump-threshold", "-4.0", "--min-slide-threshold", "4.0", "--detailed",
            "--output", "flash_crash_test.csv"
        ],
        "csv": "flash_crash_test.csv",
        "description": "On May 6, 2010, the S&P 500 collapsed and rebounded massively. The fingerprint is extreme magnitude moves compressed into an incredibly short timeframe. (Looking for Drop -> Rebound)",
        "params": "Length: 5-40 mins, Bump: <= -4.0%, Slide: >= +4.0%"
    },
    {
        "id": "2008_crisis",
        "title": "The 2008 Financial Crisis (Extreme Sustained Volatility)",
        "command": [
            "python", "goal_seek_cli.py", "--start-year", "2008", "--end-year", "2008",
            "--bump-len-start", "10", "--bump-len-end", "60", "--bump-len-step", "10",
            "--slide-len-start", "10", "--slide-len-end", "60", "--slide-len-step", "10",
            "--min-bump-threshold", "-4.0", "--min-slide-threshold", "4.0", "--detailed",
            "--output", "2008_crisis_test.csv"
        ],
        "csv": "2008_crisis_test.csv",
        "description": "The fall of 2008 saw historic VIX levels, characterized by violent intraday selloffs immediately followed by massive short-covering rallies. (Looking for Drop -> Rebound)",
        "params": "Length: 10-60 mins, Bump: <= -4.0%, Slide: >= +4.0%"
    },
    {
        "id": "covid_crash",
        "title": "COVID-19 Market Crash (Intraday Panic)",
        "command": [
            "python", "goal_seek_cli.py", "--start-year", "2020", "--end-year", "2020",
            "--bump-len-start", "10", "--bump-len-end", "60", "--bump-len-step", "10",
            "--slide-len-start", "10", "--slide-len-end", "60", "--slide-len-step", "10",
            "--min-bump-threshold", "-3.0", "--min-slide-threshold", "3.0", "--detailed",
            "--output", "covid_crash_test.csv"
        ],
        "csv": "covid_crash_test.csv",
        "description": "March 2020 featured extreme intraday moves. We look for massive intraday selloffs followed by continued violent selling or massive short-covering. (Looking for Drop -> Rebound)",
        "params": "Length: 10-60 mins, Bump: <= -3.0%, Slide: >= +3.0%"
    },
    {
        "id": "fomc_whipsaw",
        "title": "2022 Fed Rate Hike Cycle (The FOMC 'Whipsaw')",
        "command": [
            "python", "goal_seek_cli.py", "--start-year", "2022", "--end-year", "2022",
            "--bump-len-start", "15", "--bump-len-end", "45", "--bump-len-step", "15",
            "--slide-len-start", "15", "--slide-len-end", "45", "--slide-len-step", "15",
            "--min-bump-threshold", "1.5", "--min-slide-threshold", "-1.5", "--detailed",
            "--output", "fomc_whipsaw_test.csv"
        ],
        "csv": "fomc_whipsaw_test.csv",
        "description": "Throughout 2022, FOMC meetings caused massive intraday volatility. The classic FOMC fingerprint is a knee-jerk reaction at 2:00 PM EST, followed by a massive reversal. (Looking for Rally -> Drop)",
        "params": "Length: 15-45 mins, Bump: >= +1.5%, Slide: <= -1.5%"
    }
]

def generate_ascii_chart(bump_dir, slide_dir, bump_len, slide_len, bump_mag, slide_mag):
    # Determine scale
    max_len = max(bump_len, slide_len, 1)
    b_width = max(2, int((bump_len / max_len) * 10))
    s_width = max(2, int((slide_len / max_len) * 10))
    
    b_char = "↗" if bump_dir == "Up" else "↘"
    s_char = "↗" if slide_dir == "Up" else "↘"
    
    b_line = (b_char * b_width) + f" (Bump: {bump_dir} ~{bump_mag:.1f} pts, {bump_len}m)"
    s_line = (" " * b_width) + (s_char * s_width) + f" (Slide: {slide_dir} ~{slide_mag:.1f} pts, {slide_len}m)"
    
    return f"```text\n{b_line}\n{s_line}\n```"

def process_event(event):
    print(f"Running Goal Seek for {event['title']}...")
    try:
        subprocess.run(event['command'], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command for {event['id']}: {e.stderr}")
        return
    
    if not os.path.exists(event['csv']):
        print(f"Output CSV not found for {event['id']}")
        return
        
    df = pd.read_csv(event['csv'])
    
    # We want to format the best results
    results_md = ""
    best_chart = ""
    
    if len(df) > 0 and 'best_hit_date' in df.columns:
        # Check if it's summary or detailed based on 'best_hit_date' presence
        if 'slide_change' in df.columns:
            # Detailed mode
            df['abs_slide'] = df['slide_change'].abs()
            top_hits = df.sort_values(by='abs_slide', ascending=False).head(5)
            
            best_hit = top_hits.iloc[0]
            bump_dir = "Up" if best_hit['bump_change'] > 0 else "Down"
            slide_dir = "Up" if best_hit['slide_change'] > 0 else "Down"
            best_chart = generate_ascii_chart(bump_dir, slide_dir, int(best_hit['bump_len']), int(best_hit['slide_len']), abs(best_hit['bump_change']), abs(best_hit['slide_change']))
            
            results_md += "### Top 5 Matches Found\n\n"
            results_md += "| Date | Bump Len | Slide Len | Bump Change | Slide Change |\n"
            results_md += "|------|----------|-----------|-------------|--------------|\n"
            for _, row in top_hits.iterrows():
                results_md += f"| {row['best_hit_date']} | {row['bump_len']}m | {row['slide_len']}m | {row['bump_change']:.2f} | {row['slide_change']:.2f} |\n"
        else:
            # Summary mode fallback
            df['abs_best_slide'] = 0 # Not available in summary usually, but we ran with --detailed
            results_md += "No detailed rows found.\n"
    else:
        results_md = "No results met the stringent criteria."
        best_chart = "No data to visualize."

    md_content = f"""# {event['title']}

## Event Description
{event['description']}

## Goal Seek Parameters Used
- **{event['params']}**
- Command executed: `{' '.join(event['command'])}`

## Visualizing the Best Match
{best_chart}

## Goal Seek Results
{results_md}

## Analysis
The Goal Seek tool was configured to look for the distinct fingerprint of this event. Reviewing the timestamps above should confirm if the tool successfully identified the anomalous market behavior associated with the event.
"""

    report_filename = f"report_{event['id']}.md"
    with open(report_filename, "w") as f:
        f.write(md_content)
    print(f"Saved {report_filename}")

for event in events:
    process_event(event)
