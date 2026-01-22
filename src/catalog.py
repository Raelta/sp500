import numpy as np
import pandas as pd
import os
from tqdm import tqdm

class WindowCatalog:
    def __init__(self, catalog_dir="catalog"):
        self.catalog_dir = catalog_dir
        self.change_path = os.path.join(catalog_dir, "change_matrix.npy")
        self.meta_path = os.path.join(catalog_dir, "metadata.npz")
        
        # Cache for loaded data
        self.change_matrix = None
        self.vol_cumsum = None
        self.up_cumsum = None
        self.dates = None
        
    def build(self, df, max_len=360):
        """
        Builds the catalog from the provided DataFrame.
        df: DataFrame with 'open', 'close', 'volume', 'date' columns.
        max_len: Maximum window length to compute.
        """
        if not os.path.exists(self.catalog_dir):
            os.makedirs(self.catalog_dir)
            
        n_rows = len(df)
        print(f"Building catalog for {n_rows} rows, max_len={max_len}...")
        
        # 1. Create Change Matrix (Memory Mapped to write directly to disk)
        # Shape: (n_rows, max_len + 1). Column 0 is unused or length 0.
        # We will use columns 1..max_len for lengths.
        # Indices: Matrix[i, k] = Change for window starting at i with length k.
        
        print("Initializing Change Matrix...")
        change_matrix = np.memmap(
            self.change_path, 
            dtype='float32', 
            mode='w+', 
            shape=(n_rows, max_len + 1)
        )
        
        opens = df['open'].values.astype(np.float32)
        closes = df['close'].values.astype(np.float32)
        
        # Handle zeros in open to avoid division by zero
        opens[opens == 0] = np.nan
        
        print("Computing Percent Changes...")
        # Vectorized loop over lengths
        # For length L, Change[i] = (Close[i + L - 1] - Open[i]) / Open[i]
        
        # We can process in chunks of lengths to show progress
        for length in tqdm(range(1, max_len + 1), desc="Window Lengths"):
            # Shifted Closes: close at (i + length - 1)
            # We need to shift closes UP by (length - 1)
            shift = length - 1
            if shift == 0:
                # Length 1: Close[i] - Open[i]
                current_closes = closes
            else:
                # Rolling back the closes array to align end with start
                # closes[i] becomes closes[i+shift] essentially
                # numpy roll is circular, we need slicing
                # Slice closes[shift:] and pad with NaNs at the end
                current_closes = np.full_like(closes, np.nan)
                current_closes[:-shift] = closes[shift:]
                
            # Calculate change
            # (End - Start) / Start * 100
            change = (current_closes - opens) / opens * 100
            
            # Write to matrix column
            change_matrix[:, length] = change
            
        # Flush changes to disk
        change_matrix.flush()
        print("Change Matrix built.")
        
        # 2. Build Metadata (Cumulative Sums)
        print("Building Metadata...")
        
        # Volume Size (Volume * Price Move)
        # Recalculate size_vol series
        price_diff = (df['close'] - df['open']).abs()
        size_vol = (df['volume'] * price_diff).values.astype(np.float32)
        
        # Cumulative Sum (Prefix Sum)
        # Insert 0 at the beginning to make indexing easier: Sum(i, L) = C[i+L] - C[i]
        # BUT rolling sum typically aligns to the right. 
        # Here we want Sum from row i to i+L-1.
        # Let C[k] be sum of 0..k-1.
        # Sum(i to i+L-1) = C[i+L] - C[i].
        
        vol_cumsum = np.concatenate(([0], np.cumsum(size_vol)))
        
        # Up Candles
        is_up = (df['close'] > df['open']).astype(np.float32).values
        up_cumsum = np.concatenate(([0], np.cumsum(is_up)))
        
        # Dates (store dates to align search results later)
        # We store as int64 (nanoseconds)
        dates = df['date'].values.astype(np.int64)
        
        np.savez(
            self.meta_path,
            vol_cumsum=vol_cumsum,
            up_cumsum=up_cumsum,
            dates=dates,
            max_len=max_len
        )
        print("Metadata saved.")
        
    def load(self, read_only=True):
        """
        Loads the catalog for reading.
        """
        if not os.path.exists(self.change_path) or not os.path.exists(self.meta_path):
            raise FileNotFoundError("Catalog files not found. Run build command first.")
            
        # Load Metadata
        meta = np.load(self.meta_path)
        self.vol_cumsum = meta['vol_cumsum']
        self.up_cumsum = meta['up_cumsum']
        self.dates = meta['dates']
        self.max_len = int(meta['max_len'])
        
        n_rows = len(self.dates)
        
        # Map Change Matrix
        mode = 'r' if read_only else 'r+'
        self.change_matrix = np.memmap(
            self.change_path,
            dtype='float32',
            mode=mode,
            shape=(n_rows, self.max_len + 1)
        )
        
        return self

    def get_window_metrics(self, start_idx, length):
        """
        Returns (change, vol_sum, up_count) for a specific window.
        """
        if start_idx + length > len(self.change_matrix):
            return None
            
        change = self.change_matrix[start_idx, length]
        vol = self.vol_cumsum[start_idx + length] - self.vol_cumsum[start_idx]
        up = self.up_cumsum[start_idx + length] - self.up_cumsum[start_idx]
        
        return change, vol, up
