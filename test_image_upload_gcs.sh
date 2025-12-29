#!/bin/bash
# Test image upload to RESQ backend with Google Cloud Storage
# Usage: bash test_image_upload_gcs.sh

# Configuration
BASE_URL="http://localhost:8000/api"
STUDENT_TOKEN="0ae475f9cf39e1134b4003d17a2b1b9f47b1e386"
BEACON_ID="3e3f5319-b90a-4077-86b5-f81ce8e5b0a7"

# Path to your test image (UPDATE THIS!)
IMAGE_PATH="${1:-./test_image.jpg}"

# Check if image exists
if [ ! -f "$IMAGE_PATH" ]; then
    echo "❌ Error: Image file not found at: $IMAGE_PATH"
    echo "Usage: bash test_image_upload_gcs.sh /path/to/image.jpg"
    exit 1
fi

IMAGE_NAME=$(basename "$IMAGE_PATH")
IMAGE_SIZE=$(du -h "$IMAGE_PATH" | cut -f1)

echo "============================================================"
echo "Testing Image Upload with Google Cloud Storage"
echo "============================================================"
echo ""
echo "Base URL: $BASE_URL"
echo "Image File: $IMAGE_NAME"
echo "Image Size: $IMAGE_SIZE"
echo ""

# Test 1: Report incident with image
echo "[1] Uploading incident report with image..."
echo ""

REPORT_URL="$BASE_URL/incidents/report_incident/"

curl -v \
  -X POST "$REPORT_URL" \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -F "beacon_id=$BEACON_ID" \
  -F "description=Test incident with GCS upload" \
  -F "severity=MEDIUM" \
  -F "images=@$IMAGE_PATH"

echo ""
echo ""
echo "============================================================"
echo "✅ Test complete! Check the response above for the image URL"
echo "============================================================"
