import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

def plot_pattern(df, match_row, padding=10, bump_len=None, slide_len=None, avg_size_vol=None):
    """
    Plots a specific pattern (Bump + Slide) with context using subplots for Price and Volume.
    
    avg_size_vol: Optional float for the yearly average SizeVol to plot as a reference line.
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
    
    # 2. Volume Bar (SizeVol)
    # Metric: Volume * |Close - Open|
    price_delta = (plot_data['close'] - plot_data['open']).abs()
    size_vol = plot_data['volume'] * price_delta
    
    fig.add_trace(go.Bar(
        x=plot_data['date'],
        y=size_vol,
        name='SizeVol',
        marker_color='#7F7F7F',
        customdata=np.stack((plot_data['volume'], price_delta), axis=-1),
        hovertemplate='<b>Date</b>: %{x}<br>' +
                      '<b>Volume</b>: %{customdata[0]:,}<br>' +
                      '<b>Price Change</b>: %{customdata[1]:.2f}<br>' +
                      '<b>SizeVol</b>: %{y:,.2f}<extra></extra>'
    ), row=2, col=1)
    
    # Add Average SizeVol Line if available
    if avg_size_vol is not None and avg_size_vol > 0:
        fig.add_hline(
            y=avg_size_vol,
            line_dash="dash",
            line_color="blue",
            annotation_text=f"Yearly Avg: {avg_size_vol:,.0f}", 
            annotation_position="top right",
            row=2, col=1
        )
    
    # Highlights
    
    actual_max_date = plot_data['date'].max()
    slide_end = match_row['slide_end_date']
    if slide_end > actual_max_date:
        slide_end = actual_max_date

    # Visually extend the rectangles by 1 minute so they cover the full width of the last bar
    vis_offset = pd.Timedelta(minutes=1)

    # Bump Rect - Price (With Annotation)
    fig.add_vrect(
        x0=match_row['date'], x1=match_row['bump_end_date'] + vis_offset,
        fillcolor="rgba(255, 165, 0, 0.3)", # Orange
        layer="below", line_width=0,
        annotation_text="Bump", annotation_position="top left",
        row=1, col=1
    )
    
    # Bump Rect - Volume (No Annotation)
    fig.add_vrect(
        x0=match_row['date'], x1=match_row['bump_end_date'] + vis_offset,
        fillcolor="rgba(255, 165, 0, 0.3)", # Orange
        layer="below", line_width=0,
        row=2, col=1
    )
    
    # Slide Rect - Price (With Annotation)
    fig.add_vrect(
        x0=match_row['slide_start_date'], x1=slide_end + vis_offset,
        fillcolor="rgba(0, 0, 255, 0.3)", # Blue
        layer="below", line_width=0,
        annotation_text="Slide", annotation_position="top left",
        row=1, col=1
    )
    
    # Slide Rect - Volume (No Annotation)
    fig.add_vrect(
        x0=match_row['slide_start_date'], x1=slide_end + vis_offset,
        fillcolor="rgba(0, 0, 255, 0.3)", # Blue
        layer="below", line_width=0,
        row=2, col=1
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
