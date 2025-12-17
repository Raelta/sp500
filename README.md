# SP500 Bump & Slide Analysis

A Python application designed to analyze intraday SPY (S&P 500 ETF) data for "Bump and Slide" price patterns. This tool provides both an interactive Streamlit dashboard for visual analysis and a Command Line Interface (CLI) for automated or quick scans.

## Features

- **Pattern Detection**: Automatically identifies "Bump" (initial trend) and "Slide" (subsequent reaction) patterns based on user-defined criteria.
- **Dual Interfaces**: 
  - **Web Dashboard**: Interactive Streamlit app with Plotly visualizations.
  - **CLI**: Command-line tool for scriptable analysis and text-based reporting.
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

### Streamlit Dashboard (Web App)

The dashboard offers the best experience for exploring data and visualizing patterns.

```bash
streamlit run app.py
```
*   **Filters**: Use the sidebar to set Year/Day filters and Adjust parameters.
*   **Analysis**: The app updates reactively.
*   **Selection**: Click any row in the **Matches Table** to view the visualization. Click column headers to sort.
*   **Layout**: Use the "App Layout" toggle to customize your workspace.

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

## Project Structure

```
├── app.py                  # Main Streamlit application entry point
├── cli.py                  # Command Line Interface entry point
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
