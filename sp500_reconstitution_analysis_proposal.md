# Proposed Investigation: S&P 500 Reconstitution Analysis

## 1. Executive Summary
This document outlines a proposed approach to investigate the impact of S&P 500 company additions and deletions (index reconstitution) on market behavior. The goal is to understand how the swapping of constituent companies affects the overall index performance and whether it introduces specific anomalies, particularly in the context of intraday patterns like the "Bump & Slide."

## 2. Objective
To analyze the historical entry and exit of companies from the S&P 500 index and determine:
- The "Index Effect" on the specific stocks being added or removed.
- The aggregate impact of these changes on the SPY ETF over various time horizons (short-term volatility vs. long-term drift).
- The correlation between index rebalancing dates and the frequency/magnitude of Bump & Slide patterns.
- The extent of survivorship bias in standard backtesting if historical constituent changes are ignored.

## 3. Data Requirements & Acquisition
To perform this analysis accurately, we require point-in-time historical data:
- **Constituent Data:** A historical record of all S&P 500 additions and deletions, including Announcement Dates and Effective Dates.
  - *Potential Sources:* CRSP/Compustat (academic standard), EOD Historical Data API, Norgate Data (excellent for point-in-time constituents), or scraping historical Wikipedia revisions for a free, albeit less robust, dataset.
- **Individual Stock Data:** OHLCV data for the individual stocks being added or removed, surrounding the event dates.
- **Index Data:** The existing `spy_data_25yr.parquet` containing 1-minute intraday SPY data.

## 4. Proposed Methodologies & Approaches

### Approach A: Event Study Methodology (The "Index Effect")
- **Focus:** The price and volume behavior of the specific companies entering or exiting.
- **Method:** Analyze an event window (e.g., -10 days to +10 days) centered on the Announcement Date and the Effective Date.
- **Expected Outcome:** Typically, added stocks experience positive abnormal returns between announcement and effective date due to index funds buying, while deleted stocks experience negative abnormal returns. We will quantify this effect over the last 25 years to see if the alpha is decaying.

### Approach B: Intraday "Bump & Slide" Rebalancing Anomalies
- **Focus:** How the overall market (SPY) behaves during the days surrounding major rebalancing.
- **Context:** S&P 500 rebalancing often coincides with "Quadruple Witching" days (the third Friday of March, June, September, and December), leading to massive trading volumes.
- **Method:** Overlay the historical reconstitution effective dates onto our existing Bump & Slide search engine (`src/analyzer.py`).
- **Query:** Do Bump & Slide patterns occur more frequently, or with higher slide magnitudes, during rebalancing days due to institutional liquidity re-routing?

### Approach C: Market Impact & Sector Drift
- **Focus:** The long-term impact on the index's composition and performance.
- **Method:** Calculate the difference in market capitalization, beta, and sector alignment between the exiting companies and the entering companies.
- **Analysis:** Does the SPY systematically become more volatile or skewed toward specific sectors (e.g., Technology) immediately following a rebalancing cycle? How does this shift affect the baseline volatility metrics used in our intraday pattern detection?

### Approach D: Survivorship Bias Quantification
- **Focus:** Validating the integrity of long-term trading strategies.
- **Method:** Run a baseline trend-following strategy on the *current* S&P 500 constituents historically, and compare it against the same strategy run on *point-in-time* constituents.
- **Outcome:** A metric quantifying the inflation of returns caused by survivorship bias in standard retail backtests.

## 5. Implementation Steps
1. **Data Pipeline Extension:** Create a new module (e.g., `src/reconstitution_loader.py`) to fetch and clean historical addition/deletion dates.
2. **Event Flagging:** Modify `src/data_loader.py` to add boolean flags to the SPY intraday dataset indicating if a given day is an Announcement Date, an Effective Date, or within a 3-day window of these events.
3. **Engine Update:** Update `src/search_engine.py` to allow filtering by these new "Event Proximity" flags.
4. **Visualization:** Build a new Streamlit tab in `app.py` to visualize the average SPY behavior on rebalancing days versus normal days.

## 6. Conclusion
By integrating point-in-time index constituent data, we can move beyond analyzing the SPY as a static entity and understand it as a dynamic, evolving portfolio. This will not only uncover new intraday trading anomalies surrounding rebalancing events but also rigorously harden our existing algorithms against survivorship bias.