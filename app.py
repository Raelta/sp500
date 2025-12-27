import streamlit as st
import pandas as pd
import time as time_module
from src.data_loader import load_data_cached
from src.analyzer import find_bumps_and_slides
from src.visualizer import plot_pattern
from src.data_validator import validate_dataset, get_yearly_duplicate_summary
from src.news_provider import get_google_news_url
from src.ui_utils import render_checkbox_dropdown, get_app_version
from datetime import time
import argparse
import sys

# Parse CLI Args to Override Defaults
def get_cli_args():
    parser = argparse.ArgumentParser(description="SP500 Bump & Slide App")
    # Use ignore_unknown to allow streamlit args if any leak
    parser.add_argument("-bl", "--bump-len", type=int, help="Bump length (min)")
    parser.add_argument("-bt", "--bump-thresh", type=float, help="Bump threshold")
    parser.add_argument("--bump-type", choices=["percent", "value"], help="Bump threshold type")
    
    parser.add_argument("-sl", "--slide-len", type=int, help="Slide length (min)")
    parser.add_argument("-st", "--slide-thresh", type=float, help="Slide threshold")
    parser.add_argument("--slide-type", choices=["percent", "value"], help="Slide threshold type")
    
    parser.add_argument("--min-bump-vol", type=int, help="Min Bump Volume")
    parser.add_argument("--min-slide-vol", type=int, help="Min Slide Volume")
    
    # We use parse_known_args to avoid issues with Streamlit's own flags
    args, _ = parser.parse_known_args()
    return args

cli_args = get_cli_args()

# Performance Logging Utility
def log_perf(label, start_time):
    duration = time_module.time() - start_time
    msg = f"[PERF] {label}: {duration:.4f}s"
    print(msg)
    if 'perf_logs' not in st.session_state:
        st.session_state.perf_logs = []
    st.session_state.perf_logs.append(msg)
    return time_module.time() # Return new start time

st.set_page_config(page_title="SP500 Bump & Slide", layout="wide")
st.title("SP500 Bump & Slide Analysis")

# Clear logs on rerun if needed, or keep history. 
# For debugging single interaction, clearing is better.
if 'perf_logs' not in st.session_state:
    st.session_state.perf_logs = []
else:
    # Reset logs for this run
    st.session_state.perf_logs = []

t0 = time_module.time()
print(f"--- RERUN STARTED at {t0} ---")

# Load Data
# Load Data
with st.spinner("Loading data..."):
    t_load_start = time_module.time()
    df, val_report = load_data_cached("spy_data.parquet")
    t0 = log_perf("Data Load (Cached)", t_load_start)

st.success(f"Loaded {len(df)} rows.")

# Data Quality Check
# val_report is already computed and cached
has_issues = (val_report['duplicates']['count'] > 0) or \
             (len(val_report['missing_values']) > 0) or \
             (val_report['intraday_gaps']['count'] > 0)

if has_issues:
    with st.expander("⚠️ Data Quality Issues Detected", expanded=False):
        tab1, tab2, tab3, tab4 = st.tabs(["Duplicates", "Missing Values", "Intraday Gaps", "Missing Minutes"])
        
        with tab1:
            count = val_report['duplicates']['count']
            if count > 0:
                st.error(f"Found {count} duplicate timestamps.")
                yearly_summary = get_yearly_duplicate_summary(val_report['duplicates']['data'])
                st.write("Duplicates per Year:")
                st.bar_chart(yearly_summary)
            else:
                st.success("No duplicates found.")
                
        with tab2:
            count = val_report['missing_values']['count']
            if count > 0:
                st.error(f"Found {count} rows with missing values.")
                st.write("Summary:", val_report['missing_values']['summary'])
                st.dataframe(val_report['missing_values']['data'], width='stretch')
                st.download_button("Download Missing Values CSV", 
                                   val_report['missing_values']['data'].to_csv(index=False), 
                                   "missing_values.csv", 
                                   "text/csv")
            else:
                st.success("No missing values found.")
                
        with tab3:
            count = val_report['intraday_gaps']['count']
            if count > 0:
                st.warning(f"Found {count} intraday gaps.")
                st.dataframe(val_report['intraday_gaps']['data'], width='stretch')
                st.download_button("Download Gaps CSV", 
                                   val_report['intraday_gaps']['data'].to_csv(index=False), 
                                   "intraday_gaps.csv", 
                                   "text/csv")
            else:
                st.success("No intraday gaps found.")

        with tab4:
            # Check safely if missing_minutes exists (in case of cached old data, though app reload fixes this)
            if 'missing_minutes' in val_report:
                mm = val_report['missing_minutes']
                if mm['count'] > 0:
                    st.warning(f"Found {mm['count']} missing minute intervals across {mm['days_affected']} trading days.")
                    st.caption("Trading day expected to have 391 minutes (09:30 - 16:00).")
                    
                    st.dataframe(mm['data'], width='stretch')
                    
                    st.download_button("Download Missing Minutes Report", 
                                       mm['data'].to_csv(index=False), 
                                       "missing_minutes_report.csv", 
                                       "text/csv")
                else:
                    st.success("All trading days have complete data (391 minutes).")
            else:
                st.info("Validation report outdated. Please clear cache to see missing minutes.")

