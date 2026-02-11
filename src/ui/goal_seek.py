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

def load_match_into_exploration(params):
    new_config = st.session_state.get('applied_config', {}).copy()
    new_config.update({
        'bump_len': int(params['bump_len']),
        'bump_threshold': float(params['bump_threshold']),
        'bump_thresh_type': 'percent',
        'slide_len': int(params['slide_len']),
        'slide_threshold': float(params['slide_threshold']),
        'slide_thresh_type': 'percent',
        'min_bump_vol': int(params['min_bump_vol']),
        'min_slide_vol': int(params['min_slide_vol']),
        'bump_up_pct': float(params['bump_up_pct']),
        'slide_up_pct': float(params['slide_up_pct']),
    })
    st.session_state.applied_config = new_config
    st.session_state.app_mode = "Exploration"

@st.fragment(run_every=5)
def auto_monitor_job(runner, job_name, bucket):
    # Minimalistic status monitoring
    latest_exec, error_msg = runner.get_latest_execution(job_name)
    
    if error_msg:
        st.caption(f"⚠️ Status check: {error_msg}")
    elif latest_exec:
        status = latest_exec['status']
        color = {"SUCCEEDED": "green", "RUNNING": "blue", "FAILED": "red", "PENDING": "orange"}.get(status, "gray")
        
        st.markdown(f"**Last Job Status:** :{color}[{status}] (`{latest_exec['id']}`)")
        
        if status == "SUCCEEDED":
            # Auto-download if new
            if st.session_state.get('last_loaded_exec_id') != latest_exec['id']:
                with st.spinner("New results found! Loading..."):
                    local_path = "cloud_results.csv"
                    success, msg = runner.download_results(bucket, "results.csv", local_path)
                    if success:
                        try:
                            df_res = pd.read_csv(local_path)
                            st.session_state.gs_results = df_res.sort_values('total_hits', ascending=False).head(50)
                            st.session_state.last_loaded_exec_id = latest_exec['id']
                            st.rerun()
                        except Exception: pass
        elif latest_exec['is_running']:
            st.caption("⏳ Job is running. Results will load automatically when finished.")

        # Log Viewer for Debugging
        with st.expander("View Cloud Logs", expanded=False):
            st.info("Logs are fetched on-demand to save resources.")
            if st.button("Refresh Logs"):
                with st.spinner("Fetching logs..."):
                    logs = runner.get_job_logs(job_name, latest_exec['id'])
                    st.code(logs, language="text")

