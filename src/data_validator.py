import pandas as pd

def check_duplicates(df):
    if 'date' not in df.columns:
        return {"count": 0, "data": pd.DataFrame(), "error": "Date column missing"}
    
    # Check for duplicate dates
    dups_mask = df.duplicated('date', keep=False)
    data = df[dups_mask].copy()
    count = len(data)
        
    return {
        "count": count,
        "data": data
    }

def check_missing_values(df):
    # Find rows with any missing value
    missing_mask = df.isnull().any(axis=1)
    data = df[missing_mask].copy()
    count = len(data)
    
    # Summary of columns
    summary = df.isnull().sum()
    summary = summary[summary > 0].to_dict()
    
    return {
        "count": count,
        "data": data,
        "summary": summary
    }

def check_intraday_gaps(df):
    if 'date' not in df.columns:
        return {"count": 0, "data": pd.DataFrame()}
    
    # Calculate time diff
    diffs = df['date'].diff()
    
    gap_mask = diffs > pd.Timedelta(minutes=1)
    
    if not gap_mask.any():
        return {"count": 0, "data": pd.DataFrame()}
    
    gaps_indices = df.index[gap_mask]
    
    # Access gap start/end
    # gap occurs between index-1 and index
    
    # We need to handle potential index issues if not RangeIndex, 
    # but assuming standard reset_index from loader.
    
    gap_ends = df.loc[gaps_indices, 'date']
    start_indices = gaps_indices - 1
    gap_starts = df.loc[start_indices, 'date']
    
    # Align for comparison
    gap_starts.index = gaps_indices
    
    # Check if same day
    same_day_mask = gap_starts.dt.date == gap_ends.dt.date
    
    intraday_gaps_indices = gaps_indices[same_day_mask]
    
    if len(intraday_gaps_indices) == 0:
         return {"count": 0, "data": pd.DataFrame()}

    # Construct DataFrame of gaps
    # Doing this in loop might be slow if many gaps, but usually gaps are few.
    # If duplicates are 900k, maybe gaps are also many?
    # Let's vectorize the creation if possible.
    
    valid_starts = gap_starts[same_day_mask]
    valid_ends = gap_ends[same_day_mask]
    durations = valid_ends - valid_starts
    
    gaps_df = pd.DataFrame({
        "gap_start": valid_starts,
        "gap_end": valid_ends,
        "duration": durations,
        "duration_minutes": durations.dt.total_seconds() / 60
    })
    
    return {
        "count": len(gaps_df),
        "data": gaps_df
    }

def check_missing_minutes(df):
    """
    Checks for missing 1-minute intervals between 09:30 and 16:00 on trading days.
    Assumes duplicates have been removed or dealt with.
    """
    if df.empty or 'date' not in df.columns:
        return {"count": 0, "data": pd.DataFrame()}

    # Group by date to analyze each day
    # We create a reference range for each day present in the data
    
    # 1. Get unique dates
    unique_dates = df['date'].dt.date.unique()
    
    # 2. Expected count per day (09:30 to 16:00 inclusive = 391 minutes)
    # 9:30 to 16:00 is 6.5 hours = 390 mins + 1 (inclusive start/end?) 
    # Usually SPY data includes 16:00 close. 9:30, 9:31 ... 16:00 = 391 points.
    EXPECTED_COUNT = 391
    
    # 3. Count actual rows per day
    daily_counts = df.groupby(df['date'].dt.date).size()
    
    # 4. Identify days with missing data
    incomplete_days = daily_counts[daily_counts < EXPECTED_COUNT]
    
    if len(incomplete_days) == 0:
        return {"count": 0, "data": pd.DataFrame()}
    
    # 5. Create summary dataframe
    missing_stats = pd.DataFrame({
        'date': incomplete_days.index,
        'actual_count': incomplete_days.values,
        'missing_count': EXPECTED_COUNT - incomplete_days.values,
        'completeness_pct': (incomplete_days.values / EXPECTED_COUNT) * 100
    }).sort_values('date')
    
    return {
        "count": missing_stats['missing_count'].sum(), # Total missing rows across all days
        "days_affected": len(missing_stats),
        "data": missing_stats
    }

def validate_dataset(df):
    # Important: Run duplicates check first
    dup_res = check_duplicates(df)
    
    # For missing minutes, we should conceptually check on "clean" data, 
    # otherwise duplicates might mask missing times (e.g. 2x 9:30, 0x 9:31 -> count is 2, looks full)
    # So we simulate a unique dataset for the missing check
    if dup_res['count'] > 0:
        clean_df = df.drop_duplicates(subset=['date'])
    else:
        clean_df = df
        
    return {
        "duplicates": dup_res,
        "missing_values": check_missing_values(df),
        "intraday_gaps": check_intraday_gaps(df),
        "missing_minutes": check_missing_minutes(clean_df)
    }

def get_yearly_duplicate_summary(dups_df):
    if dups_df.empty:
        return {}
    return dups_df['date'].dt.year.value_counts().sort_index().to_dict()
