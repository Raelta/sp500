# SP500 Bump & Slide Analysis - Implementation Specification

This document exhaustively describes the aims, features, and design decisions of the SP500 Bump & Slide Analysis application. It serves as a blueprint capable of being used to reconstruct the system from scratch.

---

## 1. Project Aims and Objectives

The primary goal of the project is to provide a high-performance quantitative analysis tool for detecting and evaluating a specific intraday trading pattern, termed "Bump and Slide," in the S&P 500 ETF (SPY). 

*   **Bump:** An initial price movement (trend) over a specific timeframe.
*   **Slide:** The subsequent reaction (reversal or continuation) immediately following the Bump.

The application serves two main purposes:
1.  **Exploration (Standard Analysis):** Provide a rich, interactive visual dashboard for a user to input specific pattern parameters and visually inspect historical occurrences on a price chart.
2.  **Optimization (Goal Seek / Reverse Search):** Provide an exhaustive, high-performance search engine to automatically test millions of parameter combinations and find the parameters that yield the highest occurrence of the pattern or the best performance.
3.  **Scalability:** Allow heavy, exhaustive searches to be offloaded to Google Cloud for parallel execution, while maintaining a seamless user experience in the web UI.

---

## 2. Core Features

### 2.1. Pattern Detection
The core logic identifies patterns based on several configurable rules:
*   **Lengths (`bump_len`, `slide_len`):** The duration of each phase in minutes.
*   **Thresholds (`bump_threshold`, `slide_threshold`):** The minimum price movement required (can be evaluated as a `%` change or absolute `value` change). Directionality is determined by the sign of the threshold (positive for uptrend, negative for downtrend).
*   **Size Volume (`min_bump_vol`, `min_slide_vol`):** A custom metric defined as `Volume * abs(Close - Open)`. This filters out high-volume doji candles where price didn't actually move.
*   **Candle Consistency (`bump_up_pct`, `slide_up_pct`):** The percentage of individual 1-minute candles within the window that must close higher than they opened (Up candles).
*   **Time & Day Filtering:** Ability to restrict pattern detection to specific times of day or days of the week.

### 2.2. Interactive Streamlit Dashboard (`app.py`)
*   **Exploration Mode:** Form inputs for all pattern parameters. Displays results on an interactive Plotly candlestick chart.
*   **Smart Visualization:** The chart removes non-trading hours (overnights/weekends) by using a categorical X-axis, and plots vertical dotted lines to demarcate session breaks.
*   **Data Quality Reporting:** Displays an expandable warning if the underlying data has duplicates, missing minutes, or intraday gaps.

### 2.3. Goal Seek Engine
*   **Exhaustive Grid Search:** Tests all combinations of specified parameter ranges.
*   **Local & Cloud Execution:** Users can run smaller searches locally on their machine's CPU cores, or trigger a massive search on Google Cloud directly from the UI.
*   **Cloud Run Viewer:** A historical table of previous cloud executions stored in Google Cloud Storage (GCS), filterable by user tags, allowing instant loading of previous heavy computational results.
*   **Auto-Monitoring:** Real-time log scraping to display a live progress bar and status for active Cloud Run jobs.

### 2.4. Authentication & Security
*   Simple password protection (`check_password()`) using cookies for persistent sessions. Passwords are securely hashed and stored in `.streamlit/secrets.toml`.

---

## 3. System Architecture and Design Decisions

### 3.1. Data Management
*   **Format:** Intraday data (~2 million rows for 25 years) is stored in Parquet format (`spy_data_25yr.parquet`) for fast I/O and low memory footprint.
*   **Loading & Caching (`data_loader.py`):** Uses Streamlit's `@st.cache_data` to load the dataset once into memory. During load, it pre-calculates **Yearly Medians** for various metrics to be used as robust reference lines in the UI.
*   **Validation (`data_validator.py`):** Ensures data integrity by scanning for missing values, exact duplicate timestamps, and anomalous intraday gaps. Duplicates are automatically dropped.

### 3.2. Pattern Detection Engine (`analyzer.py`)
**Design Decision: Vectorization over Iteration.**
Instead of looping through rows, the analyzer utilizes Pandas vectorized rolling window operations.
1.  **Metric Pre-calculation:** `Size Volume` and `Candle Consistency` are calculated as rolling sums/means across the entire dataframe.
2.  **Alignment Shift:** Because Pandas `rolling()` anchors to the right edge of the window, `shift()` is heavily used to align Bump metrics with Slide metrics such that `index [i]` represents a pattern *starting* at time `i`.
3.  **True Hits vs. Total Hits (Non-Maximum Suppression):** A pattern might trigger on minute 10, 11, and 12 for the same broader market move. `_calculate_true_hits` implements a greedy Non-Maximum Suppression (NMS) algorithm: it sorts all overlapping matches by the absolute magnitude of their Slide change and keeps only the most extreme, discarding the overlapping lesser matches.

