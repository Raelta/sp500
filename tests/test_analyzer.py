import pytest
import pandas as pd
import datetime
from src.analyzer import find_bumps_and_slides
from src.test_utils.data_generator import MarketDataGenerator

@pytest.fixture
def generator():
    return MarketDataGenerator(seed=42)

def test_exact_match(generator):
    # Generate 5 days of data
    df = generator.generate_noise(days=5, volatility=0.0001)
    
    # Inject pattern at index 100
    # Bump 5%, Slide 5%
    df = generator.inject_pattern(df, index=100, bump_len=10, slide_len=10, bump_pct=0.05, slide_pct=-0.05)
    
    # Run analyzer
    # Thresholds lower than injected pattern (4.0 = 4%)
    results, stats = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=4.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent",
        min_bump_vol=0, min_slide_vol=0
    )
    
    assert not results.empty
    # The result index corresponds to the start of the bump
    # Check if we have a match at the injected time
    injected_time = df.iloc[100]['date']
    matches = results[results['date'] == injected_time]
    assert len(matches) == 1
    assert stats['hits'] >= 1

def test_threshold_sensitivity(generator):
    df = generator.generate_noise(days=5, volatility=0.0001)
    
    # Inject 5% bump
    df = generator.inject_pattern(df, index=100, bump_len=10, slide_len=10, bump_pct=0.05, slide_pct=-0.05)
    
    # Case 1: Threshold 4% (Should find it)
    results_found, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=4.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent"
    )
    injected_time = df.iloc[100]['date']
    assert not results_found[results_found['date'] == injected_time].empty

    # Case 2: Threshold 6% (Should miss it)
    results_missed, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=6.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent"
    )
    assert results_missed[results_missed['date'] == injected_time].empty

def test_day_of_week_filter(generator):
    # Start on a known Monday
    start_date = "2023-01-02" # Jan 2 2023 is Monday
    df = generator.generate_noise(start_date=start_date, days=7)
    
    # Inject on index 0 (which is Monday morning)
    df = generator.inject_pattern(df, index=0, bump_len=10, slide_len=10, bump_pct=0.05, slide_pct=-0.05)
    
    # Test Filter: Monday
    results_mon, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=4.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent",
        days_of_week=['Monday']
    )
    assert not results_mon.empty
    
    # Test Filter: Tuesday
    results_tue, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=4.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent",
        days_of_week=['Tuesday']
    )
    assert results_tue.empty

def test_length_parameters(generator):
    df = generator.generate_noise(days=5)
    
    # Inject with bump_len=20
    df = generator.inject_pattern(df, index=100, bump_len=20, slide_len=10, bump_pct=0.05, slide_pct=-0.05)
    
    # Search with bump_len=20
    results_20, _ = find_bumps_and_slides(
        df,
        bump_len=20, bump_threshold=4.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent"
    )
    injected_time = df.iloc[100]['date']
    assert not results_20[results_20['date'] == injected_time].empty
    
    # Search with bump_len=10
    # Over 10 mins, the 20-min 5% bump is only ~2.5%. Threshold is 4%. Should miss.
    results_10, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=4.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent"
    )
    
    # Logic check:
    # If we inject a linear 5% rise over 20 mins.
    # Over first 10 mins, it rises 2.5%.
    # Threshold is 4%. So it should FAIL the 10 min check.
    
    assert results_10[results_10['date'] == injected_time].empty

def test_true_hits_suppression(generator):
    # Create a scenario where two patterns overlap.
    # Pattern 1: Starts at index 100, Score (Slide Change) = 5%
    # Pattern 2: Starts at index 102, Score (Slide Change) = 10% (Better)
    # The greedy suppression should keep Pattern 2 and remove Pattern 1 (if they overlap significantly).
    
    df = generator.generate_noise(days=2)
    
    # Inject smaller pattern
    df = generator.inject_pattern(df, index=100, bump_len=10, slide_len=10, bump_pct=0.05, slide_pct=-0.05)
    
    # Inject larger pattern slightly later (overlapping)
    # index 102 overlaps with 100-120 range
    df = generator.inject_pattern(df, index=102, bump_len=10, slide_len=10, bump_pct=0.10, slide_pct=-0.10)
    
    results, stats = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=4.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent"
    )
    
    # We expect both to be "hits" initially, but "true_hits" should filter.
    assert stats['total_hits'] >= 2
    # Window len = 20. Start 100 vs 102. Overlap is large.
    # So true_hits should be 1.
    assert stats['true_hits'] == 1

