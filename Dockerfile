FROM python:3.11-slim

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
# Ensure logs are sent directly to terminal without buffering
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip --root-user-action=ignore
RUN pip install --no-cache-dir -r requirements.txt --root-user-action=ignore
# Add GCP storage client for cloud_job
RUN pip install --no-cache-dir google-cloud-storage --root-user-action=ignore

# Copy source code
COPY src/ ./src/
COPY spy_data_25yr.parquet .
COPY cloud_job.py .
COPY precompute_validation.py .

# Pre-compute validation report to speed up app startup
RUN python precompute_validation.py

# Entry point
CMD ["python", "cloud_job.py"]
