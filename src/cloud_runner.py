import json
import os
import pandas as pd
import streamlit as st
from datetime import time
from google.cloud import run_v2
from google.cloud import storage
from google.cloud import logging as cloud_logging
import google.auth
from google.oauth2 import service_account

class CloudEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, time):
            return obj.strftime("%H:%M:%S")
        return super().default(obj)

class CloudRunner:
    """
    Handles interacting with Google Cloud Run Jobs and Storage via Client Libraries.
    Supports both local (ADC) and deployed (st.secrets) authentication.
    """
    def __init__(self, project_id, region="us-central1"):
        self.project_id = project_id
        self.region = region
        self._run_client = None
        self._exec_client = None
        self._storage_client = None
        self._logging_client = None
        self._credentials = None

    def get_credentials(self):
        """
        Attempts to load credentials from st.secrets (cloud) or fallback to google.auth (local).
        """
        if self._credentials:
            return self._credentials

        # 1. Try Streamlit Secrets (for Cloud Deployment)
        # We check for existence first to avoid catching and silencing file-not-found errors
        # on local dev environments where secrets.toml doesn't exist.
        try:
            if "gcp_service_account" in st.secrets:
                try:
                    # Use the dictionary from secrets to create service account credentials
                    info = dict(st.secrets["gcp_service_account"])
                    self._credentials = service_account.Credentials.from_service_account_info(info)
                    return self._credentials
                except Exception as e:
                    st.error(f"Failed to load credentials from 'gcp_service_account' in secrets: {e}")
                    # If the user explicitly provided secrets but they are bad, we don't want
                    # to silently fall back to ADC which might give a confusing error later.
                    return None
        except (KeyError, FileNotFoundError, RuntimeError):
            # st.secrets access can fail if not configured or file missing
            pass
        except Exception as e:
            st.warning(f"Unexpected error accessing st.secrets: {e}")

        # 2. Fallback to Local Auth (ADC)
        try:
            self._credentials, _ = google.auth.default()
            return self._credentials
        except Exception:
            return None

    @property
    def run_client(self):
        if self._run_client is None:
            creds = self.get_credentials()
            self._run_client = run_v2.JobsClient(credentials=creds)
        return self._run_client

    @property
    def exec_client(self):
        if self._exec_client is None:
            creds = self.get_credentials()
            self._exec_client = run_v2.ExecutionsClient(credentials=creds)
        return self._exec_client

    @property
    def storage_client(self):
        if self._storage_client is None:
            creds = self.get_credentials()
            self._storage_client = storage.Client(credentials=creds, project=self.project_id)
        return self._storage_client

    @property
    def logging_client(self):
        if self._logging_client is None:
            creds = self.get_credentials()
            self._logging_client = cloud_logging.Client(credentials=creds, project=self.project_id)
        return self._logging_client

    def _get_secrets_debug_info(self):
        """
        Safely gathers debug information about available Streamlit secrets.
        """
        available_secrets = []
        try:
            available_secrets = list(st.secrets.keys())
        except Exception:
            pass

        if available_secrets:
            return f"\n\n(Debug: Streamlit sees these secret keys: `{', '.join(available_secrets)}`)"
        return "\n\n(Debug: Streamlit sees NO secrets configured)"

    def check_credentials(self):
        """
        Verifies if credentials are available and provides advice if missing.
        """
        creds = self.get_credentials()
        if creds:
            return True, "Credentials found."

        secret_hint = self._get_secrets_debug_info()
        
        return False, (
            "Google Cloud Credentials not found.\n\n"
            "**Locally:** Run 'gcloud auth application-default login' in your terminal.\n"
            "**Cloud:** Add your service account JSON to Streamlit Secrets as `[gcp_service_account]`."
            f"{secret_hint}"
        )

    def _handle_error(self, e, job_path):
        """
        Centralized error handling for GCP calls to provide better advice.
        """
        error_str = str(e)
        if "metadata.google.internal" in error_str or "Compute Engine Metadata server" in error_str:
            secret_hint = self._get_secrets_debug_info()
            return (
                "Authentication Error: The app is trying to use the Google Metadata server but cannot reach it.\n\n"
                "**If you are running on Streamlit Cloud:** You must provide a service account key in Streamlit Secrets.\n"
                "Add your service account JSON to secrets as `[gcp_service_account]`.\n\n"
                "**If you are running locally:** Run `gcloud auth application-default login`."
                f"{secret_hint}"
            )
        return f"Cloud Error at {job_path}: {error_str}"

    def get_latest_execution(self, job_name):
        """
        Fetches the latest execution status for a given job.
        Returns (result_dict, error_msg).
        """
        ok, msg = self.check_credentials()
        if not ok:
            return None, msg

        parent = f"projects/{self.project_id}/locations/{self.region}"
        job_path = f"{parent}/jobs/{job_name}"
        
        try:
            # List executions, sorted by start time descending
            request = run_v2.ListExecutionsRequest(
                parent=job_path,
                page_size=1
            )
            page = self.exec_client.list_executions(request=request)
            
            # This might trigger the authentication call
            executions = list(page)
            if not executions:
                return None, "No executions found for this job."
                
            latest = executions[0]
            
            # Simplify status
            status = "UNKNOWN"
            is_running = False
            is_done = False
            
            if latest.reconciling:
                status = "RUNNING"
                is_running = True
            elif latest.succeeded_count > 0:
                status = "SUCCEEDED"
                is_done = True
            elif latest.failed_count > 0:
                status = "FAILED"
                is_done = True
            else:
                status = "PENDING"
                is_running = True

            # Determine duration
            duration_str = None
            if latest.create_time and latest.completion_time:
                duration = latest.completion_time - latest.create_time
                duration_str = f"{duration.total_seconds():.1f}s"

            return {
                "id": latest.name.split("/")[-1],
                "status": status,
                "start_time": latest.create_time,
                "completion_time": latest.completion_time,
                "duration": duration_str,
                "is_running": is_running,
                "is_done": is_done
            }, None
        except Exception as e:
            return None, self._handle_error(e, job_path)

    def run_job(self, job_name, config_dict):
        """
        Triggers a Cloud Run Job by updating its environment variables and then executing it.
        """
        st.info(f"Initiating cloud job: {job_name}...")
        
        ok, msg = self.check_credentials()
        if not ok:
            st.error(f"Credentials check failed: {msg}")
            return False, msg

        config_json = json.dumps(config_dict, cls=CloudEncoder)
        parent = f"projects/{self.project_id}/locations/{self.region}"
        job_path = f"{parent}/jobs/{job_name}"
        
        try:
            st.write(f"Step 1: Fetching job configuration for {job_name}...")
            job = self.run_client.get_job(name=job_path)
            
            env_vars = job.template.template.containers[0].env
            
            found = False
            for env in env_vars:
                if env.name == "GOAL_SEEK_CONFIG":
                    env.value = f"^~^{config_json}"
                    found = True
                    break
            
            if not found:
                env_vars.append(run_v2.EnvVar(name="GOAL_SEEK_CONFIG", value=f"^~^{config_json}"))
            
            st.write("Step 2: Updating job with new parameters...")
            update_operation = self.run_client.update_job(job=job)
            update_operation.result() 
            
            st.write("Step 3: Triggering execution...")
            run_operation = self.run_client.run_job(name=job_path)
            # Fetch the execution name from response if possible
            
            st.success(f"Execution started successfully.")
            return True, f"Job {job_name} triggered successfully."
            
        except Exception as e:
            friendly_msg = self._handle_error(e, job_path)
            # We don't st.error(friendly_msg) here anymore, 
            # as the caller (UI) is responsible for displaying the returned error.
            if friendly_msg.startswith("Cloud Error"):
                import traceback
                st.code(traceback.format_exc())
            return False, friendly_msg

    def download_results(self, bucket_name, source_blob_name, dest_path):
        """
        Downloads a result file from GCS.
        """
        ok, msg = self.check_credentials()
        if not ok:
            return False, msg

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(source_blob_name)
            blob.download_to_filename(dest_path)
            return True, f"Downloaded {source_blob_name} to {dest_path}"
        except Exception as e:
            return False, self._handle_error(e, f"GCS Bucket {bucket_name}")

    def list_blobs(self, bucket_name, prefix=None):
        """
        Lists all blobs in the bucket that begin with the prefix.
        """
        ok, msg = self.check_credentials()
        if not ok:
            return []

        try:
            bucket = self.storage_client.bucket(bucket_name)
            # This returns an iterator
            blobs = bucket.list_blobs(prefix=prefix)
            # Sort by name (timestamp is in name usually) descending to get latest first if named correctly
            # But the caller can sort. We just return the list.
            return [b.name for b in blobs]
        except Exception as e:
            # Silent fail or log? Better to log for debug but silent for UI
            print(f"Error listing blobs: {e}")
            return []

    def read_json_blob(self, bucket_name, blob_name):
        """
        Reads a JSON blob directly from GCS and returns the dict.
        """
        ok, msg = self.check_credentials()
        if not ok:
            return None

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            content = blob.download_as_text()
            return json.loads(content)
        except Exception as e:
            print(f"Error reading blob {blob_name}: {e}")
            return None

    def generate_gcloud_command(self, job_name, config_dict, wrap=False):
        config_json = json.dumps(config_dict, cls=CloudEncoder)
        config_json_escaped = config_json.replace('"', '\\"')
        project_flag = f"--project {self.project_id}" if self.project_id else ""
        
        sep = " \\\n    " if wrap else " "
        
        update_cmd = (
            f"gcloud beta run jobs update {job_name}{sep}"
            f"--region {self.region}{sep}"
            f"{project_flag}{sep}"
            f"--set-env-vars \"^~^GOAL_SEEK_CONFIG={config_json_escaped}\""
        )
        
        execute_cmd = (
            f"gcloud beta run jobs execute {job_name}{sep}"
            f"--region {self.region}{sep}"
            f"{project_flag}"
        )
        
        return f"{update_cmd}\n\n# AND THEN RUN:\n{execute_cmd}"

    def get_deploy_instructions(self, job_name, image_name):
        return f"""
# 1. Build the image in the Cloud
gcloud builds submit --tag gcr.io/{self.project_id}/{image_name} . --project {self.project_id}

# 2. Create the Cloud Run Job
gcloud beta run jobs create {job_name} \\
    --image gcr.io/{self.project_id}/{image_name} \\
    --tasks 1 \\
    --max-retries 0 \\
    --region {self.region} \\
    --cpu 4 --memory 8Gi \\
    --project {self.project_id}

# 3. Setup Local Auth (for UI buttons to work locally)
gcloud auth application-default login
"""

    def get_job_logs(self, job_name, execution_id, max_entries=50):
        """
        Fetches recent logs for a specific job execution.
        """
        ok, msg = self.check_credentials()
        if not ok:
            return msg

        try:
            # Filter for Cloud Run Job logs specific to this execution ID
            # Note: execution_id is the full resource name's last segment (e.g. "job-name-xyz")
            filter_str = (
                f'resource.type="cloud_run_job" AND '
                f'labels."run.googleapis.com/execution_name"="{execution_id}"'
            )
            
            entries = self.logging_client.list_entries(
                filter_=filter_str,
                order_by=cloud_logging.DESCENDING,
                page_size=max_entries
            )
            
            logs = []
            for entry in entries:
                timestamp = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else ""
                payload = entry.payload
                # Payload can be a string, or a dict (jsonPayload), or None
                if isinstance(payload, dict):
                    # Try to find a message field or dump the dict
                    msg = payload.get('message', str(payload))
                else:
                    msg = str(payload)
                
                logs.append(f"[{timestamp}] {msg}")
            
            if not logs:
                return "No logs found yet. (It may take a few seconds for logs to appear)"
                
            # Return reversed (oldest first) for readability
            return "\n".join(reversed(logs))
            
        except Exception as e:
            return self._handle_error(e, f"Logging for {execution_id}")
