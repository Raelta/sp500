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

def validate_dataset(df):
    return {
        "duplicates": check_duplicates(df),
        "missing_values": check_missing_values(df),
        "intraday_gaps": check_intraday_gaps(df)
    }

def get_yearly_duplicate_summary(dups_df):
    if dups_df.empty:
        return {}
    return dups_df['date'].dt.year.value_counts().sort_index().to_dict()
