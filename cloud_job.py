import os
import json
import time
import pandas as pd
import psutil
from datetime import datetime
from src.search_engine import GoalSeeker
from src.data_loader import DATASETS, DEFAULT_SYMBOL, load_data_uncached
from src.notifications import send_google_chat_notification

def log_memory(label=""):
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024 / 1024  # in MB
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [MEM] {label}: {mem:.2f} MB", flush=True)

def parse_job_config(config_str):
    if not config_str:
        return None

    # Strip gcloud escape prefix if present (e.g. ^~^ or ^:^)
    # Prefix format is ^DELIMITER^
    if config_str.startswith("^") and len(config_str) > 3 and config_str[2] == "^":
        config_str = config_str[3:]

    return json.loads(config_str)

def run_job():
    webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK")
    log_memory("Job Start")
    # Cloud Run Jobs provide configuration via environment variables or files
    # We'll expect a JSON string in GOAL_SEEK_CONFIG
    config_str = os.environ.get("GOAL_SEEK_CONFIG")
    
    config = parse_job_config(config_str)
    if not config:
        print("Error: GOAL_SEEK_CONFIG environment variable not set.")
        if webhook_url:
            send_google_chat_notification(webhook_url, "FAILURE", {"error": "GOAL_SEEK_CONFIG environment variable not set."})
        return
    
    # Params
    # New flow uses `symbol`; older configs may still pass `data_path`.
    symbol = config.get("symbol")
    if symbol and symbol in DATASETS:
        data_path = DATASETS[symbol]["path"]
    else:
        data_path = config.get("data_path", DATASETS[DEFAULT_SYMBOL]["path"])
        symbol = symbol or DEFAULT_SYMBOL
    include_extended_hours = bool(config.get("include_extended_hours", False))
    params_grid = config.get("params_grid")
    fixed_params = config.get("fixed_params")
    
    min_bumps = config.get("min_bumps", 0)
    user_label = config.get("user_label", "unknown")
    output_path = config.get("output_path", "/tmp/results.csv")
    fast_mode = config.get("fast_mode", False)
    max_combinations = config.get("max_combinations", None)
    
    # --- SEARCH ENGINE SELECTION ---
    # Unified Engine: GoalSeeker (In-Memory)
    optimization_mode = "GOAL_SEEKER_IN_MEMORY"
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Starting Cloud Job using In-Memory Engine", flush=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Symbol: {symbol} (extended_hours={include_extended_hours})", flush=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading raw data from {data_path}...", flush=True)

    try:
        # Use the symbol if registered (so extended-hours filtering applies);
        # otherwise fall back to the raw path.
        load_arg = symbol if symbol in DATASETS else data_path
        df = load_data_uncached(load_arg, include_extended_hours=include_extended_hours)
        df = df.drop_duplicates(subset=['date'], keep='first').reset_index(drop=True)
        log_memory("Data Loaded")
    except Exception as e:
        print(f"Error loading data: {e}")
        if webhook_url:
            send_google_chat_notification(webhook_url, "FAILURE", {"error": f"Error loading data: {str(e)}", "user_label": user_label})
        return

    seeker = GoalSeeker(df)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Search...", flush=True)
    
    def progress(msg, pct):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{pct*100:.1f}%] {msg}", flush=True)
    
    try:
        start_time = time.time()
        results = seeker.search(
            params_grid,
            fixed_params=fixed_params,
            min_bumps=min_bumps,
            progress_callback=progress
        )
        end_time = time.time()
        duration_sec = end_time - start_time
        
        log_memory("Search Complete")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Search complete. Found {len(results)} results in {duration_sec:.2f} seconds.")
        
        # Inject metadata into results for UI verification
        max_confidence = 0.0
        if not results.empty:
            results['optimization_mode'] = optimization_mode
            results['symbol'] = symbol
            
            # Calculate Max Confidence for Metadata
            if 'total_hits' in results.columns and 'total_bumps' in results.columns:
                # Avoid division by zero
                temp_conf = results.apply(
                    lambda x: (x['total_hits'] / x['total_bumps'] * 100) if x['total_bumps'] > 0 else 0.0, axis=1
                )
                # Add to results dataframe as well so it's in the CSV
                results['confidence'] = temp_conf
                max_confidence = temp_conf.max()
        
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
                            "symbol": symbol,
                            "include_extended_hours": include_extended_hours,
                            "params_grid": params_grid,
                            "fixed_params": fixed_params,
                            "min_bumps": min_bumps,
                            "result_blob": blob_name,
                            "total_results": len(results),
                            "max_confidence": max_confidence,
                            "optimization_mode": optimization_mode,
                            "duration_sec": duration_sec,
                            "memory_mb": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
                        }
                        
                        meta_blob = meta_bucket.blob(meta_blob_name)
                        meta_blob.upload_from_string(json.dumps(metadata), content_type='application/json')
                        print(f"Uploaded metadata to {metadata_output}")

                except Exception as e:
                    print(f"Error uploading to GCS: {e}")
                    # Don't fail the job for GCS upload failure, but log it.
                    # We might want to notify here too? Let's just notify success with a warning note if we wanted.

        # Send SUCCESS notification
        if webhook_url:
            send_google_chat_notification(webhook_url, "SUCCESS", {
                "User Label": user_label,
                "Results Found": len(results),
                "Duration": f"{duration_sec:.2f}s",
                "Max Confidence": f"{max_confidence:.2f}%"
            })

    except Exception as e:
        print(f"Job failed with exception: {e}")
        if webhook_url:
            send_google_chat_notification(webhook_url, "FAILURE", {
                "User Label": user_label,
                "Error": str(e)
            })
        raise e

if __name__ == "__main__":
    run_job()
