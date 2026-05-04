# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A quantitative analysis tool that detects "Bump and Slide" patterns in 1-minute equity data. Two surfaces:
- **Streamlit UI** (`app.py`) — interactive Exploration mode (single parameter set on a chart) and Goal Seek mode (grid search).
- **Headless engine** — `goal_seek_cli.py` for local exhaustive search, or `cloud_job.py` for the same engine running on Google Cloud Run.

Datasets are registered in `src/data_loader.DATASETS`:
- `SPY` → `spy_data_25yr.parquet` (~25y, 09:30–16:00 ET, ~2.5M rows)
- `NVDA` → `nvda_data_6yr.parquet` (~6y, has pre/post-market 04:01–20:00 ET, ~1.45M rows; filtered to 09:30–16:00 ET = 608K rows by default)

`load_data_cached(symbol, include_extended_hours=False)` is the canonical entry point. Symbol selection happens in `app.py`'s sidebar (persisted as `st.session_state.symbol`); `include_extended_hours` is a checkbox shown only for symbols whose `DATASETS` entry has `has_extended_hours=True`. Both values are plumbed through to `cloud_job.py` via the `GOAL_SEEK_CONFIG` JSON.

## Common commands

```bash
# Run the main UI (requires .streamlit/secrets.toml with `password = "..."`)
streamlit run app.py

# Override default UI parameters (note the `--` separator for streamlit args)
streamlit run app.py -- -bl 30 -bt 0.02 --bump-type percent

# Synthetic-data debug UI for visually verifying analyzer/visualizer logic
streamlit run debug_app.py

# Headless grid search
python goal_seek_cli.py                                    # SPY, regular hours
python goal_seek_cli.py --bump-len-start 10 --bump-len-end 60 --min-bump-threshold 0.5
python goal_seek_cli.py --start-year 2020 --end-year 2024 --min-bumps 10
python goal_seek_cli.py --symbol NVDA                      # NVDA, regular hours (default)
python goal_seek_cli.py --symbol NVDA --include-extended-hours   # full pre/post-market

# Convert NVDA.csv → parquet (one-off, source-data prep)
python convert_nvda_to_parquet.py

# All tests
python -m pytest

# Single test file or test
python -m pytest tests/test_analyzer.py
python -m pytest tests/test_analyzer.py::test_exact_match -v

# Pre-compute the data validation pickle (baked into the Docker image at build time)
python precompute_validation.py

# Deploy worker image + Cloud Run Job (project sp500-479009, region europe-west2)
./deploy_cloud.sh

# Release workflow: stage → pytest → AI-authored commit → push → smoke test the deployed Streamlit app
python release.py
```

`pytest.ini` sets `pythonpath = .` and `testpaths = tests`, so import as `from src.x import y` from any test file.

## Architecture

### Data layer (`src/data_loader.py`)

`DATASETS` is a dict mapping symbol → `{path, label, expected_minutes_per_day, has_extended_hours}`. `load_data_uncached(symbol, include_extended_hours=False)` reads the parquet and, when the symbol is flagged with `has_extended_hours` and the toggle is off, filters rows to `time(9,30)..time(16,0)` so NVDA matches SPY's 391-bar regular-hours shape. Validation pickles are per-symbol and per-state: `validation_report_<SYMBOL>.pkl` (full) and `validation_report_<SYMBOL>_regular.pkl` (filtered). `precompute_validation.py` emits both at Docker build time.

Adding a new symbol requires: (1) a parquet with columns `date, open, high, low, close, volume`; (2) a new `DATASETS` entry; (3) a `COPY` line in `Dockerfile`; (4) rerun of `precompute_validation.py`. The analyzer and search engine never see the symbol — they're symbol-agnostic by design.

### Pattern detection (`src/analyzer.py`)

A "Bump" of length `bump_len` minutes is followed immediately by a "Slide" of length `slide_len`. Both are evaluated on rolling windows over the entire dataframe and aligned with `shift()` so that index `[i]` holds the metrics for a pattern *starting* at `i`. **Threshold sign carries direction**: positive thresholds match `metric >= threshold`; negative thresholds match `metric <= threshold`. SizeVol is `volume * |close - open|` (filters out high-volume dojis).

`_calculate_true_hits` performs greedy non-maximum suppression: when overlapping windows match, only the one with the largest `|slide_change|` is kept. Results expose both `total_hits` (all overlapping matches) and `true_hits` (post-NMS).

### Search engine (`src/search_engine.py`)

`GoalSeeker.search` partitions parameters into two groups:
- **Structural** (`bump_len`, `slide_len`, `bump_thresh_type`, `slide_thresh_type`) — changing these requires recomputing rolling windows. Distributed across CPU cores via `ProcessPoolExecutor`.
- **Filter** (`bump_threshold`, `slide_threshold`, `min_bump_vol`, `min_slide_vol`, `bump_up_pct`, `slide_up_pct`) — applied as boolean masks to the rolling output.

