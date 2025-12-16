import streamlit as st
import pandas as pd
from src.data_loader import load_data_cached
from src.analyzer import find_bumps_and_slides
from src.visualizer import plot_pattern
from datetime import time

st.set_page_config(page_title="SP500 Bump & Slide", layout="wide")
st.title("SP500 Bump & Slide Analysis")

# Load Data
with st.spinner("Loading data..."):
    df = load_data_cached("spy_data.parquet")
st.success(f"Loaded {len(df)} rows.")

# Sidebar Parameters
with st.sidebar.form("params_form"):
    st.header("Bump Parameters")
    bump_len = st.slider("Bump Length (min)", 3, 20, 5)
    bump_thresh_type = st.radio("Bump Threshold Type", ["percent", "value"], index=0)
    bump_threshold = st.number_input("Bump Threshold", min_value=0.0, value=0.05, step=0.01, format="%.2f")

    st.header("Slide Parameters")
    slide_len = st.slider("Slide Length (min)", 3, 20, 3)
    slide_thresh_type = st.radio("Slide Threshold Type", ["percent", "value"], index=0)
    slide_threshold = st.number_input("Slide Threshold", min_value=0.0, value=0.05, step=0.01, format="%.2f")
    
    st.header("Filters")
    min_bump_vol = st.number_input("Min Bump Volume", min_value=0, value=0, step=1000)
    min_slide_vol = st.number_input("Min Slide Volume", min_value=0, value=0, step=1000)
    
    st.subheader("Time of Day (Bump Start)")
    time_start = st.time_input("Start Time", time(9, 30))
    time_end = st.time_input("End Time", time(16, 0))
    
    st.subheader("Day of Week")
    days = st.multiselect("Days", 
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    )
    
    run_btn = st.form_submit_button("Run Analysis")

# State management for results
if 'results' not in st.session_state:
    st.session_state.results = None

if run_btn:
    # Run Analysis
    with st.spinner("Analyzing..."):
        results = find_bumps_and_slides(
            df,
            bump_len, bump_threshold, bump_thresh_type,
            slide_len, slide_threshold, slide_thresh_type,
            min_bump_vol, min_slide_vol,
            (time_start, time_end),
            days
        )
        st.session_state.results = results

# Display Results
if st.session_state.results is not None:
    results = st.session_state.results
    st.metric("Matches Found", len(results))
    
    if not results.empty:
        # Display Table
        st.subheader("Matches")
        st.dataframe(results, use_container_width=True)
        
        # Select Pattern to View
        st.subheader("Visualize Pattern")
        
        # Helper to format option
        def format_func(idx):
            row = results.loc[idx]
            return f"{row['date']} | Bump: {row['bump_change']:.2f} | Slide: {row['slide_change']:.2f}"
        
        # Limit the selectbox options if too many, or just show them all
        # If > 1000, maybe pagination?
        # For now, let's just show a selectbox. Streamlit handles large lists reasonably well, but can be slow.
        # Maybe show top 100 by default or sort?
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            match_idx = st.selectbox("Select Match", results.index, format_func=format_func)
        
        with col2:
            if match_idx is not None and match_idx in results.index:
                row = results.loc[match_idx]
                fig = plot_pattern(df, row)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No matches found with current parameters.")