def render_goal_seek(df, cli_args, val_report):
    # --- SIDEBAR INPUTS ---
    st.sidebar.title("Goal Seek Parameters")
    gs_params = {}
    b_len_start, b_len_end, b_len_step = render_range_input("Bump Length (min)", 1, 390, 3, 6, 1, "gs_b_len")
    gs_params['bump_len'] = (b_len_start, b_len_end, b_len_step)
    s_len_start, s_len_end, s_len_step = render_range_input("Slide Length (min)", 1, 390, 3, 6, 1, "gs_s_len")
    gs_params['slide_len'] = (s_len_start, s_len_end, s_len_step)
    
    st.sidebar.divider()
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
    min_bumps_req = st.sidebar.number_input("Min Bumps Required", value=0, step=1)
    
    st.sidebar.divider()
    run_cloud = st.sidebar.checkbox("☁️ Offload to Cloud (GCP)", value=True)
    
    if run_cloud:
        with st.sidebar.expander("🛠️ GCP Configuration", expanded=False):
            gcp_project = st.text_input("Project ID", value="sp500-479009", key="gs_gcp_project")
            gcp_region = st.text_input("Region", value="europe-west2", key="gs_gcp_region")
            gcp_job_name = st.text_input("Job Name", value="sp500-goal-seek", key="gs_gcp_job_name")
            gcp_bucket = st.text_input("GCS Bucket", value="sp500-goal-seek-results", key="gs_gcp_bucket")

    # Catalog Check
    from src.catalog import check_catalog_status
    cat_status, cat_msg = check_catalog_status()

    grid = generate_grid_from_ui(gs_params)
    grid['bump_threshold'] = [min_b_thresh]
    grid['slide_threshold'] = [min_s_thresh]

    # --- MAIN CONTENT ---
    if run_cloud:
        runner = CloudRunner(project_id=gcp_project, region=gcp_region)
        
        # 1. Trigger Section (Now at Top)
        st.write("### 🚀 Cloud Search Control")
        auto_monitor_job(runner, job_name=gcp_job_name, bucket=gcp_bucket)

        # Calculate search scale
        total_combos = 1
        for v in grid.values():
            total_combos *= len(v)
        
        st.markdown(f"**Search Scale:** `{total_combos}` combinations")
        with st.expander("View Parameter Summary", expanded=False):
            for k, v in grid.items():
                if len(v) > 1:
                    st.write(f"- **{k}**: {min(v)} to {max(v)} ({len(v)} steps)")
                else:
                    st.write(f"- **{k}**: {v[0]} (Locked)")

        fixed_params = { 'bump_thresh_type': 'percent', 'slide_thresh_type': 'percent' }

        config_dict = {
            "params_grid": grid, "fixed_params": fixed_params,
            "min_bumps": min_bumps_req, "gcs_output_path": f"gs://{gcp_bucket}/results.csv"
        }

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Start New Cloud Search", type="primary", use_container_width=True):
                with st.spinner("Triggering..."):
                    success, output = runner.run_job(gcp_job_name, config_dict)
                    if success:
                        st.session_state.last_loaded_exec_id = None # Force reload on next success
                        st.rerun()
                    else:
                        st.error(output)
        with col2:
            if st.button("📥 Force Download Results", use_container_width=True):
                with st.spinner("Downloading..."):
                    local_path = "cloud_results.csv"
                    success, msg = runner.download_results(gcp_bucket, "results.csv", local_path)
                    if success:
                        try:
                            df_res = pd.read_csv(local_path)
                            st.session_state.gs_results = df_res.sort_values('total_hits', ascending=False).head(50)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Load failed: {e}")
                    else:
                        st.error(msg)

        with st.expander("🛠️ Advanced / Manual Run", expanded=False):
            if cat_status != 'ok':
                st.info(f"ℹ️ **Local Catalog Status:** {cat_msg}\n\nThis affects local searches only. If you have deployed your cloud job correctly with a catalog, cloud searches will still be optimized.")
            
            st.code(runner.generate_gcloud_command(gcp_job_name, config_dict, wrap=True), language="bash")
            st.code(runner.get_deploy_instructions(gcp_job_name, "sp500-analyzer"), language="bash")

    else:
        st.write("### 💻 Local Search Control")
        if st.button("🚀 Run Local Goal Seek", type="primary", use_container_width=True):
            seeker = GoalSeeker(df)
            progress_bar = st.progress(0)
            status_text = st.empty()
            def update_progress(msg, pct):
                progress_bar.progress(pct)
                status_text.text(msg)
            start_t = time.time()
            results_df = seeker.search(grid, min_bumps=min_bumps_req, progress_callback=update_progress)
            if not results_df.empty:
                st.session_state.gs_results = results_df.sort_values('total_hits', ascending=False).head(50)
                st.success("Search complete.")
            else:
                st.error("No results found.")

    # --- RESULTS SECTION ---
    if 'gs_results' in st.session_state and st.session_state.gs_results is not None:
        st.divider()
        st.write("### 📊 Search Results")
        
        display_df = st.session_state.gs_results.copy()
        
        # Display Optimization Status
        opt_mode = display_df.iloc[0].get('optimization_mode', 'UNKNOWN') if not display_df.empty else 'UNKNOWN'
        
        if run_cloud:
            runner = CloudRunner(project_id=gcp_project, region=gcp_region)
            latest_exec, _ = runner.get_latest_execution(gcp_job_name)
            
            status_cols = st.columns([1, 1])
            with status_cols[0]:
                if latest_exec and latest_exec.get('duration'):
                    st.info(f"⏱️ Duration: **{latest_exec['duration']}**")
            with status_cols[1]:
                if opt_mode == 'CATALOG':
                    st.success("⚡ **Optimized (Catalog)**")
                elif opt_mode == 'NONE':
                    st.warning("⚠️ **Unoptimized (Raw Data)**")
                else:
                    st.caption(f"Mode: {opt_mode}")

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
            load_match_into_exploration(selected_params)
            st.rerun()
