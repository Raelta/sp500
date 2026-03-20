# 2022 Fed Rate Hike Cycle (The FOMC 'Whipsaw')

## Event Description
Throughout 2022, FOMC meetings caused massive intraday volatility. The classic FOMC fingerprint is a knee-jerk reaction at 2:00 PM EST, followed by a massive reversal. (Looking for Rally -> Drop)

## Goal Seek Parameters Used
- **Length: 15-45 mins, Bump: >= +1.5%, Slide: <= -1.5%**
- Command executed: `python goal_seek_cli.py --start-year 2022 --end-year 2022 --bump-len-start 15 --bump-len-end 45 --bump-len-step 15 --slide-len-start 15 --slide-len-end 45 --slide-len-step 15 --min-bump-threshold 1.5 --min-slide-threshold -1.5 --detailed --output fomc_whipsaw_test.csv`

## Visualizing the Best Match
```text
↗↗↗↗↗↗↗↗↗↗ (Bump: Up ~1.6 pts, 45m)
          ↘↘↘↘↘↘↘↘↘↘ (Slide: Down ~2.8 pts, 45m)
```

## Goal Seek Results
### Top 5 Matches Found

| Date | Bump Len | Slide Len | Bump Change | Slide Change |
|------|----------|-----------|-------------|--------------|
| 2022-01-24 14:10 | 45m | 45m | 1.61 | -2.77 |
| 2022-01-24 14:10 | 45m | 45m | 1.59 | -2.71 |
| 2022-01-24 14:10 | 45m | 45m | 1.54 | -2.69 |
| 2022-09-21 13:15 | 30m | 45m | 1.52 | -2.47 |
| 2022-01-24 14:10 | 45m | 45m | 1.69 | -2.47 |


## Analysis
The Goal Seek tool was configured to look for the distinct fingerprint of this event. Reviewing the timestamps above should confirm if the tool successfully identified the anomalous market behavior associated with the event.
