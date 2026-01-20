# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.2.0] - 2026-01-20

### Added
- **Goal Seek / Reverse Search**: New analysis mode to find parameter combinations that achieve a target Conversion Rate.
  - **Smart Search Engine**: Optimized algorithm that groups structural parameters to maximize search performance (`src/search_engine.py`).
  - **Variable Parameter Search**: UI to "Lock" specific parameters while varying others across a defined range.
  - **Compact Layout**: Optimized 2-column interface to minimize scrolling during configuration.
  - **Mode Selection**: Switch between "Standard Analysis" and "Goal Seek" modes via the sidebar.

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
