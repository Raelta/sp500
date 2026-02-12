#!/bin/bash

# Configuration
PROJECT_ID="sp500-479009"
BUCKET_NAME="sp500-goal-seek-results"

echo "========================================================"
echo "   📊 SP500 Analyzer - Catalog Update Script"
echo "========================================================"
echo "Project: $PROJECT_ID"
echo "Bucket:  $BUCKET_NAME"
echo "========================================================"

# Check if we should rebuild the catalog first
read -p "Do you want to rebuild the catalog locally before syncing? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🏗️  Rebuilding catalog..."
    python goal_seek_cli.py --build-catalog
    if [ $? -ne 0 ]; then
        echo "❌ Catalog build failed. Aborting sync."
        exit 1
    fi
fi

# Sync Catalog to GCS
echo ""
echo "📤 Syncing Catalog to GCS..."
echo "--------------------------------------------------------"
if [ -d "catalog" ]; then
    gcloud storage rsync -r catalog/ gs://$BUCKET_NAME/catalog/
    if [ $? -eq 0 ]; then
        echo "✅ Catalog synced successfully!"
    else
        echo "❌ Sync failed."
        exit 1
    fi
else
    echo "⚠️ Local catalog directory not found. Please build it first."
    exit 1
fi
