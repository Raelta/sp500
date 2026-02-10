import pandas as pd
import numpy as np
from tqdm import tqdm
import os

input_file = 'SP.csv'
output_file = 'spy_data_25yr.parquet'
cutoff_date = '2001-01-29'

def process_sp_to_ohlcv():
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"Starting conversion from {input_file} to {output_file}...")
    print(f"Filtering for data since {cutoff_date}...")

    # Column indices from head: Symbol(0), Date and Time(1), Date(2), Time(3), Unfiltered Price(4), Price(5)
    # Date format: YYYY/MM/DD
    # Time format: HH:MM:SS.mmm
    
    chunk_size = 500000
    aggregated_data = []
    
    # We'll use a manual aggregation to handle boundaries between chunks
    current_minute = None
    minute_ticks = []

    # Get total file size for progress bar
    total_size = os.path.getsize(input_file)
    
    pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc="Reading SP.csv")
    
    try:
        # We read as strings first to avoid parsing issues and for faster initial filtering
        reader = pd.read_csv(input_file, chunksize=chunk_size, 
                             usecols=[2, 3, 5], 
                             names=['Date', 'Time', 'Price'], 
                             header=0,
                             dtype={'Date': str, 'Time': str, 'Price': float})
        
        for chunk in reader:
            # Update progress bar based on chunk size (approximate)
            # A more accurate way would be tracking bytes read, but pandas doesn't give that easily here
            # We'll just estimate based on rows. 
            # Average row length is roughly 50-60 bytes.
            pbar.update(len(chunk) * 55) 

            # Filter by date string (YYYY/MM/DD)
            # Reformat cutoff_date to match CSV if needed
            csv_cutoff = cutoff_date.replace('-', '/')
            chunk = chunk[chunk['Date'] >= csv_cutoff]
            
            if chunk.empty:
                continue

            # Create a Minute identifier: "YYYY-MM-DD HH:MM"
            # Time column is HH:MM:SS.mmm -> take HH:MM
            chunk['Minute'] = chunk['Date'].str.replace('/', '-') + ' ' + chunk['Time'].str.slice(0, 5)
            
            # Group by Minute within the chunk
            grouped = chunk.groupby('Minute')['Price'].agg(['first', 'max', 'min', 'last', 'count'])
            
            aggregated_data.append(grouped)

        pbar.close()
        
        if not aggregated_data:
            print("No data found after the cutoff date.")
            return

        print("Finalizing aggregation...")
        # Combine all chunked aggregations
        # Since a minute might span across chunks, we need to re-aggregate the results
        full_df = pd.concat(aggregated_data)
        
        # Re-aggregate by Minute
        final_df = full_df.groupby(full_df.index).agg({
            'first': 'first',
            'max': 'max',
            'min': 'min',
            'last': 'last',
            'count': 'sum'
        })
        
        final_df.index = pd.to_datetime(final_df.index)
        final_df = final_df.sort_index()
        
        # Rename columns to match the app's expectations
        final_df = final_df.rename(columns={
            'first': 'open',
            'max': 'high',
            'min': 'low',
            'last': 'close',
            'count': 'volume'
        })
        
        # Reset index and name it 'date'
        final_df.index.name = 'date'
        final_df = final_df.reset_index()
        
        # Add barCount and average for compatibility
        final_df['barCount'] = final_df['volume'] # Using volume as proxy for barCount
        final_df['average'] = (final_df['high'] + final_df['low']) / 2
        
        print(f"Saving to {output_file} ({len(final_df)} rows)...")
        final_df.to_parquet(output_file, index=False)
        print("Done!")

    except Exception as e:
        print(f"An error occurred: {e}")
        if 'pbar' in locals():
            pbar.close()

if __name__ == "__main__":
    process_sp_to_ohlcv()
