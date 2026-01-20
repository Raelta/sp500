import pandas as pd
import numpy as np
import itertools
from src.analyzer import calculate_change

class GoalSeeker:
    def __init__(self, df):
        self.df = df.copy()

    def search(self, params_grid, fixed_params=None, target_cr_min=0, progress_callback=None):
        """
        Executes an exhaustive search over the provided parameter grid.
        
        Args:
            params_grid: Dictionary where keys are parameter names and values are lists of values to test.
                         Keys expected: 
                         - bump_len, slide_len
                         - bump_thresh_type, slide_thresh_type
                         - bump_threshold, slide_threshold
                         - min_bump_vol, min_slide_vol
                         - bump_up_pct, slide_up_pct
            fixed_params: Dictionary of parameters that are constant for this search.
                          Used primarily for 'time_range' and 'days_of_week' pre-filtering.
            target_cr_min: Minimum Conversion Rate (Hit Ratio) to include in results.
            progress_callback: Function accepting (message, percentage_float).
            
        Returns:
            pd.DataFrame of results.
        """
        # 1. Apply Global Filters (Time/Day) if present in fixed_params
        df_search = self.df.copy()
        
        if fixed_params:
            if 'time_range' in fixed_params:
                start_t, end_t = fixed_params['time_range']
                # Filter by time (using index or date column if datetime)
                # Assuming 'date' column exists and is datetime
                times = df_search['date'].dt.time
                if start_t <= end_t:
                    df_search = df_search[(times >= start_t) & (times <= end_t)]
                else:
                    df_search = df_search[(times >= start_t) | (times <= end_t)]
            
            if 'days_of_week' in fixed_params and fixed_params['days_of_week']:
                df_search = df_search[df_search['date'].dt.day_name().isin(fixed_params['days_of_week'])]

        # 2. Define Parameter Groups
        # Structural: Requires dataframe recalculation (Rolling windows, Change calculation based on type)
        structural_keys = ['bump_len', 'slide_len', 'bump_thresh_type', 'slide_thresh_type']
        
        # Filter: Lightweight boolean masking
        filter_keys = ['bump_threshold', 'slide_threshold', 'min_bump_vol', 'min_slide_vol', 'bump_up_pct', 'slide_up_pct']
        
        # Extract values for the grid, using fixed_params as fallback for single values
        # If a key is in params_grid, use it. If not, check fixed_params. If neither, default (though UI should handle this).
        
        def get_param_values(key, default=[None]):
            if key in params_grid:
                return params_grid[key]
            elif fixed_params and key in fixed_params:
                return [fixed_params[key]]
            return default

        struct_values = [get_param_values(k) for k in structural_keys]
        filter_values = [get_param_values(k) for k in filter_keys]
        
        # 3. Execute Search
        results = []
        
        # Calculate total structural iterations for progress
        total_structs = np.prod([len(v) for v in struct_values])
        current_struct_idx = 0
        
        for struct_combo in itertools.product(*struct_values):
            current_struct_idx += 1
            s_dict = dict(zip(structural_keys, struct_combo))
            
            # Update Progress
            if progress_callback:
                progress_callback(f"Analyzing structure {current_struct_idx}/{total_structs}...", current_struct_idx / total_structs)
            
            # --- HEAVY CALCULATION ---
            bump_len = int(s_dict['bump_len'])
            slide_len = int(s_dict['slide_len'])
            
            # Rolling Volumes
            # shift(-(window - 1)) aligns the rolling window to start at 'i'
            bump_vol = df_search['volume'].rolling(window=bump_len).sum().shift(-(bump_len - 1))
            slide_vol = df_search['volume'].rolling(window=slide_len).sum().shift(-(bump_len + slide_len - 1))
            
            # Changes
            bump_open = df_search['open']
            bump_close = df_search['close'].shift(-(bump_len - 1))
            bump_change = calculate_change(bump_open, bump_close, s_dict['bump_thresh_type'])
            
            slide_open = df_search['open'].shift(-bump_len)
            slide_close = df_search['close'].shift(-(bump_len + slide_len - 1))
            slide_change = calculate_change(slide_open, slide_close, s_dict['slide_thresh_type'])
            
            # Up Percents
            is_up = (df_search['close'] > df_search['open']).astype(int)
            bump_up_pct = is_up.rolling(window=bump_len).mean().shift(-(bump_len - 1)) * 100
            slide_up_pct = is_up.rolling(window=slide_len).mean().shift(-(bump_len + slide_len - 1)) * 100
            
            # Pre-calculate absolute changes for filtering
            bump_change_abs = bump_change.abs()
            slide_change_abs = slide_change.abs()
            
            # --- INNER LOOP (FILTERS) ---
            # Iterate through all filter combinations
            for filter_combo in itertools.product(*filter_values):
                f_dict = dict(zip(filter_keys, filter_combo))
                
                # Create Masks
                # Using numpy/pandas vectorization
                # We do this for every filter combo. It's fast but doing it 10k times adds up.
                # Ideally, we could sort and slice, but brute force boolean is simplest to implement correctly first.
                
                bump_mask = (bump_change_abs >= f_dict['bump_threshold']) & \
                            (bump_vol >= f_dict['min_bump_vol']) & \
                            (bump_up_pct >= f_dict['bump_up_pct'])
                
                slide_mask = (slide_change_abs >= f_dict['slide_threshold']) & \
                             (slide_vol >= f_dict['min_slide_vol']) & \
                             (slide_up_pct >= f_dict['slide_up_pct'])
                
                # Stats
                total_bumps = bump_mask.sum()
                hits = (bump_mask & slide_mask).sum()
                
                hit_ratio = (hits / total_bumps * 100) if total_bumps > 0 else 0.0
                
                if hit_ratio >= target_cr_min and total_bumps > 0:
                    # Record Result
                    # Combine all params
                    res = {**s_dict, **f_dict}
                    res['total_bumps'] = int(total_bumps)
                    res['hits'] = int(hits)
                    res['conversion_rate'] = hit_ratio
                    results.append(res)
        
        return pd.DataFrame(results)
