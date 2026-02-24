#!/bin/bash

# Configuration
PROJECT_ID="sp500-479009"
REGION="europe-west2"
JOB_NAME="sp500-goal-seek"
IMAGE_NAME="sp500-analyzer"
IMAGE_URI="gcr.io/$PROJECT_ID/$IMAGE_NAME"
BUCKET_NAME="sp500-goal-seek-results"
GOOGLE_CHAT_WEBHOOK="https://chat.googleapis.com/v1/spaces/AAQAe5YYp6U/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=wqZhESTeAJnL7CatoWGEhEkITan5m1jcVfILWfAmAA0"

echo "========================================================"
echo "   🚀 SP500 Analyzer - Cloud Deploy Script"
echo "========================================================"
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "Job:     $JOB_NAME"
echo "Image:   $IMAGE_URI"
echo "Bucket:  $BUCKET_NAME"
echo "========================================================"

# Note: Catalog update is now handled by update_catalog.sh

# 1. Build the Docker Image (using Cloud Build)
echo ""
echo "📦 Step 1: Building Docker Image with Cloud Build..."
echo "--------------------------------------------------------"
# We specifically use '.' to include the current directory context
# The .gcloudignore file ensures 'catalog/' is EXCLUDED to speed up build
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

# Delete existing job to ensure clean state (removes old volume mounts)
echo "Recreating Cloud Run Job to ensure clean volume configuration..."
gcloud beta run jobs delete "$JOB_NAME" --project "$PROJECT_ID" --region "$REGION" --quiet 2>/dev/null || true

# Create new job
gcloud beta run jobs create "$JOB_NAME" \
    --image "$IMAGE_URI" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --tasks 1 \
    --cpu 8 \
    --memory 16Gi \
    --task-timeout 60m \
    --max-retries 0 \
    --set-env-vars "GOOGLE_CHAT_WEBHOOK=$GOOGLE_CHAT_WEBHOOK"

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed."
    exit 1
fi

echo ""
echo "🎉 Success! The job has been updated with the new image."
echo "   Note: If you need to update the catalog, run ./update_catalog.sh"
echo "   You can now trigger searches from the Streamlit UI."
echo ""
