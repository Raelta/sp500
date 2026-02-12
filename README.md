# SP500 Bump & Slide Analysis

A Python application designed to analyze intraday SPY (S&P 500 ETF) data for "Bump and Slide" price patterns. This tool provides an interactive Streamlit dashboard for visual analysis with powerful filtering and configuration options.

## Features

- **Pattern Detection**: 
  - Automatically identifies "Bump" (initial trend) and "Slide" (subsequent reaction) patterns.
  - Detects patterns based on configurable lengths (minutes), thresholds (price/%), and volume.
- **Goal Seek (UI Integrated)**:
  - **Exhaustive Search**: Define parameter ranges directly in the Web UI and find the most successful combinations.
  - **Local & Cloud Execution**: Run searches on your local machine or offload them to Google Cloud for high performance.
  - **Result Summary**: View key metrics (Matches, Max Hits) and yearly distribution for top results.
  - **One-Click Visualization**: Click any result in the Goal Seek table to instantly load it into the Exploration view.
- **High Performance Search Engine**:
  - **Parallel Processing**: Utilizes all available CPU cores to execute searches concurrently.
  - **Vectorized Broadcasting**: Uses NumPy matrix multiplication to check thousands of combinations simultaneously.
  - **Window Catalog**: Pre-compute metrics to disk for near-instant lookups (Catalog mode).
- **Interactive Dashboard**: 
  - Powerful Streamlit app with reactive analysis.
  - Interactive Plotly visualizations with zoom, pan, and hover details.
- **Smart Filtering**: 
  - Excel-style "Select All" filters for Years and Days of the Week.
  - Filter by Volume, Time of Day, and Days.

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd sp500
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Web Dashboard

The primary way to use the application. Supports both manual exploration and automated Goal Seeking.

```bash
streamlit run app.py
```

*   **Exploration Mode**: Manually adjust parameters and visualize patterns on a chart.
*   **Goal Seek Mode**: Enter ranges for parameters and find the best performing configurations.

---

## Architecture: Goal Seek Process Flow

This section outlines the architectural flow of the Goal Seek / Reverse Search engine.

```mermaid
graph TD
    %% CLI Layer
    Start([User Command]) -->|Args: Ranges, Min Bumps| CLI[goal_seek_cli.py]
    CLI -->|Load Parquet| DataLoader[Data Loader]
    DataLoader -->|Clean & Validate| CLI
    CLI -->|Generate Grid| Seeker[GoalSeeker Engine]

    %% Search Engine Layer
    subgraph "Optimization Engine (src/search_engine.py)"
        Seeker -->|Apply Global Filters| PreProcess["Filter Data (Time/Day)"]
        PreProcess -->|Group by Structure| GridSplit[Split into Structural Combos]
        GridSplit -->|Distribute Tasks| Pool[ProcessPoolExecutor]
        
        %% Worker Layer
        subgraph "Worker Process (Parallel)"
            Pool -->|Bump Len, Slide Len| Calc[Rolling Calculations]
            Calc -->|Price Change, SizeVol| Metrics[Base Metrics]
            
            Metrics -->|Find Max Values| Pruning[Data-Driven Pruning]
            Pruning -->|Discard Impossible Thresholds| Masking[Boolean Mask Generation]
            
            Masking -->|Vectorize| MatrixBuild[Build Sparse Matrices]
            MatrixBuild -->|"Bump Matrix (N x B)"| DotProd[Matrix Multiplication]
            MatrixBuild -->|"Slide Matrix (N x S)"| DotProd
            
            DotProd -->|"Bump.T @ Slide"| Hits[Calculate Total Hits & Bumps]
            Hits -->|Filter| ValidMask{Hits > 0?}
            
            ValidMask -->|Yes| OverlapFilter[Identify True Hits (NMS)]
            OverlapFilter -->|Keep Best Slide| CleanHits[Calculate True Hits]
            CleanHits -->|Store| Result[Store Result]
            ValidMask -->|Else| Discard[Discard]
        end
    end

    %% Output Layer
    Result -->|Collect| Aggregator[Result Aggregation]
    Aggregator -->|Sort by Total Hits| Sorting
    Sorting -->|Top N| Console[Console Output]
    Sorting -->|All Results| CSV[CSV File]
```

### Optimized Catalog Search Flow

When using the `--use-catalog` flag, the process bypasses the rolling calculation step by using pre-computed matrices.

