# SP500 Bump & Slide Analysis

A Python application designed to analyze intraday SPY (S&P 500 ETF) data for "Bump and Slide" price patterns. This tool provides an interactive Streamlit dashboard for visual analysis with powerful filtering and configuration options.

## Features

- **Pattern Detection**: 
  - Automatically identifies "Bump" (initial trend) and "Slide" (subsequent reaction) patterns.
  - Detects patterns based on configurable lengths (minutes), thresholds (price/%), and volume.
- **Goal Seek (UI Integrated)**:
  - **Exhaustive Search**: Define parameter ranges directly in the Web UI and find the most successful combinations.
  - **Local & Cloud Execution**: Run searches on your local machine or offload them to Google Cloud for high performance.
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

---

## Project Structure

- `app.py`: Main Streamlit entry point.
- `src/ui/exploration.py`: Logic for the interactive chart view.
- `src/ui/goal_seek.py`: Logic for the automated search UI.
- `src/cloud_runner.py`: Tooling for GCP job generation and execution.
- `cloud_job.py`: Dedicated worker script for cloud execution.
- `src/search_engine.py`: Core parallelized search logic.
- `src/analyzer.py`: Pattern detection algorithms.

## Quality Assurance

To run unit and property-based tests:
```bash
python -m pytest
```
