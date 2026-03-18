import time
import sys
import urllib.request
from urllib.error import URLError, HTTPError

url = "https://raelta-hockey-stop-sp500.streamlit.app/"
print(f"Waiting 60 seconds for Streamlit deployment...")
time.sleep(60)

print(f"Polling {url} for successful deployment (Smoke Test)...")
max_retries = 24
retry_interval = 10
success = False

for i in range(max_retries):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.getcode()
            text = response.read().decode('utf-8', errors='ignore')
            
            if status_code == 200 and "SP500 Bump & Slide" in text:
                print(f"✅ Smoke test passed! App is deployed and returning expected title at {url}.")
                success = True
                break
            else:
                print(f"Attempt {i+1}/{max_retries}: App returned status {status_code}. Retrying in {retry_interval}s...")
    except Exception as e:
        print(f"Attempt {i+1}/{max_retries}: Error ({e}). Retrying in {retry_interval}s...")
    
    time.sleep(retry_interval)

if not success:
    print("❌ Smoke test failed! App did not become healthy in time.")
    sys.exit(1)
