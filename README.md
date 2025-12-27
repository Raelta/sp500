# SP500 Bump & Slide Analysis

A Python application designed to analyze intraday SPY (S&P 500 ETF) data for "Bump and Slide" price patterns. This tool provides both an interactive Streamlit dashboard for visual analysis and a Command Line Interface (CLI) for automated or quick scans.

## Features

- **Pattern Detection**: Automatically identifies "Bump" (initial trend) and "Slide" (subsequent reaction) patterns based on user-defined criteria.
- **Interactive Dashboard**: Powerful Streamlit app with reactive analysis and Plotly visualizations.
- **Smart Filtering**: 
  - Excel-style "Select All" filters for Years and Days of the Week.
  - Filter by Volume, Time of Day, and Days.
- **Interactive UI**:
  - **Table-Driven Navigation**: Click any row in the matches table to instantly view the chart.
  - **Configurable Layout**: Toggle between Table-Top or Chart-Top views.
  - **News Integration**: Contextual Google News search links for every match.
- **Data Quality**: Advanced validation checks for duplicates, gaps, and missing minutes (with downloadable reports).

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

### Web Dashboard

The dashboard offers the best experience for exploring data and visualizing patterns.

```bash
streamlit run app.py
```

*   **Filters**: Use the sidebar to set Year/Day filters and Adjust parameters.
*   **Analysis**: The app updates reactively.
*   **Selection**: Click any row in the **Matches Table** to view the visualization. Click column headers to sort.
*   **Layout**: Use the "App Layout" toggle to customize your workspace.

#### Command Line Overrides

You can launch the app with custom parameter defaults using command-line arguments. Append your flags after a `--` separator.

**Example:**
```bash
# Set Bump Length to 10 minutes and Threshold to 0.1%
streamlit run app.py -- --bump-len 10 --bump-thresh 0.1
```

**Supported Flags:**
- `-bl`, `--bump-len`: Bump Length (min)
- `-bt`, `--bump-thresh`: Bump Threshold
- `--bump-type`: 'percent' or 'value'
- `-sl`, `--slide-len`: Slide Length (min)
- `-st`, `--slide-thresh`: Slide Threshold
- `--slide-type`: 'percent' or 'value'
- `--min-bump-vol`: Min Bump Volume
- `--min-slide-vol`: Min Slide Volume

## Project Structure

```
├── app.py                  # Main Streamlit application entry point
├── requirements.txt        # Python dependencies
├── spy_data.parquet        # Default dataset (SPY Intraday Data)
├── src/
│   ├── analyzer.py         # Core logic for pattern detection
│   ├── data_loader.py      # Data loading (cached & uncached)
│   ├── data_validator.py   # Data quality checks (gaps, missing minutes)
│   ├── news_provider.py    # Google News search integration
│   ├── ui_utils.py         # Custom UI components (Excel-style filters)
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
