import time
import os
import json
import pandas as pd
from src.cloud_runner import CloudRunner

# Config
PROJECT_ID = "sp500-479009"
REGION = "europe-west2"
JOB_NAME = "sp500-goal-seek"
BUCKET_NAME = "sp500-goal-seek-results"

def run_diagnostic():
    print("--- 🛰️ Starting Cloud Flow Diagnostic ---")
    print(f"Project: {PROJECT_ID}")
    print(f"Region: {REGION}")
    print(f"Job: {JOB_NAME}")
    print(f"Bucket: {BUCKET_NAME}")

    runner = CloudRunner(project_id=PROJECT_ID, region=REGION)

    # 1. Check Credentials
    print("\n[STEP 1] Checking Credentials...")
    ok, msg = runner.check_credentials()
    if not ok:
        print(f"❌ AUTH FAILURE: {msg}")
        return
    print("✅ Auth OK.")

    # 2. Trigger Job (Small Grid)
    print("\n[STEP 2] Triggering Test Job...")
    test_config = {
        "params_grid": {
            "bump_len": [3, 4],
            "slide_len": [3, 4],
            "min_bump_vol": [0],
            "min_slide_vol": [0],
            "bump_up_pct": [0],
            "slide_up_pct": [0],
            "bump_threshold": [0.1], # Lenient thresholds
            "slide_threshold": [0.1]
        },
        "fixed_params": {
            "bump_thresh_type": "percent",
            "slide_thresh_type": "percent"
        },
        "min_bumps": 0,
        "gcs_output_path": f"gs://{BUCKET_NAME}/debug_results.csv"
    }
    
    success, msg = runner.run_job(JOB_NAME, test_config)
    if not success:
        print(f"❌ TRIGGER FAILURE: {msg}")
        return
    print(f"✅ {msg}")

    # 3. Monitor Status
    print("\n[STEP 3] Monitoring Progress...")
    max_wait = 300 # 5 minutes
    start_wait = time.time()
    last_status = None

    while (time.time() - start_wait) < max_wait:
        exec_info, error = runner.get_latest_execution(JOB_NAME)
        
        if error:
            print(f"⚠️ Status Check Error: {error}")
        elif exec_info:
            status = exec_info['status']
            if status != last_status:
                print(f"   - Current Status: {status} (ID: {exec_info['id']})")
                last_status = status
            
            if exec_info['is_done']:
                if status == "SUCCEEDED":
                    print("✅ Job finished successfully!")
                    break
                else:
                    print(f"❌ Job failed with status: {status}")
                    return
        
        time.sleep(10)
    else:
        print("❌ Diagnostic timed out waiting for job.")
        return

    # 4. Download Results
    print("\n[STEP 4] Downloading Results...")
    local_path = "debug_results.csv"
    if os.path.exists(local_path):
        os.remove(local_path)

    success, msg = runner.download_results(BUCKET_NAME, "debug_results.csv", local_path)
    if not success:
        print(f"❌ DOWNLOAD FAILURE: {msg}")
        print("💡 Hint: Check if the bucket exists and permissions allow 'storage.objects.get'.")
        return
    
    print(f"✅ {msg}")

    # 5. Verify Content
    print("\n[STEP 5] Verifying Content...")
    try:
        df = pd.read_csv(local_path)
        print(f"✅ Success! Loaded {len(df)} results from cloud.")
        print("\nTop Results:")
        print(df.head())
    except Exception as e:
        print(f"❌ VERIFICATION FAILURE: {e}")

    print("\n--- 🏁 Diagnostic Complete ---")

if __name__ == "__main__":
    run_diagnostic()
