import streamlit as st
import pandas as pd
import time as time_module
from src.analyzer import find_bumps_and_slides
from src.ui.sidebar import render_sidebar
from src.ui.results import render_results
from src.ui.utils import log_perf

def render_exploration(df, cli_args, val_report):
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

    # Prepare filtered dataframe for global usage context if needed
    selected_years = run_config['selected_years']
    all_years = run_config['all_years']

    if len(selected_years) < len(all_years):
        df_filtered = df[df['date'].dt.year.isin(selected_years)].reset_index(drop=True)
    else:
        df_filtered = df.copy()

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
            days_of_week=run_config['days_of_week'],
            exclude_cross_day=run_config.get('exclude_cross_day', True),
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
