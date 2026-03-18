#!/usr/bin/env python3
import subprocess
import sys
import time
import urllib.request
from urllib.error import URLError, HTTPError

def run_cmd(cmd, **kwargs):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, text=True, **kwargs)
    return result

def main():
    print("=== Starting Release Process ===")
    
    # 1. Stage all changes
    print("\n[1/6] Staging changes...")
    run_cmd(["git", "add", "."])

    # 2. Check if there are changes to commit
    diff_check = subprocess.run(["git", "diff", "--staged"], capture_output=True, text=True)
    if not diff_check.stdout.strip():
        print("No changes to commit. Exiting.")
        sys.exit(0)

    # 3. Run tests
    print("\n[2/6] Running tests to confirm they pass...")
    test_result = run_cmd(["pytest"])
    if test_result.returncode != 0:
        print("\n❌ Tests failed! Aborting release.")
        sys.exit(1)
    print("✅ Tests passed.")

    # 4. Generate commit message via Gemini CLI (if available)
    print("\n[3/6] Generating commit message based on changes...")
    commit_msg = ""
    try:
        gemini_result = subprocess.run(
            ["gemini", "-p", "Write a concise Conventional Commit message for this diff. Output ONLY the message without quotes or code blocks."],
            input=diff_check.stdout,
            capture_output=True,
            text=True
        )
        if gemini_result.returncode == 0 and gemini_result.stdout.strip():
            commit_msg = gemini_result.stdout.strip()
            print(f"Generated message via Gemini: {commit_msg}")
        else:
            print("Failed to generate commit message via gemini. Using default.")
            commit_msg = "chore: automated release update"
    except FileNotFoundError:
        print("gemini CLI not found. Using default commit message.")
        commit_msg = "chore: automated release update"

    # Clean up potentially markdown-wrapped responses
    if commit_msg.startswith("```"):
        commit_msg = commit_msg.split('\n')[1].strip()

    # 5. Commit and push
    print("\n[4/6] Committing changes...")
    commit_result = run_cmd(["git", "commit", "-m", commit_msg])
    if commit_result.returncode != 0:
        print("\n❌ Commit failed!")
        sys.exit(1)

    print("\n[5/6] Pushing to repository...")
    push_result = run_cmd(["git", "push"])
    if push_result.returncode != 0:
        print("\n❌ Push failed!")
        sys.exit(1)

    # 6. Wait for deployment and Smoke Test
    url = "https://raelta-hockey-stop-sp500.streamlit.app/"
    print(f"\n[6/6] Waiting 60 seconds for Streamlit deployment to process the new commit...")
    time.sleep(60)

    print(f"Polling {url} for successful deployment (Smoke Test)...")
    max_retries = 24  # 24 * 10s = 4 minutes total wait
    retry_interval = 10
    success = False

    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            return fp
        def http_error_301(self, req, fp, code, msg, headers):
            return fp
        def http_error_303(self, req, fp, code, msg, headers):
            return fp

    opener = urllib.request.build_opener(NoRedirectHandler)

    for i in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = opener.open(req, timeout=10)
            status_code = response.getcode()
            
            # Since the app requires Streamlit Community Auth, it returns a 303 Redirect.
            # If we receive this redirect or a 200 OK, the app is healthy.
            if status_code in (200, 303):
                print(f"\n✅ Smoke test passed! App is responsive and returning status {status_code} at {url}.")
                success = True
                break
            else:
                print(f"Attempt {i+1}/{max_retries}: App returned status {status_code}. Retrying in {retry_interval}s...")
        except Exception as e:
            print(f"Attempt {i+1}/{max_retries}: Error ({e}). Retrying in {retry_interval}s...")
        
        time.sleep(retry_interval)

    if not success:
        print("\n❌ Smoke test failed! App did not become healthy in time.")
        sys.exit(1)

    print("\n🎉 Release completed successfully!")

if __name__ == "__main__":
    main()
