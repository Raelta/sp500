# Test Strategy & Quality Assurance Plan

## 1. Problem Statement
The primary challenge in this project is the **Unknown Data Quality** of the input source (`spy_data_25yr.parquet`). Reliance on this data makes it difficult to verify if analytical features (Bump & Slide detection) are functioning correctly or if they are failing due to data anomalies.

## 2. Core Strategy: Synthetic Verification
To ensure robustness, we will decouple **Logic Verification** from **Data Quality**. We will achieve this by creating a **Synthetic Data Generator** that produces "controlled" market data. This allows us to verify that *if* a pattern exists, the code *will* find it.

### The Verification Pyramid
1.  **Visual Verification (Top)**: Manually inspecting generated patterns to confirm they match human intuition.
2.  **Property-Based Testing (Middle)**: "Fuzzing" the system with thousands of random inputs to ensure stability and logical consistency.
3.  **Unit Testing (Base)**: Testing specific functions with exact, known inputs to ensure mathematical precision.

---

## 3. Component Design

### A. Synthetic Data Generator (`src/test_utils/data_generator.py`)
A utility class designed to generate OHLCV (Open, High, Low, Close, Volume) data.

**Features:**
*   **Geometric Brownian Motion**: Generates realistic-looking "random walk" price data (Noise).
*   **Pattern Injection**: Ability to overwrite noise with deterministic patterns at specific indices.
    *   *Inject Bump*: Forces price up by $X%$ over $N$ minutes with Volume $V$.
    *   *Inject Slide*: Forces price down/flat by $Y%$ over $M$ minutes.
*   **Anomalies**: Option to inject missing data, zero volume, or market gaps to test robustness.

**Usage Example:**
```python
gen = MarketDataGenerator(seed=42)
df = gen.generate_noise(days=5)
gen.inject_pattern(df, index=100, type="bump_slide", bump_len=10, slide_len=10)
# Now we KNOW there is a pattern at index 100.
```

### B. Visual Debug Tool (`debug_app.py`)
A modified version of the main Streamlit application.

*   **Data Source**: Replaces `load_data_cached` with `MarketDataGenerator`.
*   **Controls**: Sidebar widgets to:
    *   Regenerate Random Data.
    *   Inject specific patterns.
    *   Adjust noise levels.
*   **Goal**: visual confirmation. You create a "Perfect Pattern" and see if the App draws the boxes around it correctly.

---

## 4. Test Categories

### Level 1: Unit Tests (Deterministic)
**Tool**: `pytest`
**Location**: `tests/test_analyzer.py`

These tests verify the "Happy Path" and specific edge cases using fixed seeds.

*   **Test Exact Match**: Inject a pattern at 10:00 AM. Assert `analyzer` returns a match at 10:00 AM.
*   **Test Threshold Sensitivity**:
    *   Inject a 5% bump.
    *   Assert it IS found when threshold = 4%.
    *   Assert it is NOT found when threshold = 6%.
*   **Test False Positives**: Generate pure noise. Assert 0 matches (or very low count).

### Level 1.5: Parameter Control Tests (Filters)
**Tool**: `pytest`
**Location**: `tests/test_analyzer_params.py`

Explicitly verify that User Interface controls function as intended.

| Control | Test Case | Expected Outcome |
| :--- | :--- | :--- |
| **Day of Week** | Inject pattern on **Tuesday**. Set filter to `['Tuesday']`. | **Match** |
| | Inject pattern on **Tuesday**. Set filter to `['Wednesday']`. | **No Match** |
| **Year Selection** | Generate 2023-2024 data. Inject pattern in **2024**. Filter `2024`. | **Match** |
| | Generate 2023-2024 data. Inject pattern in **2024**. Filter `2023`. | **No Match** |
| **Lengths** | Inject pattern with Bump Length **20**. Search `bump_len=20`. | **Match** |
| | Inject pattern with Bump Length **20**. Search `bump_len=10`. | **No Match** |

### Level 2: Property-Based Tests (Probabilistic)
**Tool**: `hypothesis`
**Location**: `tests/test_properties.py`

These tests generate random data (without specific injected patterns) to ensure the code doesn't crash and follows logical rules.

*   **Invariants**:
    *   `find_bumps_and_slides` should never return a DataFrame with more rows than the input.
    *   Resulting indices must always be within the input date range.
*   **Monotonicity**:
    *   Stricter thresholds (e.g., higher volume requirement) should never result in *more* matches than looser thresholds.

---

## 5. Implementation Roadmap

1.  **Dependencies**: Add `pytest` and `hypothesis` to `requirements.txt`.
2.  **Scaffold Generator**: Create `src/test_utils/data_generator.py`.
3.  **Write Unit Tests**: Implement `tests/test_analyzer.py` covering the core logic.
4.  **Create Debug App**: Build `debug_app.py` for interactive testing.
5.  **CI/CD Integration**: (Optional) Run `pytest` on every commit.

## 6. Best Practices Checklist
- [ ] **Determinism**: Always use a fixed random seed for Unit Tests so failures are reproducible.
- [ ] **Isolation**: Tests should not depend on the file system or external APIs (mocking `load_data`).
- [ ] **Coverage**: Ensure tests cover not just "price" but also "volume" conditions and "time of day" filters.
