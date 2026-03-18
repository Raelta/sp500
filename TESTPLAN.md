# Test Plan: SP500 Bump & Slide Analysis

This document outlines the testing strategy and coverage for the SP500 Bump & Slide project.

## 1. Core Engine Tests (Algorithmic Logic)
- **`tests/test_analyzer.py`**: Asserts perfect pattern matching using synthetic data (`MarketDataGenerator`). Validates vectorization logic in `find_bumps_and_slides`.
- **`tests/test_properties.py`**: Property-based fuzzing via Hypothesis to ensure engine stability against edge-cases (NaNs, zeroes).
- **`tests/test_goal_seek.py`**: Covers the high-performance optimizer, validating matrix broadcasting, pruning, multiprocessing, and JSON/CLI output generation.

## 2. Data Pipeline Tests (Integrity & Validation)
- **`tests/test_data_pipeline.py`**: Verifies `src/data_validator.py`. Validates that the pipeline correctly identifies duplicate timestamps, missing values, intraday time gaps, and missing minutes within regular trading hours.

## 3. Visualization Layer Tests
- **`tests/test_visualizer.py`**: Validates `src/visualizer.py` using synthetic pattern data to ensure Plotly generates the chart correctly without throwing exceptions, ensuring continuous UI stability.

## 4. Cloud Integration Tests
- **`tests/test_cloud_runner.py`**: Validates `src/cloud_runner.py` by mocking Google Cloud Client Libraries (Run, Storage). Tests credential resolution, execution payload creation (overrides), and GCS downloading logic.

## 5. UI Integration Tests (Streamlit AppTest)
- **`tests/test_app.py`**: Uses Streamlit `AppTest` to run headless integration tests.
  - Mocks data loading and heavy computation to prevent timeouts.
  - Tests UI interactions like changing parameters and applying changes.
  - Validates correct rendering of results (metrics, tables, charts).
- **`tests/test_ui_interactions.py`**: Unit tests for independent UI components.
- **`tests/test_auth.py`**: Ensures login flows work correctly.
- **`tests/test_bugfixes.py`**: Tests for specific bug regressions.
