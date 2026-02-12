import os
import json
import time
import pandas as pd
from datetime import datetime
from src.search_engine import GoalSeeker
from src.catalog_search import CatalogSearcher
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
    
    min_bumps = config.get("min_bumps", 0)
    user_label = config.get("user_label", "unknown")
    output_path = config.get("output_path", "/tmp/results.csv")
    
    # --- SEARCH ENGINE SELECTION ---
    # Check if pre-built catalog exists (Use env var for mount point)
    catalog_dir = os.environ.get("CATALOG_DIR", "catalog")
    optimization_mode = "NONE"
    
    # Debug: Check if catalog dir exists
    if os.path.exists(catalog_dir):
        print(f"Checking catalog in: {catalog_dir}")
    else:
        print(f"Catalog directory not found at: {catalog_dir}")

    if os.path.exists(os.path.join(catalog_dir, "metadata.npz")):
        print(f"✅ Pre-built catalog found in /{catalog_dir}. Using CatalogSearcher optimization.")
        # Debug: list files in catalog to verify upload
        try:
            files = os.listdir(catalog_dir)
            print(f"📁 Catalog directory contents: {files}")
        except Exception: pass
        seeker = CatalogSearcher(catalog_dir=catalog_dir)
        optimization_mode = "CATALOG"
    else:
        print(f"⚠️ Catalog not found. Loading raw data from {data_path} and using GoalSeeker.")
        df = load_data_uncached(data_path)
        # Pre-clean duplicates as app does
        df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
        seeker = GoalSeeker(df)
    
    print("Starting Search...", flush=True)
    
    def progress(msg, pct):
        print(f"[{pct*100:.1f}%] {msg}", flush=True)
    
    start_time = time.time()
    results = seeker.search(
        params_grid,
        min_bumps=min_bumps,
        progress_callback=progress
    )
    end_time = time.time()
    duration_sec = end_time - start_time
    
    print(f"Search complete. Found {len(results)} results in {duration_sec:.2f} seconds.")
    
    # Inject metadata into results for UI verification
    if not results.empty:
        results['optimization_mode'] = optimization_mode
    
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

                # Upload Metadata if requested
                metadata_output = config.get("metadata_output_path")
                if metadata_output:
                    # reuse client/bucket if same bucket (likely)
                    meta_bucket_name = metadata_output.replace("gs://", "").split("/")[0]
                    meta_blob_name = "/".join(metadata_output.replace("gs://", "").split("/")[1:])
                    
                    if meta_bucket_name == bucket_name:
                        meta_bucket = bucket
                    else:
                        meta_bucket = client.bucket(meta_bucket_name)
                        
                    metadata = {
                        "timestamp": datetime.now().isoformat(),
                        "user_label": user_label,
                        "params_grid": params_grid,
                        "min_bumps": min_bumps,
                        "result_blob": blob_name,
                        "total_results": len(results),
                        "optimization_mode": optimization_mode,
                        "duration_sec": duration_sec
                    }
                    
                    meta_blob = meta_bucket.blob(meta_blob_name)
                    meta_blob.upload_from_string(json.dumps(metadata), content_type='application/json')
                    print(f"Uploaded metadata to {metadata_output}")

            except Exception as e:
                print(f"Error uploading to GCS: {e}")

if __name__ == "__main__":
    run_job()
