import plotly.graph_objects as go
import pandas as pd

def plot_pattern(df, match_row, padding=10):
    """
    Plots a specific pattern (Bump + Slide) with context.
    
    match_row: A Series from the results DataFrame (must have name as original index)
    df: The full dataframe (for context)
    padding: Number of bars before and after to show
    """
    
    # We use the index from match_row to find location in df
    start_idx = match_row.name
    
    # We need to find the end index.
    # We can infer it from the dates if indices are not continuous, but assuming integer index is continuous.
    # Let's rely on date slicing for safety if indices are not reliable, 
    # but `data_loader` resets index so it should be 0..N.
    
    # Get the dates
    start_date = match_row['date']
    slide_end_date = match_row['slide_end_date']
    
    # Find indices for the plot window
    # We want a window around the pattern
    # We can't easily guess the index of slide_end_date without searching, 
    # unless we assume the index is clean.
    # Let's trust the index if it matches the date, otherwise search.
    
    if df.loc[start_idx, 'date'] == start_date:
        # Index is aligned
        # We need the index of the end date. 
        # Since we don't have the length explicitly in match_row, we can search or pass it.
        # But wait, in analyzer:
        # slide_end_idx = index + bump_len + slide_len - 1
        # We didn't store slide_end_idx in results, only dates.
        # But we can find the index where date == slide_end_date
        pass
    
    # Safer approach: Filter by date range with padding
    # But adding padding in "rows" is hard with dates.
    # We'll use the index from match_row (start_idx) and find the end index by searching.
    
    # Optimization: If we assume contiguous data (1 min intervals), we can guess.
    # But data might have gaps (nights, weekends).
    # So we search for the end date index.
    # This is O(N) or O(log N) if sorted.
    # Since we are plotting one, it's fine.
    
    # Find index of slide_end_date
    # Using searchsorted on dates
    # df['date'] is sorted.
    import numpy as np
    end_pos = np.searchsorted(df['date'], slide_end_date)
    # end_pos might be after the element if not found, but it should be there.
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
