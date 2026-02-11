import streamlit as st
import pandas as pd
import numpy as np
import time
from src.search_engine import GoalSeeker
from src.ui.utils import log_perf
from src.cloud_runner import CloudRunner

def render_range_input(label, min_val, max_val, default_start, default_end, default_step, key_prefix):
    st.sidebar.markdown(f"**{label}**")
    is_float = isinstance(default_step, float)
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        start = st.number_input("Start", min_value=min_val, max_value=max_val, value=default_start, key=f"{key_prefix}_start")
    with col2:
        end = st.number_input("End", min_value=min_val, max_value=max_val, value=default_end, key=f"{key_prefix}_end")
    with col3:
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
            if isinstance(start, int) and isinstance(end, int) and isinstance(step, (int, float)) and step >= 1:
                vals = np.arange(start, end + 0.0001, step).astype(int).tolist()
            else:
                vals = np.arange(start, end + 0.00001, step).tolist()
                vals = [round(x, 4) for x in vals]
        if not vals:
            vals = [start]
        grid[key] = vals
    return grid

@st.fragment(run_every=5)
def render_cloud_status(runner, job_name, bucket):
    st.write("### 🛰️ Cloud Job Status (Auto-refreshing)")
    latest_exec, error_msg = runner.get_latest_execution(job_name)
    
    if error_msg:
        st.error(f"Failed to fetch job status: {error_msg}")
        if st.button("🔄 Manual Retry"):
            st.rerun()
    elif latest_exec:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"**Last Run:** `{latest_exec['id']}`")
            st.caption(f"Started: {latest_exec['start_time']}")
        with col2:
            status_colors = {"SUCCEEDED": "green", "RUNNING": "blue", "FAILED": "red", "PENDING": "orange"}
            color = status_colors.get(latest_exec['status'], "gray")
            st.markdown(f"Status: **:{color}[{latest_exec['status']}]**")
        with col3:
            if st.button("🔄 Refresh Now"):
                st.rerun()

        if latest_exec['is_done'] and latest_exec['status'] == "SUCCEEDED":
            st.success("Cloud job finished! You can now load the results below.")
        elif latest_exec['is_running']:
            st.info("⏳ Job is currently running in the cloud. Results will be ready soon.")
    else:
        st.info("No previous cloud executions found for this job.")

