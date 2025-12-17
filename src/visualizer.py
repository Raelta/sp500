import plotly.graph_objects as go
import pandas as pd

def plot_pattern(df, match_row, padding=10, bump_len=None, slide_len=None):
    """
    Plots a specific pattern (Bump + Slide) with context.
    
    match_row: A Series from the results DataFrame (must have name as original index)
    df: The full dataframe (for context)
    padding: Number of bars before and after to show
    bump_len: Length of bump (optional, for optimization)
    slide_len: Length of slide (optional, for optimization)
    """
    
    # We use the index from match_row to find location in df
    start_idx = match_row.name
    start_date = match_row['date']

    # Optimization: If lengths are provided, we can calculate end index directly
    if bump_len is not None and slide_len is not None:
        # Pattern covers indices [start_idx, start_idx + bump_len + slide_len - 1]
        end_pos = start_idx + bump_len + slide_len - 1
    else:
        # Fallback: Find index of slide_end_date using search
        slide_end_date = match_row['slide_end_date']
        import numpy as np
        end_pos = np.searchsorted(df['date'], slide_end_date)
        if end_pos >= len(df): end_pos = len(df) - 1
    
    plot_start_idx = max(0, start_idx - padding)
    plot_end_idx = min(len(df) - 1, end_pos + padding)
    
    plot_data = df.iloc[plot_start_idx : plot_end_idx + 1]
    
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=plot_data['date'],
        open=plot_data['open'],
        high=plot_data['high'],
        low=plot_data['low'],
        close=plot_data['close'],
        name='Price'
    ))
    
    # Highlight Bump
    # From start_date to bump_end_date
    fig.add_vrect(
        x0=match_row['date'], x1=match_row['bump_end_date'],
        fillcolor="rgba(255, 165, 0, 0.3)", # Orange
        layer="below", line_width=0,
        annotation_text="Bump", annotation_position="top left"
    )
    
    # Highlight Slide
    # From bump_end_date to slide_end_date
    fig.add_vrect(
        x0=match_row['bump_end_date'], x1=match_row['slide_end_date'],
        fillcolor="rgba(0, 0, 255, 0.3)", # Blue
        layer="below", line_width=0,
        annotation_text="Slide", annotation_position="top left"
    )
    
    fig.update_layout(
        title=f"Pattern starting {start_date}",
        xaxis_rangeslider_visible=False,
        height=500
    )
    return fig
