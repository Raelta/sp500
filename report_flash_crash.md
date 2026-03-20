# The 2010 Flash Crash (Microsecond Reversals)

## Event Description
On May 6, 2010, the S&P 500 collapsed and rebounded massively. The fingerprint is extreme magnitude moves compressed into an incredibly short timeframe. (Looking for Drop -> Rebound)

## Goal Seek Parameters Used
- **Length: 5-40 mins, Bump: <= -4.0%, Slide: >= +4.0%**
- Command executed: `python goal_seek_cli.py --start-year 2010 --end-year 2010 --bump-len-start 5 --bump-len-end 40 --bump-len-step 5 --slide-len-start 5 --slide-len-end 40 --slide-len-step 5 --min-bump-threshold -4.0 --min-slide-threshold 4.0 --detailed --output flash_crash_test.csv`

## Visualizing the Best Match
```text
↘↘↘↘↘↘↘↘↘↘ (Bump: Down ~6.5 pts, 40m)
          ↗↗↗↗↗↗ (Slide: Up ~6.0 pts, 25m)
```

## Goal Seek Results
### Top 5 Matches Found

| Date | Bump Len | Slide Len | Bump Change | Slide Change |
|------|----------|-----------|-------------|--------------|
| 2010-05-06 13:06 | 40m | 25m | -6.47 | 6.05 |
| 2010-05-06 13:31 | 15m | 25m | -5.51 | 6.05 |
| 2010-05-06 13:16 | 30m | 25m | -6.15 | 6.05 |
| 2010-05-06 13:26 | 20m | 25m | -5.78 | 6.05 |
| 2010-05-06 13:36 | 10m | 25m | -5.06 | 6.05 |


## Analysis
The Goal Seek tool was configured to look for the distinct fingerprint of this event. Reviewing the timestamps above should confirm if the tool successfully identified the anomalous market behavior associated with the event.
