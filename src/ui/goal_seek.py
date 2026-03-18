import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from src.search_engine import GoalSeeker
from src.ui.utils import log_perf, derive_result_blob_name, render_version_info
from src.cloud_runner import CloudRunner
from src.analyzer import find_bumps_and_slides
from src.ui.results import render_results

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

def format_params_grid(grid):
    if not grid:
        return "-"
    
    parts = []
    # Prioritize key params
    order = ['bump_len', 'slide_len', 'bump_threshold', 'slide_threshold']
    
    # 1. Add prioritized keys
    for k in order:
        if k in grid:
            vals = grid[k]
            if isinstance(vals, list):
                if len(vals) > 1:
                    try:
                        # Try to detect range
                        v_sorted = sorted(list(set(vals)))
                        # check if int-like range
                        if all(isinstance(x, (int, float)) and x == int(x) for x in v_sorted):
                            v_ints = [int(x) for x in v_sorted]
                            if len(v_ints) > 2 and v_ints == list(range(min(v_ints), max(v_ints)+1)):
                                val_str = f"{min(v_ints)}-{max(v_ints)}"
                            else:
                                # Start..End
                                val_str = f"{min(v_ints)}..{max(v_ints)}"
                        else:
                            val_str = f"{min(vals)}..{max(vals)}"
                    except:
                        val_str = f"{len(vals)} vals"
                elif len(vals) == 1:
                    val_str = str(vals[0])
                else:
                    val_str = ""
            else:
                val_str = str(vals)
            
            # Shorten keys
            short_k = k.replace("bump", "B").replace("slide", "S").replace("threshold", "Th").replace("len", "L")
            parts.append(f"{short_k}:{val_str}")
            
    return " | ".join(parts)

