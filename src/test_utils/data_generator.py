import pandas as pd
import numpy as np
from datetime import timedelta

class MarketDataGenerator:
    def __init__(self, seed=None):
        if seed is not None:
            np.random.seed(seed)
        
    def generate_noise(self, start_date="2023-01-01", days=10, minutes_per_day=391, start_price=100.0, volatility=0.0005, start_time="08:30"):
        """
        Generates a DataFrame with random market data (Geometric Brownian Motion).
        """
        start_dt = pd.to_datetime(start_date)
        all_rows = []
        
        # Parse start_time
        h, m = map(int, start_time.split(':'))
        
        current_price = start_price
        
        for day_offset in range(days):
            current_date = start_dt + timedelta(days=day_offset)
            
            # Skip weekends logic could be added, but for simple tests we assume continuous days or just handle dates
            # Let's map to Mon-Fri if needed, but for now just sequential days
            
            # Create minute timestamps for the day
            # We must be careful not to create a naive timestamp if we want to match localization later
            # But here we just need a baseline.
            base_time = current_date.replace(hour=h, minute=m, second=0, microsecond=0)
            
            daily_prices = [current_price]
            # Generate returns
            returns = np.random.normal(0, volatility, minutes_per_day)
            
            for r in returns:
                current_price = current_price * (1 + r)
                daily_prices.append(current_price)
            
            # Remove the last one to match minutes_per_day
            daily_prices = daily_prices[:-1]
            
            # Volume noise
            daily_volume = np.random.lognormal(10, 1, minutes_per_day).astype(int)
            
            times = [base_time + timedelta(minutes=i) for i in range(minutes_per_day)]
            
            for t, p, v in zip(times, daily_prices, daily_volume):
                # Synthesize OHLC from the minute "price"
                # We'll just add tiny noise for H/L
                noise_hl = p * 0.0005
                open_p = p
                close_p = p * (1 + np.random.normal(0, volatility/2))
                high_p = max(open_p, close_p) + abs(np.random.normal(0, noise_hl))
                low_p = min(open_p, close_p) - abs(np.random.normal(0, noise_hl))
                
                all_rows.append({
                    'date': t,
                    'open': open_p,
                    'high': high_p,
                    'low': low_p,
                    'close': close_p,
                    'volume': v
                })
                
            current_price = daily_prices[-1]

        df = pd.DataFrame(all_rows)
        return df

    def inject_pattern(self, df, index, pattern_type="bump_slide", bump_len=10, slide_len=10, bump_pct=0.02, slide_pct=-0.02, volume_mult=5.0):
        """
        Injects a deterministic pattern into the DataFrame starting at `index`.
        """
        if index + bump_len + slide_len >= len(df):
            raise ValueError("Pattern exceeds dataframe length")

        start_price = df.iloc[index]['open']
        
        # --- BUMP PHASE ---
        # Linearly increase price to target
        target_bump_price = start_price * (1 + bump_pct)
        bump_prices = np.linspace(start_price, target_bump_price, bump_len + 1)[:-1] # Exclude last to smooth transition
        
        for i in range(bump_len):
            idx = index + i
            p = bump_prices[i]
            # Set OHLC tightly around this linear path
            df.at[idx, 'open'] = p
            df.at[idx, 'close'] = bump_prices[i+1] if i < len(bump_prices)-1 else target_bump_price
            df.at[idx, 'high'] = max(df.at[idx, 'open'], df.at[idx, 'close'])
            df.at[idx, 'low'] = min(df.at[idx, 'open'], df.at[idx, 'close'])
            # Inject High Volume
            df.at[idx, 'volume'] = int(df['volume'].mean() * volume_mult)

        # --- SLIDE PHASE ---
        peak_price = target_bump_price
        target_slide_price = peak_price * (1 + slide_pct)
        slide_prices = np.linspace(peak_price, target_slide_price, slide_len + 1)
        
        for i in range(slide_len):
            idx = index + bump_len + i
            p = slide_prices[i]
            # Set OHLC
            df.at[idx, 'open'] = p
            df.at[idx, 'close'] = slide_prices[i+1]
            df.at[idx, 'high'] = max(df.at[idx, 'open'], df.at[idx, 'close'])
            df.at[idx, 'low'] = min(df.at[idx, 'open'], df.at[idx, 'close'])
             # Inject High Volume (if desired, or keep normal)
            df.at[idx, 'volume'] = int(df['volume'].mean() * volume_mult)
            
        return df
