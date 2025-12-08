# SP500 Data Analysis Toolkit

## 🚀 User Guide: How to Execute

### 1. Trend Analysis (`check_increasing.py`)
Analyzes the data for increasing or decreasing trends within specific window sizes.

**Interactive Mode (Recommended):**
Simply run the script and follow the prompts.
```bash
python check_increasing.py
```

**Command Line Mode:**
Provide arguments directly: `Year`, `Column`, `Window Size`, `Trend Direction`
```bash
# Example: Check if 'open' price strictly INCREASES in 5-minute chunks for 2010
python check_increasing.py 2010 open 5 increase

# Example: Check if 'close' price strictly DECREASES in 10-minute chunks for 2011
python check_increasing.py 2011 close 10 decrease
```
*Output: Saves a CSV file (e.g., `trend_analysis_2010_open_5_increase.csv`) and prints a summary.*

### 2. Monthly Analysis (`analyze_month.py`)
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

### 3. General Exploration (`explore_data.py`)
Runs a full health check and summary of the dataset, including monthly averages over the entire period.

```bash
python explore_data.py
```

---

## 📂 File Descriptions

| File | Description |
|------|-------------|
| **`check_increasing.py`** | **Primary Analysis Tool**. Checks for price trends (increase/decrease) within defined window sizes. It also verifies if the trend *continues* into the very next value. Generates detailed CSV reports. |
| **`analyze_month.py`** | Filters data for a specific month (e.g., January) and groups it by year to show the average opening price. |
| **`explore_data.py`** | Generates a general report: summary statistics, date ranges, missing values check, and a full list of monthly averages for the entire dataset. |
| **`load_data.py`** | Utility module that handles loading the CSV file `1_min_SPY_2008-2021.csv`. It parses dates and tracks memory usage/performance. |

## ⚙️ Setup

1.  Ensure you have Python 3 installed.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
