import pandas as pd
import numpy as np

def calculate_change(start_vals, end_vals, mode):
    if mode == 'percent':
        # Avoid division by zero
        return (end_vals - start_vals) / start_vals.replace(0, np.nan) * 100
    else:
        return end_vals - start_vals

def find_bumps_and_slides(
    df,
    bump_len, bump_threshold, bump_thresh_type,
    slide_len, slide_threshold, slide_thresh_type,
    min_bump_vol=0, min_slide_vol=0,
    time_range=None, # (start_time, end_time)
    days_of_week=None, # list of ints 0-6 or names
    progress_callback=None # function(message, percent)
):
    """
    Identifies Bump followed by Slide patterns.
    
    bump_len: int, minutes
    bump_threshold: float
    bump_thresh_type: 'percent' or 'value'
    slide_len: int, minutes
    slide_threshold: float
    slide_thresh_type: 'percent' or 'value'
    """
    
    # 1. Pre-calculate Volume Sums (Rolling)
    if progress_callback: progress_callback("Calculating volume metrics...", 10)
    
    # rolling sum aligns to the right edge of window, so we shift back to align to start
    # We need rolling sum for bump_len and slide_len
    
    # Bump Volume (sum from i to i + bump_len - 1)
    bump_vol = df['volume'].rolling(window=bump_len).sum().shift(-(bump_len - 1))
    
    # Slide Volume (sum from i + bump_len to i + bump_len + slide_len - 1)
    # First get rolling sum of slide_len, aligned to start of slide
    # Slide starts at i + bump_len
    # So we want rolling sum at (i + bump_len + slide_len - 1) which is shift(-(bump_len + slide_len - 1)) ?
    # Let's trace: 
    # Rolling sum at index K is sum(K-L+1 ... K)
    # We want sum for slide starting at J = i + bump_len.
    # End of slide is J + slide_len - 1.
    # So we want rolling_sum[J + slide_len - 1].
    # J + slide_len - 1 = i + bump_len + slide_len - 1.
    # So shift(-(bump_len + slide_len - 1)).
    slide_vol = df['volume'].rolling(window=slide_len).sum().shift(-(bump_len + slide_len - 1))

    # 2. Calculate Price Changes
    if progress_callback: progress_callback("Analyzing price changes...", 30)

    # Bump Change
    bump_open = df['open']
    bump_close = df['close'].shift(-(bump_len - 1))
    bump_change = calculate_change(bump_open, bump_close, bump_thresh_type)
    
    # Slide Change
    slide_open = df['open'].shift(-bump_len)
    slide_close = df['close'].shift(-(bump_len + slide_len - 1))
    slide_change = calculate_change(slide_open, slide_close, slide_thresh_type)
    
    # 3. Create Candidate DataFrame
    if progress_callback: progress_callback("Structuring candidate data...", 50)

    # Use indices to track
    candidates = pd.DataFrame({
        'date': df['date'],
        'bump_change': bump_change,
        'slide_change': slide_change,
        'bump_vol': bump_vol,
        'slide_vol': slide_vol,
        'bump_start_price': bump_open,
        'bump_end_price': bump_close,
        'slide_start_price': slide_open,
        'slide_end_price': slide_close,
        'bump_end_date': df['date'].shift(-(bump_len - 1)),
        'slide_end_date': df['date'].shift(-(bump_len + slide_len - 1))
    })
    
    # 4. Filter by Thresholds and Volume
    if progress_callback: progress_callback("Filtering candidates...", 70)

    mask = (
        (candidates['bump_change'].abs() >= bump_threshold) &
        (candidates['slide_change'].abs() >= slide_threshold) &
        (candidates['bump_vol'] >= min_bump_vol) &
        (candidates['slide_vol'] >= min_slide_vol)
    )
    
    results = candidates[mask].copy()
    
    # 5. Filter by Time and Day
    if not results.empty:
        if progress_callback: progress_callback("Applying time and day filters...", 85)

        # Time of Day (based on Bump Start)
        if time_range:
            start_t, end_t = time_range
            results_times = results['date'].dt.time
            # Handle overnight ranges if needed, but assuming intraday for now
            if start_t <= end_t:
                results = results[(results_times >= start_t) & (results_times <= end_t)]
            else:
                # Overnight
                results = results[(results_times >= start_t) | (results_times <= end_t)]
        
        # Day of Week
        if days_of_week:
            # days_of_week expected to be list of day names (Mon, Tue...) or integers
            # Let's standardize on day_name()
            results = results[results['date'].dt.day_name().isin(days_of_week)]

    if progress_callback: progress_callback("Finalizing results...", 100)
    
    return results.dropna()
