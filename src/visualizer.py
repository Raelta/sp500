import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

def plot_pattern(df, match_row, padding=10, bump_len=None, slide_len=None):
    """
    Plots a specific pattern (Bump + Slide) with context using subplots for Price and Volume.
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
        end_pos = np.searchsorted(df['date'], slide_end_date)
        if end_pos >= len(df): end_pos = len(df) - 1
    
    plot_start_idx = max(0, start_idx - padding)
    plot_end_idx = min(len(df) - 1, end_pos + padding)
    
    plot_data = df.iloc[plot_start_idx : plot_end_idx + 1]
    
    # Create Subplots: Price (Top), Volume (Bottom)
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05, 
        row_heights=[0.7, 0.3]
    )
    
    # 1. Candlestick (Wickless: line width 0)
    fig.add_trace(go.Candlestick(
        x=plot_data['date'],
        open=plot_data['open'],
        high=plot_data['high'],
        low=plot_data['low'],
        close=plot_data['close'],
        name='Price',
        increasing_line=dict(width=0), # Hide wicks
        decreasing_line=dict(width=0), # Hide wicks
    ), row=1, col=1)
    
    # 2. Volume Bar
    # Color volume bars based on close >= open (standard trading convention)
    colors = ['#00CC96' if c >= o else '#EF553B' for c, o in zip(plot_data['close'], plot_data['open'])]
    
    fig.add_trace(go.Bar(
        x=plot_data['date'],
        y=plot_data['volume'],
        name='Volume',
        marker_color=colors
    ), row=2, col=1)
    
    # Highlights (vrect adds to all shared axes by default usually, but we want it clear)
    # We add it to the figure, it generally spans the plot area
    
    actual_max_date = plot_data['date'].max()
    slide_end = match_row['slide_end_date']
    if slide_end > actual_max_date:
        slide_end = actual_max_date

    # Bump Rect
    fig.add_vrect(
        x0=match_row['date'], x1=match_row['bump_end_date'],
        fillcolor="rgba(255, 165, 0, 0.3)", # Orange
        layer="below", line_width=0,
        annotation_text="Bump", annotation_position="top left"
    )
    
    # Slide Rect
    fig.add_vrect(
        x0=match_row['slide_start_date'], x1=slide_end,
        fillcolor="rgba(0, 0, 255, 0.3)", # Blue
        layer="below", line_width=0,
        annotation_text="Slide", annotation_position="top left"
    )
    
    fig.update_layout(
        title=f"Pattern starting {start_date}",
        height=600,
        showlegend=False,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # Disable range slider
    fig.update_xaxes(rangeslider_visible=False)
    
    return fig
