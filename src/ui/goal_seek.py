import streamlit as st
import numpy as np
import pandas as pd
from src.search_engine import GoalSeeker

def render_goal_seek_ui(df, sidebar_config):
    st.title("Goal Seek / Reverse Search")
    
    st.markdown("""
    Define a target Conversion Rate and vary parameters to find combinations that achieve it.
    
    *   **Locked Parameters**: Values taken directly from the **Sidebar**.
    *   **Vary Parameters**: Check the box to define a search range (Start, End, Step).
    """)
    
    st.info("💡 **Tip:** Keep the number of varied parameters and their ranges reasonable to avoid extremely long search times.")

    # 1. Target
    target_cr = st.number_input("Target Conversion Rate (Hit Ratio %)", min_value=0.0, max_value=100.0, value=50.0, step=1.0)
    
    st.divider()
    
    # 2. Parameter Configuration
    st.subheader("Parameter Configuration")
    
    # Dictionary to hold the ranges for the search
    params_grid = {}
    
    # Parameter Definitions: (Label, key, type, default_step)
    # We assume reasonable defaults for min/max handling in the UI logic
    param_defs = [
        ("Bump Length (min)", 'bump_len', int, 1),
        ("Bump Threshold", 'bump_threshold', float, 0.05),
        ("Bump Up %", 'bump_up_pct', float, 5.0),
        ("Min Bump Volume", 'min_bump_vol', int, 10000),
        
        ("Slide Length (min)", 'slide_len', int, 1),
        ("Slide Threshold", 'slide_threshold', float, 0.05),
        ("Slide Up %", 'slide_up_pct', float, 5.0),
        ("Min Slide Volume", 'min_slide_vol', int, 10000),
    ]
    
    total_combinations = 1
    
    # Create a cleaner grid layout
    for label, key, dtype, step in param_defs:
        current_val = sidebar_config.get(key, 0)
        
        # Use an expander or a container with columns for each row
        with st.container():
            c1, c2, c3 = st.columns([0.25, 0.15, 0.6])
            
            with c1:
                # Checkbox to unlock
                is_varying = st.checkbox(f"{label}", key=f"vary_{key}", help=f"Check to search a range for {label}")
                
            with c2:
                # Show current locked value
                st.caption(f"Locked: **{current_val}**")
                
            with c3:
                if is_varying:
                    # Range Inputs
                    r1, r2, r3 = st.columns(3)
                    
                    # Defaults
                    def_start = current_val
                    def_end = current_val + (step * 4)
                    
                    start = r1.number_input(f"Start", value=dtype(def_start), key=f"start_{key}", step=step)
                    end = r2.number_input(f"End", value=dtype(def_end), key=f"end_{key}", step=step)
                    step_val = r3.number_input(f"Step", value=dtype(step), key=f"step_{key}", step=step)
                    
                    # Validate Step
                    if step_val <= 0:
                        st.error("Step must be > 0")
                        step_val = 1 # prevent div by zero
                        
                    # Calculate Range
                    # np.arange includes start, excludes end. We usually want inclusive for UI "End".
                    # So we add a small epsilon
                    if dtype == int:
                        vals = np.arange(start, end + 0.0001, step_val).astype(int).tolist()
                    else:
                        vals = np.arange(start, end + 0.00001, step_val).tolist()
                        vals = [round(x, 4) for x in vals]
                    
                    if len(vals) == 0:
                        st.warning("Range empty")
                    else:
                        st.caption(f"Testing {len(vals)} values")
                        params_grid[key] = vals
                        total_combinations *= len(vals)
                else:
                    # Not varying, just placeholder to align
                    st.write("")
        
        st.markdown("---") # Thin separator

    st.write(f"**Total Combinations to Search:** {total_combinations}")
    
    if total_combinations > 5000:
        st.warning("⚠️ High combination count. Search may be slow.")

    # 3. Run Search
    if st.button("Run Goal Seek Search", type="primary", disabled=(total_combinations < 1)):
        seeker = GoalSeeker(df)
        
        # Prepare fixed params:
        # Everything in sidebar_config that is NOT in params_grid is fixed.
        # This allows GoalSeeker to use the sidebar values for things we didn't vary.
        fixed_params = {k: v for k, v in sidebar_config.items() if k not in params_grid}
        
        # Add Threshold Types explicitly (they are in sidebar_config usually, but ensure they pass through)
        # Note: sidebar_config contains 'bump_thresh_type', 'slide_thresh_type', 'time_range', 'days_of_week' etc.
        # These will be passed in fixed_params automatically by the logic above.
        
        pbar = st.progress(0.0)
        status = st.empty()
        
        def update_progress(msg, pct):
            status.text(msg)
            pbar.progress(pct)
            
        try:
            results_df = seeker.search(
                params_grid, 
                fixed_params, 
                target_cr_min=target_cr, 
                progress_callback=update_progress
            )
            
            pbar.progress(1.0)
            status.text("Search Complete.")
            
            if not results_df.empty:
                st.success(f"✅ Found {len(results_df)} configurations achieving >= {target_cr}% Conversion Rate.")
                
                # Sort
                results_df = results_df.sort_values('conversion_rate', ascending=False)
                
                # Display
                st.dataframe(
                    results_df.style.format({
                        'conversion_rate': "{:.2f}%",
                        'bump_threshold': "{:.2f}",
                        'slide_threshold': "{:.2f}",
                        'bump_up_pct': "{:.1f}",
                        'slide_up_pct': "{:.1f}"
                    }),
                    use_container_width=True
                )
                
                # Download
                csv = results_df.to_csv(index=False)
                st.download_button("Download Results CSV", csv, "goal_seek_results.csv", "text/csv")
                
            else:
                st.error("No configurations found meeting the target Conversion Rate.")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
