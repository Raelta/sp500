import streamlit as st
from datetime import time
from src.ui.utils import render_checkbox_dropdown, get_app_version, render_version_info

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
    """
    
    # Global Controls
    if st.sidebar.button("🔄 Reload Data", help="Clear cache and force reload from disk", use_container_width=True):
        st.cache_data.clear()
        for key in ['results', 'selected_match_idx', 'preselected_done', 'stats', 'applied_config']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    # Get previously applied config if it exists
    applied = st.session_state.get('applied_config', {})

    # BUMP TYPE
    bt_default = applied.get('bump_thresh_type', 'percent')
    bt_idx = 0 if bt_default == "percent" else 1
    
    # SLIDE TYPE
    st_default = applied.get('slide_thresh_type', 'percent')
    st_idx = 0 if st_default == "percent" else 1

    # Combined Type Selection
    col_t1, col_t2 = st.sidebar.columns(2)
    with col_t1:
        bump_thresh_type = st.radio("Bump Type", ["percent", "value"], index=bt_idx, key="sb_bump_type", horizontal=True)
    with col_t2:
        slide_thresh_type = st.radio("Slide Type", ["percent", "value"], index=st_idx, key="sb_slide_type", horizontal=True)

    # Defaults for thresholds
    if bump_thresh_type == "percent":
        b_val, b_step = applied.get('bump_threshold', 0.02), 0.01
        b_label = "Bump Thresh (%)"
    else:
        b_val, b_step = applied.get('bump_threshold', 0.50), 0.05
        b_label = "Bump Thresh (Diff)"

    if slide_thresh_type == "percent":
        s_val, s_step = applied.get('slide_threshold', 0.06), 0.01
        s_label = "Slide Thresh (%)"
    else:
        s_val, s_step = applied.get('slide_threshold', 0.50), 0.05
        s_label = "Slide Thresh (Diff)"

    # --- BUMP PARAMETERS ---
    st.sidebar.subheader("Bump Parameters")
    b_len_default = applied.get('bump_len', cli_args.bump_len if cli_args.bump_len is not None else 30)
    bump_len = render_time_input("Bump Size", b_len_default, "sb_bump_size")
    
    col_b1, col_b2 = st.sidebar.columns(2)
    with col_b1:
        bump_threshold = st.number_input(b_label, min_value=0.0, value=float(b_val), step=b_step, format="%.2f", key=f"sb_bump_th_{bump_thresh_type}")
    with col_b2:
        b_up_default = applied.get('bump_up_pct', cli_args.bump_up_pct if cli_args.bump_up_pct is not None else 0.0)
        bump_up_pct = st.number_input("Min % Up", min_value=0.0, max_value=100.0, value=float(b_up_default), step=5.0, key="sb_bump_up_pct")

    # --- SLIDE PARAMETERS ---
    st.sidebar.subheader("Slide Parameters")
    s_len_default = applied.get('slide_len', cli_args.slide_len if cli_args.slide_len is not None else 30)
    slide_len = render_time_input("Slide Size", s_len_default, "sb_slide_size")
    
    col_s1, col_s2 = st.sidebar.columns(2)
    with col_s1:
        slide_threshold = st.number_input(s_label, min_value=0.0, value=float(s_val), step=s_step, format="%.2f", key=f"sb_slide_th_{slide_thresh_type}")
    with col_s2:
        s_up_default = applied.get('slide_up_pct', cli_args.slide_up_pct if cli_args.slide_up_pct is not None else 0.0)
        slide_up_pct = st.number_input("Min % Up", min_value=0.0, max_value=100.0, value=float(s_up_default), step=5.0, key="sb_slide_up_pct")

    # --- FILTERS ---
    st.sidebar.subheader("Filters")
    mbv_default = applied.get('min_bump_vol', cli_args.min_bump_vol if cli_args.min_bump_vol is not None else 0)
    msv_default = applied.get('min_slide_vol', cli_args.min_slide_vol if cli_args.min_slide_vol is not None else 0)

    col_v1, col_v2 = st.sidebar.columns(2)
    with col_v1:
        min_bump_vol = st.number_input("Min Bump Vol", min_value=0, value=int(mbv_default), step=1000, key="sb_min_bump_vol")
    with col_v2:
        min_slide_vol = st.number_input("Min Slide Vol", min_value=0, value=int(msv_default), step=1000, key="sb_min_slide_vol")

    # --- TIME OF DAY ---
    st.sidebar.subheader("Time of Day")
    tr_default = applied.get('time_range', (time(8, 30), time(15, 0)))
    
    col_tm1, col_tm2 = st.sidebar.columns(2)
    with col_tm1:
        time_start = st.time_input("Start", tr_default[0], key="sb_time_start")
    with col_tm2:
        time_end = st.time_input("End", tr_default[1], key="sb_time_end")

    # --- DATE FILTERS ---
    st.sidebar.subheader("Date Filters")
    all_years = sorted(df['date'].dt.year.unique())
    
    # Years
    sy_default = applied.get('selected_years', all_years)
    selected_years = render_checkbox_dropdown("Years", all_years, "filter_year")
    
    # Days
    days_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    days = render_checkbox_dropdown("Days of Week", days_options, "filter_day")

    # --- APP LAYOUT ---
    lo_default = applied.get('layout_order', "Table Top")
    lo_idx = 0 if lo_default == "Table Top" else 1
    layout_order = st.sidebar.radio("View Order", ["Table Top", "Chart Top"], index=lo_idx, horizontal=True, key="sb_layout_order")

    with st.sidebar.expander("Debug Profiling", expanded=False):
        if 'perf_logs' in st.session_state:
            st.code("\n".join(st.session_state.perf_logs))

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
