# SP500 Data Analysis Toolkit

## 🚀 User Guide: How to Execute

### 🌟 Interactive Dashboard (`dashboard.py`)
Launch the full interactive dashboard to analyze trends with a user-friendly interface.
```bash
streamlit run dashboard.py
```
*Features: Year selection (single/range), sample size sliders, interactive charts with dropdowns, and data tables.*

### 1. Trend Table Generator (`generate_trend_table.py`)
Generates a comprehensive summary table analyzing trends over a **range** of sample sizes (e.g., 3 to 10). It displays the percentage of samples matching the trend and the percentage where the trend continues for the next sample.

**Interactive Mode:**
```bash
python generate_trend_table.py
```
*Follow the prompts. You can choose to generate a bar chart of the results.*

**Command Line Mode:**
```bash
# Example: Check 'close' price for INCREASING trend for sample sizes 3 to 10 in 2010
python generate_trend_table.py 2010 close 3 10 increase

# Example: Generate table AND chart
python generate_trend_table.py 2010 close 3 10 increase --chart
```
*Output: Displays table and optionally generates an interactive HTML chart (e.g., `trend_chart_2010_close_increase.html`) which automatically opens in your web browser.*

### 2. Trend Analysis (`check_increasing.py`)
Analyzes the data for increasing or decreasing trends within specific window sizes. It also verifies if that trend *continues* for a specified number of samples after the window.

**Interactive Mode (Recommended):**
Simply run the script and follow the prompts.
```bash
python check_increasing.py
```
*You will be prompted for: Year, Column Name, Window Size, Trend Direction, and Continuation Samples.*

**Command Line Mode:**
Provide arguments directly: `Year`, `Column`, `Window Size`, `Trend Direction`, `Continuation Samples`
```bash
# Example: Check if 'open' price strictly INCREASES in 5-minute chunks for 2010
# AND continues increasing for the next 3 samples
python check_increasing.py 2010 open 5 increase 3

# Example: Check if 'close' price strictly DECREASES in 10-minute chunks for 2011
# AND continues decreasing for the next 1 sample (default)
python check_increasing.py 2011 close 10 decrease 1
```
*Output: Saves a CSV file (e.g., `trend_analysis_2010_open_5_increase_cont3.csv`) containing the results and a boolean `continues_trend` column.*

### 3. Monthly Analysis (`analyze_month.py`)
Calculates the average "open" price for a specific month across all years (2008-2021).

**Interactive Mode:**
```bash
python analyze_month.py
```

**Command Line Mode:**
```bash
# Example: Analyze October
python analyze_month.py October
```

### 4. General Exploration (`explore_data.py`)
Runs a full health check and summary of the dataset, including monthly averages over the entire period.

```bash
python explore_data.py
```

---

## 📂 File Descriptions

| File | Description |
|------|-------------|
| **`dashboard.py`** | **Interactive Web Dashboard**. A Streamlit app that provides a GUI for trend analysis, allowing dynamic parameter adjustment and instant chart updates. |
| **`generate_trend_table.py`** | **Trend Table Generator**. Iterates through a range of sample sizes to produce a summary table showing the frequency of strictly increasing/decreasing trends and their continuation rates. |
| **`check_increasing.py`** | **Detailed Trend Checker**. Checks for price trends (increase/decrease) within a specific window size. It validates if the trend **continues** strictly for a user-defined number of subsequent samples. Generates detailed CSV reports. |
| **`analyze_month.py`** | Filters data for a specific month (e.g., January) and groups it by year to show the average opening price. |
| **`explore_data.py`** | Generates a general report: summary statistics, date ranges, missing values check, and a full list of monthly averages for the entire dataset. |
| **`load_data.py`** | Utility module that handles loading the CSV file `1_min_SPY_2008-2021.csv`. It parses dates and tracks memory usage/performance. |

## ⚙️ Setup

1.  Ensure you have Python 3 installed.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