```mermaid
graph TD
    Start([User Command]) -->|Args: --use-catalog| CLI[goal_seek_cli.py]
    CLI -->|Load Catalog| Catalog[src/catalog.py]
    Catalog -->|Change Matrix (MemMap)| Memory
    Catalog -->|Metadata (RAM)| Memory
    
    CLI -->|Generate Grid| Searcher[CatalogSearcher]
    
    subgraph "Catalog Search Engine (src/catalog_search.py)"
        Searcher -->|Parallelize| Threads[ThreadPoolExecutor]
        
        subgraph "Thread Worker"
            Threads -->|Bump Len, Slide Len| Slicing[Array Slicing]
            Slicing -->|Fetch Change| MatrixLookup[Matrix Lookup]
            Slicing -->|Calc Vol/Up| CumSumDiff[CumSum Subtraction]
            
            CumSumDiff -->|Apply Filters| VectorFilter[Vectorized Filtering]
            VectorFilter -->|Filter Overlaps| NMS[Non-Maximum Suppression]
            NMS -->|Count Hits| Stats[Statistics]
        end
        
        Stats -->|Result| Collection
    end
    
    Collection --> Sorting
```

### Key Components

1.  **Window Catalog**: A pre-computed database of metrics.
    *   **Change Matrix**: 2GB Memory-mapped file storing % Change for every possible window size.
    *   **Cumulative Sums**: Small in-memory arrays allowing O(1) calculation of Volume and Up-Candle counts for any window.
2.  **Structural Grouping**: Parameters that require re-scanning the dataframe (Length) are grouped.
3.  **Data-Driven Pruning**: We check the maximum possible values in the actual dataset before testing thresholds. If the data only goes up to 5% change, we don't test a 6% threshold.
4.  **Vectorization**: Instead of looping through thresholds, we convert them into boolean matrices and use Linear Algebra (Matrix Multiplication) to count overlaps (Hits) instantly.
5.  **Overlap Filtering**: A post-processing step ensures that reported matches do not overlap in time. If multiple matches occur within overlapping windows, the one with the highest slide magnitude is preserved.

---

## Quality Assurance Strategy

### 1. Problem Statement
The primary challenge in this project is the **Unknown Data Quality** of the input source (`spy_data_25yr.parquet`). Reliance on this data makes it difficult to verify if analytical features (Bump & Slide detection) are functioning correctly or if they are failing due to data anomalies.

### 2. Core Strategy: Synthetic Verification
To ensure robustness, we will decouple **Logic Verification** from **Data Quality**. We will achieve this by creating a **Synthetic Data Generator** that produces "controlled" market data. This allows us to verify that *if* a pattern exists, the code *will* find it.

#### The Verification Pyramid
1.  **Visual Verification (Top)**: Manually inspecting generated patterns to confirm they match human intuition.
2.  **Property-Based Testing (Middle)**: "Fuzzing" the system with thousands of random inputs to ensure stability and logical consistency.
3.  **Unit Testing (Base)**: Testing specific functions with exact, known inputs to ensure mathematical precision.

### 3. Component Design

#### A. Synthetic Data Generator (`src/test_utils/data_generator.py`)
A utility class designed to generate OHLCV (Open, High, Low, Close, Volume) data.

**Features:**
*   **Geometric Brownian Motion**: Generates realistic-looking "random walk" price data (Noise).
*   **Pattern Injection**: Ability to overwrite noise with deterministic patterns at specific indices.
    *   *Inject Bump*: Forces price up by $X%$ over $N$ minutes with Volume $V$.
    *   *Inject Slide*: Forces price down/flat by $Y%$ over $M$ minutes.
*   **Anomalies**: Option to inject missing data, zero volume, or market gaps to test robustness.

#### B. Visual Debug Tool (`debug_app.py`)
A modified version of the main Streamlit application.

*   **Data Source**: Replaces `load_data_cached` with `MarketDataGenerator`.
*   **Controls**: Sidebar widgets to:
    *   Regenerate Random Data.
    *   Inject specific patterns.
    *   Adjust noise levels.
*   **Goal**: visual confirmation. You create a "Perfect Pattern" and see if the App draws the boxes around it correctly.

---

## Test Plan & Inventory

This section lists the implemented tests for the SP500 Bump & Slide project. These tests ensure the correctness of the analytical logic, system stability, and application workflow.

### 1. Unit Tests (`tests/test_analyzer.py`)
These tests verify specific logic units using controlled Synthetic Data. They are deterministic (same input = same output).

| Test Function | Purpose | Methodology |
| :--- | :--- | :--- |
| `test_exact_match` | Confirm pattern detection logic. | Inject a "Perfect" pattern at a known timestamp and assert the analyzer returns exactly one match at that time. |
| `test_threshold_sensitivity` | Verify sensitivity of `bump_threshold`. | Inject a 5% bump. Assert it is **found** when threshold is 4%, but **missed** when threshold is 6%. |
| `test_day_of_week_filter` | Verify day filtering logic. | Inject patterns on Monday. Assert filter `['Monday']` finds it, while `['Tuesday']` correctly excludes it. |
| `test_length_parameters` | Verify window length parameters. | Inject a 20-min pattern. Assert it is found when searching for `bump_len=20`, but logic correctly handles mismatch when searching for `bump_len=10`. |

### 2. Property-Based Tests (`tests/test_properties.py`)
These tests use the `hypothesis` library to generate thousands of random inputs ("fuzzing") to verify system stability and logical invariants.

