# SP500 Bump & Slide Analysis

A Python application designed to analyze intraday SPY (S&P 500 ETF) data for "Bump and Slide" price patterns. This tool provides both an interactive Streamlit dashboard for visual analysis and a Command Line Interface (CLI) for automated or quick scans.

## Features

- **Pattern Detection**: Automatically identifies "Bump" (initial trend) and "Slide" (subsequent reaction) patterns based on user-defined criteria.
- **Dual Interfaces**: 
  - **Web Dashboard**: Interactive Streamlit app with Plotly visualizations.
  - **CLI**: Command-line tool for scriptable analysis and text-based reporting.
- **Flexible Configuration**:
  - Define thresholds by Percentage (%) or Absolute Value ($).
  - Set custom durations for Bump and Slide phases.
  - Filter by Volume, Time of Day, and Days of the Week.
- **Data Quality**: Built-in validation checks for duplicates, missing values, and intraday data gaps.

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd sp500
   ```

2. **Install dependencies:**
   It is recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Streamlit Dashboard (Web App)

The dashboard offers the best experience for exploring data and visualizing patterns.

```bash
streamlit run app.py
```
*   Opens in your default web browser.
*   Use the sidebar to adjust parameters (thresholds, lengths, filters) and click "Run Analysis".
*   Select a match from the results to view the interactive chart.

### Command Line Interface (CLI)

Use the CLI for quick checks or batch processing.

**Basic Run (Default Settings):**
```bash
python cli.py
```

**Custom Configuration:**
```bash
python cli.py --bump-len 10 --bump-thresh 0.1 --slide-len 5 --slide-thresh 0.05
```

**Full Help:**
```bash
python cli.py --help
```

**Common Arguments:**
- `--bump-len`: Length of Bump phase in minutes (default: 5)
- `--bump-thresh`: Threshold for Bump phase (default: 0.05)
- `--slide-len`: Length of Slide phase in minutes (default: 3)
- `--slide-thresh`: Threshold for Slide phase (default: 0.05)
- `--bump-type`, `--slide-type`: Threshold type (`percent` or `value`)
- `--start-time`, `--end-time`: Filter analysis by time of day (e.g., "09:30")

## Project Structure

```
├── app.py                  # Main Streamlit application entry point
├── cli.py                  # Command Line Interface entry point
├── requirements.txt        # Python dependencies
├── spy_data.parquet        # Default dataset (SPY Intraday Data)
├── src/
│   ├── analyzer.py         # Core logic for pattern detection
│   ├── data_loader.py      # Data loading (cached & uncached)
│   ├── data_validator.py   # Data quality checks (gaps, duplicates)
│   └── visualizer.py       # Plotly visualization logic
└── tests/
    └── test_app.py         # App integration tests
```

## Testing

The project includes tests using `pytest` and `streamlit.testing`.

Run tests with:
```bash
pytest
```
