import pandas as pd
import numpy as np
import itertools
import json
from src.catalog import WindowCatalog
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

class CatalogSearcher:
    def __init__(self, catalog_dir="catalog"):
        self.catalog = WindowCatalog(catalog_dir).load(read_only=True)
        # Helper arrays
        self.vol_cumsum = self.catalog.vol_cumsum
        self.up_cumsum = self.catalog.up_cumsum
        self.change_matrix = self.catalog.change_matrix
        self.dates_raw = self.catalog.dates
        self.n_rows = len(self.dates_raw)
        self.scale_factor = self.catalog.scale_factor
        
    def search(self, params_grid, fixed_params=None, target_cr_min=0, min_bumps=0, progress_callback=None, detailed=False):
        """
        Executes search using the pre-computed catalog.
        """
        # 2. Define Parameter Groups
        bump_lens = params_grid.get('bump_len', [10])
        slide_lens = params_grid.get('slide_len', [5])
        
        # Thresholds
        bump_threshs = np.array(params_grid.get('bump_threshold', [0.0]), dtype=np.float32)
        slide_threshs = np.array(params_grid.get('slide_threshold', [0.0]), dtype=np.float32)
        
        # Volumes
        bump_vols = np.array(params_grid.get('min_bump_vol', [0]), dtype=np.float32)
        slide_vols = np.array(params_grid.get('min_slide_vol', [0]), dtype=np.float32)
        
        # Up Ratios
        bump_ups = np.array(params_grid.get('bump_up_pct', [0.0]), dtype=np.float32)
        slide_ups = np.array(params_grid.get('slide_up_pct', [0.0]), dtype=np.float32)
        
        # Structural Combinations
        struct_combos = list(itertools.product(bump_lens, slide_lens))
        total_structs = len(struct_combos)
        
        results = []
        
        # Helper for vectorized search
        def process_structure(bump_len, slide_len):
            bump_len = int(bump_len)
            slide_len = int(slide_len)
            local_res = []
            
            # Indices for valid windows
            # We need i such that i + bump_len + slide_len < n_rows
            max_idx = self.n_rows - (bump_len + slide_len)
            if max_idx <= 0:
                return []
                
            # Slices
            # Bump Metrics
            # Unscale from int8 (fast vectorized op)
            b_change_raw = self.change_matrix[:max_idx, bump_len]
            b_change = b_change_raw.astype(np.float32) / self.scale_factor
            
            b_vol = self.vol_cumsum[bump_len : max_idx + bump_len] - self.vol_cumsum[0 : max_idx]
            
            b_up_count = self.up_cumsum[bump_len : max_idx + bump_len] - self.up_cumsum[0 : max_idx]
            b_up_pct = (b_up_count / bump_len) * 100
            
            # SLIDE Metrics
            slide_start_offset = bump_len
            s_change_raw = self.change_matrix[slide_start_offset : max_idx + slide_start_offset, slide_len]
            s_change = s_change_raw.astype(np.float32) / self.scale_factor
            
            s_vol = self.vol_cumsum[slide_start_offset + slide_len : max_idx + slide_start_offset + slide_len] - \
                    self.vol_cumsum[slide_start_offset : max_idx + slide_start_offset]
            s_up_count = self.up_cumsum[slide_start_offset + slide_len : max_idx + slide_start_offset + slide_len] - \
                         self.up_cumsum[slide_start_offset : max_idx + slide_start_offset]
            s_up_pct = (s_up_count / slide_len) * 100
            
            # Absolute changes for thresholding
            b_change_abs = np.abs(b_change)
            s_change_abs = np.abs(s_change)
            
            # Pre-calculate masks for Thresholds
            b_t_masks = {val: (b_change_abs >= val) for val in bump_threshs}
            b_v_masks = {val: (b_vol >= val) for val in bump_vols}
            b_u_masks = {val: (b_up_pct >= val) for val in bump_ups}
            
            s_t_masks = {val: (s_change_abs >= val) for val in slide_threshs}
            s_v_masks = {val: (s_vol >= val) for val in slide_vols}
            s_u_masks = {val: (s_up_pct >= val) for val in slide_ups}
            
            filter_combos = itertools.product(bump_threshs, bump_vols, bump_ups, slide_threshs, slide_vols, slide_ups)
            
            for bt, bv, bu, st, sv, su in filter_combos:
                # Bump Mask
                mask_b = b_t_masks[bt] & b_v_masks[bv] & b_u_masks[bu]
                total_bumps = np.count_nonzero(mask_b)
                
                if total_bumps < min_bumps:
                    continue
                    
                # Combine masks
                mask_s = s_t_masks[st] & s_v_masks[sv] & s_u_masks[su]
                final_mask = mask_b & mask_s
                
                # Get raw indices
                raw_hit_indices = np.where(final_mask)[0]
                hits = len(raw_hit_indices)
                
                # Calculate True Hits (Non-overlapping)
                true_hits = 0
                if hits > 0:
                    scores = s_change_abs[raw_hit_indices]
                    sorted_order = np.argsort(scores)[::-1]
                    sorted_indices = raw_hit_indices[sorted_order]
                    
                    kept_indices = []
                    occupied = np.zeros(self.n_rows, dtype=bool)
                    window_len = bump_len + slide_len
                    
                    for idx in sorted_indices:
                        end_idx = min(idx + window_len, self.n_rows)
                        if not occupied[idx:end_idx].any():
                            kept_indices.append(idx)
                            occupied[idx:end_idx] = True
                            
                    true_hits = len(kept_indices)
                    best_idx_in_scores = np.argmax(scores)
                    best_hit_idx = raw_hit_indices[best_idx_in_scores]
                    best_hit_date = pd.Timestamp(self.dates_raw[best_hit_idx]).strftime('%Y-%m-%d %H:%M')
                    true_hit_set = set(kept_indices)
                    
                    # Year Summary for True Hits
                    hit_dates = pd.to_datetime(self.dates_raw[kept_indices])
                    hits_per_year = hit_dates.year.value_counts().sort_index().to_dict()
                    hits_per_year = {str(k): int(v) for k, v in hits_per_year.items()}
                    hits_per_year_json = json.dumps(hits_per_year)

                # Store
                base_row = {
                    'bump_len': bump_len,
                    'slide_len': slide_len,
                    'bump_threshold': float(bt),
                    'min_bump_vol': int(bv),
                    'bump_up_pct': float(bu),
                    'slide_threshold': float(st),
                    'min_slide_vol': int(sv),
                    'slide_up_pct': float(su),
                    'total_bumps': int(total_bumps),
                    'total_hits': int(hits),
                    'true_hits': int(true_hits),
                    'hits': int(hits), # Alias for Total Hits
                }
                
                if hits > 0 or total_bumps > 0:
                    if hits > 0:
                        base_row['best_hit_date'] = best_hit_date
                        base_row['hits_per_year'] = hits_per_year_json
                        
                    if detailed and hits > 0:
                        hits_indices = raw_hit_indices
                        dates_start = self.dates_raw[hits_indices]
                        dates_bump_end = self.dates_raw[hits_indices + bump_len - 1]
                        dates_slide_start = self.dates_raw[hits_indices + bump_len]
                        dates_slide_end = self.dates_raw[hits_indices + bump_len + slide_len - 1]
                        
                        one_min = np.timedelta64(1, 'm')
                        gaps = dates_slide_start - dates_bump_end
                        is_gap = gaps > one_min
                        
                        val_b_change = b_change[hits_indices]
                        val_s_change = s_change[hits_indices]
                        val_b_vol = b_vol[hits_indices]
                        val_s_vol = s_vol[hits_indices]
                        val_b_up = b_up_pct[hits_indices]
                        val_s_up = s_up_pct[hits_indices]
                        
                        for k in range(hits):
                            row = base_row.copy()
                            row.update({
                                'bump_start_date': pd.Timestamp(dates_start[k]),
                                'bump_end_date': pd.Timestamp(dates_bump_end[k]),
                                'slide_start_date': pd.Timestamp(dates_slide_start[k]),
                                'slide_end_date': pd.Timestamp(dates_slide_end[k]),
                                'bump_change': float(val_b_change[k]),
                                'slide_change': float(val_s_change[k]),
                                'bump_vol': float(val_b_vol[k]),
                                'slide_vol': float(val_s_vol[k]),
                                'bump_up_pct_actual': float(val_b_up[k]),
                                'slide_up_pct_actual': float(val_s_up[k]),
                                'is_true_hit': hits_indices[k] in true_hit_set,
                                'data_gap': bool(is_gap[k])
                            })
                            local_res.append(row)
                    else:
                        local_res.append(base_row)
                        
            return local_res

        # Execute with ThreadPoolExecutor
        max_workers = os.cpu_count() or 4
        print(f"Executing search with {max_workers} threads...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_struct = {
                executor.submit(process_structure, b, s): (b, s)
                for b, s in struct_combos
            }
            
            completed_count = 0
            for future in as_completed(future_to_struct):
                completed_count += 1
                if progress_callback and completed_count % 10 == 0:
                     progress_callback(f"Processed {completed_count}/{total_structs}", completed_count/total_structs)
                
                try:
                    res = future.result()
                    if res:
                        results.extend(res)
                except Exception as exc:
                    print(f"Structure search exception: {exc}")
                
        # Format Results
        df_res = pd.DataFrame(results)
        if not df_res.empty:
            self._add_cli_commands(df_res)
        return df_res

    def _add_cli_commands(self, df_results):
        range_mapping = {
            'bump_len': 'bump-len', 'slide_len': 'slide-len', 'min_bump_vol': 'bump-vol',
            'min_slide_vol': 'slide-vol', 'bump_up_pct': 'bump-up', 'slide_up_pct': 'slide-up'
        }
        single_mapping = { 'bump_threshold': 'min-bump-threshold', 'slide_threshold': 'min-slide-threshold' }
        
        commands = []
        for _, res in df_results.iterrows():
            parts = ["python goal_seek_cli.py"]
            for key, cli_arg in range_mapping.items():
                val = res.get(key)
                if val is not None:
                    parts.append(f"--{cli_arg}-start {val} --{cli_arg}-end {val} --{cli_arg}-step 0")
            for key, cli_arg in single_mapping.items():
                val = res.get(key)
                if val is not None:
                    parts.append(f"--{cli_arg} {val}")
            commands.append(" ".join(parts))
        df_results['cli_command'] = commands
