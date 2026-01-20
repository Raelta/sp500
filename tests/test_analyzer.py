import pytest
import pandas as pd
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
