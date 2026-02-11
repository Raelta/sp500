import pandas as pd
import numpy as np
import itertools
from src.analyzer import calculate_change
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

def _process_structure(df_all, s_dict, filter_keys, filter_values, target_cr_min, min_bumps=0, detailed=False):
    """
    Worker function to process a single structural configuration.
    Uses Vectorized Broadcasting (Matrix Multiplication) to check all filter combinations efficiently.
    """
    # --- HEAVY CALCULATION (Structural) ---
    bump_len = int(s_dict['bump_len'])
    slide_len = int(s_dict['slide_len'])
    n_rows = len(df_all)
    
    # SizeVol Calculation
    size_vol_series = df_all['volume'] * (df_all['close'] - df_all['open']).abs()
    
    # Rolling Volumes (Size Volume)
    bump_vol = size_vol_series.rolling(window=bump_len).sum().shift(-(bump_len - 1))
    slide_vol = size_vol_series.rolling(window=slide_len).sum().shift(-(bump_len + slide_len - 1))
    
    # Changes
    bump_open = df_all['open']
    bump_close = df_all['close'].shift(-(bump_len - 1))
    bump_change = calculate_change(bump_open, bump_close, s_dict['bump_thresh_type'])
    
    slide_open = df_all['open'].shift(-bump_len)
    slide_close = df_all['close'].shift(-(bump_len + slide_len - 1))
    slide_change = calculate_change(slide_open, slide_close, s_dict['slide_thresh_type'])
    
    # Up Percents
    is_up = (df_all['close'] > df_all['open']).astype(int)
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
    bump_indices = [0, 2, 4]
    slide_indices = [1, 3, 5]
    bump_pruned = [pruned_filter_values[i] for i in bump_indices]
    slide_pruned = [pruned_filter_values[i] for i in slide_indices]
    
    bump_combos = list(itertools.product(*bump_pruned))
    slide_combos = list(itertools.product(*slide_pruned))
    
    metrics = [bump_change_abs, slide_change_abs, bump_vol, slide_vol, bump_up_pct, slide_up_pct]
    
    mask_cache = {}
    for idx, key in enumerate(filter_keys):
        metric = metrics[idx].to_numpy()
        metric = np.nan_to_num(metric, nan=-np.inf)
        mask_cache[key] = {}
        for val in pruned_filter_values[idx]:
            mask_cache[key][val] = (metric >= val)
            
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

    bump_matrix = build_matrix(bump_indices, bump_combos)
    slide_matrix = build_matrix(slide_indices, slide_combos)
    
    # IMPORTANT: The slide starts at i + bump_len. 
    # But in slide_matrix, index i already contains the metric for start=i.
    # Because we already shifted the raw series by -(bump_len) earlier when creating slide_change.
    # So both bump_matrix[i] and slide_matrix[i] refer to the SAME pattern starting at i.
    
    hits_matrix = np.dot(bump_matrix.T.astype(np.float32), slide_matrix.astype(np.float32))
    total_bumps_vec = bump_matrix.sum(axis=0)
    
    valid_mask = (total_bumps_vec[:, None] >= min_bumps) & (total_bumps_vec[:, None] > 0) & (hits_matrix > 0)
    b_indices, s_indices = np.where(valid_mask)
    
    local_results = []
    bump_keys_names = [filter_keys[i] for i in bump_indices]
    slide_keys_names = [filter_keys[i] for i in slide_indices]
    
    for b, s in zip(b_indices, s_indices):
        mask = bump_matrix[:, b] & slide_matrix[:, s]
        raw_hit_indices = np.where(mask)[0]
        raw_hits = len(raw_hit_indices)
        
        if raw_hits == 0:
            true_hits = 0
        else:
            scores = slide_change_abs.iloc[raw_hit_indices].values
            sorted_order = np.argsort(scores)[::-1]
            sorted_indices = raw_hit_indices[sorted_order]
            kept_indices = []
            occupied = np.zeros(n_rows, dtype=bool)
            window_len = bump_len + slide_len
            for idx in sorted_indices:
                end_idx = min(idx + window_len, n_rows)
                if not occupied[idx:end_idx].any():
                    kept_indices.append(idx)
                    occupied[idx:end_idx] = True
            true_hits = len(kept_indices)
            best_idx_in_scores = np.argmax(scores)
            best_hit_idx = raw_hit_indices[best_idx_in_scores]
            best_hit_date = df_all['date'].iloc[best_hit_idx].strftime('%Y-%m-%d %H:%M')

        total_b = int(total_bumps_vec[b])
        res = s_dict.copy()
        for k, v in zip(bump_keys_names, bump_combos[b]): res[k] = v
        for k, v in zip(slide_keys_names, slide_combos[s]): res[k] = v
        res['total_bumps'] = total_b
        res['total_hits'] = raw_hits
        res['true_hits'] = true_hits
        res['hits'] = raw_hits
        if raw_hits > 0: res['best_hit_date'] = best_hit_date
        
        if detailed and raw_hits > 0:
            true_hit_set = set(kept_indices)
            d_start = df_all['date'].iloc[raw_hit_indices].values
            d_bend = df_all['date'].shift(-(bump_len - 1)).iloc[raw_hit_indices].values
            d_sstart = df_all['date'].shift(-bump_len).iloc[raw_hit_indices].values
            d_send = df_all['date'].shift(-(bump_len + slide_len - 1)).iloc[raw_hit_indices].values
            b_change_vals = bump_change.iloc[raw_hit_indices].values
            s_change_vals = slide_change.iloc[raw_hit_indices].values
            b_vol_vals = bump_vol.iloc[raw_hit_indices].values
            s_vol_vals = slide_vol.iloc[raw_hit_indices].values
            b_up_vals = bump_up_pct.iloc[raw_hit_indices].values
            s_up_vals = slide_up_pct.iloc[raw_hit_indices].values
            
            for k in range(len(raw_hit_indices)):
                row_det = res.copy()
                row_det.update({
                    'bump_start_date': str(d_start[k]), 'bump_end_date': str(d_bend[k]),
                    'slide_start_date': str(d_sstart[k]), 'slide_end_date': str(d_send[k]),
                    'bump_change': float(b_change_vals[k]), 'slide_change': float(s_change_vals[k]),
                    'bump_vol': float(b_vol_vals[k]), 'slide_vol': float(s_vol_vals[k]),
                    'bump_up_pct_actual': float(b_up_vals[k]), 'slide_up_pct_actual': float(s_up_vals[k]),
                    'is_true_hit': raw_hit_indices[k] in true_hit_set
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
        Executes an exhaustive search over the provided parameter grid.
        """
        # 2. Define Parameter Groups
        structural_keys = ['bump_len', 'slide_len', 'bump_thresh_type', 'slide_thresh_type']
        filter_keys = ['bump_threshold', 'slide_threshold', 'min_bump_vol', 'min_slide_vol', 'bump_up_pct', 'slide_up_pct']
        
        def get_param_values(key, default=[None]):
            if key in params_grid: return params_grid[key]
            elif fixed_params and key in fixed_params: return [fixed_params[key]]
            return default

        struct_values = [get_param_values(k) for k in structural_keys]
        filter_values = [get_param_values(k) for k in filter_keys]
        
        results = []
        max_workers = os.cpu_count() or 1
        struct_combos = list(itertools.product(*struct_values))
        total_structs = len(struct_combos)
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_struct = {}
            for struct_combo in struct_combos:
                s_dict = dict(zip(structural_keys, struct_combo))
                future = executor.submit(
                    _process_structure, self.df, s_dict, filter_keys, filter_values, target_cr_min, min_bumps, detailed
                )
                future_to_struct[future] = s_dict
            
            completed_count = 0
            for future in as_completed(future_to_struct):
                completed_count += 1
                if progress_callback:
                    progress_callback(f"Analyzing {completed_count}/{total_structs}", completed_count / total_structs)
                try:
                    data = future.result()
                    if data: results.extend(data)
                except Exception as exc: print(f"Error: {exc}")
        
        if results:
            self._add_cli_commands(results)

        df_results = pd.DataFrame(results)
        if not df_results.empty:
            df_results['scope_start'] = self.df['date'].min()
            df_results['scope_end'] = self.df['date'].max()
            df_results['scope_rows'] = len(self.df)
            
        return df_results

    def _add_cli_commands(self, results):
        range_mapping = {'bump_len': 'bump-len', 'slide_len': 'slide-len', 'min_bump_vol': 'bump-vol', 'min_slide_vol': 'slide-vol', 'bump_up_pct': 'bump-up', 'slide_up_pct': 'slide-up'}
        single_mapping = {'bump_threshold': 'min-bump-threshold', 'slide_threshold': 'min-slide-threshold'}
        for res in results:
            parts = ["python goal_seek_cli.py"]
            for key, cli_arg in range_mapping.items():
                val = res.get(key)
                if val is not None: parts.append(f"--{cli_arg}-start {val} --{cli_arg}-end {val} --{cli_arg}-step 0")
            for key, cli_arg in single_mapping.items():
                val = res.get(key)
                if val is not None: parts.append(f"--{cli_arg} {val}")
            res['cli_command'] = " ".join(parts)
