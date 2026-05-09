import streamlit as st
import pandas as pd
import time as time_module
from src.visualizer import plot_pattern
from src.news_provider import get_google_news_url
from src.ui.utils import log_perf, get_change_labels

def render_results(results, stats, config, df_filtered, val_report=None):
    """
    Renders the analysis results, including statistics, table, and charts.
    
    Args:
        results: DataFrame of found patterns.
        stats: Dictionary of hit/miss statistics.
        config: Configuration dict from sidebar.
        df_filtered: The filtered source dataframe (for plotting).
        val_report: Validation report dictionary (optional, used for yearly stats).
    """
    layout_order = config['layout_order']
    bump_len = config['bump_len']
    slide_len = config['slide_len']
    
    bump_type = config.get('bump_thresh_type', 'percent')
    slide_type = config.get('slide_thresh_type', 'percent')
    
    bump_label, slide_label, bump_suffix, slide_suffix = get_change_labels(bump_type, slide_type)

    # Display Stats (Hit Rate)
    if stats:
        with st.expander("📊 Pattern Statistics (Hit Rate)", expanded=True):
            col0, col1, col2, col3, col4 = st.columns(5)
            col0.metric("Total Windows", f"{stats.get('total_rows', 0):,.0f}", help="Total number of analyzed windows/bars")
            col1.metric("Total Bumps", f"{stats['total_bumps']:,.0f}", help="Candidates matching Bump criteria")
            col2.metric("Total Hits", f"{stats.get('total_hits', stats.get('hits', 0)):,.0f}", help="All overlapping patterns")
            col3.metric("True Hits", f"{stats.get('true_hits', 0):,.0f}", help="Best unique patterns (overlap removed)")
            col4.metric("Misses", f"{stats['misses']:,.0f}", help="Bumps NOT followed by matching Slide")

    # Display Results
    if not results.empty:
        col1, col2 = st.columns([2, 8])
        with col1:
            st.metric("Matches Found", len(results))
        with col2:
            # Prepare CSV data with clear time columns
            csv_df = results.copy()
            csv_df = csv_df.rename(columns={'date': 'bump_start_date'})
            
            # Reorder columns for clarity
            desired_order = [
                'bump_start_date', 'bump_end_date', 'slide_start_date', 'slide_end_date',
                'data_gap',
                'bump_change', 'slide_change', 
                'bump_vol', 'slide_vol',
                'bump_up_pct', 'slide_up_pct',
                'bump_start_price', 'bump_end_price', 'slide_start_price', 'slide_end_price'
            ]
            # Ensure we only use columns that exist
            cols_to_export = [c for c in desired_order if c in csv_df.columns]
            
            st.download_button(
                label="📥 Download Results CSV",
                data=csv_df[cols_to_export].to_csv(index=False),
                file_name="bump_slide_results.csv",
                mime="text/csv"
            )
        
        # Define render functions for reordering
        def render_table():
            st.subheader("Matches (Top 20 by Slide Magnitude)")
            st.caption("Click a row to visualize it. (Multi-day matches are highlighted)")
            
            # Prepare Highlighted Data
            results_display = results.copy()
            
            # Sort by best slide change (magnitude) and limit to top 20
            results_display['abs_slide'] = results_display['slide_change'].abs()
            results_display = results_display.sort_values('abs_slide', ascending=False).head(20)
            
            # Create a helper column to identify multi-day patterns
            results_display['is_multiday'] = results_display['date'].dt.date != results_display['slide_end_date'].dt.date
            
            def highlight_multiday(row):
                if row['is_multiday']:
                    return ['background-color: #FFF9C4; color: black'] * len(row) # Light Yellow
                return [''] * len(row)
            
            # Apply Style (Remove helper cols from styling if needed, but style applies to whole df)
            # We must drop helper cols before styling if we don't want them or handle them
            # But style.apply iterates rows.
            styled_results = results_display.style.apply(highlight_multiday, axis=1)
            
            # Interactive Table
            event = st.dataframe(
                styled_results, 
                width="stretch",
                on_select="rerun",
                selection_mode="single-row",
                key="matches_table", # Stable key to preserve sort state across reruns
                column_config={
                    "date": st.column_config.DatetimeColumn("Bump Start", format="YYYY-MM-DD HH:mm"),
                    "bump_change": st.column_config.NumberColumn(bump_label, format="%.2f"),
                    "slide_change": st.column_config.NumberColumn(slide_label, format="%.2f"),
                    "bump_vol": st.column_config.NumberColumn("Bump Size Vol"),
                    "slide_vol": st.column_config.NumberColumn("Slide Size Vol"),
                    "data_gap": st.column_config.CheckboxColumn("Gap?"),
                    "is_multiday": None, # Hide helper column
                    "abs_slide": None, # Hide sort column
                },
                hide_index=True 
            )
            
            # Handle Table Selection
            if len(event.selection.rows) > 0:
                selected_row_numeric_idx = event.selection.rows[0]
                # Map back to original results index using the same positional index
                # Use results_display.index because we sorted/filtered
                new_idx = results_display.index[selected_row_numeric_idx]
                if 'selected_match_idx' not in st.session_state or new_idx != st.session_state.selected_match_idx:
                    st.session_state.selected_match_idx = new_idx
                    st.rerun()

        def render_chart():
            # Initialize match_idx logic
            if 'selected_match_idx' not in st.session_state:
                st.session_state.selected_match_idx = results.index[0] if not results.empty else None
            
            # Validation
            if st.session_state.selected_match_idx not in results.index and not results.empty:
                st.session_state.selected_match_idx = results.index[0]

            match_idx = st.session_state.selected_match_idx

            if match_idx is not None and match_idx in results.index:
                st.subheader("Visualize Pattern")
                
                row = results.loc[match_idx]
                
                # --- Top Info Row: Metrics and News Selector ---
                # Layout: Date | Bump | Slide | News Dropdown | Search Link
                
                # We use columns to spread info horizontally above the chart
                info_col1, info_col2, info_col3, info_col4 = st.columns([2, 1, 1, 3])
                
                with info_col1:
                    st.markdown(f"### {row['date'].date()}")
                
                with info_col2:
                    st.metric("Bump", f"{row['bump_change']:.2f}{bump_suffix}")
                    
                with info_col3:
                    st.metric("Slide", f"{row['slide_change']:.2f}{slide_suffix}")
                    
                with info_col4:
                    # Compact News Controls
                    news_date_str = str(row['date'].date())
                    # Using a simpler layout for news to save vertical space
                    search_topic = st.text_input(
                        "News Topic", 
                        value="S&P 500",
                        label_visibility="collapsed" # Save space, label implied
                    )
                    fallback_url = get_google_news_url(news_date_str, search_topic)
                    st.markdown(f"[**🔍 Search News: {search_topic}**]({fallback_url})")

                st.divider()

                # --- Chart Visualization (Full Width) ---
                t_viz_start = time_module.time()
                
                chart_container = st.empty()
                with chart_container.container():
                    st.info("⏳ **Generating visualization...**", icon="⏳")
                
                try:
                    t_prep_start = time_module.time()
                    
                    # Calculate Average SizeVol for the year
                    avg_sv = 0
                    if val_report and 'yearly_size_vol' in val_report:
                        year = row['date'].year
                        avg_sv = val_report['yearly_size_vol'].get(year, 0)
                        
                    # Use df_filtered to match the indices in results
                    fig = plot_pattern(
                        df_filtered, 
                        row, 
                        bump_len=bump_len, 
                        slide_len=slide_len,
                        avg_size_vol=avg_sv
                    )
                    log_perf("Viz: Pattern Generation", t_prep_start)
                    
                    t_render_start = time_module.time()
                    # Full width chart
                    chart_container.plotly_chart(fig, width="stretch")
                    log_perf("Viz: Render Call", t_render_start)
                    
                    log_perf("Viz: Total Flow", t_viz_start)

                except Exception as e:
                    chart_container.error(f"Error loading visualization: {str(e)}")

        # Execute Layout Order
        if layout_order == "Table Top":
            render_table()
            st.divider()
            render_chart()
        else:
            render_chart()
            st.divider()
            render_table()

    else:
        st.info("No matches found with current parameters.")
