import json
import subprocess
import os
from datetime import time

class CloudEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, time):
            return obj.strftime("%H:%M:%S")
        return super().default(obj)

class CloudRunner:
    """
    Handles triggering Google Cloud Run Jobs.
    """
    def __init__(self, project_id=None, region="us-central1"):
        self.project_id = project_id
        self.region = region

    def generate_gcloud_command(self, job_name, config_dict):
        """
        Generates a gcloud command that the user can run manually.
        """
        config_json = json.dumps(config_dict, cls=CloudEncoder)
        # Escape double quotes for shell
        config_json_escaped = config_json.replace('"', '\\"')
        
        cmd = [
            "gcloud beta run jobs execute",
            job_name,
            f"--region {self.region}",
            f"--set-env-vars \"GOAL_SEEK_CONFIG={config_json_escaped}\""
        ]
        if self.project_id:
            cmd.append(f"--project {self.project_id}")
            
        return " ".join(cmd)

    def run_job(self, job_name, config_dict):
        """
        Attempts to run the job using subprocess (requires gcloud auth).
        """
        cmd = self.generate_gcloud_command(job_name, config_dict)
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)

    def get_deploy_instructions(self, job_name, image_name):
        """
        Instructions for the user to build and deploy the job.
        """
        return f"""
# 1. Build the image in the Cloud (No local Docker needed)
gcloud builds submit --tag gcr.io/{self.project_id}/{image_name} . --project {self.project_id}

# 2. Create the Cloud Run Job
gcloud beta run jobs create {job_name} \\
    --image gcr.io/{self.project_id}/{image_name} \\
    --tasks 1 \\
    --max-retries 0 \\
    --region {self.region} \\
    --cpu 4 --memory 8Gi \\
    --project {self.project_id}

# (Optional) After step 2, you can execute it from the UI or via:
# gcloud beta run jobs execute {job_name} --region {self.region} --project {self.project_id}
"""
