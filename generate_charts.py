import pandas as pd
import matplotlib.pyplot as plt
import os

# Load data
df = pd.read_parquet('spy_data_25yr.parquet')
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

events = [
    {
        "id": "flash_crash",
        "title": "2010 Flash Crash",
        "start": "2010-05-06 12:30",
        "end": "2010-05-06 14:30"
    },
    {
        "id": "2008_crisis",
        "title": "2008 Financial Crisis Climax",
        "start": "2008-10-09 13:30",
        "end": "2008-10-09 15:30"
    },
    {
        "id": "covid_crash",
        "title": "COVID-19 Panic (March 13)",
        "start": "2020-03-13 14:00",
        "end": "2020-03-13 15:59"
    },
    {
        "id": "fomc_whipsaw",
        "title": "2022 FOMC Whipsaw",
        "start": "2022-01-24 13:30",
        "end": "2022-01-24 15:30"
    }
]

os.makedirs('charts', exist_ok=True)

plt.style.use('dark_background')

for event in events:
    # Slice data
    data = df.loc[event['start']:event['end']]
    
    if data.empty:
        print(f"No data for {event['title']}")
        continue
        
    plt.figure(figsize=(10, 5))
    plt.plot(data.index, data['close'], color='#00ff00', linewidth=2)
    plt.title(f"Market Action: {event['title']}", fontsize=14, color='white')
    plt.xlabel("Time", fontsize=10)
    plt.ylabel("SPY Price", fontsize=10)
    plt.grid(True, alpha=0.2)
    
    # Save chart
    filename = f"charts/{event['id']}.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Generated {filename}")
