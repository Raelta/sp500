# Project Context: SP500 Bump & Slide Analysis

## 1. Project Overview
This project is a Streamlit application designed to analyze intraday SPY (S&P 500 ETF) data to detect specific technical analysis patterns known as "Bump and Slide". It includes a high-performance data pipeline, vectorized analysis logic, and an interactive visualization dashboard.

## 2. File Structure & Responsibilities

| File | Responsibility |
|------|----------------|
| **`app.py`** | Main Streamlit entry point. Handles UI, sidebar configuration, performance logging, and orchestration of loading/analysis/visualization. |
| **`src/data_loader.py`** | Handles data loading using `st.cache_data`. **Critical**: It bundles data validation inside the cached function to avoid re-running validation on every interaction. |
| **`src/analyzer.py`** | Contains the core `find_bumps_and_slides` function. Uses vectorized pandas operations (rolling windows, shifts) for performance. Accepts a `progress_callback`. |
| **`src/visualizer.py`** | Generates Plotly Candlestick charts. Optimized to calculate date ranges directly from indices rather than searching. |
| **`src/data_validator.py`** | Checks for duplicates, missing values, and intraday gaps. Called exclusively by `data_loader.py` to ensure result caching. |
| **`cli.py`** | Command-line interface for running analysis without the web UI. |

## 3. Key Algorithms

### Pattern Detection (`src/analyzer.py`)
The "Bump & Slide" pattern is defined by:
1.  **Bump Phase**: A price move of magnitude $X$ (percent or value) over time $T_1$.
2.  **Slide Phase**: A subsequent price move of magnitude $Y$ over time $T_2$.
3.  **Volume Filters**: Minimum volume requirements for both phases.
*Implementation*: Uses `df.rolling()` and `df.shift()` to create a "Candidates" DataFrame, then filters by boolean masks.

### Data Loading (`src/data_loader.py`)
*   **Caching Strategy**: Uses `@st.cache_data`.
*   **Optimization**: Validation (`validate_dataset`) is performed *inside* the cached function. This prevents the expensive validation logic from blocking the UI on every interaction (which causes "faded screen" delays).

## 4. Critical Optimizations (DO NOT REVERT)

### A. Selectbox Performance (`app.py`)
**Problem**: Generating formatted labels for thousands of matches using `results.loc[idx]` in a loop is too slow (O(N) dataframe access).
**Solution**:
1.  **Vectorized Labels**: Labels are pre-calculated using pandas string concatenation:
    ```python
    labels = results['date'].astype(str) + " | Bump: " + ...
    ```
2.  **Dictionary Lookup**: These labels are converted to a `dict`. The `format_func` performs an O(1) dictionary lookup.
**Constraint**: Keep this pattern. Do not switch back to row-by-row formatting.

### B. Visualization Loading (`app.py`)
**Problem**: User perceived a delay/fade before the chart appeared.
**Solution**:
1.  **In-Place Placeholder**: Uses `st.empty()` to show a "⏳ Generating visualization..." message *in the exact space* where the chart will load, reducing layout shift.
2.  **Logic Separation**: Data loading and Validation are separated from the Visualization flow via caching so the UI remains responsive.

### C. Deprecated Arguments
**Constraint**: Use `width="stretch"` for `st.dataframe` and `st.plotly_chart`.
*   *Note*: While `use_container_width=True` is standard in newer Streamlit, the specific environment for this project explicitly warns to use `width='stretch'`. **Follow this warning.**

## 5. Performance Monitoring
The app includes a custom `log_perf` utility in `app.py`.
*   Logs are printed to the console (visible in deployment logs).
*   Logs are also shown in a "Debug Profiling" sidebar expander.
*   **Key Metric**: `[PERF] Script Execution Complete`. This timestamp marks when the server finished. Any delay after this is Client-side (Browser rendering).

## 6. Future Work Context
When adding features, ensure:
1.  **Vectorization**: Any new analysis logic must be vectorized.
2.  **Caching**: Any new data processing steps must be cached or placed inside the existing cached loader.
3.  **UI Feedback**: Long-running operations must provide explicit feedback (placeholders or status messages), as the default "faded screen" is too subtle.
