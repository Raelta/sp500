import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
from src.search_engine import GoalSeeker
from src.ui.utils import log_perf
from src.cloud_runner import CloudRunner

def render_range_input(label, min_val, max_val, default_start, default_end, default_step, key_prefix, compact=False):
    # Use st.markdown/st.columns to respect current context (expander or sidebar)
    st.markdown(f"**{label}**")
    is_float = isinstance(default_step, float)
    col1, col2, col3 = st.columns(3)
    
    label_visibility = "collapsed" if compact else "visible"

    with col1:
        if compact:
            st.markdown("<div style='font-size:0.8em; margin-bottom:0px; color:#888'>Start</div>", unsafe_allow_html=True)
        start = st.number_input("Start", min_value=min_val, max_value=max_val, value=default_start, key=f"{key_prefix}_start", label_visibility=label_visibility)
    with col2:
        if compact:
            st.markdown("<div style='font-size:0.8em; margin-bottom:0px; color:#888'>End</div>", unsafe_allow_html=True)
        end = st.number_input("End", min_value=min_val, max_value=max_val, value=default_end, key=f"{key_prefix}_end", label_visibility=label_visibility)
    with col3:
        if compact:
            st.markdown("<div style='font-size:0.8em; margin-bottom:0px; color:#888'>Step</div>", unsafe_allow_html=True)
        s_min = 0.0 if is_float else 0
        s_max = float(max_val) if is_float else int(max_val)
        s_val = float(default_step) if is_float else int(default_step)
        step = st.number_input("Step", min_value=s_min, max_value=s_max, value=s_val, key=f"{key_prefix}_step", label_visibility=label_visibility)
        
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

