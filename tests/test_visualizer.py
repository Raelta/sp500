import pandas as pd
import plotly.graph_objects as go
from src.visualizer import plot_pattern

def test_plot_pattern_generates_figure():
    # Create small synthetic dataframe
    dates = pd.date_range(start="2023-01-01 09:30:00", periods=20, freq="min")
    df = pd.DataFrame({
        "date": dates,
        "open": [100.0 + i for i in range(20)],
        "high": [101.0 + i for i in range(20)],
        "low": [99.0 + i for i in range(20)],
        "close": [100.5 + i for i in range(20)],
        "volume": [1000] * 20
    })
    
    match_row = pd.Series({
        "date": dates[5],
        "bump_end_date": dates[10],
        "slide_start_date": dates[10],
        "slide_end_date": dates[15]
    })
    match_row.name = 5 # Set index
    
    fig = plot_pattern(df, match_row, padding=2, bump_len=5, slide_len=5, avg_size_vol=500.0)
    
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 2 # Candlestick and Volume bar
