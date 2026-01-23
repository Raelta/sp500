import pandas as pd
import numpy as np
import itertools
from src.analyzer import calculate_change
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

def _process_structure(df_search, s_dict, filter_keys, filter_values, target_cr_min, min_bumps=0, detailed=False):
    """
    Worker function to process a single structural configuration.
    Uses Vectorized Broadcasting (Matrix Multiplication) to check all filter combinations efficiently.
    """
    # --- HEAVY CALCULATION (Structural) ---
    bump_len = int(s_dict['bump_len'])
    slide_len = int(s_dict['slide_len'])
    
    # SizeVol Calculation
    size_vol_series = df_search['volume'] * (df_search['close'] - df_search['open']).abs()
    
    # Rolling Volumes (Size Volume)
    bump_vol = size_vol_series.rolling(window=bump_len).sum().shift(-(bump_len - 1))
    slide_vol = size_vol_series.rolling(window=slide_len).sum().shift(-(bump_len + slide_len - 1))
    
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
    
    # Pre-calculate absolute changes
    bump_change_abs = bump_change.abs()
    slide_change_abs = slide_change.abs()
    
    # --- OPTIMIZATION: Data-Driven Pruning ---
    max_vals = {
        'bump_threshold': bump_change_abs.max(),
        'slide_threshold': slide_change_abs.max(),
        'min_bump_vol': bump_vol.max(),
        'min_slide_vol': slide_vol.max(),
        'bump_up_pct': bump_up_pct.max(),
        'slide_up_pct': slide_up_pct.max()
    }
    
    pruned_filter_values = []
    
    for i, key in enumerate(filter_keys):
        original_values = filter_values[i]
        current_max = max_vals.get(key, float('inf'))
        
        if pd.isna(current_max):
            pruned_values = []
        else:
            pruned_values = [v for v in original_values if v <= current_max]
        
        pruned_filter_values.append(pruned_values)
    
    if any(len(lst) == 0 for lst in pruned_filter_values):
        return []

    # --- VECTORIZED BROADCASTING ---
    # We assume filter_keys order: 
    # 0: bump_thresh, 1: slide_thresh, 2: bump_vol, 3: slide_vol, 4: bump_up, 5: slide_up
    
    bump_indices = [0, 2, 4]
    slide_indices = [1, 3, 5]
    
    bump_pruned = [pruned_filter_values[i] for i in bump_indices]
    slide_pruned = [pruned_filter_values[i] for i in slide_indices]
    
    # Generate partial combinations
    bump_combos = list(itertools.product(*bump_pruned))
    slide_combos = list(itertools.product(*slide_pruned))
    
    n_rows = len(df_search)
    
    # Metrics map
    metrics = [bump_change_abs, slide_change_abs, bump_vol, slide_vol, bump_up_pct, slide_up_pct]
    
    # 1. Pre-calculate Masks
    # mask_cache[key][val] = boolean array
    mask_cache = {}
    for idx, key in enumerate(filter_keys):
        metric = metrics[idx].to_numpy()
        # Handle NaNs: treat as impossible (-inf)
        metric = np.nan_to_num(metric, nan=-np.inf)
        
        mask_cache[key] = {}
        for val in pruned_filter_values[idx]:
            mask_cache[key][val] = (metric >= val)
            
    # 2. Build Matrices (N, Combos)
    def build_matrix(indices, combos):
        cols = []
        for combo in combos:
            final_mask = None
            for i, val in enumerate(combo):
                key_idx = indices[i]
                key = filter_keys[key_idx]
                mask = mask_cache[key][val]
                if final_mask is None:
                    final_mask = mask
                else:
                    final_mask = final_mask & mask
            cols.append(final_mask)
        
        if not cols:
            return np.zeros((n_rows, 0), dtype=bool)
        return np.stack(cols, axis=1)

    bump_matrix = build_matrix(bump_indices, bump_combos) # (N, B)
    slide_matrix = build_matrix(slide_indices, slide_combos) # (N, S)
    
    # 3. Matrix Multiplication
    # Hits(B, S) = bump_matrix.T @ slide_matrix
    # Use float32 to prevent overflow (int8 is too small for counts)
    hits_matrix = np.dot(bump_matrix.T.astype(np.float32), slide_matrix.astype(np.float32))
    
    # 4. Total Bumps (B,)
    total_bumps_vec = bump_matrix.sum(axis=0)
    
    # 6. Filter & Reconstruct
    # We filter by min_bumps and hits > 0.
    # We ignore target_cr_min for filtering as requested ("eliminate conversion rate completely")
    
    valid_mask = (total_bumps_vec[:, None] >= min_bumps) & (total_bumps_vec[:, None] > 0) & (hits_matrix > 0)
    b_indices, s_indices = np.where(valid_mask)
    
    local_results = []
    
    bump_keys_names = [filter_keys[i] for i in bump_indices]
    slide_keys_names = [filter_keys[i] for i in slide_indices]
    
    for b, s in zip(b_indices, s_indices):
        # --- Overlap Filtering for True Hits ---
        # 1. Identify raw hits
        mask = bump_matrix[:, b] & slide_matrix[:, s]
        raw_hit_indices = np.where(mask)[0]
        raw_hits = len(raw_hit_indices)
        
        if raw_hits == 0:
            true_hits = 0
            filtered_hit_indices = []
        else:
            # 2. Get scores (Slide Change Abs)
            # slide_change_abs is a Series, access via iloc or .values
            scores = slide_change_abs.iloc[raw_hit_indices].values
            
            # 3. Sort by score descending
            sorted_order = np.argsort(scores)[::-1]
            sorted_indices = raw_hit_indices[sorted_order]
            
            # 4. Greedy Non-Maximum Suppression
            kept_indices = []
            occupied = np.zeros(n_rows, dtype=bool)
            window_len = bump_len + slide_len
            
            for idx in sorted_indices:
                # Check for overlap
                # Window is [idx, idx + window_len)
                # Ensure we don't go out of bounds (though indices are valid starts)
                end_idx = min(idx + window_len, n_rows)
                
                if not occupied[idx:end_idx].any():
                    kept_indices.append(idx)
                    occupied[idx:end_idx] = True
            
            filtered_hit_indices = sorted(kept_indices) # Restore time order
            true_hits = len(filtered_hit_indices)

        total_b = int(total_bumps_vec[b])
        
        res = s_dict.copy()
        
        # Add Bump Params
        for k, v in zip(bump_keys_names, bump_combos[b]):
            res[k] = v
        # Add Slide Params
        for k, v in zip(slide_keys_names, slide_combos[s]):
            res[k] = v
            
        res['total_bumps'] = total_b
        res['total_hits'] = raw_hits
        res['true_hits'] = true_hits
        res['hits'] = raw_hits # Alias for backwards compatibility, using Total Hits
        
        if detailed:
            if raw_hits > 0:
                # For detailed results, we return ALL overlapping hits (raw_hits)
                # as the user wants to see "Total Hits"
                hit_indices = raw_hit_indices
                # Or do they want to see True Hits only? 
                # "total hits: this all the bump/slide matches"
                # So we should show all.
                
                # Extract Data Series (aligned)
                # Use .values to avoid index issues if df_search has non-standard index
                d_start = df_search['date'].iloc[hit_indices].values
                d_bend = df_search['date'].shift(-(bump_len - 1)).iloc[hit_indices].values
                d_sstart = df_search['date'].shift(-bump_len).iloc[hit_indices].values
                d_send = df_search['date'].shift(-(bump_len + slide_len - 1)).iloc[hit_indices].values
                
                b_change_vals = bump_change.iloc[hit_indices].values
                s_change_vals = slide_change.iloc[hit_indices].values
                b_vol_vals = bump_vol.iloc[hit_indices].values
                s_vol_vals = slide_vol.iloc[hit_indices].values
                b_up_vals = bump_up_pct.iloc[hit_indices].values
                s_up_vals = slide_up_pct.iloc[hit_indices].values
                
                for k in range(len(hit_indices)):
                    row_det = res.copy()
                    row_det.update({
                        'bump_start_date': str(d_start[k]),
                        'bump_end_date': str(d_bend[k]),
                        'slide_start_date': str(d_sstart[k]),
                        'slide_end_date': str(d_send[k]),
                        'bump_change': float(b_change_vals[k]),
                        'slide_change': float(s_change_vals[k]),
                        'bump_vol': float(b_vol_vals[k]),
                        'slide_vol': float(s_vol_vals[k]),
                        'bump_up_pct_actual': float(b_up_vals[k]),
                        'slide_up_pct_actual': float(s_up_vals[k])
                    })
                    local_results.append(row_det)
        else:
            local_results.append(res)
            
    return local_results

