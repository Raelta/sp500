import streamlit as st
import pandas as pd
import time as time_module
from src.data_loader import load_data_cached
from src.data_validator import validate_dataset, get_yearly_duplicate_summary
from src.config import get_cli_args
from src.ui.utils import log_perf, inject_compact_sidebar_style
from src.ui.exploration import render_exploration
from src.ui.goal_seek import render_goal_seek

# Setup
st.set_page_config(page_title="SP500 Bump & Slide", layout="wide")
inject_compact_sidebar_style()
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
if 'app_mode' not in st.session_state:
    st.session_state.app_mode = "Goal Seek"

t0 = time_module.time()
print(f"--- RERUN STARTED at {t0} ---")

# Parse CLI Args
cli_args = get_cli_args()

# Load Data
with st.spinner("Loading data..."):
    t_load_start = time_module.time()
    df, val_report = load_data_cached("spy_data_25yr.parquet")
    t0 = log_perf("Data Load (Cached)", t_load_start)

# Data Quality Check (Minimized display in main app)
has_issues = (val_report['duplicates']['count'] > 0) or \
             (len(val_report['missing_values']) > 0) or \
             (val_report['intraday_gaps']['count'] > 0)

if has_issues:
    with st.expander("⚠️ Data Quality Issues Detected", expanded=False):
        tab1, tab2, tab3, tab4 = st.tabs(["Duplicates", "Missing Values", "Intraday Gaps", "Missing Minutes"])
        # ... (keeping logic for tabs)
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
                st.dataframe(val_report['missing_values']['data'], width='stretch')
            else:
                st.success("No missing values found.")
        with tab3:
            count = val_report['intraday_gaps']['count']
            if count > 0:
                st.warning(f"Found {count} intraday gaps.")
                st.dataframe(val_report['intraday_gaps']['data'], width='stretch')
            else:
                st.success("No intraday gaps found.")
        with tab4:
            if 'missing_minutes' in val_report:
                mm = val_report['missing_minutes']
                if mm['count'] > 0:
                    st.warning(f"Found {mm['count']} missing minute intervals.")
                    st.dataframe(mm['data'], width='stretch')
                else:
                    st.success("All trading days have complete data.")

# Auto-clean Duplicates
if val_report['duplicates']['count'] > 0:
    df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)

# --- Navigation ---
st.sidebar.title("Navigation")
# Bind radio directly to session state key. 
# st.session_state.app_mode is initialized to "Goal Seek" above.
st.sidebar.radio(
    "Select Mode", 
    ["Exploration", "Goal Seek"], 
    key="app_mode"
)

st.sidebar.divider()

if st.session_state.app_mode == "Exploration":
    render_exploration(df, cli_args, val_report)
else:
    render_goal_seek(df, cli_args, val_report)

t_end = time_module.time()
log_perf("Script Execution Complete", t0)
print(f"--- RERUN ENDED at {t_end} (Duration: {t_end - t0:.4f}s) ---")