# Auto-clean Duplicates
if val_report['duplicates']['count'] > 0:
    original_count = len(df)
    df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
    st.info(f"🧹 Auto-cleaned data: Removed {original_count - len(df)} duplicate rows. Analysis will proceed on {len(df)} unique rows.")

# Initialize Session State
if 'results' not in st.session_state:
    st.session_state.results = None
if 'stats' not in st.session_state:
    st.session_state.stats = None

# Sidebar: Global Controls
if st.sidebar.button("🔄 Reload Data", help="Clear cache and force reload from disk"):
    st.cache_data.clear()
    # Clear session state to ensure fresh analysis
    for key in ['results', 'selected_match_idx', 'preselected_done']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# Sidebar Configuration (Types outside form for interactivity)
st.sidebar.header("Configuration")

# CLI Overrides for Types
bt_idx = 0
if cli_args.bump_type:
    bt_idx = 0 if cli_args.bump_type == "percent" else 1

st_idx = 0
if cli_args.slide_type:
    st_idx = 0 if cli_args.slide_type == "percent" else 1

bump_thresh_type = st.sidebar.radio("Bump Threshold Type", ["percent", "value"], index=bt_idx, help="Choose 'percent' for relative change (%) or 'value' for absolute price difference.")
slide_thresh_type = st.sidebar.radio("Slide Threshold Type", ["percent", "value"], index=st_idx, help="Choose 'percent' for relative change (%) or 'value' for absolute price difference.")

# Calculate defaults
if bump_thresh_type == "percent":
    b_val, b_step = 0.34, 0.01
    b_label = "Bump Threshold (%)"
    b_help = "Minimum percentage change required (e.g., 0.05 means 0.05%)."
else:
    b_val, b_step = 0.50, 0.05
    b_label = "Bump Threshold (Price Difference)"
    b_help = "Minimum price change required in dollars (e.g., 0.50 means 50 cents)."

# CLI Override for Bump Threshold
if cli_args.bump_thresh is not None:
    b_val = cli_args.bump_thresh

if slide_thresh_type == "percent":
    s_val, s_step = 0.34, 0.01
    s_label = "Slide Threshold (%)"
    s_help = "Minimum percentage change required during the slide (e.g., 0.05 means 0.05%)."
else:
    s_val, s_step = 0.50, 0.05
    s_label = "Slide Threshold (Price Difference)"
    s_help = "Minimum price change required during the slide in dollars."

# CLI Override for Slide Threshold
if cli_args.slide_thresh is not None:
    s_val = cli_args.slide_thresh

# Sidebar Configuration (Reactive - No Form)
st.sidebar.header("Bump Parameters")

# CLI Override for Bump Length
b_len_default = cli_args.bump_len if cli_args.bump_len is not None else 5
bump_len = st.sidebar.slider("Bump Length (min)", 3, 20, b_len_default, help="Duration of the initial trend window in minutes.")
bump_threshold = st.sidebar.number_input(b_label, min_value=0.0, value=float(b_val), step=b_step, format="%.2f", key=f"bump_th_{bump_thresh_type}", help=b_help)

st.sidebar.header("Slide Parameters")

# CLI Override for Slide Length
s_len_default = cli_args.slide_len if cli_args.slide_len is not None else 3
slide_len = st.sidebar.slider("Slide Length (min)", 1, 20, s_len_default, help="Duration of the subsequent reaction window in minutes.")
slide_threshold = st.sidebar.number_input(s_label, min_value=0.0, value=float(s_val), step=s_step, format="%.2f", key=f"slide_th_{slide_thresh_type}", help=s_help)

