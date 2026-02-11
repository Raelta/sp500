import streamlit as st
import pandas as pd
import numpy as np
import time
from src.search_engine import GoalSeeker
from src.ui.utils import log_perf
from src.cloud_runner import CloudRunner

def render_range_input(label, min_val, max_val, default_start, default_end, default_step, key_prefix):
    st.sidebar.markdown(f"**{label}**")
    
    # Determine type based on default_step
    is_float = isinstance(default_step, float)
    
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        start = st.number_input("Start", min_value=min_val, max_value=max_val, value=default_start, key=f"{key_prefix}_start")
    with col2:
        end = st.number_input("End", min_value=min_val, max_value=max_val, value=default_end, key=f"{key_prefix}_end")
    with col3:
        # Match type of min_value/max_value/value
        s_min = 0.0 if is_float else 0
        s_max = float(max_val) if is_float else int(max_val)
        s_val = float(default_step) if is_float else int(default_step)
        step = st.number_input("Step", min_value=s_min, max_value=s_max, value=s_val, key=f"{key_prefix}_step")
    return start, end, step

def generate_grid_from_ui(params):
    grid = {}
    for key, (start, end, step) in params.items():
        if step <= 0:
            vals = [start]
        else:
            # Handle both int and float ranges
            if isinstance(start, int) and isinstance(end, int) and isinstance(step, (int, float)) and step >= 1:
                vals = np.arange(start, end + 0.0001, step).astype(int).tolist()
            else:
                vals = np.arange(start, end + 0.00001, step).tolist()
                vals = [round(x, 4) for x in vals]
        
        if not vals:
            vals = [start]
        grid[key] = vals
    return grid

