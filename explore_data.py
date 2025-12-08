from load_data import load_spy_data

def explore():
    print("Loading data for exploration...")
    df = load_spy_data()
    
    if df is None:
        print("Failed to load data.")
        return

    print("\n" + "="*40)
    print("       DATA EXPLORATION REPORT")
    print("="*40)

    # 1. Basic Stats
    print("\n1. Summary Statistics (Numerical Columns):")
    print(df.describe())

    # 2. Date Range
    if 'date' in df.columns:
        print("\n2. Date Range:")
        print(f"Start: {df['date'].min()}")
        print(f"End:   {df['date'].max()}")
        print(f"Total Span: {df['date'].max() - df['date'].min()}")
    
    # 3. Missing Values
    print("\n3. Missing Values Check:")
    missing = df.isnull().sum()
    if missing.sum() == 0:
        print("No missing values found.")
    else:
        print(missing[missing > 0])
        
    # 4. Column Names
    print("\n4. Columns Available:")
    print(df.columns.tolist())

    # 5. Monthly Average Open
    print("\n5. Monthly Average Open Price:")
    # Resample by Month End ('ME') using the 'date' column
    # We use 'ME' because 'M' is deprecated in pandas 2.x
    monthly_avg = df.resample('ME', on='date')['open'].mean()
    print(monthly_avg)

if __name__ == "__main__":
    explore()
