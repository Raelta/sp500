import pandas as pd
import pytest
from src.data_validator import validate_dataset

def test_data_validator_identifies_issues():
    # Create synthetic data with intentional flaws
    dates = pd.date_range(start="2023-01-01 09:30:00", periods=5, freq="min").tolist()
    # Add a duplicate date
    dates.append(dates[-1])
    # Add a gap
    dates.append(pd.Timestamp("2023-01-01 10:00:00"))
    
    df = pd.DataFrame({
        "date": dates,
        "open": [100.0] * 7,
        "high": [101.0] * 7,
        "low": [99.0] * 7,
        "close": [100.5] * 7,
        "volume": [1000] * 6 + [None] # One missing value
    })
    
    report = validate_dataset(df)
    
    assert report['duplicates']['count'] == 2
    assert report['missing_values']['count'] == 1
    assert report['intraday_gaps']['count'] == 1
    # Missing minutes will be large because we only have a few minutes of the trading day
    assert report['missing_minutes']['count'] > 0