def test_volume_filtering(generator):
    df = generator.generate_noise(days=2)
    # Inject pattern with low volume
    df = generator.inject_pattern(df, index=100, bump_len=10, slide_len=10, bump_pct=0.05, slide_pct=-0.05)
    # Set volume to 0 for this period
    df.loc[100:120, 'volume'] = 0
    
    # Search with min_bump_vol > 0
    results, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=4.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent",
        min_bump_vol=1000, min_slide_vol=1000
    )
    injected_time = df.iloc[100]['date']
    assert results[results['date'] == injected_time].empty

def test_up_pct_filtering(generator):
    df = generator.generate_noise(days=2)
    
    # Manually craft a perfect bump
    start_idx = 100
    length = 10
    base_price = 100.0
    for i in range(length):
        df.at[start_idx+i, 'open'] = base_price + i
        df.at[start_idx+i, 'close'] = base_price + i + 0.9 # Always UP
    
    # Run with bump_up_pct = 100 (requires 100% up candles)
    results, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=0.1, bump_thresh_type="percent",
        slide_len=10, slide_threshold=0.0, slide_thresh_type="percent",
        bump_up_pct=100.0
    )
    
    injected_time = df.iloc[start_idx]['date']
    match = results[results['date'] == injected_time]
    assert not match.empty
    
    # Now try with a stricter requirement that fails (e.g., require 100% but we make one candle down)
    df.at[start_idx+1, 'close'] = df.at[start_idx+1, 'open'] - 0.1 # Down candle
    
    results_fail, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=0.1, bump_thresh_type="percent",
        slide_len=10, slide_threshold=0.0, slide_thresh_type="percent",
        bump_up_pct=100.0
    )
    assert results_fail[results_fail['date'] == injected_time].empty

def test_value_threshold(generator):
    df = generator.generate_noise(days=2)
    
    # Inject 5% bump at price ~100. Change ~5.0.
    df = generator.inject_pattern(df, index=100, bump_len=10, slide_len=10, bump_pct=0.05, slide_pct=-0.05)
    
    # Search with value threshold = 4.0. Should pass.
    results, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=4.0, bump_thresh_type="value",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="value"
    )
    injected_time = df.iloc[100]['date']
    assert not results[results['date'] == injected_time].empty
    
    # Search with value threshold = 6.0. Should fail.
    results_fail, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=6.0, bump_thresh_type="value",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="value"
    )
    assert results_fail[results_fail['date'] == injected_time].empty

def test_time_range_filter(generator):
    # Inject pattern at 10:00 AM
    df = generator.generate_noise(days=1, start_time="09:30")
    
    # 09:30 -> index 0. 10:00 -> index 30.
    df = generator.inject_pattern(df, index=30, bump_len=10, slide_len=10, bump_pct=0.05, slide_pct=-0.05)
    injected_time = df.iloc[30]['date'] 
    
    # Filter 1: 09:00 to 11:00. Should find.
    t_start = datetime.time(9, 0)
    t_end = datetime.time(11, 0)
    
    results, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=4.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent",
        time_range=(t_start, t_end)
    )
    assert not results[results['date'] == injected_time].empty
    
    # Filter 2: 12:00 to 14:00. Should miss.
    t_start_late = datetime.time(12, 0)
    t_end_late = datetime.time(14, 0)
    
    results_fail, _ = find_bumps_and_slides(
        df,
        bump_len=10, bump_threshold=4.0, bump_thresh_type="percent",
        slide_len=10, slide_threshold=4.0, slide_thresh_type="percent",
        time_range=(t_start_late, t_end_late)
    )
    assert results_fail[results_fail['date'] == injected_time].empty
