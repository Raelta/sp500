# Test Plan & Verification Inventory

## Overview
This document lists the implemented tests for the SP500 Bump & Slide project. These tests ensure the correctness of the analytical logic, system stability, and application workflow.

## 1. Unit Tests (`tests/test_analyzer.py`)
These tests verify specific logic units using controlled Synthetic Data. They are deterministic (same input = same output).

| Test Function | Purpose | Methodology |
| :--- | :--- | :--- |
| `test_exact_match` | Confirm pattern detection logic. | Inject a "Perfect" pattern at a known timestamp and assert the analyzer returns exactly one match at that time. |
| `test_threshold_sensitivity` | Verify sensitivity of `bump_threshold`. | Inject a 5% bump. Assert it is **found** when threshold is 4%, but **missed** when threshold is 6%. |
| `test_day_of_week_filter` | Verify day filtering logic. | Inject patterns on Monday. Assert filter `['Monday']` finds it, while `['Tuesday']` correctly excludes it. |
| `test_length_parameters` | Verify window length parameters. | Inject a 20-min pattern. Assert it is found when searching for `bump_len=20`, but logic correctly handles mismatch when searching for `bump_len=10`. |

## 2. Property-Based Tests (`tests/test_properties.py`)
These tests use the `hypothesis` library to generate thousands of random inputs ("fuzzing") to verify system stability and logical invariants.

| Test Function | Purpose | Methodology |
| :--- | :--- | :--- |
| `test_analyzer_no_crash` | Verify crash resilience. | Run analyzer on 50+ completely random dataframes (valid floats). Assert no exceptions are raised. |
| `test_output_invariants` | Verify structural integrity. | Check that all result indices are valid and exist within the input dataframe (no out-of-bounds results). |

## 3. Integration Tests (`tests/test_app.py`)
These tests verify the end-to-end application workflow using Streamlit's testing framework.

| Test Function | Purpose | Methodology |
| :--- | :--- | :--- |
| `test_app_analysis_flow` | Verify App Startup & Analysis pipeline. | Use `AppTest` to headless-load `app.py`, simulate a user clicking "Apply Changes", and assert that Metrics and Visualization components are rendered without error. |

## 4. Manual Verification (`debug_app.py`)
A dedicated tool for visual inspection, allowing you to "see" what the code sees.

*   **Goal**: Bridge the gap between code logic and visual intuition.
*   **Usage**: Run `streamlit run debug_app.py`.
*   **Features**:
    *   **Generate Noise**: Create realistic random market data.
    *   **Inject Patterns**: Place specific "Perfect Patterns" at known indices.
    *   **Verify**: Visually confirm that the colored boxes drawn by the analyzer align perfectly with the injected candle pattern.
