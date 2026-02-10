import pandas as pd

try:
    df = pd.read_parquet('spy_data_25yr.parquet')
    print("Columns:", df.columns.tolist())
    print(df.head())
except Exception as e:
    print(f"Error: {e}")