### 3.3. High-Performance Search Engine (`search_engine.py`)
The Goal Seek engine is the most computationally complex component. To perform an exhaustive search in seconds/minutes, it employs three distinct architectural optimizations:

#### A. Process Pool Parallelism (Structural Grouping)
Parameters are split into two categories:
*   **Structural Parameters:** (`bump_len`, `slide_len`, threshold types). Changing these requires recalculating the rolling windows over the entire dataframe.
*   **Filter Parameters:** (Thresholds, Volumes, Up %). Changing these only requires applying different boolean masks to the already calculated rolling data.
The `ProcessPoolExecutor` distributes unique combinations of *Structural Parameters* across available CPU cores.

#### B. Data-Driven Pruning ("Fail Fast")
Before generating millions of filter combinations, the worker process calculates the absolute `min` and `max` values present in the current rolling dataset. It compares the requested parameter grid against these bounds. If a user asks to test a 5% bump threshold, but the dataset's maximum bump is only 3%, that threshold (and all combinations involving it) is instantly dropped from the search space.

#### C. Vectorized Broadcasting (Matrix Multiplication)
Instead of a nested `for` loop to check remaining threshold combinations:
1.  **Mask Generation:** It creates a dictionary of boolean arrays for every valid threshold value (e.g., `mask_cache['bump_threshold'][2.0] = [True, False, True...]`).
2.  **Matrix Building:** It stacks these 1D arrays to build a dense boolean matrix for all Bump combinations (`N_rows` x `B_combos`) and Slide combinations (`N_rows` x `S_combos`).
3.  **Dot Product Check:** It uses NumPy matrix multiplication (`np.dot(bump_matrix.T, slide_matrix)`) to instantly calculate the total occurrences (Hits) for every pair of Bump and Slide configurations simultaneously.

### 3.4. Cloud Architecture (`cloud_runner.py` & `cloud_job.py`)
To prevent the Streamlit server from hanging on massive jobs, the app offloads work to Google Cloud Run Jobs.
*   **Execution Overrides:** The base Cloud Run Job acts as an idle template. When a user triggers a search, the Streamlit app uses the GCP `run_v2` Client to trigger an *Execution*, passing the specific Goal Seek configuration as a JSON string via an environment variable override (`GOAL_SEEK_CONFIG`). This allows multiple users to run concurrent, isolated searches.
*   **Storage:** The worker script (`cloud_job.py`) runs the `search_engine.py` logic. Upon completion, it dumps the resulting Pandas DataFrame to CSV/JSON and uploads it to a Google Cloud Storage (GCS) bucket.
*   **Log Scraping:** The Streamlit app uses the GCP Logging Client to query logs specific to the Execution ID, parsing messages formatted as `[45.0%] Calculating...` to drive a live progress bar in the UI.

---

## 4. Quality Assurance Strategy

The project tackles the "Unknown Data Quality" problem (where bad data causes algorithm failure) by entirely decoupling logic verification from historical data.

### 4.1. Synthetic Data Generator (`src/test_utils/data_generator.py`)
A custom class that generates Geometric Brownian Motion (random walk) to simulate market noise, and provides methods to explicitly "inject" perfect Bump and Slide patterns at known indices.

### 4.2. Testing Layers
*   **Unit Tests (`test_analyzer.py`):** Uses the Synthetic Data Generator to inject a pattern and asserts the analyzer finds exactly 1 hit at the exact timestamp.
*   **Property-Based Fuzzing (`test_properties.py`):** Uses the `hypothesis` library to generate thousands of random dataframes (with NaNs, extreme values, zeros) to ensure the core algorithms (`search_engine.py`, `analyzer.py`) never crash.
*   **Integration Tests (`test_app.py`):** Uses Streamlit's `AppTest` framework to simulate user clicks, parameter adjustments, and ensure the UI components render without unhandled exceptions.
*   **Visual Debug App (`debug_app.py`):** An alternate entry point that replaces the Parquet data with the Synthetic Data Generator, allowing developers to visually verify that the drawn Plotly boxes correctly encapsulate the injected mathematical patterns.

---

## 5. Extensibility and Future Considerations
*   **Data Backend:** The system currently loads Parquet into Pandas. If the dataset scales significantly beyond 25 years (e.g., tick data instead of 1-minute data), the engine could be ported to `Polars` or `Dask` for out-of-core computation.
*   **Targeting Logic:** The Goal Seek engine currently optimizes for raw occurrences (`total_hits`). The architecture easily supports adding optimization targets like "Maximum Average Slide Magnitude" or "Win Rate".