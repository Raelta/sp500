import pandas as pd
import numpy as np
import itertools
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
        self.n_rows = len(self.catalog.dates)
        
    def search(self, params_grid, fixed_params=None, target_cr_min=0, min_bumps=0, progress_callback=None, detailed=False):
        """
        Executes search using the pre-computed catalog.
        """
        # 1. Define Parameter Groups
        # We perform search by iterating over structural parameters (lengths)
        # and using vectorized operations for thresholds.
        
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
            local_res = []
            
            # 1. Get Base Arrays (Vectorized from Catalog)
            # Bump: Starts at i, length bump_len
            # Slide: Starts at i + bump_len, length slide_len
            
            # Indices for valid windows
            # We need i such that i + bump_len + slide_len < n_rows
            max_idx = self.n_rows - (bump_len + slide_len)
            if max_idx <= 0:
                return []
                
            # Slices
            # Bump Metrics
            # Change: From Matrix
            b_change = self.change_matrix[:max_idx, bump_len]
            # Volume: CumSum[i + L] - CumSum[i]
            # indices 0..max_idx-1
            # start indices: 0..max_idx
            # end indices: bump_len..max_idx+bump_len
            
            # Pre-compute arrays for this structure
            
            # BUMP VOL
            # vol_cumsum has size N+1. index i corresponds to sum up to i.
            # Vol[i, L] = CumSum[i+L] - CumSum[i]
            # We take slice [0 : max_idx] as starts
            # ends = starts + bump_len
            b_vol = self.vol_cumsum[bump_len : max_idx + bump_len] - self.vol_cumsum[0 : max_idx]
            
            # BUMP UP RATIO
            # UpCount[i, L]
            b_up_count = self.up_cumsum[bump_len : max_idx + bump_len] - self.up_cumsum[0 : max_idx]
            b_up_pct = (b_up_count / bump_len) * 100
            
            # SLIDE Metrics
            # Starts at i + bump_len
            # Ends at i + bump_len + slide_len
            slide_start_offset = bump_len
            
            # Change: We access change matrix at row (i + bump_len) with length (slide_len)
            s_change = self.change_matrix[slide_start_offset : max_idx + slide_start_offset, slide_len]
            
            # Volume
            s_vol = self.vol_cumsum[slide_start_offset + slide_len : max_idx + slide_start_offset + slide_len] - \
                    self.vol_cumsum[slide_start_offset : max_idx + slide_start_offset]
                    
            # Up Pct
            s_up_count = self.up_cumsum[slide_start_offset + slide_len : max_idx + slide_start_offset + slide_len] - \
                         self.up_cumsum[slide_start_offset : max_idx + slide_start_offset]
            s_up_pct = (s_up_count / slide_len) * 100
            
            # Absolute changes for thresholding
            b_change_abs = np.abs(b_change)
            s_change_abs = np.abs(s_change)
            
            # 2. Iterate Threshold Combinations (Vectorized over filters)
            # We iterate filters here. For massive grids, we could optimize further,
            # but simple iteration over thresholds is usually fast enough if arrays are pre-computed.
            
            # To optimize: Filter Bumps first, then Slides.
            
            # Pre-calculate masks for Bump Thresholds
            # b_thresh_masks[val] = boolean array
            b_t_masks = {val: (b_change_abs >= val) for val in bump_threshs}
            b_v_masks = {val: (b_vol >= val) for val in bump_vols}
            b_u_masks = {val: (b_up_pct >= val) for val in bump_ups}
            
            s_t_masks = {val: (s_change_abs >= val) for val in slide_threshs}
            s_v_masks = {val: (s_vol >= val) for val in slide_vols}
            s_u_masks = {val: (s_up_pct >= val) for val in slide_ups}
            
            # Iterating itertools.product inside here might be slow if grid is huge.
            # But typically grid is manageable.
            
            filter_combos = itertools.product(bump_threshs, bump_vols, bump_ups, slide_threshs, slide_vols, slide_ups)
            
            # Optimization: Group by Bump filters first
            # Bump Hits = (Thresh & Vol & Up)
            # Slide Hits = (Thresh & Vol & Up)
            # Total Hits = Bump Hits & Slide Hits
            
            # Let's just iterate straightforwardly for correctness first
            # Or use the matrix broadcasting trick from original search engine if needed.
            # Given we have the arrays in memory, basic boolean ops are fast.
            
            for bt, bv, bu, st, sv, su in filter_combos:
                # Bump Mask
                mask_b = b_t_masks[bt] & b_v_masks[bv] & b_u_masks[bu]
                total_bumps = np.count_nonzero(mask_b)
                
                if total_bumps < min_bumps:
                    continue
                    
                # Slide Mask (only check where bump is true?)
                # Vectorized AND is fast.
                mask_s = s_t_masks[st] & s_v_masks[sv] & s_u_masks[su]
                
                # Combine masks
                final_mask = mask_b & mask_s
                
                # Get raw indices
                raw_hit_indices = np.where(final_mask)[0]
                hits = len(raw_hit_indices)
                
                # Calculate True Hits (Non-overlapping)
                true_hits = 0
                if hits > 0:
                    # --- Overlap Filtering ---
                    # Get scores (Slide Change Abs)
                    # s_change_abs is a numpy array defined earlier in the function
                    scores = s_change_abs[raw_hit_indices]
                    
                    # Sort by score descending
                    sorted_order = np.argsort(scores)[::-1]
                    sorted_indices = raw_hit_indices[sorted_order]
                    
                    kept_indices = []
                    # self.n_rows is available from class instance
                    occupied = np.zeros(self.n_rows, dtype=bool)
                    window_len = bump_len + slide_len
                    
                    for idx in sorted_indices:
                        # Window is [idx, idx + window_len)
                        end_idx = min(idx + window_len, self.n_rows)
                        if not occupied[idx:end_idx].any():
                            kept_indices.append(idx)
                            occupied[idx:end_idx] = True
                            
                    true_hits = len(kept_indices)

                # We ignore target_cr_min check as requested
                
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
                
                # Return result if we have hits (or if we want to show 0 hits? usually 0 hits is boring)
                if hits > 0 or total_bumps > 0:
                    local_res.append(base_row)

                    if detailed and hits > 0:
                        # Extract Detailed Rows using RAW hits (Total Hits)
                        hits_indices = raw_hit_indices
                        
                        dates_start = self.catalog.dates[hits_indices]
                        dates_bump_end = self.catalog.dates[hits_indices + bump_len - 1]
                        dates_slide_start = self.catalog.dates[hits_indices + bump_len]
                        dates_slide_end = self.catalog.dates[hits_indices + bump_len + slide_len - 1]
                        
                        # Extract Values
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
                                'slide_up_pct_actual': float(val_s_up[k])
                            })
                            local_res.append(row)
                    elif not detailed:
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
                     # Update progress less frequently to reduce overhead
                     progress_callback(f"Processed {completed_count}/{total_structs}", completed_count/total_structs)
                
                try:
                    res = future.result()
                    if res:
                        results.extend(res)
                except Exception as exc:
                    print(f"Structure search exception: {exc}")
                
        # Format Results
        df_res = pd.DataFrame(results)
        
        # Add CLI command string if results exist
        if not df_res.empty:
            self._add_cli_commands(df_res)
            
        return df_res

    def _add_cli_commands(self, df_results):
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
            
            parts.append("--target-cr 0")
            commands.append(" ".join(parts))
            
        df_results['cli_command'] = commands
