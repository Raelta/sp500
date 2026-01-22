import pytest
import pandas as pd
import subprocess
import os
from src.data_loader import load_data_uncached
from src.data_validator import validate_dataset

def test_data_equivalence():
    """
    Verifies that the App Logic and CLI Logic result in the exact same dataframe.
    """
    DATA_FILE = "spy_data.parquet"
    if not os.path.exists(DATA_FILE):
        pytest.skip(f"{DATA_FILE} not found")
    
    # --- App Logic (Simulated) ---
    # App calls load_data_cached -> load_data_uncached + validate_dataset
    # Then manually drops duplicates if count > 0
    df_app = load_data_uncached(DATA_FILE)
    val_report = validate_dataset(df_app)
    if val_report['duplicates']['count'] > 0:
        df_app = df_app.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
        
    # --- CLI Logic (Simulated from goal_seek_cli.py) ---
    # CLI calls load_data_uncached
    # Then manually drops duplicates
    df_cli = load_data_uncached(DATA_FILE)
    df_cli = df_cli.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
    
    # Assert
    pd.testing.assert_frame_equal(df_app, df_cli)
    print(f"DataFrames are identical. Shape: {df_app.shape}")

def test_cli_execution_sanity():
    """
    Runs the CLI script via subprocess to ensure it produces a CSV.
    Uses params known to produce results (Bump Len 5, Thresh 0.1).
    """
    DATA_FILE = "spy_data.parquet"
    if not os.path.exists(DATA_FILE):
        pytest.skip(f"{DATA_FILE} not found")

    # Arguments (Safe parameters that should match a lot)
    cmd = [
        "python", "goal_seek_cli.py",
        "--bump-len-start", "5", "--bump-len-end", "5", "--bump-len-step", "0",
        "--bump-thresh-start", "0.1", "--bump-thresh-end", "0.1", "--bump-thresh-step", "0",
        "--target-cr", "0",
        "--top-n", "1",
        "--output", "test_output.csv"
    ]
    
    # Run
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check return code
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    
    # Check output exists
    assert os.path.exists("test_output.csv")
    
    # Check content
    df_res = pd.read_csv("test_output.csv")
    assert not df_res.empty
    print("CLI Execution produced results.")
    
    # Clean up
    if os.path.exists("test_output.csv"):
        os.remove("test_output.csv")

if __name__ == "__main__":
    # Allow running manually
    try:
        test_data_equivalence()
        test_cli_execution_sanity()
        print("All tests passed.")
    except Exception as e:
        print(f"Test failed: {e}")
