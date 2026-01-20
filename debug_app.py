import streamlit as st
import pandas as pd
from src.test_utils.data_generator import MarketDataGenerator
from src.analyzer import find_bumps_and_slides
from src.ui.results import render_results
from src.data_validator import validate_dataset

st.set_page_config(page_title="SP500 Bump & Slide - DEBUG MODE", layout="wide")
st.title("🐞 Debug Mode: Synthetic Data Verification")

# Initialize Generator
if 'generator' not in st.session_state:
    st.session_state.generator = MarketDataGenerator(seed=42)

# Sidebar - Generator Controls
st.sidebar.header("1. Data Generation")
days = st.sidebar.slider("Days of Data", 1, 30, 5)
volatility = st.sidebar.number_input("Volatility", 0.0001, 0.01, 0.0005, format="%.4f")
seed = st.sidebar.number_input("Random Seed", 0, 1000, 42)

if st.sidebar.button("Regenerate Noise"):
    st.session_state.generator = MarketDataGenerator(seed=seed)
    st.session_state.df = st.session_state.generator.generate_noise(days=days, volatility=volatility)
    st.session_state.results = None

# Initialize DF if missing
if 'df' not in st.session_state:
    st.session_state.df = st.session_state.generator.generate_noise(days=days, volatility=volatility)

df = st.session_state.df

# Sidebar - Pattern Injection
st.sidebar.header("2. Pattern Injection")
inject_idx = st.sidebar.number_input("Inject at Index", 0, len(df)-50, 100)
bump_len_inj = st.sidebar.number_input("Inj Bump Len", 5, 60, 10)
slide_len_inj = st.sidebar.number_input("Inj Slide Len", 5, 60, 10)
bump_pct = st.sidebar.number_input("Inj Bump %", 0.0, 0.1, 0.02)
slide_pct = st.sidebar.number_input("Inj Slide %", -0.1, 0.0, -0.02)

if st.sidebar.button("Inject Pattern"):
    # Re-generate clean noise first to avoid stacking
    st.session_state.generator = MarketDataGenerator(seed=seed)
    temp_df = st.session_state.generator.generate_noise(days=days, volatility=volatility)
    try:
        st.session_state.df = st.session_state.generator.inject_pattern(
            temp_df, 
            index=inject_idx, 
            bump_len=bump_len_inj, slide_len=slide_len_inj, 
            bump_pct=bump_pct, slide_pct=slide_pct
        )
        st.success(f"Injected pattern at index {inject_idx}")
    except Exception as e:
        st.error(f"Injection failed: {e}")

# Sidebar - Analysis Params
st.sidebar.header("3. Analyzer Settings")
bump_len = st.sidebar.number_input("Bump Length (mins)", 5, 60, bump_len_inj)
slide_len = st.sidebar.number_input("Slide Length (mins)", 5, 60, slide_len_inj)
bump_thresh = st.sidebar.number_input("Bump Threshold %", 0.0, 10.0, 1.0) / 100
slide_thresh = st.sidebar.number_input("Slide Threshold %", 0.0, 10.0, 1.0) / 100

# Run Analysis
if st.button("Run Analyzer"):
    results, stats = find_bumps_and_slides(
        st.session_state.df,
        bump_len=bump_len, bump_threshold=bump_thresh, bump_thresh_type="percent",
        slide_len=slide_len, slide_threshold=slide_thresh, slide_thresh_type="percent",
        min_bump_vol=0, min_slide_vol=0
    )
    st.session_state.results = results
    st.session_state.stats = stats

# Display
st.write(f"Data Shape: {st.session_state.df.shape}")
st.line_chart(st.session_state.df['close'])

if 'results' in st.session_state and st.session_state.results is not None:
    # Create fake val_report for render_results
    val_report = validate_dataset(st.session_state.df)
    # Mock yearly size vol
    val_report['yearly_size_vol'] = {2023: 1000000} 
    
    render_results(st.session_state.results, st.session_state.stats, {
        'bump_len': bump_len, 'slide_len': slide_len # minimal config needed for vis
    }, st.session_state.df, val_report)
