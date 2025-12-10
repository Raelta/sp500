import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from load_data import load_spy_data

# Set page config
st.set_page_config(page_title="SPY Trend Analysis Dashboard", layout="wide")

# --- Helper Functions ---

@st.cache_data
def get_data():
    """Load the SPY data once and cache it."""
    return load_spy_data()

def calculate_trends(df, years, column_name, start_sample, end_sample, trend_direction):
    """
    Calculates trend statistics for the given parameters.
    Returns a DataFrame containing the results.
    """
    all_years_data = []
    
    # Normalize trend direction
    trend_direction = trend_direction.lower()
    
    for year in years:
        # Filter for the specific year
        try:
            year_mask = df['date'].dt.year == int(year)
            year_df = df[year_mask].copy()
        except Exception as e:
            st.error(f"Error filtering for year {year}: {e}")
            continue

        if year_df.empty:
            continue

        if column_name not in year_df.columns:
            st.error(f"Column '{column_name}' not found.")
            return pd.DataFrame()

        values = year_df[column_name].values
        n_rows = len(values)
        
        for sample_size in range(start_sample, end_sample + 1):
            total_samples = 0
            match_count = 0
            continued_count = 0
            
            # Iterate through chunks (vectorized-ish or loop)
            # Keeping the loop logic from generate_trend_table.py for consistency
            for i in range(0, n_rows, sample_size):
                chunk_end = i + sample_size
                if chunk_end > n_rows:
                    break 
                    
                chunk = values[i : chunk_end]
                
                # Check trend
                matches_trend = True
                for j in range(sample_size - 1):
                    if trend_direction == 'increase':
                        if chunk[j] >= chunk[j+1]:
                            matches_trend = False
                            break
                    else: # decrease
                        if chunk[j] <= chunk[j+1]:
                            matches_trend = False
                            break
                
                total_samples += 1
                
                if matches_trend:
                    match_count += 1
                    
                    # Check continuation
                    if chunk_end < n_rows:
                        next_val = values[chunk_end]
                        last_val = chunk[-1]
                        
                        if trend_direction == 'increase':
                            if last_val < next_val:
                                continued_count += 1
                        else: # decrease
                            if last_val > next_val:
                                continued_count += 1
            
            # Calculate percentages
            if total_samples > 0:
                pct_increasing = (match_count / total_samples * 100)
                pct_continued_total = (continued_count / total_samples * 100)
            else:
                pct_increasing = 0
                pct_continued_total = 0
                
            # Calculate % Continuation (Relative to matches)
            if match_count > 0:
                pct_continuation_relative = (continued_count / match_count * 100)
            else:
                pct_continuation_relative = 0
            
            all_years_data.append({
                'Year': year,
                'Total Rows': n_rows,
                'Sample Size': sample_size,
                'Total Samples': total_samples,
                'Matches': match_count,
                'Matches & Cont': continued_count,
                '% Increasing': round(pct_increasing, 2),
                '% Inc & Cont': round(pct_continued_total, 2),
                '% Continuation': round(pct_continuation_relative, 2)
            })
            
    return pd.DataFrame(all_years_data)

# --- App Layout ---

st.title("📈 SPY Trend Analysis Dashboard")
st.markdown("Analyze price trends over various sample sizes and years.")

# Load Data
with st.spinner("Loading data..."):
    df = get_data()

