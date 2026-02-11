#!/bin/bash

# Configuration
PROJECT_ID="sp500-479009"
REGION="europe-west2"
JOB_NAME="sp500-goal-seek"
IMAGE_NAME="sp500-analyzer"
IMAGE_URI="gcr.io/$PROJECT_ID/$IMAGE_NAME"

echo "========================================================"
echo "   🚀 SP500 Analyzer - Cloud Deploy Script"
echo "========================================================"
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "Job:     $JOB_NAME"
echo "Image:   $IMAGE_URI"
echo "========================================================"

# 1. Build the Docker Image (using Cloud Build)
echo ""
echo "📦 Step 1: Building Docker Image with Cloud Build..."
echo "--------------------------------------------------------"
# We specifically use '.' to include the current directory context
# The .gcloudignore file will ensure 'catalog/' is included but other junk is ignored
gcloud builds submit --tag "$IMAGE_URI" . --project "$PROJECT_ID"

if [ $? -ne 0 ]; then
    echo "❌ Build failed. Aborting."
    exit 1
fi

echo "✅ Build successful!"

# 2. Update the Cloud Run Job
echo ""
echo "🔄 Step 2: Updating Cloud Run Job..."
echo "--------------------------------------------------------"

# Check if job exists first
if gcloud beta run jobs describe "$JOB_NAME" --project "$PROJECT_ID" --region "$REGION" > /dev/null 2>&1; then
    # Update existing job
    gcloud beta run jobs update "$JOB_NAME" \
        --image "$IMAGE_URI" \
        --region "$REGION" \
        --project "$PROJECT_ID" \
        --tasks 1 \
        --cpu 4 \
        --memory 8Gi
else
    # Create new job if it doesn't exist
    echo "Job not found. Creating new job..."
    gcloud beta run jobs create "$JOB_NAME" \
        --image "$IMAGE_URI" \
        --region "$REGION" \
        --project "$PROJECT_ID" \
        --tasks 1 \
        --cpu 4 \
        --memory 8Gi \
        --max-retries 0
fi

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed."
    exit 1
fi

echo ""
echo "🎉 Success! The job has been updated with the new image (including the catalog)."
echo "   You can now trigger searches from the Streamlit UI."
echo ""