def render_goal_seek(df, cli_args, val_report):
    # --- SIDEBAR INPUTS ---
    with st.sidebar:
        gs_params = {}
        
        # Lengths (Compact Mode)
        b_len_start, b_len_end, b_len_step = render_range_input("Bump Length (min)", 1, 2880, 10, 10, 1, "gs_b_len", compact=True)
        gs_params['bump_len'] = (b_len_start, b_len_end, b_len_step)
        
        s_len_start, s_len_end, s_len_step = render_range_input("Slide Length (min)", 1, 2880, 10, 10, 1, "gs_s_len", compact=True)
        gs_params['slide_len'] = (s_len_start, s_len_end, s_len_step)
        
        # Thresholds & Direction
        st.markdown("**Bump Settings**")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            b_dir = st.radio("Bump Direction", ["Positive", "Negative"], horizontal=True, label_visibility="collapsed", key="gs_b_dir")
        with col_b2:
            min_b_thresh = st.number_input("Min Bump %", value=0.5, step=0.1, key="gs_min_b_thresh")

        st.markdown("**Slide Settings**")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            s_dir = st.radio("Slide Direction", ["Positive", "Negative"], horizontal=True, label_visibility="collapsed", key="gs_s_dir")
        with col_s2:
            min_s_thresh = st.number_input("Min Slide %", value=0.3, step=0.1, key="gs_min_s_thresh")
        
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
        
        # Year Range (Always Visible, above Advanced)
        st.markdown("**Search Range**")
        min_year = int(df['date'].dt.year.min())
        max_year = int(df['date'].dt.year.max())
        
        col_y1, col_y2 = st.columns(2)
        with col_y1:
            start_year = st.number_input("Start Year", min_value=min_year, max_value=max_year, value=min_year)
        with col_y2:
            end_year = st.number_input("End Year", min_value=min_year, max_value=max_year, value=max_year)

        # Execution
        run_cloud = st.checkbox("☁️ Cloud Run", value=True)
        
        if run_cloud:
            with st.expander("🛠️ GCP Configuration", expanded=False):
                gcp_project = st.text_input("Project ID", value="sp500-479009", key="gs_gcp_project")
                gcp_region = st.text_input("Region", value="europe-west2", key="gs_gcp_region")
                gcp_job_name = st.text_input("Job Name", value="sp500-goal-seek", key="gs_gcp_job_name")
                gcp_bucket = st.text_input("GCS Bucket", value="sp500-goal-seek-results", key="gs_gcp_bucket")
                
                # Use authenticated username
                user_label = st.session_state.get("username", "user")
                st.info(f"Running as: **{user_label}**")

        render_version_info()

    # --- MAIN CONTENT ---

    # Prepare Config Grid
    grid = generate_grid_from_ui(gs_params)
    
    # Adjust thresholds based on direction
    # If Negative, we want to look for values <= -threshold
    # The backend will handle the logic if we pass the direction or if we sign the threshold?
    # Let's pass the raw threshold and a direction flag, OR just sign the threshold.
    # The user said: "toggle for positive and negative and the results should filter for data that exceeds those magnitudes"
    # If I pass -0.5, logic should be change <= -0.5
    # If I pass 0.5, logic should be change >= 0.5
    
    final_b_thresh = min_b_thresh if b_dir == "Positive" else -min_b_thresh
    final_s_thresh = min_s_thresh if s_dir == "Positive" else -min_s_thresh
    
    grid['bump_threshold'] = [final_b_thresh]
    grid['slide_threshold'] = [final_s_thresh]
    
    fixed_params = { 
        'bump_thresh_type': 'percent', 
        'slide_thresh_type': 'percent',
        'start_year': start_year,
        'end_year': end_year
    }

    # Calculate and display estimate
    total_configs = 1
    for k, v in grid.items():
        total_configs *= len(v)
    
    est_time_mins = (total_configs / 1000) * 6
    
    st.info(f"**Estimated Workload:** {total_configs:,} configurations.  \n"
            f"**Rough Time Estimate:** ~{est_time_mins:.1f} minutes (based on 6 mins/1000 configs).")

    if run_cloud:
        runner = CloudRunner(project_id=gcp_project, region=gcp_region)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Trigger Cloud Search", type="primary", use_container_width=True):
                # Generate unique Run ID
                run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.session_state.current_cloud_run_id = run_id
                
                # Sanitize user label
                safe_label = "".join([c for c in user_label if c.isalnum() or c in ('-', '_')]).strip()
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
                        
                        # Log submission
                        try:
                            hist_blob = "submission_history.json"
                            history = runner.read_json_blob(gcp_bucket, hist_blob) or []
                            history.append({
                                "run_id": run_id,
                                "timestamp": datetime.now().isoformat(),
                                "user_label": safe_label,
                                "total_configs": total_configs,
                                "est_time_mins": est_time_mins,
                                "params_grid": grid,
                                "fixed_params": fixed_params
                            })
                            # Keep last 100
                            if len(history) > 100: history = history[-100:]
                            runner.write_json_blob(gcp_bucket, hist_blob, history)
                        except Exception as e:
                            print(f"Failed to log submission: {e}")

                    else:
                        st.error(output)

        with col2:
            if st.button("🔄 Refresh Status", use_container_width=True):
                 # 1. Update Current Job Status
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
                     
                     # Auto-download results if SUCCEEDED
                     if status == "SUCCEEDED":
                        target = None
                        if st.session_state.get('current_cloud_run_id'):
                             # Use authenticated username for label
                             current_user = st.session_state.get("username", "user")
                             safe_label = "".join([c for c in current_user if c.isalnum() or c in ('-', '_')]).strip()
                             if not safe_label: safe_label = "user"
                             target = f"results_{safe_label}_{st.session_state.current_cloud_run_id}.csv"
                        else:
                            target = "results.csv" # Fallback if no specific run ID known
                        
                        with st.spinner(f"Run Complete! Downloading {target}..."):
                            local_path = "cloud_results.csv"
                            success, msg = runner.download_results(gcp_bucket, target, local_path)
                            if success:
                                try:
                                    df_res = pd.read_csv(local_path)
                                    st.session_state.gs_results = df_res
                                    st.success(f"Downloaded {len(df_res)} results.")
                                    # We do NOT rerun here immediately, so we can update history first
                                except Exception as e:
                                    st.error(f"Failed to parse CSV: {e}")
                            else:
                                st.warning(f"Could not download results: {msg}")

                 # 2. Update History
                 with st.spinner("Fetching run history..."):
                     # Fetch submission history
                     sub_hist = runner.read_json_blob(gcp_bucket, "submission_history.json") or []
                     sub_map = {item['run_id']: item for item in sub_hist}

                     # Fetch metadata blobs (Completed jobs)
                     blobs = runner.list_blobs(gcp_bucket, prefix="metadata_")

                     # Fetch recent executions to check for failures
                     recent_execs = runner.list_recent_executions(gcp_job_name, limit=50)
                     
                     def find_matching_execution(sub_ts_iso):
                         try:
                             if not sub_ts_iso: return None
                             # sub_ts_iso is from datetime.now().isoformat()
                             sub_dt = datetime.fromisoformat(sub_ts_iso)
                             sub_ts = sub_dt.timestamp()
                             
                             best_match = None
                             min_diff = float('inf')
                             
                             for exc in recent_execs:
                                 # exc['create_time'] is a datetime object
                                 exec_dt = exc['create_time']
                                 exec_ts = exec_dt.timestamp()
                                 
                                 diff = abs(exec_ts - sub_ts)
                                 
                                 # 2 minutes tolerance to account for clock skew and startup time
                                 if diff < 120: 
                                     if diff < min_diff:
                                         min_diff = diff
                                         best_match = exc
                             
                             return best_match
                         except Exception:
                             return None
                     
                     combined_history = []
                     seen_run_ids = set()

                     # Process Completed Jobs
                     for blob_name in blobs[:50]:
                         meta = runner.read_json_blob(gcp_bucket, blob_name)
                         if meta:
                             run_id = meta.get('run_id')
                             if not run_id:
                                 # Try to extract from blob name: metadata_{safe_label}_{run_id}.json
                                 parts = blob_name.replace("metadata_", "").replace(".json", "").split("_")
                                 if len(parts) >= 2:
                                     run_id = "_".join(parts[-2:])
                             
                             if run_id:
                                seen_run_ids.add(run_id)
                                # Merge with submission info if available
                                if run_id in sub_map:
                                    sub = sub_map[run_id]
                                    meta['est_time_mins'] = sub.get('est_time_mins')
                                    meta['total_configs'] = sub.get('total_configs')
                             
                             meta['status'] = 'COMPLETED'
                             # Derive result blob name from metadata blob name
                             # metadata_user_2026...json -> results_user_2026...csv
                             result_blob_name = derive_result_blob_name(blob_name)
                             meta['result_blob'] = result_blob_name
                             combined_history.append(meta)

                     # Add Submitted (but not yet completed/metadata-ed) jobs
                     for item in sub_hist:
                         if item['run_id'] not in seen_run_ids:
                             item['status'] = 'SUBMITTED'
                             
                             # Check actual cloud status
                             match = find_matching_execution(item.get('timestamp'))
                             if match:
                                 item['status'] = match['status']
                             
                             item['total_results'] = '-' # Placeholder
                             item['duration_sec'] = 0
                             combined_history.append(item)
                     
                     # Sort by timestamp desc
                     combined_history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                     st.session_state.run_history = combined_history

        # --- RUN HISTORY ---
        with st.expander("📂 Cloud Run History", expanded=False):
             if 'run_history' in st.session_state and st.session_state.run_history:
                 # Display Table
                 hist_data = []
                 now = datetime.now()
                 for h in st.session_state.run_history:
                     # Format timestamp nicely
                     ts_str = h.get('timestamp', '')
                     ts_dt = None
                     try:
                         ts_dt = datetime.fromisoformat(ts_str)
                         ts_fmt = ts_dt.strftime("%Y-%m-%d %H:%M")
                     except:
                         ts_fmt = ts_str
                     
                     # Time Since
                     time_since = ""
                     if ts_dt:
                         diff = now - ts_dt
                         mins = int(diff.total_seconds() / 60)
                         if mins < 60:
                             time_since = f"{mins}m ago"
                         else:
                             hours = int(mins / 60)
                             rem_mins = mins % 60
                             time_since = f"{hours}h {rem_mins}m ago"

                     # Est Duration
                     est_dur = h.get('est_time_mins')
                     est_str = f"~{est_dur:.1f}m" if est_dur else "-"
                     
                     # Actual Duration
                     dur_sec = h.get('duration_sec', 0)
                     act_str = f"{dur_sec:.1f}s" if dur_sec > 0 else "-"
                     
                     # Params Summary
                     p_grid = h.get('params_grid')
                     p_summary = format_params_grid(p_grid)

                     hist_data.append({
                         "Run Time": ts_fmt,
                         "Time Since": time_since,
                         "User": h.get('user_label', 'Unknown'),
                         "Status": h.get('status', 'UNKNOWN'),
                         "Est. Time": est_str,
                         "Actual Time": act_str,
                         "Configs": str(h.get('total_configs', '-')),
                         "Params": p_summary,
                         "Results": str(h.get('total_results', 'N/A')),
                         "Max Conf": f"{h.get('max_confidence', 0):.2f}%" if h.get('max_confidence') else "-",
                         "_blob": h.get('result_blob') # Hidden column
                     })
                 
                 df_hist = pd.DataFrame(hist_data)
                 
                 st.caption("Select a run to load its results.")
                 event = st.dataframe(
                     df_hist,
                     column_config={
                        "_blob": None # Hide blob name
                     },
                     use_container_width=True,
                     on_select="rerun",
                     selection_mode="single-row",
                     hide_index=True,
                     key="cloud_history_table"
                 )
                 
                 if len(event.selection.rows) > 0:
                     idx = event.selection.rows[0]
                     selected_run = df_hist.iloc[idx]
                     blob_name = selected_run['_blob']
                     
                     # Display Params Detail
                     # Map back to original history item (df_hist preserves order)
                     if idx < len(st.session_state.run_history):
                         orig_item = st.session_state.run_history[idx]
                         p_grid = orig_item.get('params_grid')
                         f_params = orig_item.get('fixed_params')
                         if p_grid:
                             with st.expander("ℹ️ Search Parameters", expanded=False):
                                 st.json({"grid": p_grid, "fixed": f_params})

                     # Check if we need to load (avoid reload loop)
                     if not blob_name or pd.isna(blob_name):
                         st.warning("This job is submitted but results are not yet available (or it failed).")
                     elif st.session_state.get('last_loaded_blob') != blob_name:
                         with st.spinner(f"Loading results from {selected_run['Run Time']}..."):
                             local_path = "cloud_results.csv"
                             success, msg = runner.download_results(gcp_bucket, blob_name, local_path)
                             if success:
                                 try:
                                     df_res = pd.read_csv(local_path)
                                     st.session_state.gs_results = df_res
                                     st.session_state.last_loaded_blob = blob_name
                                     st.success(f"Loaded {len(df_res)} results.")
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
            # Calculate Confidence
            if 'total_hits' in df_res.columns and 'total_bumps' in df_res.columns:
                 df_res['confidence'] = df_res.apply(
                     lambda x: (x['total_hits'] / x['total_bumps'] * 100) if x['total_bumps'] > 0 else 0, axis=1
                 )
            
            # Sort by Confidence (or total_hits as fallback)
            if 'confidence' in df_res.columns:
                 df_res = df_res.sort_values('confidence', ascending=False)
                 # Reorder columns to put confidence first
                 cols = ['confidence'] + [c for c in df_res.columns if c != 'confidence']
                 df_res = df_res[cols]
            else:
                 df_res = df_res.sort_values('total_hits', ascending=False)

            # Metrics based on Best Result
            best_row = df_res.iloc[0]
            num_configs = len(df_res)
            best_bumps = best_row.get('total_bumps', 0)
            best_hits = best_row.get('total_hits', 0)
            best_conf = best_row.get('confidence', 0)
            best_scope_rows = best_row.get('scope_rows', 0)
            
            col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
            col_s1.metric("Configurations", f"{num_configs:,.0f}")
            col_s2.metric("Total Windows", f"{best_scope_rows:,.0f}", help="Total analyzed windows in the best configuration")
            col_s3.metric("Total Bumps (Best)", f"{best_bumps:,.0f}")
            col_s4.metric("Total Hits (Best)", f"{best_hits:,.0f}")
            col_s5.metric("Confidence (Best)", f"{best_conf:.2f}%")
            
            # Interactive Table
            event = st.dataframe(
                df_res, 
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # Download Button for CSV
            csv = df_res.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name="goal_seek_results.csv",
                mime="text/csv",
            )
            
            # --- Visualization Logic ---
            if len(event.selection.rows) > 0:
                selected_row_idx = event.selection.rows[0]
                row_data = df_res.iloc[selected_row_idx]
                
                st.divider()
                st.subheader(f"Detailed Analysis (Row {selected_row_idx})")
                
                # 1. Extract Params
                try:
                    # Construct config dict for find_bumps_and_slides
                    viz_config = {
                        'bump_len': int(row_data['bump_len']),
                        'bump_threshold': float(row_data['bump_threshold']),
                        'bump_thresh_type': str(row_data.get('bump_thresh_type', 'percent')),
                        'slide_len': int(row_data['slide_len']),
                        'slide_threshold': float(row_data['slide_threshold']),
                        'slide_thresh_type': str(row_data.get('slide_thresh_type', 'percent')),
                        'min_bump_vol': int(row_data.get('min_bump_vol', 0)),
                        'min_slide_vol': int(row_data.get('min_slide_vol', 0)),
                        'bump_up_pct': float(row_data.get('bump_up_pct', 0.0)),
                        'slide_up_pct': float(row_data.get('slide_up_pct', 0.0)),
                        'time_range': None, # Default full day
                        'days_of_week': None, # Default all days
                        'layout_order': "Table Top", # Default layout
                        # Pass through scalar values for potential plotting needs
                        'selected_years': sorted(df['date'].dt.year.unique()), # All years
                        'all_years': sorted(df['date'].dt.year.unique())
                    }
                    
                    with st.expander("Analysis Configuration", expanded=False):
                        st.json({k: v for k, v in viz_config.items() if k not in ['selected_years', 'all_years']})
                    
                    with st.spinner("Finding matches for visualization..."):
                        # Filter dataframe if scope metadata is available
                        df_viz = df
                        if 'scope_start' in row_data and not pd.isna(row_data['scope_start']):
                            try:
                                s_start = pd.to_datetime(row_data['scope_start'])
                                s_end = pd.to_datetime(row_data['scope_end'])
                                df_viz = df[(df['date'] >= s_start) & (df['date'] <= s_end)].copy()
                            except Exception as e:
                                print(f"Error filtering viz dataframe: {e}")

                        # Run Analysis Locally for this specific config
                        results, stats = find_bumps_and_slides(
                            df_viz,
                            viz_config['bump_len'], viz_config['bump_threshold'], viz_config['bump_thresh_type'],
                            viz_config['slide_len'], viz_config['slide_threshold'], viz_config['slide_thresh_type'],
                            min_bump_vol=viz_config['min_bump_vol'],
                            min_slide_vol=viz_config['min_slide_vol'],
                            bump_up_pct=viz_config['bump_up_pct'],
                            slide_up_pct=viz_config['slide_up_pct']
                        )
                        
                        if not results.empty:
                            render_results(results, stats, viz_config, df, val_report)
                        else:
                            st.warning("No matches found when re-running with these parameters locally. (Data mismatch?)")
                            
                except Exception as e:
                    st.error(f"Error preparing visualization: {str(e)}")
            
        else:
            st.info("No matches in result set.")