def render_goal_seek(df, cli_args, val_report):
    # --- SIDEBAR INPUTS ---
    with st.sidebar:
        st.header("Goal Seek Parameters")
        gs_params = {}
        
        # Lengths (Compact Mode)
        b_len_start, b_len_end, b_len_step = render_range_input("Bump Length (min)", 1, 2880, 3, 6, 1, "gs_b_len", compact=True)
        gs_params['bump_len'] = (b_len_start, b_len_end, b_len_step)
        
        s_len_start, s_len_end, s_len_step = render_range_input("Slide Length (min)", 1, 2880, 3, 6, 1, "gs_s_len", compact=True)
        gs_params['slide_len'] = (s_len_start, s_len_end, s_len_step)
        
        st.markdown("---")
        
        # Thresholds (Side by side)
        col_th1, col_th2 = st.columns(2)
        with col_th1:
            min_b_thresh = st.number_input("Min Bump Thresh %", value=3.0, step=0.1, key="gs_min_b_thresh")
        with col_th2:
            min_s_thresh = st.number_input("Min Slide Thresh %", value=3.0, step=0.1, key="gs_min_s_thresh")
        
        st.markdown("---")
        
        # Advanced Parameters Expander
        with st.expander("Advanced parameters", expanded=False):
            # Volumes
            b_vol_start, b_vol_end, b_vol_step = render_range_input("Min Bump Volume", 0, 10000000, 0, 0, 10000, "gs_b_vol", compact=True)
            gs_params['min_bump_vol'] = (b_vol_start, b_vol_end, b_vol_step)
            
            s_vol_start, s_vol_end, s_vol_step = render_range_input("Min Slide Volume", 0, 10000000, 0, 0, 10000, "gs_s_vol", compact=True)
            gs_params['min_slide_vol'] = (s_vol_start, s_vol_end, s_vol_step)
            
            # Percentages
            b_up_start, b_up_end, b_up_step = render_range_input("Bump Up %", 0, 100, 0, 0, 5, "gs_b_up", compact=True)
            gs_params['bump_up_pct'] = (b_up_start, b_up_end, b_up_step)
            
            s_up_start, s_up_end, s_up_step = render_range_input("Slide Up %", 0, 100, 0, 0, 5, "gs_s_up", compact=True)
            gs_params['slide_up_pct'] = (s_up_start, s_up_end, s_up_step)

            min_bumps_req = st.number_input("Min Bumps Req", value=0, step=1)
        
        st.markdown("---")
        
        # Execution
        run_cloud = st.checkbox("☁️ Cloud Run", value=True)
        
        if run_cloud:
            with st.expander("🛠️ GCP Configuration", expanded=False):
                gcp_project = st.text_input("Project ID", value="sp500-479009", key="gs_gcp_project")
                gcp_region = st.text_input("Region", value="europe-west2", key="gs_gcp_region")
                gcp_job_name = st.text_input("Job Name", value="sp500-goal-seek", key="gs_gcp_job_name")
                gcp_bucket = st.text_input("GCS Bucket", value="sp500-goal-seek-results", key="gs_gcp_bucket")
                gcp_user_label = st.text_input("User / Run Label", value="user", key="gs_gcp_user_label", help="Identifier for who is running this job. Used in filenames.")

    # --- MAIN CONTENT ---
    st.title("Goal Seek")

    # Prepare Config Grid
    grid = generate_grid_from_ui(gs_params)
    grid['bump_threshold'] = [min_b_thresh]
    grid['slide_threshold'] = [min_s_thresh]
    
    fixed_params = { 'bump_thresh_type': 'percent', 'slide_thresh_type': 'percent' }

    if run_cloud:
        runner = CloudRunner(project_id=gcp_project, region=gcp_region)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 Trigger Cloud Search", type="primary", use_container_width=True):
                # Generate unique Run ID
                run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.session_state.current_cloud_run_id = run_id
                
                # Sanitize user label
                safe_label = "".join([c for c in gcp_user_label if c.isalnum() or c in ('-', '_')]).strip()
                if not safe_label: safe_label = "user"
                
                result_blob = f"results_{safe_label}_{run_id}.csv"
                metadata_blob = f"metadata_{safe_label}_{run_id}.json"
                
                config_dict = {
                    "params_grid": grid, 
                    "fixed_params": fixed_params, 
                    "min_bumps": min_bumps_req,
                    "user_label": safe_label,
                    "gcs_output_path": f"gs://{gcp_bucket}/{result_blob}",
                    "metadata_output_path": f"gs://{gcp_bucket}/{metadata_blob}"
                }
                
                with st.spinner("Queueing Job..."):
                    success, output = runner.run_job(gcp_job_name, config_dict)
                    if success:
                        st.success(f"Job Queued! Run ID: {run_id}")
                    else:
                        st.error(output)

        with col2:
            if st.button("🔄 Refresh Status", use_container_width=True):
                 latest_exec, error_msg = runner.get_latest_execution(gcp_job_name)
                 if error_msg:
                     st.error(f"Status check failed: {error_msg}")
                 elif latest_exec:
                     status = latest_exec['status']
                     color = {"SUCCEEDED": "green", "RUNNING": "blue", "FAILED": "red", "PENDING": "orange"}.get(status, "gray")
                     st.markdown(f"**Status:** :{color}[{status}]")
                     if latest_exec.get('duration'):
                         st.markdown(f"**Duration:** {latest_exec['duration']}")
                     if latest_exec.get('is_running'):
                         pct, p_msg = runner.get_latest_progress(gcp_job_name, latest_exec['id'])
                         st.progress(pct, text=f"{pct*100:.1f}% - {p_msg}")

        with col3:
            if st.button("📥 Download & Summarize", use_container_width=True):
                # Determine target file
                target = None
                if st.session_state.get('current_cloud_run_id'):
                     safe_label = "".join([c for c in gcp_user_label if c.isalnum() or c in ('-', '_')]).strip()
                     if not safe_label: safe_label = "user"
                     target = f"results_{safe_label}_{st.session_state.current_cloud_run_id}.csv"
                else:
                    target = "results.csv" # Fallback if no specific run ID known
                
                with st.spinner(f"Downloading {target}..."):
                    local_path = "cloud_results.csv"
                    success, msg = runner.download_results(gcp_bucket, target, local_path)
                    if success:
                        try:
                            df_res = pd.read_csv(local_path)
                            st.session_state.gs_results = df_res
                            st.success(f"Downloaded {len(df_res)} results.")
                        except Exception as e:
                            st.error(f"Failed to parse CSV: {e}")
                    else:
                        st.error(msg)
                        
    else:
        # Local Mode
        if st.button("🚀 Run Local Search", type="primary"):
            seeker = GoalSeeker(df)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(msg, pct):
                progress_bar.progress(pct)
                status_text.text(msg)
                
            start_t = time.time()
            results_df = seeker.search(grid, min_bumps=min_bumps_req, progress_callback=update_progress)
            
            if not results_df.empty:
                st.session_state.gs_results = results_df.sort_values('total_hits', ascending=False)
                st.success(f"Search complete. Found {len(results_df)} matches.")
            else:
                st.error("No results found.")

    # --- RESULTS SUMMARY ---
    if 'gs_results' in st.session_state and st.session_state.gs_results is not None:
        st.divider()
        st.write("### 📊 Results Summary")
        
        df_res = st.session_state.gs_results
        
        if not df_res.empty:
            total_hits = df_res['total_hits'].sum()
            true_hits = df_res['true_hits'].sum() if 'true_hits' in df_res.columns else 0
            matches = len(df_res)
            hit_percentage = (total_hits / matches) if matches > 0 else 0
            
            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("Total Hits", f"{total_hits:,.0f}")
            col_s2.metric("True Hits", f"{true_hits:,.0f}")
            col_s3.metric("Hit Percentage (Avg Hits/Match)", f"{hit_percentage:.2f}")
            
            st.dataframe(df_res, use_container_width=True)
            
            # Download Button for CSV
            csv = df_res.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name="goal_seek_results.csv",
                mime="text/csv",
            )
        else:
            st.info("No matches in result set.")