if df is not None:
    # --- Sidebar Inputs ---
    st.sidebar.header("Configuration")
    
    # Column Selection
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    default_col = 'close' if 'close' in numeric_cols else numeric_cols[0]
    column_name = st.sidebar.selectbox("Select Column", numeric_cols, index=numeric_cols.index(default_col) if default_col in numeric_cols else 0)
    
    # Trend Direction
    trend_direction = st.sidebar.selectbox("Trend Direction", ["Increase", "Decrease"])
    
    # Year Selection
    min_year = int(df['date'].dt.year.min())
    max_year = int(df['date'].dt.year.max())
    
    year_mode = st.sidebar.radio("Year Selection Mode", ["Single Year", "Range"])
    
    selected_years = []
    if year_mode == "Single Year":
        selected_year = st.sidebar.number_input("Year", min_value=min_year, max_value=max_year, value=2010)
        selected_years = [selected_year]
    else:
        year_range = st.sidebar.slider("Select Year Range", min_value=min_year, max_value=max_year, value=(2010, 2012))
        selected_years = list(range(year_range[0], year_range[1] + 1))
        
    # Sample Size Range
    st.sidebar.subheader("Sample Size Window")
    sample_range = st.sidebar.slider("Range (Start - End)", min_value=2, max_value=50, value=(3, 10))
    start_sample, end_sample = sample_range

    # --- Analysis & Visualization ---
    
    if st.sidebar.button("Run Analysis", type="primary"):
        with st.spinner("Calculating trends..."):
            results_df = calculate_trends(df, selected_years, column_name, start_sample, end_sample, trend_direction)
        
        if not results_df.empty:
            # --- Chart ---
            st.subheader(f"Trend Continuation Probability ({trend_direction})")
            
            # Create interactive chart with dropdown logic (or just a simple chart if single year, but logic works for multi)
            # Actually, Streamlit handles interactivity well. We can just show the chart.
            # If multiple years, we can use Plotly's color encoding or facets, OR just use the same dropdown logic as before.
            # Since the user liked the dropdown in the HTML, let's replicate that feel or improve it.
            # Streamlit allows user to filter the VIEW of the chart using widgets too.
            # But the user asked for "a simple interface... Each time a parameter is entered the bar chart will update."
            # If I plot all years in one chart with a dropdown *inside* Plotly, that works.
            
            # Reusing the Plotly Logic from generate_trend_table.py
            fig = go.Figure()
            
            unique_years = sorted(results_df['Year'].unique())
            
            for i, year in enumerate(unique_years):
                year_data = results_df[results_df['Year'] == year]
                
                hover_text = [
                    f"Sample Size: {ss}<br>% Continuation: {pct:.2f}%<br>% Inc & Cont: {pct_ic:.2f}%"
                    for ss, pct, pct_ic in zip(year_data['Sample Size'], year_data['% Continuation'], year_data['% Inc & Cont'])
                ]
                
                bar_text = [
                    f"Tot: {t}<br>Mat: {m}<br>Cont: {c}"
                    for t, m, c in zip(year_data['Total Samples'], year_data['Matches'], year_data['Matches & Cont'])
                ]
                
                visible = (i == 0)
                
                fig.add_trace(go.Bar(
                    x=year_data['Sample Size'],
                    y=year_data['% Continuation'],
                    name=str(year),
                    visible=visible,
                    marker_color='#2c3e50',
                    text=bar_text,
                    textposition='outside',
                    hoverinfo='text',
                    hovertext=hover_text
                ))
                
            # Dropdown menu
            buttons = []
            for i, year in enumerate(unique_years):
                visibility = [False] * len(unique_years)
                visibility[i] = True
                
                n_rows = results_df[results_df['Year'] == year]['Total Rows'].iloc[0]
                
                buttons.append(dict(
                    label=str(year),
                    method="update",
                    args=[{"visible": visibility},
                          {"title.text": f"Trend Continuation Probability ({year})<br>Total Rows: {n_rows} | Column: {column_name} | Trend: {trend_direction}"}]
                ))
            
            initial_year = unique_years[0]
            initial_rows = results_df[results_df['Year']==initial_year]['Total Rows'].iloc[0]
            initial_title = f"Trend Continuation Probability ({initial_year})<br>Total Rows: {initial_rows} | Column: {column_name} | Trend: {trend_direction}"

            fig.update_layout(
                updatemenus=[dict(
                    active=0,
                    buttons=buttons,
                    x=1.0,
                    xanchor='right',
                    y=1.15
                )],
                title=dict(text=initial_title),
                xaxis_title="Sample Size",
                yaxis_title="% Continuation (Relative to Matches)",
                yaxis=dict(range=[0, results_df['% Continuation'].max() * 1.3]),
                xaxis=dict(type='category'),
                template="plotly_white",
                height=600
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # --- Data Table ---
            st.subheader("Detailed Data")
            st.dataframe(results_df, use_container_width=True)
            
        else:
            st.warning("No data found for the selected criteria.")
    else:
        st.info("Select parameters in the sidebar and click 'Run Analysis' to generate the dashboard.")

else:
    st.error("Failed to load data.")
