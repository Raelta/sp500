import streamlit as st
from datetime import time
from src.ui.utils import render_checkbox_dropdown, get_app_version

def render_time_input(label, default_minutes, key_prefix):
    """
    Renders 3 number inputs (Days, Hours, Minutes) and returns total minutes.
    """
    st.sidebar.markdown(f"**{label}**")
    
    # Calculate defaults
    d_default = int(default_minutes // 1440)
    h_default = int((default_minutes % 1440) // 60)
    m_default = int(default_minutes % 60)
    
    col1, col2, col3 = st.sidebar.columns(3)
    
    with col1:
        days = st.number_input("Days", min_value=0, value=d_default, key=f"{key_prefix}_days")
    with col2:
        hours = st.number_input("Hours", min_value=0, max_value=23, value=h_default, key=f"{key_prefix}_hours")
    with col3:
        minutes = st.number_input("Mins", min_value=0, max_value=59, value=m_default, key=f"{key_prefix}_mins")
        
    total_mins = (days * 1440) + (hours * 60) + minutes
    return max(1, total_mins) # Ensure at least 1 min

def render_sidebar(df, cli_args):
    """
    Renders the sidebar components and returns the configuration parameters.
    
    Args:
        df: The dataframe (used for Date filters).
        cli_args: Command line arguments for default overrides.
        
    Returns:
        dict: A dictionary containing all filter and analysis parameters.
    """
    
    # Global Controls
    if st.sidebar.button("🔄 Reload Data", help="Clear cache and force reload from disk"):
        st.cache_data.clear()
        # Clear session state to ensure fresh analysis
        for key in ['results', 'selected_match_idx', 'preselected_done', 'stats', 'applied_config']:
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
    bump_len = render_time_input("Bump Size", b_len_default, "bump_size")
    
    bump_threshold = st.sidebar.number_input(b_label, min_value=0.0, value=float(b_val), step=b_step, format="%.2f", key=f"bump_th_{bump_thresh_type}", help=b_help)
    
    b_up_default = cli_args.bump_up_pct if cli_args.bump_up_pct is not None else 0.0
    bump_up_pct = st.sidebar.slider("Min % Up Candles", 0.0, 100.0, float(b_up_default), step=5.0, key="bump_up_pct", help="Minimum percentage of bars where Close > Open.")

    st.sidebar.header("Slide Parameters")

    # CLI Override for Slide Length
    s_len_default = cli_args.slide_len if cli_args.slide_len is not None else 3
    slide_len = render_time_input("Slide Size", s_len_default, "slide_size")
    
    slide_threshold = st.sidebar.number_input(s_label, min_value=0.0, value=float(s_val), step=s_step, format="%.2f", key=f"slide_th_{slide_thresh_type}", help=s_help)
    
    s_up_default = cli_args.slide_up_pct if cli_args.slide_up_pct is not None else 0.0
    slide_up_pct = st.sidebar.slider("Min % Up Candles", 0.0, 100.0, float(s_up_default), step=5.0, key="slide_up_pct", help="Minimum percentage of bars where Close > Open.")

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
    
    return {
        'bump_len': bump_len,
        'bump_threshold': bump_threshold,
        'bump_thresh_type': bump_thresh_type,
        'bump_up_pct': bump_up_pct,
        'slide_len': slide_len,
        'slide_threshold': slide_threshold,
        'slide_thresh_type': slide_thresh_type,
        'slide_up_pct': slide_up_pct,
        'min_bump_vol': min_bump_vol,
        'min_slide_vol': min_slide_vol,
        'time_range': (time_start, time_end),
        'days_of_week': days,
        'selected_years': selected_years,
        'layout_order': layout_order,
        'all_years': all_years
    }
