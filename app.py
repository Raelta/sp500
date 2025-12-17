import streamlit as st
import pandas as pd
from src.data_loader import load_data_cached
from src.analyzer import find_bumps_and_slides
from src.visualizer import plot_pattern
from src.data_validator import validate_dataset, get_yearly_duplicate_summary
from datetime import time

st.set_page_config(page_title="SP500 Bump & Slide", layout="wide")
st.title("SP500 Bump & Slide Analysis")

# Load Data
with st.spinner("Loading data..."):
    df = load_data_cached("spy_data.parquet")
st.success(f"Loaded {len(df)} rows.")

# Data Quality Check
val_report = validate_dataset(df)
has_issues = (val_report['duplicates']['count'] > 0) or \
             (len(val_report['missing_values']) > 0) or \
             (val_report['intraday_gaps']['count'] > 0)

if has_issues:
    with st.expander("⚠️ Data Quality Issues Detected", expanded=False):
        tab1, tab2, tab3 = st.tabs(["Duplicates", "Missing Values", "Intraday Gaps"])
        
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

# Auto-clean Duplicates
if val_report['duplicates']['count'] > 0:
    original_count = len(df)
    df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
    st.info(f"🧹 Auto-cleaned data: Removed {original_count - len(df)} duplicate rows. Analysis will proceed on {len(df)} unique rows.")

# Initialize Session State
if 'results' not in st.session_state:
    st.session_state.results = None

# Sidebar Configuration (Types outside form for interactivity)
st.sidebar.header("Configuration")
bump_thresh_type = st.sidebar.radio("Bump Threshold Type", ["percent", "value"], index=0, help="Choose 'percent' for relative change (%) or 'value' for absolute price difference.")
slide_thresh_type = st.sidebar.radio("Slide Threshold Type", ["percent", "value"], index=0, help="Choose 'percent' for relative change (%) or 'value' for absolute price difference.")

# Calculate defaults
if bump_thresh_type == "percent":
    b_val, b_step = 0.05, 0.01
    b_label = "Bump Threshold (%)"
    b_help = "Minimum percentage change required (e.g., 0.05 means 0.05%)."
else:
    b_val, b_step = 0.50, 0.05
    b_label = "Bump Threshold (Price Difference)"
    b_help = "Minimum price change required in dollars (e.g., 0.50 means 50 cents)."

if slide_thresh_type == "percent":
    s_val, s_step = 0.05, 0.01
    s_label = "Slide Threshold (%)"
    s_help = "Minimum percentage change required during the slide (e.g., 0.05 means 0.05%)."
else:
    s_val, s_step = 0.50, 0.05
    s_label = "Slide Threshold (Price Difference)"
    s_help = "Minimum price change required during the slide in dollars."

# Sidebar Form (Values & Execution)
with st.sidebar.form("analysis_form"):
    run_btn_top = st.form_submit_button("Run Analysis", type="primary", width="stretch", key="run_top")
    
    st.header("Bump Parameters")
    bump_len = st.slider("Bump Length (min)", 3, 20, 5, help="Duration of the initial trend window in minutes.")
    bump_threshold = st.number_input(b_label, min_value=0.0, value=b_val, step=b_step, format="%.2f", key=f"bump_th_{bump_thresh_type}", help=b_help)

    st.header("Slide Parameters")
    slide_len = st.slider("Slide Length (min)", 3, 20, 3, help="Duration of the subsequent reaction window in minutes.")
    slide_threshold = st.number_input(s_label, min_value=0.0, value=s_val, step=s_step, format="%.2f", key=f"slide_th_{slide_thresh_type}", help=s_help)
    
    st.header("Filters")
    min_bump_vol = st.number_input("Min Bump Volume", min_value=0, value=0, step=1000, help="Minimum total volume traded during the Bump period.")
    min_slide_vol = st.number_input("Min Slide Volume", min_value=0, value=0, step=1000, help="Minimum total volume traded during the Slide period.")
    
    st.subheader("Time of Day (Bump Start)")
    time_start = st.time_input("Start Time", time(9, 30), help="Only include patterns starting after this time.")
    time_end = st.time_input("End Time", time(16, 0), help="Only include patterns starting before this time.")
    
    st.subheader("Day of Week")
    days = []
    days_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for day in days_options:
        if st.checkbox(day, value=True, key=f"check_{day}"):
            days.append(day)

# Run Logic
if run_btn_top:
    # Progress UI Elements (Centered at top of main area)
    prog_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(msg, percent):
        prog_bar.progress(percent)
        status_text.markdown(f"**{msg}**")

    results = find_bumps_and_slides(
        df,
        bump_len, bump_threshold, bump_thresh_type,
        slide_len, slide_threshold, slide_thresh_type,
        min_bump_vol=min_bump_vol,
        min_slide_vol=min_slide_vol,
        time_range=(time_start, time_end),
        days_of_week=days,
        progress_callback=update_progress
    )
    
    # Clear progress after completion
    prog_bar.empty()
    status_text.empty()
    
    st.session_state.results = results

# Display Results
if st.session_state.results is not None:
    results = st.session_state.results
    st.metric("Matches Found", len(results))
    
    if not results.empty:
        st.subheader("Visualize Pattern")
        
        def format_func(idx):
            row = results.loc[idx]
            return f"{row['date']} | Bump: {row['bump_change']:.2f} | Slide: {row['slide_change']:.2f}"
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            match_idx = st.selectbox("Select Match", results.index, format_func=format_func)
        
        with col2:
            if match_idx is not None and match_idx in results.index:
                row = results.loc[match_idx]
                fig = plot_pattern(df, row)
                st.plotly_chart(fig, width="stretch")

        st.subheader("Matches")
        st.dataframe(results, width='stretch')
    else:
        st.info("No matches found with current parameters.")
