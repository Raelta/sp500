import pandas as pd
import numpy as np

def _calculate_true_hits(hits_df, bump_len, slide_len, total_rows):
    """
    Calculates True Hits (non-overlapping best matches) using greedy suppression.
    """
    if hits_df.empty:
        return 0
    
    # Get indices (assumed to be integer positions from RangeIndex)
    indices = hits_df.index.values
    # Use absolute slide change as score
    scores = hits_df['slide_change'].abs().values
    
    # Sort by score descending
    sorted_order = np.argsort(scores)[::-1]
    sorted_indices = indices[sorted_order]
    
    # Safety buffer for occupied array
    occupied = np.zeros(total_rows + bump_len + slide_len, dtype=bool)
    window_len = bump_len + slide_len
    
    count = 0
    for idx in sorted_indices:
        # Check bounds (though indices should be valid)
        if idx >= total_rows: continue
        
        # Check overlap
        end_idx = min(idx + window_len, total_rows)
        if not occupied[idx:end_idx].any():
            occupied[idx:end_idx] = True
            count += 1
            
    return count

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
    bump_up_pct=0.0, slide_up_pct=0.0,
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
    min_bump_vol: Minimum volume for bump period
    min_slide_vol: Minimum volume for slide period
    bump_up_pct: Minimum percentage of Up candles (Close > Open) in bump
    slide_up_pct: Minimum percentage of Up candles (Close > Open) in slide
    """
    
    # 1. Pre-calculate Size Volume Sums (Rolling)
    if progress_callback: progress_callback("Calculating volume metrics...", 10)
    
    # SizeVol = Volume * |Close - Open|
    size_vol_series = df['volume'] * (df['close'] - df['open']).abs()
    
    # rolling sum aligns to the right edge of window, so we shift back to align to start
    # We need rolling sum for bump_len and slide_len
    
    # Bump Size Volume (sum from i to i + bump_len - 1)
    bump_vol = size_vol_series.rolling(window=bump_len).sum().shift(-(bump_len - 1))
    
    # Slide Size Volume (sum from i + bump_len to i + bump_len + slide_len - 1)
    slide_vol = size_vol_series.rolling(window=slide_len).sum().shift(-(bump_len + slide_len - 1))

    # 2. Calculate Price Changes & Consistency
    if progress_callback: progress_callback("Analyzing price changes...", 30)

    # Bump Change
    bump_open = df['open']
    bump_close = df['close'].shift(-(bump_len - 1))
    bump_change = calculate_change(bump_open, bump_close, bump_thresh_type)
    
    # Slide Change %
    slide_open = df['open'].shift(-bump_len)
    slide_close = df['close'].shift(-(bump_len + slide_len - 1))
    slide_change = calculate_change(slide_open, slide_close, slide_thresh_type)
    
    # Candle Direction (Up = 1)
    is_up = (df['close'] > df['open']).astype(int)
    
    # Rolling Up Ratio
    bump_up_ratio = is_up.rolling(window=bump_len).mean().shift(-(bump_len - 1))
    slide_up_ratio = is_up.rolling(window=slide_len).mean().shift(-(bump_len + slide_len - 1))
    
    # 3. Create Candidate DataFrame
    if progress_callback: progress_callback("Structuring candidate data...", 50)

    # Use indices to track
    candidates = pd.DataFrame({
        'date': df['date'],
        'bump_change': bump_change,
        'slide_change': slide_change,
        'bump_vol': bump_vol,
        'slide_vol': slide_vol,
        'bump_up_pct': bump_up_ratio * 100,
        'slide_up_pct': slide_up_ratio * 100,
        'bump_start_price': bump_open,
        'bump_end_price': bump_close,
        'slide_start_price': slide_open,
        'slide_end_price': slide_close,
        'bump_end_date': df['date'].shift(-(bump_len - 1)),
        'slide_start_date': df['date'].shift(-bump_len),
        'slide_end_date': df['date'].shift(-(bump_len + slide_len - 1))
    })
    
    # Identify Data Gaps (Time difference > 1 minute between Bump End and Slide Start)
    # This captures missing data or day boundaries.
    candidates['data_gap'] = (candidates['slide_start_date'] - candidates['bump_end_date']) > pd.Timedelta(minutes=1)
    
    # 3.5 Apply Time and Day Filters (Moved before threshold filtering to calculate stats on valid scope)
    if progress_callback: progress_callback("Applying time and day filters...", 60)
    
    if not candidates.empty:
        # Time of Day (based on Bump Start)
        if time_range:
            start_t, end_t = time_range
            results_times = candidates['date'].dt.time
            # Handle overnight ranges if needed, but assuming intraday for now
            if start_t <= end_t:
                candidates = candidates[(results_times >= start_t) & (results_times <= end_t)]
            else:
                candidates = candidates[(results_times >= start_t) | (results_times <= end_t)]
        
        # Day of Week
        if days_of_week:
            # days_of_week expected to be list of day names (Mon, Tue...) or integers
            # Let's standardize on day_name()
            candidates = candidates[candidates['date'].dt.day_name().isin(days_of_week)]

    # 4. Filter by Thresholds and Volume
    if progress_callback: progress_callback("Filtering candidates...", 70)

    if candidates.empty:
         return pd.DataFrame(), {'total_bumps': 0, 'hits': 0, 'misses': 0, 'hit_ratio': 0}

    # Calculate masks
    # Directional Logic:
    # If threshold >= 0, we look for change >= threshold (Positive Move)
    # If threshold < 0, we look for change <= threshold (Negative Move)
    
    if bump_threshold >= 0:
        bump_change_mask = (candidates['bump_change'] >= bump_threshold)
    else:
        bump_change_mask = (candidates['bump_change'] <= bump_threshold)
        
    if slide_threshold >= 0:
        slide_change_mask = (candidates['slide_change'] >= slide_threshold)
    else:
        slide_change_mask = (candidates['slide_change'] <= slide_threshold)

    bump_mask = bump_change_mask & \
                (candidates['bump_vol'] >= min_bump_vol) & \
                (candidates['bump_up_pct'] >= bump_up_pct)
                
    slide_mask = slide_change_mask & \
                 (candidates['slide_vol'] >= min_slide_vol) & \
                 (candidates['slide_up_pct'] >= slide_up_pct)
    
    total_bumps = bump_mask.sum()
    total_hits = (bump_mask & slide_mask).sum()
    misses = (bump_mask & ~slide_mask).sum()
    
    results = candidates[bump_mask & slide_mask].copy()
    
    # Calculate True Hits (Non-overlapping)
    true_hits = _calculate_true_hits(results, bump_len, slide_len, len(df))

    stats = {
        'total_rows': len(df),
        'total_bumps': int(total_bumps),
        'total_hits': int(total_hits),
        'hits': int(total_hits), # Alias for backward compatibility (Total Hits)
        'true_hits': int(true_hits),
        'misses': int(misses),
        'hit_ratio': float((total_hits / total_bumps * 100) if total_bumps > 0 else 0) # Based on Total Hits
    }

    if progress_callback: progress_callback("Finalizing results...", 100)
    
    return results.dropna(), stats
