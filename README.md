# SP500 Bump & Slide Analysis

This project provides a comprehensive toolset for analyzing time-series data (S&P 500) to identify "Bump" (trend) and "Slide" (reaction) patterns. It includes data validation, automatic cleaning, and interactive visualization.

## Features

-   **Pattern Detection**: Identifies "Bumps" (Start -> End trend) and subsequent "Slides" based on configurable lengths and thresholds.
-   **Flexible Thresholds**: Supports both Percentage-based and Value-based (price change) thresholds.
-   **Data Quality Checks**: Automatically detects duplicate timestamps, missing values, and intraday gaps on load.
-   **Auto-Cleaning**: Automatically removes duplicate rows to ensure analysis integrity.
-   **Interactive Dashboard**: Streamlit-based UI for exploring matches with candlestick charts.
-   **CLI Support**: Command-line interface for headless execution and integration.

## Installation

1.  **Clone the repository**.
2.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Streamlit Dashboard

Launch the interactive web application:

```bash
streamlit run app.py
```

-   **Sidebar**: Configure Bump/Slide lengths, thresholds, and filters.
-   **Run Analysis**: Click the button to execute the scan.
-   **Visualize**: Select a match from the results table to view its detailed chart.

### Command Line Interface (CLI)

Run the analysis directly from the terminal:

```bash
python cli.py --bump-len 5 --bump-thresh 0.05 --slide-len 3
```

**Arguments:**
-   `--bump-len`, `--slide-len`: Length in minutes (default: 5, 3).
-   `--bump-thresh`, `--slide-thresh`: Threshold value (default: 0.05).
-   `--bump-type`, `--slide-type`: `percent` or `value` (default: percent).
-   `--min-bump-vol`, `--min-slide-vol`: Minimum volume filters.
-   `--start-time`, `--end-time`: Time of day filter (HH:MM).
-   `--days`: Days of week filter.

## Technical Choices

-   **Data Storage**: Parquet format is used for efficient storage and fast I/O of the 13-year minute-level dataset.
-   **Vectorization**: `pandas` vectorization is used for pattern detection to handle millions of rows efficiently without slow loops.
-   **Caching**: `streamlit.cache_data` ensures the data load happens only once, making UI interactions snappy.
-   **Testing**: `pytest` and `AppTest` ensure the application logic and UI flows function correctly.

## Project Structure

-   `app.py`: Streamlit entry point.
-   `cli.py`: CLI entry point.
-   `src/`: Core logic modules.
    -   `data_loader.py`: Data ingestion.
    -   `data_validator.py`: Quality checks.
    -   `analyzer.py`: Pattern detection algorithm.
    -   `visualizer.py`: Plotly chart generation.
-   `tests/`: Test suite.
