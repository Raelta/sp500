# COVID-19 Market Crash (Intraday Panic)

## Event Description
March 2020 featured extreme intraday moves. We look for massive intraday selloffs followed by continued violent selling or massive short-covering. (Looking for Drop -> Rebound)

## Goal Seek Parameters Used
- **Length: 10-60 mins, Bump: <= -3.0%, Slide: >= +3.0%**
- Command executed: `python goal_seek_cli.py --start-year 2020 --end-year 2020 --bump-len-start 10 --bump-len-end 60 --bump-len-step 10 --slide-len-start 10 --slide-len-end 60 --slide-len-step 10 --min-bump-threshold -3.0 --min-slide-threshold 3.0 --detailed --output covid_crash_test.csv`

## Visualizing the Best Match
```text
↘↘↘↘↘↘↘↘↘↘ (Bump: Down ~10.2 pts, 60m)
          ↗↗↗↗↗↗↗↗↗↗ (Slide: Up ~4.9 pts, 60m)
```

## Goal Seek Results
### Top 5 Matches Found

| Date | Bump Len | Slide Len | Bump Change | Slide Change |
|------|----------|-----------|-------------|--------------|
| 2020-03-13 15:12 | 60m | 60m | -10.17 | 4.86 |
| 2020-03-13 15:12 | 60m | 60m | -10.08 | 4.64 |
| 2020-03-13 15:12 | 60m | 60m | -9.77 | 4.53 |
| 2020-03-16 08:40 | 10m | 50m | -3.53 | 4.47 |
| 2020-03-13 14:51 | 50m | 50m | -9.09 | 4.47 |


## Analysis
The Goal Seek tool was configured to look for the distinct fingerprint of this event. Reviewing the timestamps above should confirm if the tool successfully identified the anomalous market behavior associated with the event.
