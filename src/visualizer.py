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
    
    # Create copy to avoid SettingWithCopyWarning when adding date_str
    plot_data = df.iloc[plot_start_idx : plot_end_idx + 1].copy()
    
    # Format Date for X-Axis (Removes nanoseconds / trailing zeros)
    # We use this string for x-values to ensure Plotly treats them as discrete categories without auto-formatting
    plot_data['date_str'] = plot_data['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Create Subplots: Price (Top), Volume (Bottom)
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05, 
        row_heights=[0.7, 0.3]
    )
    
    # 1. Candlestick (Wickless: line width 0)
    fig.add_trace(go.Candlestick(
        x=plot_data['date_str'],
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
        x=plot_data['date_str'],
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
            annotation_text=f"Yearly Median: {avg_size_vol:,.0f}", 
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
    
    # Helper to format timestamps for Plotly Shapes (must match x-axis string format)
    def fmt_date(dt):
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    # Bump Rect - Price (With Annotation)
    bump_end_ts = match_row['bump_end_date'] + vis_offset
    fig.add_vrect(
        x0=fmt_date(match_row['date']), x1=fmt_date(bump_end_ts),
        fillcolor="rgba(255, 165, 0, 0.3)", # Orange
        layer="below", line_width=0,
        annotation_text="Bump", annotation_position="top left",
        row=1, col=1
    )
    
    # Bump Rect - Volume (No Annotation)
    fig.add_vrect(
        x0=fmt_date(match_row['date']), x1=fmt_date(bump_end_ts),
        fillcolor="rgba(255, 165, 0, 0.3)", # Orange
        layer="below", line_width=0,
        row=2, col=1
    )
    
    # Slide Rect - Price (With Annotation)
    # Changed annotation_position to 'bottom left' to avoid overlap with Bump text
    slide_end_ts = slide_end + vis_offset
    fig.add_vrect(
        x0=fmt_date(match_row['slide_start_date']), x1=fmt_date(slide_end_ts),
        fillcolor="rgba(0, 0, 255, 0.3)", # Blue
        layer="below", line_width=0,
        annotation_text="Slide", annotation_position="bottom left",
        row=1, col=1
    )
    
    # Slide Rect - Volume (No Annotation)
    fig.add_vrect(
        x0=fmt_date(match_row['slide_start_date']), x1=fmt_date(slide_end_ts),
        fillcolor="rgba(0, 0, 255, 0.3)", # Blue
        layer="below", line_width=0,
        row=2, col=1
    )
    
    # --- Centre Line (Entry) ---
    # Distinct line separating Bump and Slide
    fig.add_vline(
        x=fmt_date(match_row['slide_start_date']),
        line_width=1,
        line_dash="dot",
        line_color="black",
        opacity=0.5,
        row="all"
    )
    
    # --- Gap Indication Logic ---
    # Calculate time diffs to detect breaks (e.g. overnight)
    time_diffs = plot_data['date'].diff()
    # Threshold: > 30 minutes implies a session break or gap
    gap_mask = time_diffs > pd.Timedelta(minutes=30)
    
    # Iterate to get duration for tooltip
    gap_indices = plot_data.index[gap_mask]
    
    for idx in gap_indices:
        date = plot_data.loc[idx, 'date']
        duration = time_diffs[idx]
        
        # Format Duration nicely
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        dur_str = f"{hours}h {minutes}m"
        
        date_str = fmt_date(date)
        
        # Distinct Line
        fig.add_vline(
            x=date_str, 
            line_dash="dash", 
            line_color="#EF5350", # Red-ish
            line_width=2,
            opacity=0.8,
            row="all"
        )
        
        # Tooltip (Invisible Marker on Price Chart)
        # We place it at the High price so it's discoverable
        hover_y = plot_data.loc[idx, 'high']
        fig.add_trace(go.Scatter(
            x=[date_str],
            y=[hover_y],
            mode='markers',
            marker=dict(size=10, opacity=0), # Invisible but hoverable
            hovertemplate=f"<b>Gap</b><br>Skipped: {dur_str}<extra></extra>",
            showlegend=False,
            name="Gap"
        ), row=1, col=1)

    fig.update_layout(
        title=f"Pattern starting {start_date}",
        height=600,
        showlegend=False,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # Generate Clean Time-Only Ticks
    # Select a subset of ticks to avoid crowding
    n_ticks_target = 15
    step = max(1, len(plot_data) // n_ticks_target)
    tick_indices = list(range(0, len(plot_data), step))
    
    # Ensure the last point is included if it's far from the last tick
    if len(plot_data) - 1 not in tick_indices:
        tick_indices.append(len(plot_data) - 1)
        
    tick_vals = plot_data['date_str'].iloc[tick_indices]
    tick_text = plot_data['date'].iloc[tick_indices].dt.strftime('%H:%M')
    
    # Disable range slider and use Category axis to remove gaps
    fig.update_xaxes(
        rangeslider_visible=False,
        type='category',
        tickmode='array',
        tickvals=tick_vals,
        ticktext=tick_text
    )
    
    return fig