| Test Function | Purpose | Methodology |
| :--- | :--- | :--- |
| `test_analyzer_no_crash` | Verify crash resilience. | Run analyzer on 50+ completely random dataframes (valid floats). Assert no exceptions are raised. |
| `test_output_invariants` | Verify structural integrity. | Check that all result indices are valid and exist within the input dataframe (no out-of-bounds results). |

### 3. Integration Tests (`tests/test_app.py`)
These tests verify the end-to-end application workflow using Streamlit's testing framework.

| Test Function | Purpose | Methodology |
| :--- | :--- | :--- |
| `test_app_analysis_flow` | Verify App Startup & Analysis pipeline. | Use `AppTest` to headless-load `app.py`, simulate a user clicking "Apply Changes", and assert that Metrics and Visualization components are rendered without error. |

### 4. Goal Seek Tests (`tests/test_goal_seek.py`)
Verify the search engine's ability to find parameters and aggregate results.

| Test Function | Purpose | Methodology |
| :--- | :--- | :--- |
| `test_goal_seeker_basic` | Verify basic search. | Run search on mock data with known trends. |
| `test_hits_per_year` | Verify result summary. | Ensure `hits_per_year` JSON is correctly generated for multi-year data. |

### 5. Manual Verification (`debug_app.py`)
A dedicated tool for visual inspection, allowing you to "see" what the code sees.
*   **Usage**: Run `streamlit run debug_app.py`.

---

## Cloud Offloading (Google Cloud Platform)

For massive searches that require significant compute power, you can offload the workload to **Google Cloud Run Jobs**.

### 1. Initial Setup (One-Time)

You will need the `gcloud` CLI installed and authenticated to your project.

```bash
# Set your project ID
gcloud config set project sp500-479009

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com artifactregistry.googleapis.com run.googleapis.com
```

### 2. Permissions (Troubleshooting Log)

If you encounter `403 Forbidden` errors during build or execution, ensure the **Compute Engine default service account** (used by Cloud Build) has the following roles (Note: The build uses Python 3.11-slim as defined in the `Dockerfile`):

```bash
# Replace [PROJECT_NUMBER] with your project's number (e.g. 190958000714)
SA_EMAIL="[PROJECT_NUMBER]-compute@developer.gserviceaccount.com"

# Grant permissions
gcloud projects add-iam-policy-binding sp500-479009 --member=serviceAccount:$SA_EMAIL --role=roles/storage.admin
gcloud projects add-iam-policy-binding sp500-479009 --member=serviceAccount:$SA_EMAIL --role=roles/artifactregistry.admin
gcloud projects add-iam-policy-binding sp500-479009 --member=serviceAccount:$SA_EMAIL --role=roles/logging.logWriter
```

### 3. Build & Deploy Workflow

The app uses **Google Cloud Build** so you don't need Docker installed locally.

1.  **Build the Image**:
    ```bash
    gcloud builds submit --tag gcr.io/sp500-479009/sp500-analyzer .
    ```
2.  **Create the Job**:
    ```bash
    gcloud beta run jobs create sp500-goal-seek \
        --image gcr.io/sp500-479009/sp500-analyzer \
        --tasks 1 --region europe-west2 --cpu 4 --memory 8Gi
    ```
3.  **Setup Local Auth (for UI buttons)**:
    ```bash
    gcloud auth application-default login
    ```

4.  **Execute**:
    Trigger the job from the **Goal Seek UI** in the Streamlit app, or via:
    ```bash
    gcloud beta run jobs execute sp500-goal-seek --region europe-west2
    ```

### 4. Monitoring & Logs

You can verify if the cloud job is running correctly (and using the optimized Catalog) by checking the logs:

-   **Web Console**: Go to [Cloud Run Jobs](https://console.cloud.google.com/run/jobs) -> `sp500-goal-seek` -> **Logs** tab.
-   **CLI**:
    ```bash
    gcloud beta run jobs logs read sp500-goal-seek --project sp500-479009 --region europe-west2 --limit 50
    ```

Look for the `✅ Pre-built catalog found` message to confirm the optimization is active.

### 5. Engine Consistency Check

If you suspect differences between local and cloud results, run the consistency tool:
```bash
PYTHONPATH=. python src/test_utils/engine_consistency.py
```
This tool runs an identical search on both the standard engine (`GoalSeeker`) and the optimized engine (`CatalogSearcher`) and verifies their results match exactly.

---

## Project Structure

- `app.py`: Main Streamlit entry point.
- `src/ui/exploration.py`: Logic for the interactive chart view.
- `src/ui/goal_seek.py`: Logic for the automated search UI.
- `src/cloud_runner.py`: Tooling for GCP job generation and execution.
- `cloud_job.py`: Dedicated worker script for cloud execution.
- `src/search_engine.py`: Core parallelized search logic.
- `src/analyzer.py`: Pattern detection algorithms.

## Quality Assurance Commands

To run unit and property-based tests:
```bash
python -m pytest
```
