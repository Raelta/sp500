import pandas as pd
import psutil
import os
import time

# Define the file path
DEFAULT_FILE_PATH = '1_min_SPY_2008-2021.csv'

def get_process_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # Convert to MB

def load_spy_data(file_path=DEFAULT_FILE_PATH):
    """
    Loads the SPY data from CSV, prints performance metrics, and returns the dataframe.
    """
    try:
        print(f"Starting process. Initial Memory Usage: {get_process_memory():.2f} MB")
        
        start_time = time.time()
        start_mem = get_process_memory()

        # Load the CSV file
        # The first column (index 0) looks like an integer index, so we'll set it as the index_col
        # We will parse the 'date' column. 
        # Since the date format is specific (YYYYMMDD  HH:MM:SS), we can specify it for efficiency.
        
        df = pd.read_csv(
            file_path, 
            index_col=0, 
            parse_dates=['date'],
            date_format='%Y%m%d  %H:%M:%S'
        )
        
        end_time = time.time()
        end_mem = get_process_memory()

        # Print success message
        print("\nSuccessfully loaded the dataframe.")
        
        # Display overhead stats
        print("\n--- Performance Metrics ---")
        print(f"Time taken to load: {end_time - start_time:.4f} seconds")
        print(f"Memory Usage Increase (Overhead): {end_mem - start_mem:.2f} MB")
        print(f"Current Process Memory Usage: {end_mem:.2f} MB")
        
        # Dataframe memory usage
        df_mem = df.memory_usage(deep=True).sum() / (1024 * 1024)
        print(f"Dataframe Internal Memory Usage (deep): {df_mem:.2f} MB")
        
        return df

    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None

if __name__ == "__main__":
    # This block only runs when the script is executed directly
    df = load_spy_data()
    
    if df is not None:
        # Display the first few rows
        print("\nFirst 5 rows:")
        print(df.head())
        
        # Display information about the dataframe
        print("\nDataframe Info:")
        print(df.info())
