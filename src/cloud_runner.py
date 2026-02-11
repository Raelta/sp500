import json
import os
import pandas as pd
import streamlit as st
from datetime import time
from google.cloud import run_v2
from google.cloud import storage
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
        self._credentials = None

    def get_credentials(self):
        """
        Attempts to load credentials from st.secrets (cloud) or fallback to google.auth (local).
        """
        if self._credentials:
            return self._credentials

        # 1. Try Streamlit Secrets (for Cloud Deployment)
        try:
            if "gcp_service_account" in st.secrets:
                # Use the dictionary from secrets to create service account credentials
                info = dict(st.secrets["gcp_service_account"])
                self._credentials = service_account.Credentials.from_service_account_info(info)
                return self._credentials
        except Exception:
            # st.secrets can raise an exception if the file doesn't exist
            pass

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

    def check_credentials(self):
        """
        Verifies if credentials are available and provides advice if missing.
        """
        creds = self.get_credentials()
        if creds:
            return True, "Credentials found."
        
        return False, (
            "Google Cloud Credentials not found.\n\n"
            "**Locally:** Run 'gcloud auth application-default login' in your terminal.\n"
            "**Cloud:** Add your service account JSON to Streamlit Secrets as [gcp_service_account]."
        )

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

            return {
                "id": latest.name.split("/")[-1],
                "status": status,
                "start_time": latest.create_time,
                "is_running": is_running,
                "is_done": is_done
            }, None
        except Exception as e:
            return None, str(e)

    def run_job(self, job_name, config_dict):
        """
        Triggers a Cloud Run Job by updating its environment variables and then executing it.
        """
        ok, msg = self.check_credentials()
        if not ok:
            return False, msg

        config_json = json.dumps(config_dict, cls=CloudEncoder)
        parent = f"projects/{self.project_id}/locations/{self.region}"
        job_path = f"{parent}/jobs/{job_name}"
        
        try:
            # 1. Update the Job with new configuration
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
            
            update_operation = self.run_client.update_job(job=job)
            update_operation.result() 
            
            # 2. Execute the Job
            run_operation = self.run_client.run_job(name=job_path)
            
            return True, f"Job {job_name} updated and triggered successfully."
            
        except Exception as e:
            return False, f"Error: {str(e)}"

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
            return False, str(e)

    def generate_gcloud_command(self, job_name, config_dict):
        config_json = json.dumps(config_dict, cls=CloudEncoder)
        config_json_escaped = config_json.replace('"', '\\"')
        project_flag = f"--project {self.project_id}" if self.project_id else ""
        
        update_cmd = (
            f"gcloud beta run jobs update {job_name} "
            f"--region {self.region} {project_flag} "
            f"--set-env-vars \"^~^GOAL_SEEK_CONFIG={config_json_escaped}\""
        )
        
        execute_cmd = (
            f"gcloud beta run jobs execute {job_name} "
            f"--region {self.region} {project_flag}"
        )
        
        return f"{update_cmd} && {execute_cmd}"

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
