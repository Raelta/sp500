# The 2008 Financial Crisis (Extreme Sustained Volatility)

## Event Description
The fall of 2008 saw historic VIX levels, characterized by violent intraday selloffs immediately followed by massive short-covering rallies. (Looking for Drop -> Rebound)

## Goal Seek Parameters Used
- **Length: 10-60 mins, Bump: <= -4.0%, Slide: >= +4.0%**
- Command executed: `python goal_seek_cli.py --start-year 2008 --end-year 2008 --bump-len-start 10 --bump-len-end 60 --bump-len-step 10 --slide-len-start 10 --slide-len-end 60 --slide-len-step 10 --min-bump-threshold -4.0 --min-slide-threshold 4.0 --detailed --output 2008_crisis_test.csv`

## Visualizing the Best Match
```text
↘↘↘↘↘↘↘↘↘↘ (Bump: Down ~11.3 pts, 60m)
          ↗↗↗↗↗ (Slide: Up ~8.2 pts, 30m)
```

## Goal Seek Results
### Top 5 Matches Found

| Date | Bump Len | Slide Len | Bump Change | Slide Change |
|------|----------|-----------|-------------|--------------|
| 2008-10-09 14:08 | 60m | 30m | -11.31 | 8.15 |
| 2008-10-09 14:28 | 40m | 30m | -10.28 | 8.15 |
| 2008-10-09 14:58 | 10m | 30m | -8.65 | 8.15 |
| 2008-10-09 14:18 | 50m | 30m | -10.50 | 8.15 |
| 2008-10-09 14:38 | 30m | 30m | -9.44 | 8.15 |


## Analysis
The Goal Seek tool was configured to look for the distinct fingerprint of this event. Reviewing the timestamps above should confirm if the tool successfully identified the anomalous market behavior associated with the event.