Inside each worker, `_process_structure` does three things in order:
1. **Data-driven pruning** — drops requested filter values that fall outside the actual `min`/`max` of the rolling series.
2. **Mask cache + matrix build** — every surviving filter value becomes a boolean column. Bump and slide masks are stacked into `(N_rows × B_combos)` and `(N_rows × S_combos)` matrices.
3. **`np.dot(bump_matrix.T, slide_matrix)`** — single matmul yields hit counts for every bump×slide combination simultaneously.

Year filtering (`start_year`/`end_year` in `fixed_params`) is applied to the dataframe before search, not as a post-filter. `detailed=True` returns one row per match instead of one row per combination.

### Cloud execution (`src/cloud_runner.py` + `cloud_job.py`)

The Cloud Run Job is an idle template; each search is an **execution override** that injects the JSON config as `GOAL_SEEK_CONFIG` env var. This lets multiple users trigger concurrent runs of the same image with different parameters. Worker writes results CSV + metadata JSON to GCS (`sp500-goal-seek-results`). The UI:
- Polls `ListExecutions` for status.
- Scrapes Cloud Logging for `[NN.N%] message` lines (emitted by `cloud_job.progress()`) to drive the progress bar.
- Sends Google Chat notifications on success/failure via `GOOGLE_CHAT_WEBHOOK` env var (set in deploy script).

Credentials: `CloudRunner.get_credentials()` first tries `st.secrets["gcp_service_account"]` (cloud deployment), then falls back to ADC (`gcloud auth application-default login` for local).

### UI layout

`app.py` routes between two top-level views:
- `src/ui/exploration.py` — single-config analysis. Uses `applied_config` session state with an "Apply Changes" button to avoid recomputing on every widget tweak.
- `src/ui/goal_seek.py` — grid search, cloud submission, and the "Cloud Results Viewer" history table.

Auth is in `src/ui/auth.py` (SHA256 of `username + SALT` cookie, password from `st.secrets["password"]` or `APP_PASSWORD` env var). `app.py` short-circuits with `st.stop()` until auth passes.

### Synthetic testing

`src/test_utils/data_generator.MarketDataGenerator` produces Geometric Brownian Motion noise and injects deterministic Bump/Slide patterns at known indices. **Logic correctness is verified against synthetic data, never against `spy_data_25yr.parquet`** — the parquet has known data quality issues (duplicates auto-dropped, intraday gaps reported in the UI). `tests/test_analyzer.py` is the canonical example. `tests/test_properties.py` uses `hypothesis` to fuzz the analyzer on random dataframes for crash resilience.

## Conventions to preserve

- **Vectorize everything** in `analyzer.py` and `search_engine.py`. No `iterrows`, no `apply`, no Python loops over rows. The matrix-multiplication architecture in `_process_structure` is load-bearing — adding a new filter parameter means (a) extending `filter_keys`, (b) adding pruning bounds, (c) adding to `mask_cache`, (d) including its index in `bump_indices`/`slide_indices`. Threshold-style params use directional comparison (`>=` for positive, `<=` for negative); volume/up-pct params are always `>=`.
- **Headless safety**: `search_engine.py` runs inside `cloud_job.py` with no Streamlit. Don't import `streamlit` from `analyzer.py`, `search_engine.py`, `data_validator.py`, `notifications.py`, or `cloud_job.py`. New cloud config keys must be JSON-serializable (`CloudEncoder` handles `datetime.time`).
- **NMS scoring direction**: in `_process_structure`, the slide threshold's sign decides whether higher or more-negative `slide_change` is "best" when picking the survivor of overlapping matches.
- Adding a new filter parameter requires changes in five places: `analyzer.find_bumps_and_slides`, `search_engine.{filter_keys, pruning bounds, mask_cache}`, `goal_seek_cli.add_range_args`, `src/ui/goal_seek.py`, plus a synthetic test in `tests/test_analyzer.py`.

## GCP

- Project: `sp500-479009`, region: `europe-west2`, job: `sp500-goal-seek`, image: `gcr.io/sp500-479009/sp500-analyzer`, results bucket: `sp500-goal-seek-results`.
- The Dockerfile bakes both parquets (`spy_data_25yr.parquet`, `nvda_data_6yr.parquet`) and runs `precompute_validation.py` so all per-symbol validation pickles are ready before the worker starts.
- Cloud config (`GOAL_SEEK_CONFIG` env var) accepts `symbol` and `include_extended_hours`. Older configs that pass `data_path` instead of `symbol` still work for SPY-only paths.