st.sidebar.header("Filters")

# CLI Override for Filters
mbv_default = cli_args.min_bump_vol if cli_args.min_bump_vol is not None else 0
msv_default = cli_args.min_slide_vol if cli_args.min_slide_vol is not None else 0

min_bump_vol = st.sidebar.number_input("Min Bump Volume", min_value=0, value=mbv_default, step=1000, help="Minimum total volume traded during the Bump period.")
min_slide_vol = st.sidebar.number_input("Min Slide Volume", min_value=0, value=msv_default, step=1000, help="Minimum total volume traded during the Slide period.")

st.sidebar.subheader("Time of Day (Bump Start)")
time_start = st.sidebar.time_input("Start Time", time(9, 30), help="Only include patterns starting after this time.")
time_end = st.sidebar.time_input("End Time", time(16, 0), help="Only include patterns starting before this time.")

st.sidebar.subheader("Date Filters")

# Year Selection (Excel-style)
all_years = sorted(df['date'].dt.year.unique())
# Use sidebar context for the custom component
with st.sidebar:
    selected_years = render_checkbox_dropdown("Years", all_years, "filter_year")
    
    # Day Selection (Excel-style)
    days_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    days = render_checkbox_dropdown("Days of Week", days_options, "filter_day")

st.sidebar.subheader("App Layout")
layout_order = st.sidebar.radio("View Order", ["Table Top", "Chart Top"], index=0, horizontal=True)

# Show Debug Logs in Sidebar
with st.sidebar.expander("Debug Profiling", expanded=False):
    if 'perf_logs' in st.session_state:
        st.code("\n".join(st.session_state.perf_logs))

# Version Info
st.sidebar.divider()
ver = get_app_version()
st.sidebar.markdown(f"**Version:** v0.1.{ver['count']} ({ver['hash']})")
st.sidebar.markdown(f"**Date:** {ver['date']}")

# Apply Filters to Dataframe globally (for Analysis and Viz consistency)
# We must reset index so that results indices match the dataframe passed to Viz
if len(selected_years) < len(all_years):
    df_filtered = df[df['date'].dt.year.isin(selected_years)].reset_index(drop=True)
else:
    df_filtered = df.copy() # Copy to be safe if we modify it later (though we don't)

# Run Logic (Reactive)
t_analysis_start = time_module.time()

# Only run if we have data selected
if len(selected_years) > 0 and len(days) > 0:
    results, stats = find_bumps_and_slides(
        df_filtered,
        bump_len, bump_threshold, bump_thresh_type,
        slide_len, slide_threshold, slide_thresh_type,
        min_bump_vol=min_bump_vol,
        min_slide_vol=min_slide_vol,
        time_range=(time_start, time_end),
        days_of_week=days,
        # No progress bar needed for instant reactive updates unless slow
    )
    st.session_state.results = results
    st.session_state.stats = stats
    
    # Pre-select specific row if first run or requested
    # Target: 2020-04-06 13:53:00
    if 'preselected_done' not in st.session_state and not results.empty:
        # Search for the target date
        target_timestamp = pd.Timestamp("2020-04-06 13:53:00")
        matches = results[results['date'] == target_timestamp]
        
        if not matches.empty:
            target_idx = matches.index[0]
            st.session_state.selected_match_idx = target_idx
            st.session_state.preselected_done = True
            # We might need to rerun to reflect the selection immediately
            # But since we are inside the run logic, the selection logic below will pick it up
        else:
            # Mark as done so we don't keep trying
            st.session_state.preselected_done = True

else:
    st.session_state.results = pd.DataFrame() # Empty if no filters
    st.session_state.stats = None

log_perf("Full Analysis", t_analysis_start)

