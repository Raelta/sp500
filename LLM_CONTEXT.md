# Project Context: SP500 Bump & Slide Analysis

## 1. Project Overview
This project is a high-performance analysis tool for detecting "Bump and Slide" technical patterns in intraday SPY (S&P 500 ETF) data. It consists of a **Streamlit Dashboard** for interactive exploration and a **Command-Line Interface (CLI)** for exhaustive parameter optimization (Goal Seek).

## 2. File Structure & Responsibilities

| File | Responsibility |
|------|----------------|
| **`app.py`** | Main Streamlit dashboard. Handles "Standard Analysis" mode, visualization, and interactivity. |
| **`goal_seek_cli.py`** | CLI tool for "Goal Seek" (Reverse Search). Finds parameters achieving a target Conversion Rate. Uses parallel processing. |
| **`src/search_engine.py`** | **Core Optimization Engine**. Used by CLI. Implements Multiprocessing, Data-Driven Pruning, and Vectorized Broadcasting. |
| **`src/analyzer.py`** | Core pattern detection logic. Calculates **Size Volume** (Vol × PriceChange) and rolling metrics. |
| **`src/data_loader.py`** | Handles data loading/caching. Calculates **Yearly Median** metrics for reference lines. |
| **`src/visualizer.py`** | Generates Plotly charts. **Key Feature**: Uses `category` axis to remove time gaps (overnight/weekend) and marks session breaks with vertical lines. |
| **`src/data_validator.py`** | Checks for duplicates, gaps, and missing minutes. |
| **`src/news_provider.py`** | Generates Google News search links. |

## 3. Key Algorithms

### Pattern Detection (`src/analyzer.py`)
*   **Metric**: Uses **Size Volume** (`Volume * abs(Close - Open)`) instead of raw volume for filtering.
*   **Logic**: Uses vectorized rolling window operations to identify candidates.

### High-Performance Search (`src/search_engine.py`)
Designed for exhaustive grid search over parameter space using standard rolling windows.
1.  **Parallel Processing**: Distributes structural combinations (Length pairs) across CPU cores using `ProcessPoolExecutor`.
2.  **Data-Driven Pruning**: Calculates max possible values in data subset to instantly discard impossible parameter thresholds ("Fail Fast").
3.  **Vectorized Broadcasting**: Uses NumPy matrix multiplication to check thousands of threshold combinations simultaneously, eliminating the inner loop.
4.  **Overlap Filtering**: Applies **Non-Maximum Suppression (NMS)** to filter out overlapping matches. Keeps the match with the highest slide magnitude.

## 4. Architectural Decisions

### A. UI vs. CLI Separation
*   **UI (`app.py`)**: Focused on **Standard Analysis** (visualizing known parameters). Goal Seek functionality was moved to CLI for better performance handling and focused workflow.
*   **CLI (`goal_seek_cli.py`)**: Focused on **Optimization**. Runs on the full dataset (ignoring filters) to find global optima.

### B. Visualization
*   **Gap Removal**: The X-axis uses `type='category'` to eliminate non-trading hours (blank spaces).
*   **Session Indicators**: Dotted vertical lines mark where time gaps >30 mins occur (e.g., new trading day).
*   **Reference Lines**: Uses **Median** (robust to outliers) instead of Mean for yearly averages.

### C. Data Consistency
*   Both UI and CLI enforce **Duplicate Removal** on load to ensure row counts match (~2M rows for full history).
*   CLI results include `scope_metadata` columns to verify the exact data range processed.

## 5. Performance Monitoring
*   `log_perf` utility tracks execution time of key phases.
*   CLI logs progress per "Structural" step.

## 6. Future Work Context
*   **Search Engine**: Is heavily optimized. Further gains would require `numba` JIT or porting to `polars`.
*   **Data**: Currently uses Parquet. 
*   **Tests**: `tests/test_consistency.py` verifies that App and CLI data loading logic remains synchronized.
