# SP500 Bump & Slide Analysis - AI Assistant Context (GEMINI.md)

Welcome to the SP500 Bump & Slide Analysis project. This document serves as the foundational context and mandate for any AI assistant (like Gemini CLI) working on this codebase. It provides the architectural rules, file mapping, and design decisions to enable efficient feature development and bug fixing without needing to read the entire codebase every time.

## 1. Project Overview
This project is a high-performance quantitative analysis tool for detecting "Bump and Slide" technical patterns in intraday SPY data. 
- **Bump:** Initial price movement (trend).
- **Slide:** Subsequent reaction immediately following the Bump.
It provides a Streamlit web UI for standard exploration and an exhaustive, parallelized search engine (Goal Seek) for parameter optimization, which can be run locally or offloaded to Google Cloud Run.

## 2. File Structure & Responsibilities

### UI & Presentation Layer
*   `app.py`: Main entry point for the Streamlit dashboard. Handles high-level routing, data quality popups, and authentication.
*   `src/ui/exploration.py`: Renders the interactive "Standard Analysis" chart (Plotly) and parameter inputs.
*   `src/ui/goal_seek.py`: Renders the UI for the automated search engine, cloud execution monitoring, and result loading.
*   `src/ui/auth.py`: Simple password protection and cookie management.
*   `src/visualizer.py`: Contains Plotly charting logic. Crucially uses a categorical X-axis to remove non-trading hours (gaps) and demarcates session breaks.

### Core Engine & Data Processing
*   `src/analyzer.py`: The core pattern detection logic. **Crucial Rule:** Uses purely vectorized Pandas rolling window operations. No nested Python `for` loops.
*   `src/search_engine.py`: The high-performance "Goal Seek" optimizer. Uses `ProcessPoolExecutor` for multiprocessing, data-driven pruning to skip impossible thresholds, and NumPy matrix multiplication (vectorized broadcasting) to test millions of filter combinations instantly.
*   `goal_seek_cli.py`: The CLI wrapper for the search engine.
*   `src/data_loader.py`: Handles caching Parquet data and calculating yearly medians for reference lines.
*   `src/data_validator.py`: Ensures data integrity (missing values, duplicates).

### Cloud Integration
*   `src/cloud_runner.py`: Tooling for GCP `run_v2` and Storage APIs. Uses Execution Overrides to pass JSON configurations via environment variables, allowing isolated concurrent runs.
*   `cloud_job.py`: The headless worker script that runs `search_engine.py` in a Cloud Run instance and saves results to GCS.
*   `deploy_cloud.sh` / `Dockerfile`: Deployment configuration for Google Cloud Build and Cloud Run.

### Testing & QA
*   `src/test_utils/data_generator.py`: Generates synthetic market data (Geometric Brownian Motion) to test logic independently of historical data quality.
*   `tests/test_analyzer.py`: Unit tests asserting perfect pattern matching using synthetic data.
*   `tests/test_properties.py`: Hypothesis property-based fuzzing to ensure the engine handles edge-cases (NaNs, zeroes) without crashing.
*   `tests/test_app.py`: Streamlit `AppTest` integration tests.
*   `debug_app.py`: A specialized UI that visualizes synthetic data to debug charting and pattern logic manually.

## 3. Core Architectural Rules & Mandates

When modifying or extending this codebase, you MUST adhere to the following principles:

### A. Performance is Paramount (Vectorization)
*   **NEVER** use `iterrows()`, `apply()`, or standard Python loops over the DataFrame in `analyzer.py` or `search_engine.py`.
*   All price calculations, rolling windows, and aggregations must be vectorized using Pandas or NumPy operations.
*   The `search_engine.py` relies on building boolean matrices and taking the dot product (`np.dot`). Preserve this architecture for any new filtering parameters.

### B. True Overlap Handling (NMS)
*   A market move might trigger multiple valid overlapping patterns. The system relies on Non-Maximum Suppression (NMS), currently implemented as `_calculate_true_hits`. It sorts overlapping matches by the absolute magnitude of the slide change and keeps the best one. 

### C. Testing Strategy
*   **Logic vs. Data:** Do not rely on historical data (`spy_data_25yr.parquet`) to verify logic. If you change pattern detection logic, update or add a test using the `data_generator.py` in `tests/test_analyzer.py`.
*   Ensure the fuzzer (`pytest tests/test_properties.py`) passes before finalizing any changes to the core algorithms.

### D. Cloud Compatibility
*   Any changes to `search_engine.py` must remain headless-compatible. The search engine is run by `cloud_job.py` on Cloud Run, which does not have access to Streamlit session state or UI components.
*   Configurations for the cloud worker are passed via the `GOAL_SEEK_CONFIG` environment variable as a JSON string. Ensure any new parameters are JSON serializable.

### E. UI Conventions
*   The application uses Streamlit. Keep the UI performant by utilizing `@st.cache_data` and `@st.cache_resource` appropriately.
*   Avoid adding massive data loads on the main thread; ensure progress bars or spinners are used for heavy computations.

## 4. Common Tasks & Implementation Guides

### Adding a New Filter Parameter
1. **Engine Update:** Add the parameter to `analyzer.py` and implement the boolean mask.
2. **Search Engine Update:** Add the parameter to the `filter_keys` array in `search_engine.py`. Define how it prunes invalid values, and add it to the matrix generation logic.
3. **UI Update:** Add a Streamlit widget in `src/ui/exploration.py` and `src/ui/goal_seek.py`.
4. **CLI Update:** Add argparse arguments in `goal_seek_cli.py`.
5. **Testing:** Write a synthetic test in `tests/test_analyzer.py` proving the filter works.

### Optimizing a Target
Currently, the search engine maximizes `total_hits`. If instructed to change the optimization target (e.g., "Win Rate" or "Average Slide Magnitude"), update the scoring logic inside `_process_structure` in `search_engine.py` where the sorting and true hits calculation occurs.