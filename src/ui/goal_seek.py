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

    # Split into two groups
    bump_defs = param_defs[:4]
    slide_defs = param_defs[4:]
    
    # Helper to render a column of parameters
    def render_param_column(defs):
        local_combos = 1
        for i, (label, key, dtype, step) in enumerate(defs):
            current_val = sidebar_config.get(key, 0)
            
            with st.container():
                # Header Row: Checkbox | Locked Value
                # Using columns to put them on the same line
                c1, c2 = st.columns([0.7, 0.3])
                with c1:
                    is_varying = st.checkbox(label, key=f"vary_{key}")
                with c2:
                    st.caption(f"Lock: **{current_val}**")
                
                # Input Row (Only if varying)
                if is_varying:
                    r1, r2, r3 = st.columns(3)
                    
                    def_start = current_val
                    def_end = current_val + (step * 4)
                    
                    # Compact inputs with "S/E/St" labels or full names
                    start = r1.number_input("Start", value=dtype(def_start), key=f"start_{key}", step=step)
                    end = r2.number_input("End", value=dtype(def_end), key=f"end_{key}", step=step)
                    step_val = r3.number_input("Step", value=dtype(step), key=f"step_{key}", step=step)
                    
                    if step_val <= 0:
                        st.error("Step > 0")
                        step_val = 1
                        
                    # Calculate Range
                    if dtype == int:
                        vals = np.arange(start, end + 0.0001, step_val).astype(int).tolist()
                    else:
                        vals = np.arange(start, end + 0.00001, step_val).tolist()
                        vals = [round(x, 4) for x in vals]
                    
                    if len(vals) > 0:
                        params_grid[key] = vals
                        local_combos *= len(vals)
                        st.caption(f"Testing {len(vals)} values")
                    else:
                        st.warning("Empty")
            
            # Add divider except for the last item
            if i < len(defs) - 1:
                 st.divider()
                 
        return local_combos

    # Layout: Two Columns
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### Bump Parameters")
        combos_left = render_param_column(bump_defs)
        
    with col_right:
        st.markdown("#### Slide Parameters")
        combos_right = render_param_column(slide_defs)
        
    total_combinations = combos_left * combos_right

    st.markdown("---")
    st.write(f"**Total Combinations to Search:** {total_combinations}")
    
    if total_combinations > 5000:
        st.warning("⚠️ High combination count. Search may be slow.")

    # 3. Run Search
    if st.button("Run Goal Seek Search", type="primary", disabled=(total_combinations < 1)):
        seeker = GoalSeeker(df)
        
        # Prepare fixed params (everything not in params_grid)
        fixed_params = {k: v for k, v in sidebar_config.items() if k not in params_grid}
        
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
