import os
import json
import pandas as pd
from datetime import datetime
from src.search_engine import GoalSeeker
from src.data_loader import load_data_uncached

def run_job():
    # Cloud Run Jobs provide configuration via environment variables or files
    # We'll expect a JSON string in GOAL_SEEK_CONFIG
    config_str = os.environ.get("GOAL_SEEK_CONFIG")
    if not config_str:
        print("Error: GOAL_SEEK_CONFIG environment variable not set.")
        return

    # Strip gcloud escape prefix if present (e.g. ^~^ or ^:^)
    # Prefix format is ^DELIMITER^
    if config_str.startswith("^") and len(config_str) > 3 and config_str[2] == "^":
        config_str = config_str[3:]

    config = json.loads(config_str)
    
    # Params
    data_path = config.get("data_path", "spy_data_25yr.parquet")
    params_grid = config.get("params_grid")
    fixed_params = config.get("fixed_params", {})
    
    # Deserialize time_range if it exists
    if 'time_range' in fixed_params:
        tr = fixed_params['time_range']
        if isinstance(tr, list) and len(tr) == 2:
            fixed_params['time_range'] = (
                datetime.strptime(tr[0], "%H:%M:%S").time(),
                datetime.strptime(tr[1], "%H:%M:%S").time()
            )
            
    min_bumps = config.get("min_bumps", 0)
    output_path = config.get("output_path", "/tmp/results.csv")
    
    print(f"Loading data: {data_path}")
    df = load_data_uncached(data_path)
    
    # Pre-clean duplicates as app does
    df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
    
    # Apply scope filters if present in fixed_params (normally handled by seeker, but good to be sure)
    # Actually GoalSeeker handles time_range and days_of_week if passed in fixed_params.
    
    print("Starting Search...")
    seeker = GoalSeeker(df)
    
    def progress(msg, pct):
        print(f"[{pct*100:.1f}%] {msg}")
        
    results = seeker.search(
        params_grid,
        fixed_params=fixed_params,
        min_bumps=min_bumps,
        progress_callback=progress
    )
    
    print(f"Search complete. Found {len(results)} results.")
    
    # Always save a file to avoid 404s on the client side
    results.to_csv(output_path, index=False)
    print(f"Results saved to {output_path}")
    
    # If running in GCP, we might want to upload this to GCS
    gcs_output = config.get("gcs_output_path")
    if gcs_output:
            try:
                from google.cloud import storage
                client = storage.Client()
                # parse gs://bucket/path
                bucket_name = gcs_output.replace("gs://", "").split("/")[0]
                blob_name = "/".join(gcs_output.replace("gs://", "").split("/")[1:])
                
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(output_path)
                print(f"Uploaded results to {gcs_output}")
            except Exception as e:
                print(f"Error uploading to GCS: {e}")

if __name__ == "__main__":
    run_job()
