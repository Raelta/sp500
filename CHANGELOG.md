# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Metric Upgrade**: Introduced "True Hits" (best unique matches) and "Total Hits" (all overlapping matches) metrics.
- **Data Gap Detection**: New `data_gap` column identifies matches with time discontinuities (e.g., missing minutes, day boundaries).
- **Goal Seek CLI**: Updated output to sort by Total Hits and include `best_hit_date` and hit counts.
- **Window Catalog**: Implemented a "Hybrid Catalog" system for ultra-fast Goal Seek performance.
  - **Pre-parsed Data**: Stores pre-computed Price Change matrices (Memory-Mapped) and Cumulative Volume/Up-Count arrays.
  - **Parallel Search**: Added `CatalogSearcher` which uses multi-threaded vector operations to search millions of combinations in seconds.
  - **CLI Commands**: Added `--build-catalog` to generate data and `--use-catalog` to search using the optimized engine.
- **Goal Seek**: Added `--min-bumps` argument to filter results by a minimum number of pattern occurrences.

### Changed
- **Conversion Rate Eliminated**: Removed conversion rate filtering and metrics to provide a more complete view of pattern occurrences. The `--target-cr` argument is deprecated/removed.
- **Goal Seek Filtering**: Implemented **Non-Maximum Suppression (NMS)** logic to differentiate between "Total Hits" (raw overlaps) and "True Hits" (filtered bests).
- **CLI Arguments**: Simplified threshold parameters. Replaced range-based arguments (`--bump-thresh-start/end/step`) with single minimum threshold arguments (`--min-bump-threshold`, `--min-slide-threshold`). The search now treats these as fixed minimum requirements rather than optimization variables.

## [0.2.0] - 2026-01-20

### Added
- **Goal Seek / Reverse Search**: New analysis mode to find parameter combinations that achieve a target Conversion Rate.
  - **Smart Search Engine**: Optimized algorithm that groups structural parameters to maximize search performance (`src/search_engine.py`).
  - **Variable Parameter Search**: UI to "Lock" specific parameters while varying others across a defined range.
  - **Compact Layout**: Optimized 2-column interface to minimize scrolling during configuration.
  - **Performance Optimization**: 
    - **Data-Driven Pruning**: Instantly discards impossible parameter combinations based on data limits.
    - **Parallel Processing**: Uses multi-core processing to execute search tasks concurrently.
    - **Vectorized Broadcasting**: Replaced the inner search loop with NumPy matrix operations, enabling near-instant checking of thousands of threshold combinations.
  - **Metrics**: Updated "Volume" parameter to "Size Volume" (Price Change * Volume) and switched Yearly Stats from Mean to Median.
  - **Visualization**: Enhanced charts to remove time gaps (using Category Axis) and indicate session breaks with vertical lines.

### Changed
- **UI Cleanup**: Removed "Goal Seek" mode from the web interface to focus on Standard Analysis. Goal Seek functionality is now exclusive to the CLI (`goal_seek_cli.py`).

## [0.1.0] - 2025-12-27

### Added
- **Core Analysis**: Algorithm to detect "Bump and Slide" patterns based on configurable lengths and thresholds.
- **Streamlit Dashboard**: Interactive web interface (`app.py`) for data exploration.
- **Data Loading**: Optimized Parquet loader with Streamlit caching (`src/data_loader.py`).
- **Data Quality**: Automated checks for duplicates, missing values, and intraday gaps (`src/data_validator.py`).
- **Visualization**: 
  - Interactive Candlestick charts using Plotly (`src/visualizer.py`).
  - "Wickless" candles for cleaner price visualization.
  - Separate Volume subplot with mono-color bars.
  - Visual highlighting of Bump and Slide windows with 1-minute visual extension for accuracy.
- **Filtering**:
  - Year and Day-of-Week filters with "Select All" capability.
  - Time-of-Day filtering (e.g., 9:30-16:00).
  - Volume thresholds for Bump and Slide phases.
- **Statistics**:
  - Real-time "Hit Rate" calculation (Total Bumps vs Valid Hits).
  - Conversion rate metrics displayed in the UI.
- **CLI Overrides**: Ability to override default UI parameters via command-line arguments (e.g., `streamlit run app.py -- -bl 10`).
- **News Integration**: Contextual Google News search links for pattern dates.
- **Versioning**: Sidebar display of the current Git commit hash, build count, and date.

### Changed
- **Visuals**: Moved "Bump/Slide" text annotations to the Price chart only to prevent overlap with Volume bars.
- **Logic**: Adjusted Slide window calculation to strictly follow the Bump window (no overlap).
- **UI**: Replaced "News Topic" dropdown with a free-text input field.
- **Defaults**: Minimum Slide Length reduced to 1 minute.

### Removed
- **Legacy CLI**: Removed standalone `cli.py` script in favor of `app.py` with CLI arguments.
