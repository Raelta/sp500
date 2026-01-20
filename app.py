import streamlit as st
import pandas as pd
import time as time_module
from src.data_loader import load_data_cached
from src.analyzer import find_bumps_and_slides
from src.data_validator import validate_dataset, get_yearly_duplicate_summary
from src.config import get_cli_args
from src.ui.sidebar import render_sidebar
from src.ui.results import render_results
from src.ui.utils import log_perf
from src.ui.goal_seek import render_goal_seek_ui

# Setup
st.set_page_config(page_title="SP500 Bump & Slide", layout="wide")
st.title("SP500 Bump & Slide Analysis")

# Initialize Session State
if 'perf_logs' not in st.session_state:
    st.session_state.perf_logs = []
else:
    st.session_state.perf_logs = []

if 'results' not in st.session_state:
    st.session_state.results = None
if 'stats' not in st.session_state:
    st.session_state.stats = None

t0 = time_module.time()
print(f"--- RERUN STARTED at {t0} ---")

# Parse CLI Args
cli_args = get_cli_args()

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

# --- MODE SELECTOR ---
st.sidebar.title("Navigation")
app_mode = st.sidebar.radio("Mode", ["Standard Analysis", "Goal Seek"], index=0)
st.sidebar.divider()

# Sidebar Render
# Returns config dictionary with current parameters from widgets
config = render_sidebar(df, cli_args)

# --- Apply Button Logic ---
if 'applied_config' not in st.session_state:
    # First run: auto-apply
    st.session_state.applied_config = config

# Check if current config differs from applied config
has_changes = config != st.session_state.applied_config

if st.sidebar.button("Apply Changes", disabled=not has_changes, type="primary"):
    st.session_state.applied_config = config
    st.rerun()

# Use APPLIED config for analysis
run_config = st.session_state.applied_config

# Prepare filtered dataframe for global usage context if needed (mostly passed to visualizer inside render_results)
selected_years = run_config['selected_years']
all_years = run_config['all_years']

if len(selected_years) < len(all_years):
    df_filtered = df[df['date'].dt.year.isin(selected_years)].reset_index(drop=True)
else:
    df_filtered = df.copy()

# --- MAIN LOGIC BRANCH ---

if app_mode == "Goal Seek":
    # GOAL SEEK MODE
    render_goal_seek_ui(df_filtered, config)

else:
    # STANDARD ANALYSIS MODE
    # Run Analysis Logic
    t_analysis_start = time_module.time()

    # Only run if we have data selected
    if len(selected_years) > 0 and len(run_config['days_of_week']) > 0:
        results, stats = find_bumps_and_slides(
            df_filtered,
            run_config['bump_len'], run_config['bump_threshold'], run_config['bump_thresh_type'],
            run_config['slide_len'], run_config['slide_threshold'], run_config['slide_thresh_type'],
            min_bump_vol=run_config['min_bump_vol'],
            min_slide_vol=run_config['min_slide_vol'],
            bump_up_pct=run_config['bump_up_pct'],
            slide_up_pct=run_config['slide_up_pct'],
            time_range=run_config['time_range'],
            days_of_week=run_config['days_of_week']
        )
        st.session_state.results = results
        st.session_state.stats = stats
        
        # Pre-select logic
        if 'preselected_done' not in st.session_state and not results.empty:
            # Search for the target date
            target_timestamp = pd.Timestamp("2020-04-06 13:53:00")
            matches = results[results['date'] == target_timestamp]
            
            if not matches.empty:
                target_idx = matches.index[0]
                st.session_state.selected_match_idx = target_idx
                st.session_state.preselected_done = True
            else:
                st.session_state.preselected_done = True

    else:
        st.session_state.results = pd.DataFrame()
        st.session_state.stats = None

    log_perf("Full Analysis", t_analysis_start)

    # Render Results
    if st.session_state.results is not None:
        render_results(st.session_state.results, st.session_state.stats, run_config, df_filtered, val_report)
    else:
        st.info("No matches found with current parameters.")

t_end = time_module.time()
log_perf("Script Execution Complete", t0)
print(f"--- RERUN ENDED at {t_end} (Duration: {t_end - t0:.4f}s) ---")