def render_goal_seek(df, cli_args, val_report):
    st.sidebar.title("Goal Seek Parameters")
    
    # Range Inputs
    gs_params = {}
    
    # Lengths
    b_len_start, b_len_end, b_len_step = render_range_input("Bump Length (min)", 1, 390, 3, 6, 1, "gs_b_len")
    gs_params['bump_len'] = (b_len_start, b_len_end, b_len_step)
    
    s_len_start, s_len_end, s_len_step = render_range_input("Slide Length (min)", 1, 390, 3, 6, 1, "gs_s_len")
    gs_params['slide_len'] = (s_len_start, s_len_end, s_len_step)
    
    st.sidebar.divider()
    
    # Thresholds (Fixed mins for search)
    st.sidebar.markdown("**Thresholds (Minima)**")
    min_b_thresh = st.sidebar.number_input("Min Bump Threshold %", value=3.0, step=0.1, key="gs_min_b_thresh")
    min_s_thresh = st.sidebar.number_input("Min Slide Threshold %", value=3.0, step=0.1, key="gs_min_s_thresh")
    
    st.sidebar.divider()
    
    # Volumes
    b_vol_start, b_vol_end, b_vol_step = render_range_input("Min Bump Volume", 0, 10000000, 0, 0, 10000, "gs_b_vol")
    gs_params['min_bump_vol'] = (b_vol_start, b_vol_end, b_vol_step)
    
    s_vol_start, s_vol_end, s_vol_step = render_range_input("Min Slide Volume", 0, 10000000, 0, 0, 10000, "gs_s_vol")
    gs_params['min_slide_vol'] = (s_vol_start, s_vol_end, s_vol_step)
    
    st.sidebar.divider()
    
    # Up Percents
    b_up_start, b_up_end, b_up_step = render_range_input("Bump Up %", 0, 100, 0, 0, 5, "gs_b_up")
    gs_params['bump_up_pct'] = (b_up_start, b_up_end, b_up_step)
    
    s_up_start, s_up_end, s_up_step = render_range_input("Slide Up %", 0, 100, 0, 0, 5, "gs_s_up")
    gs_params['slide_up_pct'] = (s_up_start, s_up_end, s_up_step)
    
    st.sidebar.divider()
    
    # Search Scope (Optional: filter df before search)
    st.sidebar.markdown("**Search Scope**")
    use_current_filters = st.sidebar.checkbox("Use current Exploration filters (Years/Time/Days)", value=True)
    
    min_bumps_req = st.sidebar.number_input("Min Bumps Required", value=0, step=1)
    
    # Execution
    st.sidebar.divider()
    run_cloud = st.sidebar.checkbox("☁️ Offload to Cloud (GCP)", value=False)
    
    gcp_project = "sp500-479009"
    gcp_region = "europe-west2"
    gcp_job_name = "sp500-goal-seek"
    
    if run_cloud:
        st.sidebar.info("Cloud Run Job configuration:")
        gcp_project = st.sidebar.text_input("GCP Project ID", value=st.session_state.get('gs_gcp_project', 'sp500-479009'), key="gs_gcp_project")
        gcp_region = st.sidebar.text_input("Region", value="europe-west2", key="gs_gcp_region")
        gcp_job_name = st.sidebar.text_input("Job Name", value="sp500-goal-seek", key="gs_gcp_job_name")
        
        if not gcp_project:
            st.sidebar.warning("Please enter a GCP Project ID.")
            
    if st.sidebar.button("🚀 Run Goal Seek", type="primary", use_container_width=True, disabled=run_cloud and not gcp_project):
        grid = generate_grid_from_ui(gs_params)
        grid['bump_threshold'] = [min_b_thresh]
        grid['slide_threshold'] = [min_s_thresh]
        
        # Calculate combinations
        total_combos = 1
        for v in grid.values():
            total_combos *= len(v)
            
        st.write(f"### Running Search for {total_combos} combinations...")
        
        # Filter data based on scope if requested
        df_to_search = df
        fixed_params = {
            'bump_thresh_type': 'percent',
            'slide_thresh_type': 'percent'
        }
        
        if use_current_filters and 'applied_config' in st.session_state:
            ac = st.session_state.applied_config
            df_to_search = df[df['date'].dt.year.isin(ac['selected_years'])].reset_index(drop=True)
            fixed_params['time_range'] = ac['time_range']
            fixed_params['days_of_week'] = ac['days_of_week']

        if run_cloud:
            runner = CloudRunner(project_id=gcp_project, region=gcp_region)
            config_dict = {
                "params_grid": grid,
                "fixed_params": fixed_params,
                "min_bumps": min_bumps_req,
                # "gcs_output_path": f"gs://{gcp_project}-results/results.csv" # Optional
            }
            
            st.write("### Cloud Job Deployment")
            with st.expander("Show Deployment Instructions", expanded=True):
                st.code(runner.get_deploy_instructions(gcp_job_name, "sp500-analyzer"), language="bash")
            
            st.write("### Execute Job")
            cmd = runner.generate_gcloud_command(gcp_job_name, config_dict)
            st.code(cmd, language="bash")
            
            if st.button("Trigger Job via API (Experimental)"):
                with st.spinner("Triggering Cloud Run Job..."):
                    success, output = runner.run_job(gcp_job_name, config_dict)
                    if success:
                        st.success("Job triggered successfully!")
                        st.text(output)
                    else:
                        st.error("Failed to trigger job.")
                        st.text(output)
            return # Exit early for cloud mode
            
        # Local Search
        seeker = GoalSeeker(df_to_search)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(msg, pct):
            progress_bar.progress(pct)
            status_text.text(msg)
            
        start_t = time.time()
        results_df = seeker.search(
            grid, 
            fixed_params=fixed_params, 
            min_bumps=min_bumps_req,
            progress_callback=update_progress
        )
        elapsed = time.time() - start_t
        
        if not results_df.empty:
            st.success(f"Search complete in {elapsed:.2f}s. Found {len(results_df)} valid configurations.")
            # Store results in session state
            st.session_state.gs_results = results_df.sort_values('total_hits', ascending=False).head(50)
        else:
            st.error(f"Search complete in {elapsed:.2f}s. No results found.")
            st.session_state.gs_results = None

    # Results Display
    if 'gs_results' in st.session_state and st.session_state.gs_results is not None:
        st.write("### Top 50 Results")
        st.info("💡 Click a row to load its parameters into the Exploration view.")
        
        # Use st.dataframe with selection
        # Note: selection is available in newer streamlit, for older we can use data_editor or just display
        # Let's use st.dataframe with on_select if possible, or a simple index selector.
        
        display_df = st.session_state.gs_results.copy()
        # Select key columns for display
        cols = ['total_hits', 'true_hits', 'total_bumps', 'bump_len', 'slide_len', 'bump_threshold', 'slide_threshold', 'min_bump_vol', 'min_slide_vol', 'best_hit_date']
        existing_cols = [c for c in cols if c in display_df.columns]
        
        event = st.dataframe(
            display_df[existing_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        if len(event.selection.rows) > 0:
            selected_row_idx = event.selection.rows[0]
            selected_params = display_df.iloc[selected_row_idx]
            
            if st.button(f"Load configuration into Exploration View"):
                # Start with current applied config or empty dict
                new_config = st.session_state.get('applied_config', {}).copy()
                
                # Update with Goal Seek result params
                new_config.update({
                    'bump_len': int(selected_params['bump_len']),
                    'bump_threshold': float(selected_params['bump_threshold']),
                    'bump_thresh_type': 'percent',
                    'slide_len': int(selected_params['slide_len']),
                    'slide_threshold': float(selected_params['slide_threshold']),
                    'slide_thresh_type': 'percent',
                    'min_bump_vol': int(selected_params['min_bump_vol']),
                    'min_slide_vol': int(selected_params['min_slide_vol']),
                    'bump_up_pct': float(selected_params['bump_up_pct']),
                    'slide_up_pct': float(selected_params['slide_up_pct']),
                })
                
                # Overwrite applied config
                st.session_state.applied_config = new_config
                
                # Switch mode
                st.session_state.app_mode = "Exploration"
                st.rerun()
