# SP500 Bump & Slide Analysis

A Python application designed to analyze intraday SPY (S&P 500 ETF) data for "Bump and Slide" price patterns. This tool provides an interactive Streamlit dashboard for visual analysis with powerful filtering and configuration options.

## Features

- **Pattern Detection**: 
  - Automatically identifies "Bump" (initial trend) and "Slide" (subsequent reaction) patterns.
  - Detects patterns based on configurable lengths (minutes), thresholds (price/%), and volume.
- **Goal Seek / Reverse Search**:
  - Define a target Conversion Rate and find parameter combinations that achieve it.
  - "Lock" specific parameters while varying others across a range.
  - **High Performance**:
    - **Parallel Processing**: Utilizes all available CPU cores to execute the search concurrently.
    - **Vectorized Broadcasting**: Uses NumPy matrix multiplication to check thousands of parameter combinations simultaneously, eliminating slow loops.
    - **Smart Pruning**: Automatically discards impossible parameter combinations based on data limits.
  - **Window Catalog (Optimized Search)**:
    - Pre-compute window metrics to disk for instant lookups.
    - **Hybrid Storage**: Uses a memory-mapped matrix for Price Change (2GB) and cumulative sums for Volume/Up Ratio (50MB) to balance speed and storage.
    - **Parallel Search**: Uses `ThreadPoolExecutor` to perform vectorized searches across multiple CPU cores, achieving >900 parameter combinations per second.
- **Interactive Dashboard**: 
  - Powerful Streamlit app with reactive analysis.
  - Interactive Plotly visualizations with zoom, pan, and hover details.
- **Advanced Visualization**:
  - **Wickless Candles**: Cleaner price charts that emphasize Open/Close bodies.
  - **Volume Subplot**: Dedicated volume chart synchronized with price action.
  - **Pattern Highlighting**: Visual rectangles indicating exactly where Bump and Slide windows occur.
- **Smart Filtering**: 
  - Excel-style "Select All" filters for Years and Days of the Week.
  - Filter by Volume, Time of Day, and Days.
- **Statistics**:
  - Real-time "Hit Rate" calculation showing how many bumps convert to valid slides.
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
- `--min-bump-vol`: Min Bump Size Vol
- `--min-slide-vol`: Min Slide Size Vol

### Goal Seek CLI

You can also run the Goal Seek analysis directly from the terminal without the web interface.

```bash
python goal_seek_cli.py --min-bumps 10 --top-n 10
```

**Common Arguments:**
- `--min-bumps`: Minimum Total Bumps required (default 0)
- `--top-n`: Number of top results to display (default 20)
- `--output`: Output CSV filename (default `goal_seek_results.csv`)
- **Ranges**: Define ranges for parameters using `--[name]-start`, `--[name]-end`, `--[name]-step`.
  - Example: `--bump-len-start 3 --bump-len-end 5 --bump-len-step 1`

#### Default Ranges (if unspecified)
If you run the CLI without specific parameter arguments, it defaults to:
*   **Bump/Slide Length**: 3 to 6 (Step 1)
*   **Bump/Slide Threshold**: 3.0 to 10.0 (Step 0.5)
*   **Size Vol**: Locked at 0
*   **Up %**: Locked at 0

#### Optimized Catalog Search
For exhaustive searches (e.g., checking thousands of window size combinations), you should use the pre-computed Window Catalog.

1. **Build the Catalog** (Run once):
   ```bash
   python goal_seek_cli.py --build-catalog --catalog-max-len 360
   ```
   *   Generates `catalog/change_matrix.npy` (~2GB) and `catalog/metadata.npz` (~50MB).
   *   `--catalog-max-len` sets the maximum window size in minutes (default 360).

2. **Run Fast Search**:
   The CLI automatically detects and uses the catalog if it exists.
   ```bash
   python goal_seek_cli.py --bump-len-start 15 --bump-len-end 60
   ```
   *   Uses the pre-computed data for instant lookups.
   *   Supports multi-threaded execution automatically.

#### Understanding Progress Logs
During execution, you will see logs like:
`[33.3%] Analyzing structure 8/24...`

*   **Structure**: Refers to a unique combination of **Bump Length** and **Slide Length**. These are the "heavy" parameters that require re-scanning the dataset.
*   **Optimization**: Inside each "Structure", the engine tests hundreds of Threshold/Volume combinations almost instantly using vectorized operations and Data-Driven Pruning.

## Project Structure

```
.
├── app.py                  # Main Streamlit application entry point
├── debug_app.py            # Visual verification tool using synthetic data
├── CHANGELOG.md            # History of changes and versions
├── README.md               # Documentation
├── requirements.txt        # Python dependencies
├── spy_data.parquet        # Default dataset (SPY Intraday Data)
├── TEST_STRATEGY.md        # Detailed QA strategy document
└── src/
    ├── analyzer.py         # Core logic for pattern detection and stats
    ├── config.py           # CLI argument parsing and configuration
    ├── data_loader.py      # Data loading (cached & uncached)
    ├── data_validator.py   # Data quality checks (gaps, missing minutes)
    ├── news_provider.py    # Google News search integration
    ├── search_engine.py    # Optimized search logic for Goal Seek
    ├── visualizer.py       # Plotly visualization logic (Charts)
    ├── test_utils/         # Test utilities
    │   └── data_generator.py # Synthetic data generation logic
    └── ui/                 # UI Component Package
        ├── __init__.py
        ├── results.py      # Logic for displaying tables, charts, and stats
        ├── sidebar.py      # Logic for rendering the configuration sidebar
        └── utils.py        # Shared UI utilities and helpers
```

## Quality Assurance & Testing

We employ a robust testing strategy using Synthetic Data to verify logic independent of data quality.

### Running Tests
To run Unit and Property-based tests:
```bash
python -m pytest
```

### Visual Debug Mode
To verify the analyzer logic against controlled synthetic data:
```bash
streamlit run debug_app.py
```
This mode allows you to:
- Generate random market noise.
- Inject specific "Perfect Patterns" at known indices.
- Verify if the analyzer detects them correctly.

See [TEST_STRATEGY.md](TEST_STRATEGY.md) for full details.