# Display Stats (Hit Rate)
if st.session_state.stats:
    stats = st.session_state.stats
    with st.expander("📊 Pattern Statistics (Hit Rate)", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Bumps", stats['total_bumps'], help="Candidates matching Bump criteria")
        col2.metric("Hits (Valid)", stats['hits'], help="Bumps followed by matching Slide")
        col3.metric("Misses", stats['misses'], help="Bumps NOT followed by matching Slide")
        col4.metric("Conversion Rate", f"{stats['hit_ratio']:.1f}%", help="Percentage of bumps that become valid patterns")

# Display Results
if st.session_state.results is not None:
    results = st.session_state.results
    st.metric("Matches Found", len(results))
    
    if not results.empty:
        # Define render functions for reordering
        def render_table():
            st.subheader("Matches")
            st.caption("Click a row to visualize it.")
            
            # Interactive Table
            event = st.dataframe(
                results, 
                width="stretch",
                on_select="rerun",
                selection_mode="single-row",
                key="matches_table", # Stable key to preserve sort state across reruns
                column_config={
                    "date": st.column_config.DatetimeColumn("Bump Start", format="YYYY-MM-DD HH:mm"),
                    "bump_change": st.column_config.NumberColumn("Bump Change %", format="%.2f"),
                    "slide_change": st.column_config.NumberColumn("Slide Change %", format="%.2f"),
                    "bump_vol": st.column_config.NumberColumn("Bump Vol"),
                    "slide_vol": st.column_config.NumberColumn("Slide Vol"),
                },
                hide_index=True 
            )
            
            # Handle Table Selection
            if len(event.selection.rows) > 0:
                selected_row_numeric_idx = event.selection.rows[0]
                new_idx = results.index[selected_row_numeric_idx]
                if 'selected_match_idx' not in st.session_state or new_idx != st.session_state.selected_match_idx:
                    st.session_state.selected_match_idx = new_idx
                    st.rerun()

        def render_chart():
            # Initialize match_idx logic
            if 'selected_match_idx' not in st.session_state:
                st.session_state.selected_match_idx = results.index[0] if not results.empty else None
            
            # Validation
            if st.session_state.selected_match_idx not in results.index and not results.empty:
                st.session_state.selected_match_idx = results.index[0]

            match_idx = st.session_state.selected_match_idx

            if match_idx is not None and match_idx in results.index:
                st.subheader("Visualize Pattern")
                
                row = results.loc[match_idx]
                
                # --- Top Info Row: Metrics and News Selector ---
                # Layout: Date | Bump | Slide | News Dropdown | Search Link
                
                # We use columns to spread info horizontally above the chart
                info_col1, info_col2, info_col3, info_col4 = st.columns([2, 1, 1, 3])
                
                with info_col1:
                    st.markdown(f"### {row['date'].date()}")
                
                with info_col2:
                    st.metric("Bump", f"{row['bump_change']:.2f}%")
                    
                with info_col3:
                    st.metric("Slide", f"{row['slide_change']:.2f}%")
                    
                with info_col4:
                    # Compact News Controls
                    news_date_str = str(row['date'].date())
                    # Using a simpler layout for news to save vertical space
                    search_topic = st.text_input(
                        "News Topic", 
                        value="S&P 500",
                        label_visibility="collapsed" # Save space, label implied
                    )
                    fallback_url = get_google_news_url(news_date_str, search_topic)
                    st.markdown(f"[**🔍 Search News: {search_topic}**]({fallback_url})")

                st.divider()

                # --- Chart Visualization (Full Width) ---
                t_viz_start = time_module.time()
                
                chart_container = st.empty()
                with chart_container.container():
                    st.info("⏳ **Generating visualization...**", icon="⏳")
                
                try:
                    t_prep_start = time_module.time()
                    # Use df_filtered to match the indices in results
                    fig = plot_pattern(df_filtered, row, bump_len=bump_len, slide_len=slide_len)
                    log_perf("Viz: Pattern Generation", t_prep_start)
                    
                    t_render_start = time_module.time()
                    # Full width chart
                    chart_container.plotly_chart(fig, width="stretch")
                    log_perf("Viz: Render Call", t_render_start)
                    
                    log_perf("Viz: Total Flow", t_viz_start)

                except Exception as e:
                    chart_container.error(f"Error loading visualization: {str(e)}")

        # Execute Layout Order
        if layout_order == "Table Top":
            render_table()
            st.divider()
            render_chart()
        else:
            render_chart()
            st.divider()
            render_table()

    else:
        st.info("No matches found with current parameters.")

t_end = time_module.time()
log_perf("Script Execution Complete", t0)
print(f"--- RERUN ENDED at {t_end} (Duration: {t_end - t0:.4f}s) ---")