class GoalSeeker:
    def __init__(self, df):
        self.df = df.copy()

    def search(self, params_grid, fixed_params=None, target_cr_min=0, min_bumps=0, progress_callback=None, detailed=False):
        """
        Executes an exhaustive search over the provided parameter grid using Multiprocessing and Vectorization.
        """
        # 1. Apply Global Filters (Time/Day) if present in fixed_params
        df_search = self.df.copy()
        
        if fixed_params:
            if 'time_range' in fixed_params:
                start_t, end_t = fixed_params['time_range']
                times = df_search['date'].dt.time
                if start_t <= end_t:
                    df_search = df_search[(times >= start_t) & (times <= end_t)]
                else:
                    df_search = df_search[(times >= start_t) | (times <= end_t)]
            
            if 'days_of_week' in fixed_params and fixed_params['days_of_week']:
                df_search = df_search[df_search['date'].dt.day_name().isin(fixed_params['days_of_week'])]

        # 2. Define Parameter Groups
        structural_keys = ['bump_len', 'slide_len', 'bump_thresh_type', 'slide_thresh_type']
        filter_keys = ['bump_threshold', 'slide_threshold', 'min_bump_vol', 'min_slide_vol', 'bump_up_pct', 'slide_up_pct']
        
        def get_param_values(key, default=[None]):
            if key in params_grid:
                return params_grid[key]
            elif fixed_params and key in fixed_params:
                return [fixed_params[key]]
            return default

        struct_values = [get_param_values(k) for k in structural_keys]
        filter_values = [get_param_values(k) for k in filter_keys]
        
        # 3. Execute Search with Parallel Processing
        results = []
        
        max_workers = os.cpu_count() or 1
        
        struct_combos = list(itertools.product(*struct_values))
        total_structs = len(struct_combos)
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_struct = {}
            
            for struct_combo in struct_combos:
                s_dict = dict(zip(structural_keys, struct_combo))
                # Submit task
                future = executor.submit(
                    _process_structure, 
                    df_search, 
                    s_dict, 
                    filter_keys, 
                    filter_values, 
                    target_cr_min,
                    min_bumps,
                    detailed
                )
                future_to_struct[future] = s_dict
            
            # Handle results
            completed_count = 0
            for future in as_completed(future_to_struct):
                completed_count += 1
                s_dict = future_to_struct[future]
                
                # Update Progress
                if progress_callback:
                    struct_desc = ", ".join([f"{k}={v}" for k, v in s_dict.items()])
                    progress_callback(f"Analyzing structure {completed_count}/{total_structs}: {struct_desc}", completed_count / total_structs)
                
                try:
                    data = future.result()
                    if data:
                        results.extend(data)
                except Exception as exc:
                    print(f"Structure generation exception: {exc}")
        
        # --- Post-process: Add CLI Command for reproduction ---
        if results:
            range_mapping = {
                'bump_len': 'bump-len',
                'slide_len': 'slide-len',
                'min_bump_vol': 'bump-vol',
                'min_slide_vol': 'slide-vol',
                'bump_up_pct': 'bump-up',
                'slide_up_pct': 'slide-up'
            }
            
            single_mapping = {
                'bump_threshold': 'min-bump-threshold',
                'slide_threshold': 'min-slide-threshold'
            }
            
            for res in results:
                parts = ["python goal_seek_cli.py"]
                
                # Ranges (Locked)
                for key, cli_arg in range_mapping.items():
                    val = res.get(key)
                    if val is not None:
                        # Use step=0 to lock the range to this specific value
                        parts.append(f"--{cli_arg}-start {val} --{cli_arg}-end {val} --{cli_arg}-step 0")
                
                # Singles
                for key, cli_arg in single_mapping.items():
                    val = res.get(key)
                    if val is not None:
                        parts.append(f"--{cli_arg} {val}")
                
                # Ensure target CR allows this result to show (set to 0)
                parts.append("--target-cr 0")
                
                res['cli_command'] = " ".join(parts)

        df_results = pd.DataFrame(results)
        
        if not df_results.empty:
            # Add Scope Metadata to confirm what data was used
            df_results['scope_start'] = df_search['date'].min()
            df_results['scope_end'] = df_search['date'].max()
            # unique days names
            days_str = ",".join(sorted(df_search['date'].dt.day_name().unique()))
            df_results['scope_days'] = days_str
            df_results['scope_rows'] = len(df_search)
            
        return df_results