def render_goal_seek(df, cli_args, val_report):
    st.sidebar.title("Goal Seek Parameters")
    
    gs_params = {}
    b_len_start, b_len_end, b_len_step = render_range_input("Bump Length (min)", 1, 390, 3, 6, 1, "gs_b_len")
    gs_params['bump_len'] = (b_len_start, b_len_end, b_len_step)
    
    s_len_start, s_len_end, s_len_step = render_range_input("Slide Length (min)", 1, 390, 3, 6, 1, "gs_s_len")
    gs_params['slide_len'] = (s_len_start, s_len_end, s_len_step)
    
    st.sidebar.divider()
    st.sidebar.markdown("**Thresholds (Minima)**")
    min_b_thresh = st.sidebar.number_input("Min Bump Threshold %", value=3.0, step=0.1, key="gs_min_b_thresh")
    min_s_thresh = st.sidebar.number_input("Min Slide Threshold %", value=3.0, step=0.1, key="gs_min_s_thresh")
    
    st.sidebar.divider()
    b_vol_start, b_vol_end, b_vol_step = render_range_input("Min Bump Volume", 0, 10000000, 0, 0, 10000, "gs_b_vol")
    gs_params['min_bump_vol'] = (b_vol_start, b_vol_end, b_vol_step)
    s_vol_start, s_vol_end, s_vol_step = render_range_input("Min Slide Volume", 0, 10000000, 0, 0, 10000, "gs_s_vol")
    gs_params['min_slide_vol'] = (s_vol_start, s_vol_end, s_vol_step)
    
    st.sidebar.divider()
    b_up_start, b_up_end, b_up_step = render_range_input("Bump Up %", 0, 100, 0, 0, 5, "gs_b_up")
    gs_params['bump_up_pct'] = (b_up_start, b_up_end, b_up_step)
    s_up_start, s_up_end, s_up_step = render_range_input("Slide Up %", 0, 100, 0, 0, 5, "gs_s_up")
    gs_params['slide_up_pct'] = (s_up_start, s_up_end, s_up_step)
    
    st.sidebar.divider()
    st.sidebar.markdown("**Search Scope**")
    use_current_filters = st.sidebar.checkbox("Use current Exploration filters (Years/Time/Days)", value=True)
    min_bumps_req = st.sidebar.number_input("Min Bumps Required", value=0, step=1)
    
    st.sidebar.divider()
    run_cloud = st.sidebar.checkbox("☁️ Offload to Cloud (GCP)", value=True)
    
    # Pre-generate grid for use in buttons
    grid = generate_grid_from_ui(gs_params)
    grid['bump_threshold'] = [min_b_thresh]
    grid['slide_threshold'] = [min_s_thresh]

    # --- CLOUD MODE UI ---
    if run_cloud:
        with st.sidebar.expander("🛠️ GCP Configuration", expanded=False):
            gcp_project = st.text_input("Project ID", value="sp500-479009", key="gs_gcp_project")
            gcp_region = st.text_input("Region", value="europe-west2", key="gs_gcp_region")
            gcp_job_name = st.text_input("Job Name", value="sp500-goal-seek", key="gs_gcp_job_name")
            gcp_bucket = st.text_input("GCS Bucket", value="sp500-goal-seek-results", key="gs_gcp_bucket")

        runner = CloudRunner(project_id=gcp_project, region=gcp_region)
        
        # 1. Job Status Dashboard (Fragmented for auto-refresh)
        render_cloud_status(runner, gcp_job_name, gcp_bucket)
        
        st.divider()

        # 2. Execution Controls
        st.write("### 🚀 Trigger New Job")
        fixed_params = { 'bump_thresh_type': 'percent', 'slide_thresh_type': 'percent' }
        if use_current_filters and 'applied_config' in st.session_state:
            ac = st.session_state.applied_config
            fixed_params['time_range'] = ac['time_range']
            fixed_params['days_of_week'] = ac['days_of_week']

        config_dict = {
            "params_grid": grid,
            "fixed_params": fixed_params,
            "min_bumps": min_bumps_req,
            "gcs_output_path": f"gs://{gcp_bucket}/results.csv"
        }

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Trigger Cloud Job Now", type="primary", use_container_width=True):
                with st.spinner("Triggering..."):
                    success, output = runner.run_job(gcp_job_name, config_dict)
                    if success:
                        st.success(output)
                        st.rerun()
                    else:
                        st.error(output)
        with col2:
            with st.expander("Show Manual Command"):
                st.code(runner.generate_gcloud_command(gcp_job_name, config_dict), language="bash")

        st.divider()

        # 3. Result Retrieval
        st.write("### 📥 Retrieve Results")
        if st.button("📥 Download & View Cloud Results", use_container_width=True):
            with st.spinner("Fetching from GCS..."):
                local_path = "cloud_results.csv"
                success, msg = runner.download_results(gcp_bucket, "results.csv", local_path)
                if success:
                    try:
                        df_res = pd.read_csv(local_path)
                        st.session_state.gs_results = df_res.sort_values('total_hits', ascending=False).head(50)
                        st.success("Results loaded into table below!")
                        # st.rerun() # Optional: rerun to ensure table renders fresh
                    except Exception as e:
                        st.error(f"Error loading CSV: {e}")
                else:
                    st.error(f"Download failed: {msg}")

    # --- LOCAL MODE UI ---
    else:
        st.write("### 💻 Local Search")
        if st.button("🚀 Run Local Goal Seek", type="primary"):
            seeker = GoalSeeker(df) # Logic for filtering omitted for brevity or add here
            progress_bar = st.progress(0)
            status_text = st.empty()
            def update_progress(msg, pct):
                progress_bar.progress(pct)
                status_text.text(msg)
            
            start_t = time.time()
            results_df = seeker.search(grid, min_bumps=min_bumps_req, progress_callback=update_progress)
            elapsed = time.time() - start_t
            
            if not results_df.empty:
                st.success(f"Search complete in {elapsed:.2f}s.")
                st.session_state.gs_results = results_df.sort_values('total_hits', ascending=False).head(50)
            else:
                st.error("No results found.")
                st.session_state.gs_results = None

    # --- RESULTS TABLE (COMMON) ---
    if 'gs_results' in st.session_state and st.session_state.gs_results is not None:
        st.write("---")
        st.write("### 📊 Top 50 Results")
        st.info("💡 Click a row and then 'Load configuration' to visualize.")
        
        display_df = st.session_state.gs_results.copy()
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
                new_config = st.session_state.get('applied_config', {}).copy()
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
                st.session_state.applied_config = new_config
                st.session_state.app_mode = "Exploration"
                st.rerun()
