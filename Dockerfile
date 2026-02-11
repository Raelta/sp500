FROM python:3.9-slim

WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Add GCP storage client for cloud_job
RUN pip install --no-cache-dir google-cloud-storage

# Copy source code
COPY src/ ./src/
COPY spy_data_25yr.parquet .
COPY cloud_job.py .

# Entry point
CMD ["python", "cloud_job.py"]
